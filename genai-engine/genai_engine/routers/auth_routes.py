import logging
from base64 import b64encode

from auth import auth_constants
from auth.auth_constants import OAUTH_CLIENT_NAME
from auth.authorization_header_elements import get_token_from_bearer
from dependencies import get_oauth_client
from fastapi import APIRouter, Depends
from routers.route_handler import GenaiEngineRoute
from starlette.requests import Request
from starlette.responses import RedirectResponse
from utils import constants
from utils.users import get_user_info_from_payload
from utils.utils import get_auth_logout_uri, get_env_var, public_endpoint

logger = logging.getLogger()

auth_routes = APIRouter(
    prefix="/auth",
    route_class=GenaiEngineRoute,
    include_in_schema=False,
)


@auth_routes.get("/login")
@public_endpoint
async def login(request: Request, oauth_client=Depends(get_oauth_client)):
    redirect_uri = request.url_for("callback")
    return await oauth_client.authorize_redirect(request, redirect_uri)


@auth_routes.get("/config")
@public_endpoint
async def get_auth_config():
    return {
        "url": get_env_var(constants.GENAI_ENGINE_KEYCLOAK_HOST_URI_ENV_VAR),
        "realm": get_env_var(constants.GENAI_ENGINE_KEYCLOAK_REALM_ENV_VAR),
        "clientId": get_env_var(constants.GENAI_ENGINE_AUTH_CLIENT_ID_ENV_VAR),
    }


@auth_routes.get("/callback")
@public_endpoint
async def callback(
    request: Request,
    oauth_client=Depends(get_oauth_client),
):
    token = await oauth_client.authorize_access_token(request)

    # removing old unused session persisted as cookies
    request_url = str(request.url)
    key_string = f"_state_{OAUTH_CLIENT_NAME}"
    for k, v in list(request.session.items()):
        if (
            key_string in k and v["data"]["redirect_uri"] in request_url
        ):  # only removing session information related to this url after token exchange
            del request.session[k]

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        auth_constants.ACCESS_TOKEN_COOKIE_NAME,
        f"Bearer {token['access_token']}",
        max_age=token["expires_in"],
        httponly=True,
    )
    response.set_cookie(
        auth_constants.ID_TOKEN_COOKIE_NAME,
        f"Bearer {token['id_token']}",
        max_age=token["expires_in"],
        httponly=True,
    )
    user_info = token.get("userinfo")
    user = get_user_info_from_payload(user_info)
    encoded_user_json = b64encode(user.model_dump_json().encode("utf-8"))
    if user:
        response.set_cookie(
            auth_constants.USER_INFO_COOKIE_NAME,
            encoded_user_json.decode("utf-8"),
            max_age=token["expires_in"],
        )

    return response


@auth_routes.get("/logout")
@public_endpoint
def logout(request: Request):
    redirect_uri = request.url_for("logout_callback")
    id_bearer_token = request.cookies.get(auth_constants.ID_TOKEN_COOKIE_NAME)
    id_token = None
    try:
        id_token = get_token_from_bearer(id_bearer_token)
    except Exception as exc:
        logger.warning(
            "Can't extract ID token, will execute two step logout flow",
            exc_info=True,
        )
    logout_uri = get_auth_logout_uri(str(redirect_uri), id_token)
    return RedirectResponse(logout_uri, status_code=302)


@auth_routes.get("/logout/callback")
@public_endpoint
def logout_callback(request: Request):
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(auth_constants.ACCESS_TOKEN_COOKIE_NAME)
    response.delete_cookie(auth_constants.ACCESS_TOKEN_COOKIE_NAME)
    response.delete_cookie(auth_constants.USER_CHAT_SESSION_ID_COOKIE_NAME)
    response.delete_cookie(auth_constants.USER_INFO_COOKIE_NAME)
    response.delete_cookie(auth_constants.ID_TOKEN_COOKIE_NAME)

    return response
