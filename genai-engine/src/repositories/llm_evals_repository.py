from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query

from db_models.llm_eval_models import DatabaseLLMEval
from schemas.llm_eval_schemas import LLMEval
from schemas.request_schemas import CreateEvalRequest


class LLMEvalsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def _get_latest_db_eval(self, base_query: Query) -> DatabaseLLMEval:
        return (
            base_query.filter(DatabaseLLMEval.deleted_at.is_(None))
            .order_by(DatabaseLLMEval.version.desc())
            .first()
        )

    def _get_db_eval_by_version_number(
        self,
        base_query: Query,
        eval_version: str,
    ) -> DatabaseLLMEval:
        return base_query.filter(
            DatabaseLLMEval.version == int(eval_version),
        ).first()

    def _get_db_eval_by_datetime(
        self,
        base_query: Query,
        eval_version: str,
    ) -> DatabaseLLMEval:
        try:
            target_dt = datetime.fromisoformat(eval_version)
            return (
                base_query.filter(
                    sa.func.abs(
                        sa.func.extract("epoch", DatabaseLLMEval.created_at)
                        - sa.func.extract("epoch", target_dt),
                    )
                    < 1,
                )
                .order_by(DatabaseLLMEval.created_at.desc())
                .first()
            )
        except ValueError:
            raise ValueError(
                f"Invalid eval_version format '{eval_version}'. Must be 'latest', "
                f"a version number, or an ISO datetime string.",
            )

    def _get_db_eval_by_version(
        self,
        base_query: Query,
        eval_version: str,
        err_message: str = "LLM eval version not found",
    ) -> DatabaseLLMEval:
        db_eval = None

        if eval_version == "latest":
            db_eval = self._get_latest_db_eval(base_query)
        elif eval_version.isdigit():
            db_eval = self._get_db_eval_by_version_number(
                base_query,
                eval_version,
            )
        else:
            db_eval = self._get_db_eval_by_datetime(base_query, eval_version)

        if not db_eval:
            raise ValueError(err_message)

        return db_eval

    def save_eval(
        self,
        task_id: str,
        eval_name: str,
        eval_config: CreateEvalRequest,
    ) -> LLMEval:
        """
        Save an LLMEval to the database.
        If an eval with the same name exists, increment version.
        Otherwise, start at version 1.
        """
        llm_eval = LLMEval(name=eval_name, **eval_config.model_dump())

        # Check for existing versions of this eval
        latest_version = (
            self.db_session.query(sa.func.max(DatabaseLLMEval.version))
            .filter(
                DatabaseLLMEval.task_id == task_id,
                DatabaseLLMEval.name == llm_eval.name,
            )
            .scalar()
        )

        # Assign version
        llm_eval.version = (latest_version + 1) if latest_version else 1

        db_eval = llm_eval.to_db_model(task_id)

        try:
            self.db_session.add(db_eval)
            self.db_session.commit()
            self.db_session.refresh(db_eval)
            return LLMEval.from_db_model(db_eval)
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Failed to save llm eval '{llm_eval.name}' for task '{task_id}' — possible duplicate constraint.",
            )

    def soft_delete_eval_version(
        self,
        task_id: str,
        eval_name: str,
        eval_version: str,
    ) -> bool:
        """
        Soft delete a specific version of an llm eval by task_id, name and version. This will delete all the data associated with
        that llm eval version except for task_id, name, created_at, deleted_at and version.

        Parameters:
            task_id: str - the id of the task
            eval_name: str - the name of the llm eval
            eval_version: str - the version of the llm eval

        * Note - Supports:
            - eval_version='latest' -> marks latest version as deleted
            - eval_version=<string number> (e.g. '1', '2', etc.) -> marks that version as deleted
            - eval_version=<datetime> (YYYY-MM-DDTHH:MM:SS, checks to the second) -> marks version created at that time
        """
        base_query = self.db_session.query(DatabaseLLMEval).filter(
            DatabaseLLMEval.task_id == task_id,
            DatabaseLLMEval.name == eval_name,
        )

        err_msg = f"llm eval '{eval_name}' not found for task '{task_id}'"
        db_eval = self._get_db_eval_by_version(
            base_query,
            eval_version,
            err_message=err_msg,
        )

        if db_eval.deleted_at is not None:
            raise ValueError(
                f"LLM eval '{eval_name}' (version {db_eval.version}) has already been deleted.",
            )

        db_eval.deleted_at = datetime.now()
        db_eval.model_name = ""
        db_eval.instructions = ""
        db_eval.min_score = 0
        db_eval.max_score = 1
        db_eval.config = None

        self.db_session.commit()

    def delete_eval(self, task_id: str, eval_name: str) -> None:
        """
        Deletes all versions of an llm eval for a given task and removes them from the database

        Parameters:
            task_id: str - the id of the task
            eval_name: str - the name of the llm eval
        """
        db_evals = (
            self.db_session.query(DatabaseLLMEval)
            .filter(
                DatabaseLLMEval.task_id == task_id,
                DatabaseLLMEval.name == eval_name,
            )
            .all()
        )

        if not db_evals:
            raise ValueError(f"LLM eval '{eval_name}' not found for task '{task_id}'")

        for db_eval in db_evals:
            self.db_session.delete(db_eval)

        self.db_session.commit()
