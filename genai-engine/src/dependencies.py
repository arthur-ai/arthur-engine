import logging
import os
from datetime import datetime
from typing import Generator, Optional
from uuid import UUID

# Disable tokenizers parallelism to avoid fork warnings in threaded environments
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from arthur_common.models.enums import MetricType, RuleType
from authlib.integrations.starlette_client import OAuth
from cachetools import TTLCache
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Query
from psycopg2 import OperationalError as Psycopg2OperationalError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from auth.api_key_validator_client import APIKeyValidatorClient
from auth.auth_constants import OAUTH_CLIENT_NAME
from auth.jwk_client import JWKClient
from clients.auth.abc_keycloak_client import ABCAuthClient
from clients.auth.keycloak_client import KeycloakClient
from clients.s3.azure_client import AzureBlobStorageClient
from clients.s3.InMemoryS3Client import InMemoryClient
from clients.s3.S3Client import S3Client
from config.config import Config
from config.database_config import DatabaseConfig
from config.keycloak_config import KeyCloakSettings
from db_models import Base
from metrics_engine import MetricsEngine
from repositories.configuration_repository import ConfigurationRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.enums import DocumentStorageEnvironment
from schemas.internal_schemas import (
    ApplicationConfiguration,
    DocumentStorageConfiguration,
    Task,
)
from schemas.request_schemas import (
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
    TransformListFilterRequest,
)
from scorer import (
    BinaryPIIDataClassifier,
    BinaryPIIDataClassifierV1,
    BinaryPromptInjectionClassifier,
    HallucinationClaimsV2,
    KeywordScorer,
    RegexScorer,
    ResponseRelevanceScorer,
    SensitiveDataCustomExamples,
    ToolSelectionCorrectnessScorer,
    ToxicityScorer,
    UserQueryRelevanceScorer,
)
from scorer.score import ScorerClient
from utils import constants
from utils.model_load import (
    CLAIM_CLASSIFIER_EMBEDDING_MODEL,
    PROMPT_INJECTION_MODEL,
    PROMPT_INJECTION_TOKENIZER,
    TOXICITY_MODEL,
    TOXICITY_TOKENIZER,
    USE_PII_MODEL_V2,
)
from utils.utils import (
    get_auth_metadata_uri,
    get_env_var,
    is_local_environment,
    seed_database,
)

SINGLETON_GRADER_LLM = None
SINGLETON_INFERENCE_REPOSITORY = None
SINGLETON_DB_ENGINE = None
SINGLETON_SCORER_CLIENT: ScorerClient | None = None
SINGLETON_METRICS_ENGINE = None
SINGLETON_JWK_CLIENT = None
SINGLETON_OAUTH_CLIENT: OAuth | None = None
API_KEY_CACHE = None
API_KEY_VALIDATOR_CLIENT = None
KEYCLOAK_CLIENT: ABCAuthClient | None = None

load_dotenv()


def load_env_vars():
    # Any rewriting / assertions should go in here
    pass


load_env_vars()

logger = logging.getLogger(__name__)


def get_keycloak_settings() -> KeyCloakSettings:
    return KeyCloakSettings(_env_file=os.environ.get("KEYCLOAK_CONFIG_PATH", ".env"))


def get_db_config() -> DatabaseConfig:
    return DatabaseConfig(_env_file=os.environ.get("DATABASE_CONFIG_PATH", ".env"))


def get_db_engine(db_config: DatabaseConfig | None = None):
    if db_config is None:
        db_config = get_db_config()
    global SINGLETON_DB_ENGINE
    if not SINGLETON_DB_ENGINE:
        engine = create_engine(
            **db_config.get_connection_params(),
        )
        SINGLETON_DB_ENGINE = engine
        if db_config.TEST_DATABASE:
            logger.info("Using in memory DB..")
            Base.metadata.create_all(engine)
            seed_session_class = sessionmaker(SINGLETON_DB_ENGINE)
            seed_session = seed_session_class()
            seed_database(seed_session)
            seed_session.close()

    return SINGLETON_DB_ENGINE


# Access singletons via these functions so test framework can override these via DI
def get_db_session() -> Generator[Session, None, None]:
    db_config = get_db_config()
    # Make unique session for each request thread
    session_maker = sessionmaker(get_db_engine(db_config))
    try:
        session = session_maker()
        yield session
    except (OperationalError, Psycopg2OperationalError) as e:
        logger.error(f"Error connecting to database: {db_config.url}")
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to database: {db_config.url}",
        ) from None
    finally:
        if session:
            session.close()


