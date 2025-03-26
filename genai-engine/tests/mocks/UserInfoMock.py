from typing import Optional

from pydantic import BaseModel


class RealmAccess(BaseModel):
    roles: Optional[list[str]]


class UserInfo(BaseModel):
    sub: str
    given_name: Optional[str]
    family_name: Optional[str]
    email: Optional[str]
    realm_access: Optional[RealmAccess]
