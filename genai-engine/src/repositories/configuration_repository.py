from db_models.db_models import DatabaseApplicationConfiguration
from arthur_common.models.enums import ApplicationConfigurations
from schemas.internal_schemas import ApplicationConfiguration
from arthur_common.models.request_schemas import ApplicationConfigurationUpdateRequest
from sqlalchemy.orm import Session


class ConfigurationRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def update_configurations(
        self,
        request: ApplicationConfigurationUpdateRequest,
    ):
        existing_configurations = self.get_database_configurations()
        if request.chat_task_id:
            chat_config = update_or_create_config(
                ApplicationConfigurations.CHAT_TASK_ID,
                request.chat_task_id,
                existing_configurations,
            )
            self.db_session.add(chat_config)

        if request.document_storage_configuration:
            rows = []
            config = request.document_storage_configuration
            if config.environment:
                rows.append(
                    update_or_create_config(
                        ApplicationConfigurations.DOCUMENT_STORAGE_ENV,
                        config.environment,
                        existing_configurations,
                    ),
                )
            if config.bucket_name:
                rows.append(
                    update_or_create_config(
                        ApplicationConfigurations.DOCUMENT_STORAGE_BUCKET_NAME,
                        config.bucket_name,
                        existing_configurations,
                    ),
                )
            if config.assumable_role_arn:
                rows.append(
                    update_or_create_config(
                        ApplicationConfigurations.DOCUMENT_STORAGE_ROLE_ARN,
                        config.assumable_role_arn,
                        existing_configurations,
                    ),
                )
            if config.connection_string:
                rows.append(
                    update_or_create_config(
                        ApplicationConfigurations.DOCUMENT_STORAGE_CONNECTION_STRING,
                        config.connection_string,
                        existing_configurations,
                    ),
                )
            if config.container_name:
                rows.append(
                    update_or_create_config(
                        ApplicationConfigurations.DOCUMENT_STORAGE_CONTAINER_NAME,
                        config.container_name,
                        existing_configurations,
                    ),
                )

            self.db_session.add_all(rows)
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