def get_application_config(session=Depends(get_db_session)) -> ApplicationConfiguration:
    config_repo = ConfigurationRepository(session)
    application_config = config_repo.get_configurations()

    return application_config


def get_scorer_client():
    global SINGLETON_SCORER_CLIENT
    if not SINGLETON_SCORER_CLIENT:
        if USE_PII_MODEL_V2:
            pii_data_classifier = BinaryPIIDataClassifier()
        else:
            pii_data_classifier = BinaryPIIDataClassifierV1()

        SINGLETON_SCORER_CLIENT = ScorerClient(
            {
                RuleType.MODEL_HALLUCINATION_V2: HallucinationClaimsV2(
                    sentence_transformer=CLAIM_CLASSIFIER_EMBEDDING_MODEL,
                ),
                RuleType.MODEL_SENSITIVE_DATA: SensitiveDataCustomExamples(),
                RuleType.PROMPT_INJECTION: BinaryPromptInjectionClassifier(
                    model=PROMPT_INJECTION_MODEL,
                    tokenizer=PROMPT_INJECTION_TOKENIZER,
                ),
                RuleType.PII_DATA: pii_data_classifier,
                RuleType.KEYWORD: KeywordScorer(),
                RuleType.REGEX: RegexScorer(),
                RuleType.TOXICITY: ToxicityScorer(
                    toxicity_model=TOXICITY_MODEL,
                    toxicity_tokenizer=TOXICITY_TOKENIZER,
                    harmful_request_model=None,
                    harmful_request_tokenizer=None,
                ),
                MetricType.QUERY_RELEVANCE: UserQueryRelevanceScorer(),
                MetricType.RESPONSE_RELEVANCE: ResponseRelevanceScorer(),
                MetricType.TOOL_SELECTION: ToolSelectionCorrectnessScorer(),
            },
        )
    return SINGLETON_SCORER_CLIENT


def get_metrics_engine() -> MetricsEngine:
    global SINGLETON_METRICS_ENGINE
    if not SINGLETON_METRICS_ENGINE:
        scorer_client = get_scorer_client()
        SINGLETON_METRICS_ENGINE = MetricsEngine(scorer_client)
    return SINGLETON_METRICS_ENGINE


def get_jwk_client():
    global SINGLETON_JWK_CLIENT
    if not SINGLETON_JWK_CLIENT:
        ingress_uri = get_env_var(
            constants.GENAI_ENGINE_INGRESS_URI_ENV_VAR,
            none_on_missing=True,
        )
        if ingress_uri:
            SINGLETON_JWK_CLIENT = JWKClient(ingress_uri)
        else:
            SINGLETON_JWK_CLIENT = None
    return SINGLETON_JWK_CLIENT


def get_oauth_client() -> OAuth:
    global SINGLETON_OAUTH_CLIENT
    if not SINGLETON_OAUTH_CLIENT:
        oauth = OAuth()
        client = oauth.register(
            name=OAUTH_CLIENT_NAME,
            server_metadata_url=get_auth_metadata_uri(),
            client_kwargs={"scope": "openid email profile"},
            client_id=get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR),
            client_secret=get_env_var(
                constants.GENAI_ENGINE_AUTH_CLIENT_SECRET_ENV_VAR,
            ),
        )
        SINGLETON_OAUTH_CLIENT = client
    return SINGLETON_OAUTH_CLIENT


def get_api_key_cache():
    # Creating a 10-second cache, the elements will expire after 10 seconds. As this cache is not centralized for all
    # genai-engine instances, every instance will have it's own cache. We don't need to kick elements out of the cache when
    # someone deactivates a key, as in worst case it will only be in cache for 10 seconds, after that it will grab
    # the valid keys from db again.
    global API_KEY_CACHE
    if not API_KEY_CACHE:
        API_KEY_CACHE = TTLCache(maxsize=Config.max_api_key_limit(), ttl=10)
    return API_KEY_CACHE


def get_api_key_validator_client(
    api_key_cache=Depends(get_api_key_cache),
) -> APIKeyValidatorClient:
    global API_KEY_VALIDATOR_CLIENT
    if not API_KEY_VALIDATOR_CLIENT:
        API_KEY_VALIDATOR_CLIENT = APIKeyValidatorClient(api_key_cache)
    return API_KEY_VALIDATOR_CLIENT


