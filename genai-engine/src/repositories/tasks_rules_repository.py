import logging

from cachetools import TTLCache
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from config.cache_config import cache_config
from db_models import DatabaseTaskToRules

CACHED_TASK_RULES = TTLCache(maxsize=1000, ttl=cache_config.TASK_RULES_CACHE_TTL)
logger = logging.getLogger(__name__)


class TasksRulesRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_task_rules_ids_cached(self, task_id: str) -> list[str]:
        if not cache_config.TASK_RULES_CACHE_ENABLED:
            return self._get_task_rules_ids(task_id)
        CACHED_TASK_RULES.expire()
        # Try to get from cache first
        cached_rules = CACHED_TASK_RULES.get(task_id)
        if cached_rules is not None:
            logger.debug(f"Returning cached rules for task {task_id}")
            return cached_rules

        # If not in cache, query from DB
        logger.debug(f"Querying DB for rules for task {task_id}")
        rules = self._get_task_rules_ids(task_id)
        # Store in cache for future use
        CACHED_TASK_RULES[task_id] = rules
        return rules

    def _get_task_rules_ids(self, task_id: str, only_enabled: bool = True) -> list[str]:
        statement = select(DatabaseTaskToRules).where(
            DatabaseTaskToRules.task_id == task_id,
        )
        if only_enabled:
            statement = statement.where(DatabaseTaskToRules.enabled == True)
        statement = statement.options(joinedload(DatabaseTaskToRules.task))
        result = self.db_session.execute(statement).unique().scalars().all()
        return [rule.rule_id for rule in result]

    def clear_cache(self):
        CACHED_TASK_RULES.clear()
