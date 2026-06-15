from sqlalchemy.orm import Session

from db_models import DatabaseApplicationConfiguration
from schemas.enums import ApplicationConfigurations
from schemas.internal_schemas import ApplicationConfiguration
from schemas.request_schemas import ApplicationConfigurationUpdateRequest


class ConfigurationRepository:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def update_configurations(
        self,
        request: ApplicationConfigurationUpdateRequest,
    ) -> ApplicationConfiguration:
        existing_configurations = self.get_database_configurations()
        if request.default_currency is not None:
            default_currency_row = update_or_create_config(
                ApplicationConfigurations.DEFAULT_CURRENCY,
                request.default_currency.strip().upper(),
                existing_configurations,
            )
            self.db_session.add(default_currency_row)

        if request.max_llm_rules_per_task_count:
            max_llm_rules = update_or_create_config(
                ApplicationConfigurations.MAX_LLM_RULES_PER_TASK_COUNT,
                str(request.max_llm_rules_per_task_count),
                existing_configurations,
            )
            self.db_session.add(max_llm_rules)

        if request.trace_retention_days is not None:
            trace_retention = update_or_create_config(
                ApplicationConfigurations.TRACE_RETENTION_DAYS,
                str(request.trace_retention_days),
                existing_configurations,
            )
            self.db_session.add(trace_retention)

        self.db_session.commit()
        return self.get_configurations()

    def get_database_configurations(self) -> list[DatabaseApplicationConfiguration]:
        query = self.db_session.query(DatabaseApplicationConfiguration)
        return query.all()

    def get_configurations(self) -> ApplicationConfiguration:
        configs = self.get_database_configurations()
        config = ApplicationConfiguration._from_database_model(configs)
        return config


def update_or_create_config(
    key: str,
    value: str,
    existing_configs: list[DatabaseApplicationConfiguration],
) -> DatabaseApplicationConfiguration:
    configs = {config.name: config for config in existing_configs}
    if key in configs:
        config = configs[key]
        config.value = value
        return config
    else:
        return DatabaseApplicationConfiguration(name=key, value=value)
