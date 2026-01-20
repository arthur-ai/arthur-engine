import json
import logging

from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import SecretStr
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

from dependencies import get_db_session
from repositories.model_provider_repository import ModelProviderRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import (
    AwsBedrockCredentials,
    GCPServiceAccountCredentials,
    User,
)
from schemas.request_schemas import PutModelProviderCredentials
from schemas.response_schemas import (
    ModelProviderList,
    ModelProviderModelList,
)
from utils.users import permission_checker

logger = logging.getLogger(__name__)

model_provider_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@model_provider_routes.put(
    "/model_providers/{provider}",
    summary="Set the configuration for a model provider.",
    description="Set the configuration for a model provider. Optionally upload a GCP service account JSON credentials file or bedrock credentials",
    status_code=HTTP_201_CREATED,
    responses={
        HTTP_201_CREATED: {"description": "Configuration set"},
        HTTP_400_BAD_REQUEST: {
            "description": "Invalid JSON file or missing required fields",
        },
    },
    tags=["Model Providers"],
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_WRITE.value)
async def set_model_provider(
    provider: ModelProvider,
    project_id: str | None = Form(None),
    region: str | None = Form(None),
    api_key: str | None = Form(None),
    aws_access_key_id: str | None = Form(None),
    aws_secret_access_key: str | None = Form(None),
    aws_bedrock_runtime_endpoint: str | None = Form(None),
    aws_role_name: str | None = Form(None),
    aws_session_name: str | None = Form(None),
    credentials_file: UploadFile | None = File(
        None,
        description="Optional JSON file containing GCP service account credentials",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """Set the configuration for a model provider"""
    provider_credentials = PutModelProviderCredentials(
        project_id=project_id,
        region=region,
        api_key=api_key,
    )

    try:
        repo = ModelProviderRepository(db_session)
        repo.validate_model_provider_credentials(
            provider=provider,
            provider_credentials=provider_credentials,
            has_aws_access_key_id=aws_access_key_id is not None,
            has_aws_secret_access_key=aws_secret_access_key is not None,
            has_credentials_file=credentials_file is not None,
        )

        # Extract vertex credentials if provided
        vertex_credentials = None
        if credentials_file is not None:
            # Validate file type
            if credentials_file.content_type != "application/json":
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail=f"File: {credentials_file.content_type} must be a JSON file",
                )

            # Read and parse the uploaded JSON file
            content = await credentials_file.read()
            credentials_data = json.loads(content)
            vertex_credentials = GCPServiceAccountCredentials.model_validate(
                credentials_data,
            )

        aws_bedrock_credentials = AwsBedrockCredentials(
            aws_access_key_id=(
                SecretStr(aws_access_key_id) if aws_access_key_id else None
            ),
            aws_secret_access_key=(
                SecretStr(aws_secret_access_key) if aws_secret_access_key else None
            ),
            aws_bedrock_runtime_endpoint=(
                SecretStr(aws_bedrock_runtime_endpoint)
                if aws_bedrock_runtime_endpoint
                else None
            ),
            aws_role_name=SecretStr(aws_role_name) if aws_role_name else None,
            aws_session_name=SecretStr(aws_session_name) if aws_session_name else None,
        )

        repo.set_model_provider_credentials(
            provider=provider,
            api_key=provider_credentials.api_key,
            project_id=provider_credentials.project_id,
            region=provider_credentials.region,
            vertex_credentials=vertex_credentials,
            aws_bedrock_credentials=aws_bedrock_credentials,
        )
        return Response(status_code=HTTP_201_CREATED)
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@model_provider_routes.delete(
    "/model_providers/{provider}",
    summary="Disables the configuration for a model provider.",
    description="Disables the configuration for a model provider",
    tags=["Model Providers"],
    status_code=HTTP_204_NO_CONTENT,
    responses={HTTP_204_NO_CONTENT: {"description": "Provider deleted."}},
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_WRITE.value)
def delete_model_provider(
    provider: ModelProvider,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """Set the configuration for a model provider"""
    try:
        repo = ModelProviderRepository(db_session)
        repo.delete_model_provider_credentials(
            provider=provider,
        )
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()


@model_provider_routes.get(
    "/model_providers",
    summary="List the model providers.",
    description="Shows all model providers and if they're enabled.",
    tags=["Model Providers"],
    response_model=ModelProviderList,
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_READ.value)
def get_model_providers(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ModelProviderList:
    """Set the configuration for a model provider"""
    try:
        repo = ModelProviderRepository(db_session)
        return ModelProviderList(providers=repo.list_model_providers())
    finally:
        db_session.close()


@model_provider_routes.get(
    "/model_providers/{provider}/available_models",
    summary="List the models available from a provider.",
    description="Returns a list of the names of all available models for a provider.",
    tags=["Model Providers"],
    response_model=ModelProviderModelList,
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_READ.value)
def get_model_providers_available_models(
    provider: ModelProvider,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ModelProviderModelList:
    """Set the configuration for a model provider"""
    try:
        repo = ModelProviderRepository(db_session)
        return ModelProviderModelList(
            provider=provider,
            available_models=repo.list_models_for_provider(provider=provider),
        )
    finally:
        db_session.close()
