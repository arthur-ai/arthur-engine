from db_models.db_models import DatabaseRule
from fastapi import HTTPException
from arthur_common.models.enums import PaginationSortMethod, RuleScope, RuleType
from schemas.internal_schemas import Rule
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from utils import constants


class RuleRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_rule_by_id(self, rule_id: str) -> Rule:
        rule = self.db_session.get(DatabaseRule, rule_id)
        if not rule:
            raise HTTPException(
                status_code=404,
                detail=constants.ERROR_RULE_NOT_FOUND % rule_id,
            )
        return Rule._from_database_model(rule)

    def query_rules(
        self,
        rule_ids: list[str] = None,
        prompt_enabled: bool = None,
        response_enabled: bool = None,
        include_archived: bool = False,
        rule_scopes: list[RuleScope] = None,
        rule_types: list[RuleType] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page_size: int = None,
        page: int = 0,
    ):
        query = self.db_session.query(DatabaseRule)
        if rule_ids is not None:
            query = query.where(DatabaseRule.id.in_(rule_ids))
        if rule_scopes is not None:
            query = query.where(DatabaseRule.scope.in_(rule_scopes))
        if rule_types is not None:
            query = query.where(DatabaseRule.type.in_(rule_types))
        if prompt_enabled is not None:
            query = query.where(DatabaseRule.prompt_enabled.is_(prompt_enabled))
        if response_enabled is not None:
            query = query.where(DatabaseRule.response_enabled.is_(response_enabled))

        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseRule.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseRule.created_at))

        query = query.where(DatabaseRule.archived == include_archived)
        count = query.count()

        if page and page_size:
            query = query.offset(page * page_size)
        if page_size:
            query = query.limit(page_size)

        results = query.all()

        rules = [Rule._from_database_model(op) for op in results]
        return rules, count

    def create_rule(self, rule: Rule):
        self.db_session.add(rule._to_database_model())
        self.db_session.commit()

        return Rule._from_database_model(rule)

    def archive_rule(self, rule_id: str):
        rule = self.db_session.get(DatabaseRule, rule_id)
        if not rule:
            raise HTTPException(
                status_code=404,
                detail=constants.ERROR_RULE_NOT_FOUND % rule_id,
            )
        rule.archived = True
        self.db_session.commit()

    def delete_rule(self, rule_id: str):
        self.db_session.query(DatabaseRule).filter(DatabaseRule.id == rule_id).delete()
        self.db_session.commit()
