from db_models.db_models import DatabaseApplicationConfiguration
from schemas.enums import ApplicationConfigurations
from schemas.internal_schemas import ApplicationConfiguration
from schemas.request_schemas import ApplicationConfigurationUpdateRequest
from sqlalchemy.orm import Session


class ConfigurationRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def update_configurations(
        self,
        request: ApplicationConfigurationUpdateRequest,
    ):
        existing_configurations = self.get_database_configurations()

        if request.max_llm_rules_per_task_count:
            max_llm_rules = update_or_create_config(
                ApplicationConfigurations.MAX_LLM_RULES_PER_TASK_COUNT,
                str(request.max_llm_rules_per_task_count),
                existing_configurations,
            )
            self.db_session.add(max_llm_rules)

        self.db_session.commit()
        return self.get_configurations()

    def get_database_configurations(self):
        query = self.db_session.query(DatabaseApplicationConfiguration)
        return query.all()

    def get_configurations(self):
        configs = self.get_database_configurations()
        config = ApplicationConfiguration._from_database_model(configs)
        return config


def update_or_create_config(
    key: str,
    value: str,
    existing_configs: list[DatabaseApplicationConfiguration],
):
    configs = {config.name: config for config in existing_configs}
    if key in configs:
        config = configs[key]
        config.value = value
        return config
    else:
        return DatabaseApplicationConfiguration(name=key, value=value)
