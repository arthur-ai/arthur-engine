from datetime import datetime
from typing import Annotated
from uuid import UUID

from arthur_common.models.request_schemas import (
    ChatDefaultTaskRequest,
    ChatRequest,
    FeedbackRequest,
    PromptValidationRequest,
    ResponseValidationRequest,
)
from arthur_common.models.response_schemas import (
    ChatDefaultTaskResponse,
    ChatDocumentContext,
    ChatResponse,
    ConversationBaseResponse,
    ExternalDocument,
    FileUploadResult,
)
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi_pagination import Page, Params
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response

from auth.oauth_validator import validate_token
from chat.chat import ArthurChat
from chat.embedding import EmbeddingModel
from clients.s3.S3Client import S3Client
from dependencies import (
    get_application_config,
    get_db_session,
    get_s3_client,
    get_scorer_client,
)
from repositories.configuration_repository import ConfigurationRepository
from repositories.documents_repository import DocumentRepository
from repositories.embedding_repository import EmbeddingRepository
from repositories.feedback_repository import save_feedback
from repositories.inference_repository import InferenceRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from repositories.tasks_rules_repository import TasksRulesRepository
from routers.route_handler import GenaiEngineRoute
from schemas.custom_exceptions import LLMContentFilterException
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, User, _serialize_datetime
from schemas.request_schemas import ApplicationConfigurationUpdateRequest
from scorer.score import ScorerClient
from utils import constants as constants
from utils.file_parsing import parse_file_words
from utils.users import permission_checker
from validation.prompt import validate_prompt
from validation.response import validate_response

app_chat_routes = APIRouter(
    prefix="/api/chat",
    route_class=GenaiEngineRoute,
    tags=["Chat"],
)