def get_keycloak_client() -> Generator[ABCAuthClient, None, None]:
    keycloak_settings = KeyCloakSettings(
        _env_file=os.environ.get("GENAI_ENGINE_CONFIG_FILE", ".env"),
    )
    keycloak_client = KeycloakClient(keycloak_settings)
    keycloak_client.get_genai_engine_realm_admin_connection()
    yield keycloak_client


def get_s3_client(
    application_config: ApplicationConfiguration = Depends(get_application_config),
):
    client = s3_client_from_config(application_config.document_storage_configuration)
    if not is_local_environment() and type(client) == InMemoryClient:
        raise HTTPException(
            status_code=400,
            detail="You cannot perform file operations without a valid document storage configuration",
        )
    return client


def s3_client_from_config(doc_storage_config: DocumentStorageConfiguration):
    if doc_storage_config is None:
        return InMemoryClient()
    elif (
        doc_storage_config.document_storage_environment
        == DocumentStorageEnvironment.AWS
    ):
        return S3Client(
            doc_storage_config.bucket_name,
            doc_storage_config.assumable_role_arn,
        )
    elif (
        doc_storage_config.document_storage_environment
        == DocumentStorageEnvironment.AZURE
    ):
        return AzureBlobStorageClient(
            doc_storage_config.connection_string,
            doc_storage_config.container_name,
        )
    else:
        raise NotImplementedError(doc_storage_config.document_storage_environment)


def get_task_repository(
    db_session: Session,
    application_config: ApplicationConfiguration,
) -> TaskRepository:
    return TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        application_config,
    )


def get_validated_agentic_task(
    task_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> Task:
    """Dependency that validates task exists and is agentic"""
    task_repo = get_task_repository(db_session, application_config)
    task = task_repo.get_task_by_id(str(task_id))

    if not task.is_agentic:
        raise HTTPException(status_code=400, detail="Task is not agentic")

    return task


def llm_get_versions_filter_parameters(
    model_provider: Optional[str] = Query(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    ),
    model_name: Optional[str] = Query(
        None,
        description="Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').",
    ),
    created_after: Optional[str] = Query(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    created_before: Optional[str] = Query(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    exclude_deleted: bool = Query(
        False,
        description="Whether to exclude deleted prompt versions from the results. Default is False.",
    ),
    min_version: Optional[int] = Query(
        None,
        ge=1,
        description="Minimum version number to filter on (inclusive).",
    ),
    max_version: Optional[int] = Query(
        None,
        ge=1,
        description="Maximum version number to filter on (inclusive).",
    ),
) -> LLMGetVersionsFilterRequest:
    """Create an LLMGetVersionsFilterRequest from query parameters."""
    return LLMGetVersionsFilterRequest(
        model_provider=model_provider,
        model_name=model_name,
        created_after=datetime.fromisoformat(created_after) if created_after else None,
        created_before=(
            datetime.fromisoformat(created_before) if created_before else None
        ),
        exclude_deleted=exclude_deleted,
        min_version=min_version,
        max_version=max_version,
    )


def llm_get_all_filter_parameters(
    llm_asset_names: Optional[list[str]] = Query(
        None,
        description="LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned",
    ),
    model_provider: Optional[str] = Query(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    ),
    model_name: Optional[str] = Query(
        None,
        description="Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').",
    ),
    created_after: Optional[str] = Query(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    created_before: Optional[str] = Query(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
) -> LLMGetAllFilterRequest:
    """Create a LLMGetAllFilterRequest from query parameters."""
    return LLMGetAllFilterRequest(
        llm_asset_names=llm_asset_names,
        model_provider=model_provider,
        model_name=model_name,
        created_after=datetime.fromisoformat(created_after) if created_after else None,
        created_before=(
            datetime.fromisoformat(created_before) if created_before else None
        ),
    )


def transform_list_filter_parameters(
    name: Optional[str] = Query(
        None,
        description="Name of the transform to filter on using partial matching.",
    ),
    created_after: Optional[str] = Query(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    created_before: Optional[str] = Query(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
) -> TransformListFilterRequest:
    """Create a LLMGetAllFilterRequest from query parameters."""
    return TransformListFilterRequest(
        name=name,
        created_after=datetime.fromisoformat(created_after) if created_after else None,
        created_before=(
            datetime.fromisoformat(created_before) if created_before else None
        ),
    )
