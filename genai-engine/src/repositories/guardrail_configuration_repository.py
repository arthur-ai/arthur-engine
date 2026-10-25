from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from db_models.configuration_models import DatabaseApplicationConfiguration
from db_models.secret_storage_models import DatabaseSecretStorage
from schemas.enums import ApplicationConfigurations, SecretType
from schemas.guardrail_schemas import GuardrailLLMConfiguration, GuardrailLLMStatus
from utils.constants import ORG_ADMIN

# All writers and snapshot readers share this deployment-wide transaction lock.
GUARDRAIL_CONFIGURATION_LOCK = 0x47554152444C4C4D


def lock_guardrail_configuration(session: Session, *, shared: bool = False) -> None:
    if session.get_bind().dialect.name == "postgresql":
        function = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
        session.execute(
            text(f"SELECT {function}(:key)"), {"key": GUARDRAIL_CONFIGURATION_LOCK}
        )


class GuardrailConfigurationRepository:
    def __init__(self, session: Session):
        self.session = session

    def read(self) -> tuple[GuardrailLLMConfiguration | None, GuardrailLLMStatus]:
        value = self.session.execute(
            select(DatabaseApplicationConfiguration.value).where(
                DatabaseApplicationConfiguration.name
                == ApplicationConfigurations.GUARDRAIL_LLM,
            ),
        ).scalar_one_or_none()
        if value is None:
            return None, "needs_configuration"
        try:
            selection = GuardrailLLMConfiguration.model_validate_json(value)
            if selection.provider.value == "empty":
                return None, "invalid"
        except ValidationError:
            return None, "invalid"
        enabled = self.session.execute(
            select(DatabaseSecretStorage.id).where(
                DatabaseSecretStorage.secret_type == SecretType.MODEL_PROVIDER,
                DatabaseSecretStorage.name == selection.provider,
            ),
        ).first()
        return selection, "configured" if enabled else "needs_configuration"

    def write(self, selection: GuardrailLLMConfiguration | None) -> None:
        if selection is None:
            self.session.execute(
                delete(DatabaseApplicationConfiguration).where(
                    DatabaseApplicationConfiguration.name
                    == ApplicationConfigurations.GUARDRAIL_LLM,
                ),
            )
            return
        insert = (
            pg_insert
            if self.session.get_bind().dialect.name == "postgresql"
            else sqlite_insert
        )
        statement = insert(DatabaseApplicationConfiguration).values(
            name=ApplicationConfigurations.GUARDRAIL_LLM,
            value=selection.model_dump_json(),
        )
        self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[DatabaseApplicationConfiguration.name],
                set_={"value": statement.excluded.value},
            ),
        )

    def authorize_provider_mutation(
        self, provider: ModelProvider, roles: set[str]
    ) -> None:
        lock_guardrail_configuration(self.session)
        selection, status = self.read()
        if (
            status == "invalid" or (selection and selection.provider == provider)
        ) and ORG_ADMIN not in roles:
            raise HTTPException(
                status_code=403,
                detail="Only an organization administrator can change the guardrail provider.",
            )
