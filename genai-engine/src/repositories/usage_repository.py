from datetime import datetime
from itertools import groupby
from typing import Optional

from db_models.db_models import (
    DatabaseInference,
    DatabaseInferencePrompt,
    DatabaseInferenceResponse,
    DatabasePromptRuleResult,
    DatabaseResponseRuleResult,
    DatabaseRule,
)
from pydantic import BaseModel
from schemas.enums import TokenUsageScope
from schemas.response_schemas import TokenUsageCount, TokenUsageResponse
from sqlalchemy import func, select, union
from sqlalchemy.orm import Session


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
        start_time: datetime = None,
        end_time: datetime = None,
        group_by: list[TokenUsageScope] = [TokenUsageScope.RULE_TYPE],
    ) -> list[TokenUsageResponse]:
        rows = self.run_tokens_query(start_time, end_time)

        def get_group_key(row: TokenQueryRow) -> int:
            key = []
            for group in group_by:
                if group == TokenUsageScope.RULE_TYPE:
                    key.append(row.rule_type)
                elif group == TokenUsageScope.TASK:
                    key.append(row.task_id)
            return hash(tuple(key))

        usages = []
        # itertools.groupby groups contiguous blocks of equal keys, so the rows must be sorted by the group key
        rows = sorted(rows, key=lambda x: get_group_key(x))
        for _, group in groupby(rows, lambda x: get_group_key(x)):
            group = list(group)
            counter = TokenUsageCount(
                inference=0,
                eval_prompt=0,
                eval_completion=0,
                user_input=0,
                prompt=0,
                completion=0,
            )
            for row in group:
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
                    usage.rule_type = group[0].rule_type
                elif scope == TokenUsageScope.TASK:
                    usage.task_id = group[0].task_id

            usages.append(usage)
        return usages

    def run_tokens_query(self, start_time, end_time) -> list[TokenQueryRow]:
        query = get_token_query_statement(start_time, end_time)

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
def get_token_query_statement(start_time: datetime, end_time: datetime):
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
