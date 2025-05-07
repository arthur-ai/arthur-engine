import logging
import os
from typing import Generator

from auth.api_key_validator_client import APIKeyValidatorClient
from auth.auth_constants import OAUTH_CLIENT_NAME
from auth.jwk_client import JWKClient
from authlib.integrations.starlette_client import OAuth
from cachetools import TTLCache
from clients.auth.abc_keycloak_client import ABCAuthClient
from clients.auth.keycloak_client import KeycloakClient
from clients.s3.azure_client import AzureBlobStorageClient
from clients.s3.InMemoryS3Client import InMemoryClient
from clients.s3.S3Client import S3Client
from config.config import Config
from config.database_config import DatabaseConfig
from config.keycloak_config import KeyCloakSettings
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from psycopg2 import OperationalError as Psycopg2OperationalError
from repositories.configuration_repository import ConfigurationRepository
from schemas.enums import DocumentStorageEnvironment, RuleType
from schemas.internal_schemas import (
    ApplicationConfiguration,
    DocumentStorageConfiguration,
)
from scorer import (
    BinaryPIIDataClassifier,
    BinaryPromptInjectionClassifier,
    HallucinationClaimsV2,
    KeywordScorer,
    RegexScorer,
    SensitiveDataCustomExamples,
    ToxicityScorer,
)
from scorer.score import ScorerClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from utils import constants
from utils.model_load import (
    CLAIM_CLASSIFIER_EMBEDDING_MODEL,
    PROMPT_INJECTION_MODEL,
    PROMPT_INJECTION_TOKENIZER,
    TOXICITY_MODEL,
    TOXICITY_TOKENIZER,
)
from utils.utils import (
    get_auth_metadata_uri,
    get_env_var,
    is_local_environment,
    seed_database,
)

from db_models.db_models import Base

from db_models.db_models import Base

from db_models.db_models import Base

SINGLETON_GRADER_LLM = None
SINGLETON_INFERENCE_REPOSITORY = None
SINGLETON_DB_ENGINE = None
SINGLETON_SCORER_CLIENT = None
SINGLETON_JWK_CLIENT = None
SINGLETON_OAUTH_CLIENT = None
API_KEY_CACHE = None
API_KEY_VALIDATOR_CLIENT = None
KEYCLOAK_CLIENT = None

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
def get_db_session():
    db_config = get_db_config()
    # Make unique session for each request thread
    session_maker = sessionmaker(get_db_engine(db_config))
    try:
        session = session_maker()
        session.execute(text("SELECT 1"))
        return session
    except (OperationalError, Psycopg2OperationalError) as e:
        logger.error(f"Error connecting to database: {db_config.url}")
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to database: {db_config.url}",
        ) from None


def get_application_config(session=Depends(get_db_session)) -> ApplicationConfiguration:
    config_repo = ConfigurationRepository(session)
    application_config = config_repo.get_configurations()

    return application_config


def get_scorer_client():
    global SINGLETON_SCORER_CLIENT
    if not SINGLETON_SCORER_CLIENT:
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
                RuleType.PII_DATA: BinaryPIIDataClassifier(),
                RuleType.KEYWORD: KeywordScorer(),
                RuleType.REGEX: RegexScorer(),
                RuleType.TOXICITY: ToxicityScorer(
                    toxicity_model=TOXICITY_MODEL,
                    toxicity_tokenizer=TOXICITY_TOKENIZER,
                    harmful_request_model=None,
                    harmful_request_tokenizer=None,
                ),
            },
        )
    return SINGLETON_SCORER_CLIENT


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


def get_oauth_client():
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
