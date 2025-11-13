from __future__ import annotations

from datetime import datetime
from typing import List

from arthur_common.models.enums import RuleScope, RuleType
from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import Base, IsArchivable
from schemas.enums import RuleScoringMethod


class DatabaseRule(Base, IsArchivable):
    __tablename__ = "rules"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[RuleType] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    prompt_enabled: Mapped[bool] = mapped_column(Boolean)
    response_enabled: Mapped[bool] = mapped_column(Boolean)
    scoring_method: Mapped[RuleScoringMethod] = mapped_column(String)
    scope: Mapped[RuleScope] = mapped_column(String)
    rule_data: Mapped[List["DatabaseRuleData"]] = relationship(lazy="joined")


class DatabaseRuleData(Base):
    __tablename__ = "rule_data"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    rule_id: Mapped[str] = mapped_column(String, ForeignKey("rules.id"), index=True)
    data_type: Mapped[str] = mapped_column(String)
    data: Mapped[str] = mapped_column(String)
