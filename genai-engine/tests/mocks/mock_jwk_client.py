from auth.jwk_client import JWKClient
from schemas.custom_exceptions import BadCredentialsException
from tests.mocks.UserInfoMock import RealmAccess, UserInfo
from utils import constants
from utils.users import get_user_info_from_payload


class MockJWKClient(JWKClient):
    def __init__(self):
        pass

    def validate(self, jwt_access_token: str):
        if jwt_access_token.startswith("user_"):
            sub = "00000000-1111-2222-3333-44444444"
            roles = [constants.TASK_ADMIN]
            realm_access = RealmAccess(roles=roles)
        elif jwt_access_token.startswith("genai_engine_user_"):
            sub = "00000000-1111-2222-3333-77777777"
            roles = [constants.VALIDATION_USER]
            realm_access = RealmAccess(roles=roles)
        elif jwt_access_token.startswith("admin_"):
            sub = "00000000-1111-2222-3333-55555555"
            roles = [constants.ORG_ADMIN]
            realm_access = RealmAccess(roles=roles)
        elif jwt_access_token.startswith("no_name_"):
            sub = "00000000-1111-2222-3333-66666666"
            roles = ["random_role"]
            realm_access = RealmAccess(roles=roles)
        elif jwt_access_token.startswith("auditor_"):
            sub = "00000000-1111-2222-3333-88888888"
            roles = [constants.ORG_AUDITOR]
            realm_access = RealmAccess(roles=roles)
        else:
            raise BadCredentialsException

        user_info = UserInfo(
            sub=sub,
            given_name="test",
            family_name="test",
            email=jwt_access_token,
            realm_access=realm_access,
        )
        return get_user_info_from_payload(user_info.model_dump())
