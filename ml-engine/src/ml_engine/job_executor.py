import json
import logging
from typing import Any
from uuid import uuid4

from arthur_client.api_bindings import (
    AlertCheckJobSpec,
    AlertRulesV1Api,
    AlertsV1Api,
    ApiClient,
    ConnectorCheckJobSpec,
    ConnectorsV1Api,
    CreateModelLinkTaskJobSpec,
    DataRetrievalV1Api,
    DatasetsV1Api,
    JobKind,
    JobRun,
    JobState,
    JobsV1Api,
    MetricsCalculationJobSpec,
    MetricsV1Api,
    ModelsV1Api,
    RegenerateTaskValidationKeyJobSpec,
    ScheduleJobsJobSpec,
    SchemaInspectionJobSpec,
    TasksV1Api,
)
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOAuthSessionAPIConfiguration,
    ArthurOIDCMetadata,
)
from arthur_common.models.task_job_specs import (
    CreateModelTaskJobSpec,
    DeleteModelTaskJobSpec,
    FetchModelTaskJobSpec,
    UpdateModelTaskRulesJobSpec,
)
from config import Config
from job_executors.alert_check_executor import AlertCheckExecutor
from job_executors.connector_test_executor import ConnectorTestExecutor
from job_executors.fetch_data_executor import FetchDataExecutor
from job_executors.list_datasets_executor import ListDatasetsExecutor
from job_executors.metrics_calculation_executor import MetricsCalculationExecutor
from job_executors.schedule_jobs_executor import ScheduleJobsExecutor
from job_executors.schema_inference_executor import SchemaInferenceExecutor
from job_executors.task_management_job_executors import (
    CreateTaskJobExecutor,
    DeleteTaskJobExecutor,
    FetchTaskJobExecutor,
    LinkTaskJobExecutor,
    RegenerateTaskValidationKeyJobExecutor,
    UpdateTaskJobExecutor,
)
from job_log_exporter import ExportContextedLogger, ScopeJobLogExporter
from pydantic import StrictBytes
from tools.connector_constructor import ConnectorConstructor

logging.basicConfig()


class JobSpecRawParser:
    """
    the generated API clients don't properly parse the shield rule config union types
    so parsing it manually using the scope common job spec models
    """

    JOB_SPEC_KEY = "job_spec"

    def __init__(self, b: StrictBytes):
        self.raw_payload = b

    def _parse_job_spec_field(self) -> Any:
        job_dict = json.loads(self.raw_payload)
        if self.JOB_SPEC_KEY not in job_dict:
            raise ValueError("Job must have 'job_spec' field")
        return job_dict[self.JOB_SPEC_KEY]

    def to_create_model_task_spec(self) -> CreateModelTaskJobSpec:
        return CreateModelTaskJobSpec.model_validate(self._parse_job_spec_field())

    def to_update_model_task_spec(self) -> UpdateModelTaskRulesJobSpec:
        return UpdateModelTaskRulesJobSpec.model_validate(self._parse_job_spec_field())

    def to_delete_model_task_spec(self) -> DeleteModelTaskJobSpec:
        return DeleteModelTaskJobSpec.model_validate(self._parse_job_spec_field())

    def to_fetch_model_task_spec(self) -> FetchModelTaskJobSpec:
        return FetchModelTaskJobSpec.model_validate(self._parse_job_spec_field())


