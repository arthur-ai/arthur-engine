from sqlalchemy.orm import Session

from db_models.db_models import DatabaseMetric
from schemas.internal_schemas import Metric
from schemas.request_schemas import UpdateMetricRequest


class MetricsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_metric(self, metric: Metric):
        database_metric = metric._to_database_model()
        self.db_session.add(database_metric)
        self.db_session.commit()

    def get_metric(self, metric_id: str) -> Metric:
        database_metric = self.db_session.query(DatabaseMetric).filter(DatabaseMetric.id == metric_id).first()
        return Metric._from_database_model(database_metric)

    def update_metric(self, metric_id: str, metric: UpdateMetricRequest):
        database_metric = self.db_session.query(DatabaseMetric).filter(DatabaseMetric.id == metric_id).first()
        if not database_metric:
            raise ValueError(f"Metric with id {metric_id} not found")

        database_metric.metric_name = metric.metric_name
        database_metric.metric_metadata = metric.metric_metadata

        self.db_session.commit()
        return Metric._from_database_model(database_metric)
