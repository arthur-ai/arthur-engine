"""Helpers for engine models that extend arthur_common models with new fields."""

from typing import Any

from pydantic import BaseModel, model_validator


class AcceptsCommonModel(BaseModel):
    """Lets code that still builds the arthur_common model pass it where the
    engine model is expected."""

    @model_validator(mode="before")
    @classmethod
    def _from_common_model(cls, data: Any) -> Any:
        if isinstance(data, BaseModel) and not isinstance(data, cls):
            return data.model_dump()
        return data
