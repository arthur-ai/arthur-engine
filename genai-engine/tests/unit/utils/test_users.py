import pytest
from fastapi import HTTPException
from schemas.common_schemas import AuthUserRole
from schemas.internal_schemas import User
from utils.users import get_user_info_from_payload, permission_checker

pytest_plugins = ("pytest_asyncio",)


@pytest.mark.parametrize(
    "payload, expected_user",
    [
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
            },
            User(id="dummy_id", email="foo@example.com", roles=[]),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "given_name": "Foo",
            },
            User(id="dummy_id", email="foo@example.com", roles=[], first_name="Foo"),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "family_name": "Bar",
            },
            User(id="dummy_id", email="foo@example.com", roles=[], last_name="Bar"),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "given_name": "Foo",
                "family_name": "Bar",
            },
            User(
                id="dummy_id",
                email="foo@example.com",
                roles=[],
                first_name="Foo",
                last_name="Bar",
            ),
        ),
        (
            {
                "sub": "dummy_id",
                "email": "foo@example.com",
                "given_name": "Foo",
                "family_name": "Bar",
                "realm_access": {
                    "roles": [
                        "offline_access",
                        "uma_authorization",
                        "default-roles-genai-engine",
                    ],
                },
            },
            User(
                id="dummy_id",
                email="foo@example.com",
                first_name="Foo",
                last_name="Bar",
                roles=[
                    AuthUserRole(
                        id="0",
                        name="offline_access",
                        description="DUMMY",
                        composite=True,
                    ),
                    AuthUserRole(
                        id="1",
                        name="uma_authorization",
                        description="DUMMY",
                        composite=True,
                    ),
                    AuthUserRole(
                        id="2",
                        name="default-roles-genai-engine",
                        description="DUMMY",
                        composite=True,
                    ),
                ],
            ),
        ),
    ],
)
@pytest.mark.unit_tests
def test_get_user_info_from_payload(payload, expected_user):
    user = get_user_info_from_payload(payload)

    assert user == expected_user


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_permission_checker():
    @permission_checker(set(["TEST"]))
    def x(current_user) -> bool:
        return True

    result = await x(
        current_user=User(
            id="dummy_id",
            email="foo@example.com",
            first_name="Foo",
            last_name="Bar",
            roles=[
                AuthUserRole(id="0", name="test", description="DUMMY", composite=True),
            ],
        ),
    )
    assert result is True


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_permission_checker_user_unauthorized():
    @permission_checker(set(["TEST"]))
    def x(current_user) -> bool:
        return True

    with pytest.raises(HTTPException) as error_info:
        _ = await x(current_user=None)
    assert error_info.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.unit_tests
async def test_permission_checker_user_forbidden():
    @permission_checker(set(["ANOTHER_TEST"]))
    def x(current_user) -> bool:
        return True

    with pytest.raises(HTTPException) as error_info:
        _ = await x(
            current_user=User(
                id="dummy_id",
                email="foo@example.com",
                first_name="Foo",
                last_name="Bar",
                roles=[
                    AuthUserRole(
                        id="0",
                        name="test",
                        description="DUMMY",
                        composite=True,
                    ),
                ],
            ),
        )
    assert error_info.value.status_code == 403
