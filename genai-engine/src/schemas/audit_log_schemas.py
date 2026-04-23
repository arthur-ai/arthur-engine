from pydantic import BaseModel


class RouteInfo(BaseModel):
    resource_name: str
    collection_field: str | None
    id_field: str
