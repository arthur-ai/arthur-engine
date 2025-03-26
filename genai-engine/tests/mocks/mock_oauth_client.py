from authlib.integrations.starlette_client import StarletteOAuth2App
from tests.mocks.UserInfoMock import RealmAccess, UserInfo
from tests.unit.utils.test_utils import UserType
from utils import constants


class MockAuthClient(StarletteOAuth2App):
    def __init__(self):
        pass

    async def authorize_access_token(self, request, **kwargs):
        user_type = request.cookies.get("user_type")
        user_info = None
        if user_type == UserType.ADMIN:
            roles = [constants.TASK_ADMIN]
            realm_access = RealmAccess(roles=roles)
            user_info = UserInfo(
                sub="genai_engine_admin_user",
                given_name="test",
                family_name="test",
                email="test@arthur.ai",
                realm_access=realm_access,
            )
        if user_type == UserType.NON_ADMIN:
            roles = [constants.CHAT_USER]
            realm_access = RealmAccess(roles=roles)
            user_info = UserInfo(
                sub="genai_engine_user",
                given_name="test",
                family_name="test",
                email="test@arthur.ai",
                realm_access=realm_access,
            )
        if user_type == UserType.NO_NAME:
            roles = ["random_role"]
            realm_access = RealmAccess(roles=roles)
            user_info = UserInfo(
                sub="random_role_user",
                given_name="",
                family_name="",
                email="test@arthur.ai",
                realm_access=realm_access,
            )
        return {
            "access_token": "accessToken",
            "id_token": "id_token",
            "expires_in": 300,
            "userinfo": user_info.model_dump(),
        }
