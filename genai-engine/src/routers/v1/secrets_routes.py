import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from starlette.status import HTTP_204_NO_CONTENT

from dependencies import get_db_session
from repositories.secrets_repository import SecretsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from utils.users import permission_checker

logger = logging.getLogger(__name__)

secrets_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@secrets_routes.post(
    "/secrets/rotation",
    summary="Rotates secrets",
    description="This endpoint re-encrypts all the secrets in the database. The procedure calling this endpoint is as follows: \n"
    "First: Deploy a new version of the service with GENAI_ENGINE_SECRET_STORE_KEY set to a value like 'new-key::old-key'. \n"
    "Second: call this endpoint - all secrets will be re-encrypted with 'new-key'. \n"
    "Third: Deploy a new version of the service removing the old key from GENAI_ENGINE_SECRET_STORE_KEY, like 'new-key'. \n"
    "At this point all existing and new secrets will be managed by 'new-key'.",
    tags=["Secrets"],
    status_code=HTTP_204_NO_CONTENT,
    responses={HTTP_204_NO_CONTENT: {"description": "Secrets rotated."}},
)
@permission_checker(permissions=PermissionLevelsEnum.ROTATE_SECRETS.value)
def rotate_secrets(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """Rotates all secrets in the database"""
    try:
        secrets_repo = SecretsRepository(db_session)
        secrets_repo.rotate_secrets()
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()
