from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from db_models.secret_storage_models import DatabaseSecretStorage


class SecretsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def rotate_secrets(self) -> None:
        # rotate all secrets in the database
        secrets = self.db_session.query(DatabaseSecretStorage).all()
        for secret in secrets:
            # mark the encrypted column as modified so sqlalchemy re-encrypts it
            flag_modified(secret, "value")
        self.db_session.commit()