@app_chat_routes.post(
    "/files",
    include_in_schema=True,
    description="Upload files via form-data. Only PDF, CSV, TXT types accepted.",
    response_model=FileUploadResult,
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def upload_embeddings_file(
    file: UploadFile,
    current_user: Annotated[User, Depends(validate_token)],
    s3_client: S3Client = Depends(get_s3_client),
    db_session: Session = Depends(get_db_session),
    is_global: bool = False,
) -> FileUploadResult:
    try:
        if (
            file.content_type != "application/pdf"
            and file.content_type != "text/csv"
            and file.content_type != "text/plain"
        ):
            raise HTTPException(
                400,
                detail=constants.ERROR_INVALID_DOCUMENT_TYPE,
            )
        if not file.filename:
            raise HTTPException(
                400,
                detail="File name is required",
            )
        # Add the document to the database
        doc_repo = DocumentRepository(db_session, s3_client)
        doc = doc_repo.create_document(file, current_user.email, is_global)
        file = doc_repo.get_file(doc.id)
        parsed_words = parse_file_words(doc, file.file)

        # Create and add embedding to the database
        embedding_model = EmbeddingModel()
        embedding_repo = EmbeddingRepository(db_session, embedding_model)
        _ = embedding_repo.add_embeddings(parsed_words, doc.id)

        return FileUploadResult(
            id=doc.id,
            name=file.filename,  # type: ignore[arg-type]
            type=doc.type,
            word_count=len(parsed_words),
            success=True,
        )
    except:
        raise
    finally:
        db_session.close()


@app_chat_routes.get(
    "/files",
    description="List uploaded files. Only files that are global or owned by the caller are returned.",
    include_in_schema=True,
    response_model=list[ExternalDocument],
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def get_files(
    current_user: Annotated[User, Depends(validate_token)],
    s3_client: S3Client = Depends(get_s3_client),
    db_session: Session = Depends(get_db_session),
) -> list[ExternalDocument]:
    try:
        doc_repo = DocumentRepository(db_session, s3_client)
        docs = doc_repo.get_documents(current_user.email)

        return [d._to_response_model() for d in docs]
    except:
        raise
    finally:
        db_session.close()


@app_chat_routes.delete(
    "/files/{file_id}",
    description="Remove a file by ID. This action cannot be undone.",
    include_in_schema=True,
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def delete_file(
    file_id: UUID,
    current_user: Annotated[User, Depends(validate_token)],
    s3_client: S3Client = Depends(get_s3_client),
    db_session: Session = Depends(get_db_session),
) -> Response:
    try:
        doc_repo = DocumentRepository(db_session, s3_client)
        file = doc_repo.get_document_by_id(str(file_id))
        if file.owner_id != current_user.email:
            raise HTTPException(
                status_code=400,
                detail=f"File {file_id} not owned by {current_user.email}. Can't delete file.",
            )
        doc_repo.delete_document(str(file_id))
        return Response(status_code=status.HTTP_200_OK)
    except:
        raise
    finally:
        db_session.close()


@app_chat_routes.post(
    "/",
    operation_id="chat_request",
    description="Chat request for Arthur Chat",
    include_in_schema=True,
    response_model=ChatResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def chat(
    body: ChatRequest,
    current_user: Annotated[User, Depends(validate_token)],
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> ChatResponse:
    try:
        # Get the relevant data repositories
        inference_repo = InferenceRepository(db_session)
        embedding_model = EmbeddingModel()
        embedding_repo = EmbeddingRepository(db_session, embedding_model)
        tasks_rules_repo = TasksRulesRepository(db_session)
        task_id = application_config.chat_task_id
        if not task_id:
            raise HTTPException(
                400,
                detail="Task ID is required",
            )
        task_rules = tasks_rules_repo.get_task_rules_ids_cached(task_id)
        rules_repo = RuleRepository(db_session)
        prompt_rules, _ = rules_repo.query_rules(
            rule_ids=task_rules,
            prompt_enabled=True,
        )
        response_rules, _ = rules_repo.query_rules(
            rule_ids=task_rules,
            response_enabled=True,
        )

        # Create the chat object
        chat_object = ArthurChat(
            inference_repo,
            embedding_repo,
            body.conversation_id,
            body.file_ids,
        )

        # Send the prompt to GenAI Engine
        retrieval_info = chat_object.retrieve_augmented_context(body.user_prompt)
        validation_prompt_request = validate_prompt(
            task_id=task_id,
            body=PromptValidationRequest(
                prompt=body.user_prompt,
                conversation_id=body.conversation_id,
                user_id=current_user.id,
            ),
            db_session=db_session,
            scorer_client=scorer_client,
            rules=prompt_rules,
        )

        try:
            # Get LLM response from the chat
            chat_response = chat_object.chat(
                user_query=body.user_prompt,
            )
        except LLMContentFilterException:
            return ChatResponse(
                inference_id=validation_prompt_request.inference_id,
                conversation_id=body.conversation_id,
                timestamp=_serialize_datetime(datetime.now()),
                retrieved_context=[
                    dc._to_response_model() for dc in retrieval_info.embeddings
                ],
                llm_response="The response was filtered due to the prompt triggering LLM provider content management "
                "policy. Please modify your prompt and retry.",
                prompt_results=validation_prompt_request.rule_results or [],
                response_results=[],
            )

        # Send response to GenAI Engine
        validation_response_request = validate_response(
            inference_id=validation_prompt_request.inference_id,
            body=ResponseValidationRequest(
                response=chat_response,
                context=(
                    retrieval_info.prompts_to_str()
                    if len(retrieval_info.embeddings) > 0
                    else None
                ),
            ),
            db_session=db_session,
            scorer_client=scorer_client,
            rules=response_rules,
        )

        inference_repo.save_inference_document_context(
            validation_response_request.inference_id,
            retrieval_info.embeddings,
        )

        return ChatResponse(
            inference_id=validation_prompt_request.inference_id,
            conversation_id=body.conversation_id,
            timestamp=_serialize_datetime(datetime.now()),
            retrieved_context=[
                dc._to_response_model() for dc in retrieval_info.embeddings
            ],
            llm_response=chat_response,
            prompt_results=validation_prompt_request.rule_results or [],
            response_results=validation_response_request.rule_results or [],
        )
    except Exception as err:
        raise err
    finally:
        db_session.close()


@app_chat_routes.get(
    "/context/{inference_id}",
    description="Get document context used for a past inference ID.",
    include_in_schema=True,
    response_model=list[ChatDocumentContext],
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def get_inference_document_context(
    inference_id: UUID,
    current_user: Annotated[User, Depends(validate_token)],
    db_session: Session = Depends(get_db_session),
) -> list[ChatDocumentContext]:
    try:
        inference_repo = InferenceRepository(db_session)
        embeddings = inference_repo.get_inference_document_context(str(inference_id))

        return [e._to_response_model() for e in embeddings]
    except:
        raise
    finally:
        db_session.close()


@app_chat_routes.post(
    "/feedback/{inference_id}",
    description="Post feedback for Arthur Chat.",
    include_in_schema=True,
    tags=["Chat"],
    status_code=status.HTTP_201_CREATED,
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def post_chat_feedback(
    body: FeedbackRequest,
    inference_id: UUID,
    current_user: Annotated[User, Depends(validate_token)],
    db_session: Session = Depends(get_db_session),
) -> Response:
    try:
        save_feedback(
            str(inference_id),
            body.target,
            body.score,
            body.reason or "",
            current_user.id,
            db_session,
        )
        return Response(status_code=status.HTTP_201_CREATED)
    except Exception as e:
        raise e
    finally:
        db_session.close()


@app_chat_routes.get(
    "/conversations",
    description="Get list of conversation IDs.",
    include_in_schema=True,
    responses={200: {"model": Page[ConversationBaseResponse]}},
)
@permission_checker(permissions=PermissionLevelsEnum.CHAT_WRITE.value)
def get_conversations(
    current_user: Annotated[User, Depends(validate_token)],
    db_session: Session = Depends(get_db_session),
    query_params: Params = Depends(),
) -> Page[ConversationBaseResponse]:
    inference_repo = InferenceRepository(db_session)
    return inference_repo.get_all_user_conversations(current_user.id, query_params)


@app_chat_routes.get(
    "/default_task",
    response_model=ChatDefaultTaskResponse,
    description="Get the default task for Arthur Chat.",
)
@permission_checker(permissions=PermissionLevelsEnum.APP_CONFIG_READ.value)
def get_default_task(
    current_user: Annotated[User, Depends(validate_token)],
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> ChatDefaultTaskResponse:
    if not application_config.chat_task_id:
        raise HTTPException(
            status_code=404,
            detail="No default task found",
        )
    return ChatDefaultTaskResponse(task_id=application_config.chat_task_id)


@app_chat_routes.put(
    "/default_task",
    response_model=ChatDefaultTaskResponse,
    description="Update the default task for Arthur Chat.",
)
@permission_checker(permissions=PermissionLevelsEnum.APP_CONFIG_WRITE.value)
def update_default_task(
    body: ChatDefaultTaskRequest,
    current_user: Annotated[User, Depends(validate_token)],
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> ChatDefaultTaskResponse:
    try:
        tasks_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        tasks_repo.get_db_task_by_id(body.task_id)
        config_repo = ConfigurationRepository(db_session)
        config_repo.update_configurations(
            ApplicationConfigurationUpdateRequest(chat_task_id=body.task_id),
        )
        return ChatDefaultTaskResponse(task_id=body.task_id)
    except Exception as e:
        raise e
    finally:
        db_session.close()
