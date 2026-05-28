from datetime import datetime
from itertools import groupby
from typing import Any, Optional
from uuid import UUID

from arthur_common.models.enums import TokenUsageScope
from arthur_common.models.response_schemas import TokenUsageCount, TokenUsageResponse
from pydantic import BaseModel
from sqlalchemy import func, select, union
from sqlalchemy.orm import Session
from sqlalchemy.sql import CompoundSelect

from db_models import (
    DatabaseInference,
    DatabaseInferencePrompt,
    DatabaseInferenceResponse,
    DatabasePromptRuleResult,
    DatabaseResponseRuleResult,
    DatabaseRule,
)


class TokenQueryRow(BaseModel):
    rule_type: str
    task_id: Optional[str]
    user_input_tokens: int
    prompt_tokens: int
    completion_tokens: int


class UsageRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_tokens_usage(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        group_by: list[TokenUsageScope] = [TokenUsageScope.RULE_TYPE],
        org_scope: Optional[UUID] = None,
    ) -> list[TokenUsageResponse]:
        rows = self.run_tokens_query(start_time, end_time, org_scope=org_scope)

        def get_group_key(row: TokenQueryRow) -> int:
            key: list[str] = []
            for group in group_by:
                if group == TokenUsageScope.RULE_TYPE:
                    key.append(row.rule_type)
                elif group == TokenUsageScope.TASK:
                    key.append(row.task_id or "")
            return hash(tuple(key))

        usages = []
        # itertools.groupby groups contiguous blocks of equal keys, so the rows must be sorted by the group key
        rows = sorted(rows, key=lambda x: get_group_key(x))
        for _, group_iter in groupby(rows, lambda x: get_group_key(x)):
            group_list = list(group_iter)
            counter = TokenUsageCount(
                inference=0,
                eval_prompt=0,
                eval_completion=0,
                user_input=0,
                prompt=0,
                completion=0,
            )
            for row in group_list:
                counter.inference += row.user_input_tokens
                counter.eval_prompt += row.prompt_tokens
                counter.eval_completion += row.completion_tokens
                # These are deprecated fields, but we keep them for backwards compatibility
                counter.user_input += row.user_input_tokens
                counter.prompt += row.prompt_tokens
                counter.completion += row.completion_tokens

            usage = TokenUsageResponse(count=counter)
            for scope in group_by:
                if scope == TokenUsageScope.RULE_TYPE:
                    usage.rule_type = group_list[0].rule_type
                elif scope == TokenUsageScope.TASK:
                    usage.task_id = group_list[0].task_id

            usages.append(usage)
        return usages

    def run_tokens_query(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        org_scope: Optional[UUID] = None,
    ) -> list[TokenQueryRow]:
        query = get_token_query_statement(start_time, end_time, org_scope=org_scope)

        grouped_prompt_tokens = self.db_session.execute(query).all()
        rows = [
            TokenQueryRow(
                rule_type=row[0],
                task_id=row[1],
                user_input_tokens=row[2],
                prompt_tokens=row[3],
                completion_tokens=row[4],
            )
            for row in grouped_prompt_tokens
        ]
        return rows


# Query result is a list of rows with columns (rule_type, task_id, input_tokens, prompt_tokens, response_tokens)
# There are at most 2*n*m rows (n = number of unique rule types, m = unique tasks (None included)) because there can be n rows per our 2 results tables
# (in reality some rules aren't applicable to prompts and vice versa with responses)
def get_token_query_statement(
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    org_scope: Optional[UUID] = None,
) -> CompoundSelect[Any]:
    prompt_subquery = (
        select(
            DatabaseRule.type,
            DatabaseInference.task_id,
            func.sum(DatabaseInferencePrompt.tokens).label("user_input_tokens"),
            func.sum(DatabasePromptRuleResult.prompt_tokens),
            func.sum(DatabasePromptRuleResult.completion_tokens),
        )
        .join(DatabaseRule)
        .join(DatabaseInferencePrompt)
        .join(DatabaseInference)
        .group_by(DatabaseRule.type, DatabaseInference.task_id)
    )
    response_subquery = (
        select(
            DatabaseRule.type,
            DatabaseInference.task_id,
            func.sum(DatabaseInferenceResponse.tokens).label("user_input_tokens"),
            func.sum(DatabaseResponseRuleResult.prompt_tokens),
            func.sum(DatabaseResponseRuleResult.completion_tokens),
        )
        .join(DatabaseRule)
        .join(DatabaseInferenceResponse)
        .join(DatabaseInference)
        .group_by(DatabaseRule.type, DatabaseInference.task_id)
    )

    # Tenant callers: filter both rule_result tables by their denormalized
    # org_id column (added by UP-4424 Migration 3). Admin (org_scope=None) sees
    # the whole engine's usage.
    if org_scope is not None:
        prompt_subquery = prompt_subquery.where(
            DatabasePromptRuleResult.org_id == org_scope,
        )
        response_subquery = response_subquery.where(
            DatabaseResponseRuleResult.org_id == org_scope,
        )

    if start_time:
        prompt_subquery = prompt_subquery.where(
            DatabasePromptRuleResult.created_at >= start_time,
        )
        response_subquery = response_subquery.where(
            DatabaseResponseRuleResult.created_at >= start_time,
        )

    if end_time:
        prompt_subquery = prompt_subquery.where(
            DatabasePromptRuleResult.created_at < end_time,
        )
        response_subquery = response_subquery.where(
            DatabaseResponseRuleResult.created_at < end_time,
        )

    return union(prompt_subquery, response_subquery)
