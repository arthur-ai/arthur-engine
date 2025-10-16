import logging
import uuid
from datetime import datetime
from typing import List, Optional

from arthur_common.models.enums import PaginationSortMethod, RuleResultEnum, RuleType
from arthur_common.models.response_schemas import (
    ConversationBaseResponse,
    ConversationResponse,
)
from fastapi import HTTPException
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate
from opentelemetry import trace
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, selectinload

from db_models import (
    DatabaseEmbeddingReference,
    DatabaseInference,
    DatabaseInferencePrompt,
    DatabaseInferenceResponse,
    DatabasePromptRuleResult,
    DatabaseResponseRuleResult,
    DatabaseRule,
    DatabaseTask,
)
from schemas.custom_exceptions import AlreadyValidatedException
from schemas.internal_schemas import (
    Embedding,
    Inference,
    InferencePrompt,
    InferenceResponse,
    PromptRuleResult,
    ResponseRuleResult,
    RuleEngineResult,
)
from utils.token_count import TokenCounter

logger = logging.getLogger()
tracer = trace.get_tracer(__name__)


class InferenceRepository:
    def __init__(
        self,
        db_session: Session,
    ):
        self.db_session: Session = db_session
        self.token_counter = TokenCounter()

    def get_inference(self, inference_id: str):
        inference = (
            self.db_session.query(DatabaseInference)
            .filter(DatabaseInference.id == inference_id)
            .first()
        )
        if not inference:
            raise HTTPException(
                status_code=404,
                detail="Inference %s not found." % inference_id,
            )
        return inference

    @tracer.start_as_current_span("query_inferences")
    def query_inferences(
        self,
        sort: PaginationSortMethod,
        page: int,
        task_ids: list[str] = [],
        task_name: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        model_name: str | None = None,
        page_size: int = 10,
        start_time: datetime = None,
        end_time: datetime = None,
        rule_types: list[RuleType] = [],
        rule_results: list[RuleResultEnum] = [],
        prompt_statuses: list[RuleResultEnum] = [],
        response_statuses: list[RuleResultEnum] = [],
        include_count: bool = True,
    ) -> tuple[list[Inference], int]:
        stmt = self.db_session.query(DatabaseInference.id, DatabaseInference.created_at)

        # Rule types and rule results need this join as a prereq to their later joins
        if prompt_statuses or response_statuses or rule_types or rule_results:
            stmt = stmt.join(DatabaseInferencePrompt, isouter=True).join(
                DatabaseInferenceResponse,
                isouter=True,
            )

        # Only join tables if the corresponding filters are provided
        if rule_types or rule_results:
            # Because we reference DatabaseRule in both PromptRR and ResponseRR, we need to join these together seperately and twice.
            # SQLAlchemy doesn't make this easy, so we need to use an alias of DR to join it twice. Later on we check both columns
            prompt_rules = aliased(DatabaseRule)
            stmt = (
                stmt.join(DatabasePromptRuleResult, isouter=True)
                .join(DatabaseResponseRuleResult, isouter=True)
                .join(
                    DatabaseRule,
                    DatabaseResponseRuleResult.rule_id == DatabaseRule.id,
                    isouter=True,
                )
                .join(
                    prompt_rules,
                    DatabasePromptRuleResult.rule_id == prompt_rules.id,
                    isouter=True,
                )
            )

        if sort == PaginationSortMethod.DESCENDING or sort is None:
            stmt = stmt.order_by(desc(DatabaseInference.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            stmt = stmt.order_by(asc(DatabaseInference.created_at))
        if task_ids:
            stmt = stmt.where(DatabaseInference.task_id.in_(task_ids))
        if task_name:
            stmt = stmt.where(
                DatabaseInference.task.has(DatabaseTask.name.icontains(task_name)),
            )
        if conversation_id:
            stmt = stmt.where(DatabaseInference.conversation_id == conversation_id)
        if user_id:
            stmt = stmt.where(DatabaseInference.user_id == user_id)
        if model_name:
            stmt = stmt.where(DatabaseInference.model_name.ilike(f"%{model_name}%"))
        if start_time:
            stmt = stmt.where(DatabaseInference.created_at >= start_time)
        if end_time:
            stmt = stmt.where(DatabaseInference.created_at < end_time)
        if prompt_statuses:
            stmt = stmt.where(DatabaseInferencePrompt.result.in_(prompt_statuses))
        if response_statuses:
            stmt = stmt.where(DatabaseInferenceResponse.result.in_(response_statuses))
        if rule_types and rule_results:
            stmt = stmt.where(
                or_(
                    and_(
                        DatabaseRule.type.in_(rule_types),
                        DatabaseResponseRuleResult.rule_result.in_(rule_results),
                    ),
                    and_(
                        prompt_rules.type.in_(rule_types),
                        DatabasePromptRuleResult.rule_result.in_(rule_results),
                    ),
                ),
            )
        elif rule_types:
            stmt = stmt.where(
                or_(
                    DatabaseRule.type.in_(rule_types),
                    prompt_rules.type.in_(rule_types),
                ),
            )
        elif rule_results:
            stmt = stmt.where(
                or_(
                    DatabaseResponseRuleResult.rule_result.in_(rule_results),
                    DatabasePromptRuleResult.rule_result.in_(rule_results),
                ),
            )

        # The double joining will create duplicates which we need to get rid of, this needs to be done before the limit query so we don't limit to 10 and the dedupe to something smaller
        stmt = stmt.distinct()

        # Calculate the count prior to applying the offset
        if include_count:
            count = stmt.count()
        else:
            count = -1

        if page is not None:
            stmt = stmt.offset(page * page_size)
        stmt = stmt.limit(page_size)
        inference_id_timestamps = stmt.all()
        inference_ids = [row[0] for row in inference_id_timestamps]

        # Think about the highly nested structure of GenAI Engine inferences with this handy AI generated example:
        # TLDR: Using selectinload lets the data returned by the db scale linearly with the number of rows at the cost of multiple db queries
        #
        # Example of joining rows with list fields to base rows repeatedly,
        # showing exponential growth in the number of result rows
        #
        # Consider three tables: 'users', 'posts', and 'comments'
        # users table:
        # | id | name  |
        # |----|-------|
        # | 1  | Alice |
        # | 2  | Bob   |
        #
        # posts table:
        # | id | user_id | title        |
        # |----|---------|--------------|
        # | 1  | 1       | Alice Post 1 |
        # | 2  | 2       | Bob Post 1   |
        #
        # When we join users and posts, we get 2 rows:
        # | user_id | name  | post_id | title        |
        # |---------|-------|---------|--------------|
        # | 1       | Alice | 1       | Alice Post 1 |
        # | 2       | Bob   | 2       | Bob Post 1   |
        #
        # Now, let's add the comments table with multiple comments per post:
        # comments table:
        # | id | post_id | content        |
        # |----|---------|----------------|
        # | 1  | 1       | Comment 1 on A1|
        # | 2  | 1       | Comment 2 on A1|
        # | 3  | 1       | Comment 3 on A1|
        # | 4  | 1       | Comment 4 on A1|
        # | 5  | 2       | Comment 1 on B1|
        # | 6  | 2       | Comment 2 on B1|
        # | 7  | 2       | Comment 3 on B1|
        # | 8  | 2       | Comment 4 on B1|
        #
        # Joining all three tables results in 8 rows:
        # | user_id | name  | post_id | title        | comment_id | content        |
        # |---------|-------|---------|--------------|------------|----------------|
        # | 1       | Alice | 1       | Alice Post 1 | 1          | Comment 1 on A1|
        # | 1       | Alice | 1       | Alice Post 1 | 2          | Comment 2 on A1|
        # | 1       | Alice | 1       | Alice Post 1 | 3          | Comment 3 on A1|
        # | 1       | Alice | 1       | Alice Post 1 | 4          | Comment 4 on A1|
        # | 2       | Bob   | 2       | Bob Post 1   | 5          | Comment 1 on B1|
        # | 2       | Bob   | 2       | Bob Post 1   | 6          | Comment 2 on B1|
        # | 2       | Bob   | 2       | Bob Post 1   | 7          | Comment 3 on B1|
        # | 2       | Bob   | 2       | Bob Post 1   | 8          | Comment 4 on B1|
        #
        # Now, let's add another table 'reactions' with 4 reactions per comment:
        # reactions table:
        # | id | comment_id | reaction |
        # |----|------------|----------|
        # | 1  | 1          | Like     |
        # | 2  | 1          | Love     |
        # | 3  | 1          | Haha     |
        # | 4  | 1          | Wow      |
        # | 5  | 2          | Like     |
        # | 6  | 2          | Angry    |
        # | 7  | 2          | Sad      |
        # | 8  | 2          | Love     |
        # ... (reactions for comments 3-8 omitted for brevity)
        #
        # Joining all four tables results in 32 rows (8 * 4).
        # Here are the first 8 rows of the final result:
        # | user_id | name  | post_id | title        | comment_id | content        | reaction_id | reaction |
        # |---------|-------|---------|--------------|------------|----------------|-------------|----------|
        # | 1       | Alice | 1       | Alice Post 1 | 1          | Comment 1 on A1| 1           | Like     |
        # | 1       | Alice | 1       | Alice Post 1 | 1          | Comment 1 on A1| 2           | Love     |
        # | 1       | Alice | 1       | Alice Post 1 | 1          | Comment 1 on A1| 3           | Haha     |
        # | 1       | Alice | 1       | Alice Post 1 | 1          | Comment 1 on A1| 4           | Wow      |
        # | 1       | Alice | 1       | Alice Post 1 | 2          | Comment 2 on A1| 5           | Like     |
        # | 1       | Alice | 1       | Alice Post 1 | 2          | Comment 2 on A1| 6           | Angry    |
        # | 1       | Alice | 1       | Alice Post 1 | 2          | Comment 2 on A1| 7           | Sad      |
        # | 1       | Alice | 1       | Alice Post 1 | 2          | Comment 2 on A1| 8           | Love     |
        # As you can see, the number of rows increases exponentially with each join:
        # - Users to Posts: 2 rows
        # - Users to Posts to Comments: 8 rows
        # - Users to Posts to Comments to Reactions: 32 rows (8 * 4)
        #
        # This exponential growth in the number of rows can lead to performance issues
        # and increased memory usage. Using techniques like selectinload can help avoid
        # this problem by fetching related data without multiplying the number of rows.
        # Remember, we only have 2 posts but now have 32 rows.
        stmt = (
            self.db_session.query(DatabaseInference)
            .options(
                selectinload(DatabaseInference.inference_prompt)
                .selectinload(DatabaseInferencePrompt.prompt_rule_results)
                .selectinload(DatabasePromptRuleResult.rule_details),
                selectinload(DatabaseInference.inference_response)
                .selectinload(DatabaseInferenceResponse.response_rule_results)
                .selectinload(DatabaseResponseRuleResult.rule_details),
                selectinload(DatabaseInference.inference_feedback),
                selectinload(DatabaseInference.task),
            )
            .where(DatabaseInference.id.in_(inference_ids))
        )

        if sort == PaginationSortMethod.DESCENDING or sort is None:
            stmt = stmt.order_by(desc(DatabaseInference.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            stmt = stmt.order_by(asc(DatabaseInference.created_at))
        results = stmt.all()

        inferences = [Inference._from_database_model(di) for di in results]
        return inferences, count

    def save_prompt(
        self,
        prompt: str,
        prompt_rule_results: List[RuleEngineResult],
        task_id: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
    ) -> InferencePrompt:
        inference = get_new_inference(task_id, conversation_id)
        inference_prompt = get_inference_prompt(
            inference.id,
            prompt,
            prompt_rule_results,
            tokens=self.token_counter.count(prompt),
        )

        inference.result = inference_prompt.result
        inference.inference_prompt = inference_prompt
        inference.user_id = user_id

        if any(
            [
                r.rule_result == RuleResultEnum.UNAVAILABLE
                for r in inference_prompt.prompt_rule_results
            ],
        ):
            logger.warning(f"Inference {inference.id} prompt had failed rule results.")
        db_inference = inference._to_database_model()
        self.db_session.add(db_inference)
        self.db_session.commit()

        return inference.inference_prompt

    def save_response(
        self,
        inference_id: str,
        response: str,
        response_context: str,
        response_rule_results: List[RuleEngineResult],
        model_name: str | None = None,
    ):
        inference_response = get_inference_response(
            inference_id,
            response,
            response_context,
            response_rule_results,
            tokens=self.token_counter.count(response),
        )

        db_inference_response = inference_response._to_database_model()
        try:
            self.db_session.add(db_inference_response)
            db_inference = self.get_inference(inference_id)
            db_inference.updated_at = datetime.now()
            db_inference.result = (
                RuleResultEnum.PASS
                if (
                    db_inference.result == RuleResultEnum.PASS
                    and db_inference_response.result == RuleResultEnum.PASS
                )
                else RuleResultEnum.FAIL
            )
            db_inference.model_name = model_name
            self.db_session.commit()
        except IntegrityError as err:
            logger.warning("Response was already validated.")
            self.db_session.rollback()
            raise AlreadyValidatedException()

        if any(
            [
                r.rule_result == RuleResultEnum.UNAVAILABLE
                for r in db_inference_response.response_rule_results
            ],
        ):
            logger.warning(
                f"Inference {db_inference.id} response had failed rule results.",
            )

        return inference_response

    def save_inference_document_context(
        self,
        inference_id: str,
        context_embeddings: list[Embedding],
    ):
        embedding_references = [
            e._to_reference_database_model(inference_id) for e in context_embeddings
        ]
        self.db_session.add_all(embedding_references)
        self.db_session.commit()

    def get_inference_document_context(self, inference_id: str) -> list[Embedding]:
        inference = self.get_inference(inference_id)
        query = self.db_session.query(DatabaseEmbeddingReference).where(
            DatabaseEmbeddingReference.inference_id == inference.id,
        )
        return [Embedding._from_database_model(e.embedding) for e in query.all()]

    def get_all_user_conversations(
        self,
        user_id: str,
        query_params: Params = Params(),
    ) -> Page[List[ConversationBaseResponse]]:
        subquery = (
            self.db_session.query(
                DatabaseInference.conversation_id,
                func.max(DatabaseInference.updated_at).label("newest_entry"),
            )
            .filter(DatabaseInference.user_id == user_id)
            .group_by(DatabaseInference.conversation_id)
            .subquery("t2")
        )

        query = self.db_session.query(DatabaseInference).join(
            subquery,
            and_(
                DatabaseInference.conversation_id == subquery.c.conversation_id,
                DatabaseInference.updated_at == subquery.c.newest_entry,
            ),
        )
        paginated_user_inferences = paginate(
            self.db_session,
            query,
            params=query_params,
            transformer=lambda inferences: [
                ConversationBaseResponse(
                    id=inference.conversation_id,
                    updated_at=inference.updated_at,
                )
                for inference in inferences
            ],
        )
        return paginated_user_inferences

    def get_conversation_by_id(
        self,
        conversation_id: str,
        user_id: str,
    ) -> ConversationResponse | None:
        inferences = (
            self.db_session.query(DatabaseInference)
            .filter(
                DatabaseInference.conversation_id == conversation_id,
                DatabaseInference.user_id == user_id,
            )
            .order_by(DatabaseInference.updated_at.desc())
            .all()
        )
        if not inferences:
            return None
        return ConversationResponse(
            id=conversation_id,
            updated_at=inferences[0].updated_at,
            inferences=[
                Inference._from_database_model(inference)._to_response_model()
                for inference in inferences
            ],
        )

    def delete_inference(self, inference_id: str) -> None:
        self.db_session.query(DatabaseInference).filter(
            DatabaseInference.id == inference_id,
        ).delete()
        self.db_session.commit()


def get_new_inference(task_id: str = None, conversation_id: str = None) -> Inference:
    inference = Inference(
        id=str(uuid.uuid4()),
        result=RuleResultEnum.PASS,
        task_id=task_id,
        conversation_id=conversation_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        inference_prompt=None,
        inference_feedback=[],
    )

    return inference


def get_inference_prompt(
    inference_id: str,
    prompt: str,
    rule_engine_results: List[RuleEngineResult],
    user_id: str = None,
    tokens: Optional[int] = None,
) -> InferencePrompt:
    prompt_rule_results = [
        PromptRuleResult._from_rule_engine_model(r) for r in rule_engine_results
    ]
    inference_prompt_id = str(uuid.uuid4())
    inference_prompt = InferencePrompt(
        id=inference_prompt_id,
        inference_id=inference_id,
        result=(
            RuleResultEnum.PASS
            if all([x.rule_result is RuleResultEnum.PASS for x in prompt_rule_results])
            else RuleResultEnum.FAIL
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message=prompt,
        prompt_rule_results=prompt_rule_results,
        tokens=tokens,
    )

    return inference_prompt


def get_inference_response(
    inference_id: str,
    response: str,
    response_context: str,
    rule_engine_results: List[RuleEngineResult],
    tokens: Optional[int] = None,
    model_name: str | None = None,
) -> InferenceResponse:
    response_rule_results = [
        ResponseRuleResult._from_rule_engine_model(r) for r in rule_engine_results
    ]
    inference_response_id = str(uuid.uuid4())
    inference_response = InferenceResponse(
        id=inference_response_id,
        inference_id=inference_id,
        result=(
            RuleResultEnum.PASS
            if all(
                [x.rule_result is RuleResultEnum.PASS for x in response_rule_results],
            )
            else RuleResultEnum.FAIL
        ),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        message=response,
        context=response_context,
        response_rule_results=response_rule_results,
        tokens=tokens,
        model_name=model_name,
    )

    return inference_response