class JobExecutor:
    def __init__(self) -> None:
        sess = ArthurClientCredentialsAPISession(
            client_id=Config.settings.ARTHUR_CLIENT_ID,
            client_secret=Config.settings.ARTHUR_CLIENT_SECRET,
            metadata=ArthurOIDCMetadata(arthur_host=Config.settings.ARTHUR_API_HOST),
        )
        client = ApiClient(
            configuration=ArthurOAuthSessionAPIConfiguration(session=sess),
        )
        self.alerts_client = AlertsV1Api(client)
        self.alert_rules_client = AlertRulesV1Api(client)
        self.data_retrieval_client = DataRetrievalV1Api(client)
        self.jobs_client = JobsV1Api(client)
        self.models_client = ModelsV1Api(client)
        self.connectors_client = ConnectorsV1Api(client)
        self.metrics_client = MetricsV1Api(client)
        self.datasets_client = DatasetsV1Api(client)
        self.tasks_client = TasksV1Api(client)

        self.logger: logging.Logger = logging.getLogger(str(uuid4()))
        self.logger.setLevel(logging.INFO)

        self.connector_constructor = ConnectorConstructor(
            self.connectors_client,
            self.logger,
        )

    def execute(self, job_run: JobRun) -> JobState:
        job_resp = self.jobs_client.get_job_with_http_info(job_run.job_id)
        job = job_resp.data
        scope_export_handler = ScopeJobLogExporter(
            job_id=job.id,
            job_run_id=job_run.id,
            jobs_client=self.jobs_client,
        )
        with ExportContextedLogger(self.logger, scope_export_handler):
            self.logger.info(f"Starting job {job.id} - {job.kind}")

            # Overwrite the connector constructor such that the new one has the job level logger with handler configured
            self.connector_constructor = ConnectorConstructor(
                self.connectors_client,
                self.logger,
            )
            try:
                match job.kind:
                    case JobKind.METRICS_CALCULATION:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            MetricsCalculationJobSpec,
                        ):
                            raise ValueError(
                                f"Expected MetricsCalculationJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        MetricsCalculationExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.metrics_client,
                            self.jobs_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job, job.job_spec.actual_instance)
                    case JobKind.CONNECTOR_CHECK:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            ConnectorCheckJobSpec,
                        ):
                            raise ValueError(
                                f"Expected ConnectorCheckJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        ConnectorTestExecutor(
                            self.connectors_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job.job_spec.actual_instance)
                    case JobKind.LIST_DATASETS:
                        ListDatasetsExecutor(
                            self.datasets_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job.job_spec.actual_instance)
                    case JobKind.SCHEMA_INSPECTION:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            SchemaInspectionJobSpec,
                        ):
                            raise ValueError(
                                f"Expected SchemaInspectionJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        SchemaInferenceExecutor(
                            self.datasets_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job.job_spec.actual_instance)
                    case JobKind.ALERT_CHECK:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            AlertCheckJobSpec,
                        ):
                            raise ValueError(
                                f"Expected AlertCheckJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        AlertCheckExecutor(
                            self.alerts_client,
                            self.alert_rules_client,
                            self.jobs_client,
                            self.metrics_client,
                            self.logger,
                        ).execute(job, job.job_spec.actual_instance)
                    case JobKind.SCHEDULE_JOBS:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            ScheduleJobsJobSpec,
                        ):
                            raise ValueError(
                                f"Expected ScheduleJobsJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        ScheduleJobsExecutor(
                            self.models_client,
                            self.jobs_client,
                            self.logger,
                        ).execute(job, job.job_spec.actual_instance)
                    case JobKind.FETCH_DATA:
                        if not Config.get_bool("FETCH_RAW_DATA_ENABLED", default=True):
                            self.logger.error(
                                "Raw data access is disabled for this engine. Please adjust your engine's "
                                "installation settings, or contact your administrator if you believe this is a misconfiguration.",
                            )
                            return JobState.FAILED
                        FetchDataExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.data_retrieval_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job.job_spec.actual_instance)
                    case JobKind.CREATE_MODEL_TASK:
                        CreateTaskJobExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.tasks_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(
                            job_spec=JobSpecRawParser(
                                job_resp.raw_data,
                            ).to_create_model_task_spec(),
                        )
                    case JobKind.UPDATE_MODEL_TASK_RULES:
                        UpdateTaskJobExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.tasks_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(
                            job_spec=JobSpecRawParser(
                                job_resp.raw_data,
                            ).to_update_model_task_spec(),
                        )
                    case JobKind.DELETE_MODEL_TASK:
                        DeleteTaskJobExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.tasks_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(
                            job_spec=JobSpecRawParser(
                                job_resp.raw_data,
                            ).to_delete_model_task_spec(),
                        )
                    case JobKind.FETCH_MODEL_TASK:
                        FetchTaskJobExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.tasks_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(
                            job_spec=JobSpecRawParser(
                                job_resp.raw_data,
                            ).to_fetch_model_task_spec(),
                        )
                    case JobKind.REGENERATE_TASK_VALIDATION_KEY:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            RegenerateTaskValidationKeyJobSpec,
                        ):
                            raise ValueError(
                                f"Expected RegenerateTaskValidationKeyJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        RegenerateTaskValidationKeyJobExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.tasks_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job.job_spec.actual_instance)
                    case JobKind.CREATE_MODEL_LINK_TASK:
                        if not isinstance(
                            job.job_spec.actual_instance,
                            CreateModelLinkTaskJobSpec,
                        ):
                            raise ValueError(
                                f"Expected CreateModelLinkTaskJobSpec type, got {type(job.job_spec.actual_instance)}.",
                            )
                        LinkTaskJobExecutor(
                            self.models_client,
                            self.datasets_client,
                            self.tasks_client,
                            self.connector_constructor,
                            self.logger,
                        ).execute(job.job_spec.actual_instance)
                    case _:
                        raise NotImplementedError(f"Job type {job.kind} not supported.")
                self.logger.info(f"Job {job.id} - {job.kind} completed")
                return JobState.COMPLETED
            except Exception as e:
                self.logger.error(
                    f"Error executing job: {job.id} - {job.kind}",
                    exc_info=e,
                )
                return JobState.FAILED
