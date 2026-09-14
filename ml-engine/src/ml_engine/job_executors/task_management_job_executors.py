import logging
from functools import cached_property
from typing import NamedTuple, Tuple

import arthur_client
import genai_client.exceptions
from arthur_client.api_bindings import (
    ApiException,
    ConnectorType,
    ContinuousEvalResponse,
    CreateModelLinkTaskJobSpec,
    Dataset,
    DatasetLocator,
    DatasetLocatorField,
    DatasetsV1Api,
    DefaultApi,
    Eval,
    Model,
    ModelProblemType,
    ModelsV1Api,
    PostDataset,
    PostModel,
    PostTaskValidationAPIKey,
    PutDatasetSchema,
    PutTaskConnectionInfo,
    PutTaskStateCacheRequest,
    RegenerateTaskValidationKeyJobSpec,
    TasksV1Api,
    TraceTransformResponse,
)
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.request_schemas import NewMetricRequest, NewRuleRequest
from arthur_common.models.response_schemas import (
    MetricResponse,
    RuleResponse,
    TaskResponse,
)
from arthur_common.models.schema_definitions import AGENTIC_TRACE_SCHEMA, SHIELD_SCHEMA
from arthur_common.models.task_job_specs import (
    CreateModelTaskJobSpec,
    DeleteModelTaskJobSpec,
    FetchModelTaskJobSpec,
    UpdateModelTaskRulesJobSpec,
)

from connectors.connector import Connector
from connectors.shield_connector import ShieldBaseConnector
from tools.api_client_type_converters import ScopeClientTypeConverter
from tools.connector_constructor import ConnectorConstructor
from tools.converters import common_to_client_put_dataset_schema


class InvalidConnectorException(Exception):
    pass


# Platform releases before this one require an Arthur shield model to be linked to
# exactly one dataset, so they reject the consolidated two-dataset task shape with a
# 400 and the engine has to fall back to the legacy single-dataset shape (UP-5022).
MIN_CONSOLIDATED_TASK_DATASETS_PLATFORM_RELEASE = (1, 4, 2592)

# Which dataset a task keeps when the engine must emit the legacy single-dataset
# shape but cannot tell what kind of task it is. Only the link path lands here: its
# job spec never carried task_type and TaskResponse.is_agentic is now always True, so
# the task's original kind is unrecoverable. PENDING PRODUCT DECISION (UP-5022) —
# ARTHUR_SHIELD keeps guardrails, AGENTIC_TRACE would keep traces and evals instead.
# Flip this one value to change it.
LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE = ModelProblemType.ARTHUR_SHIELD

# arthur-common dropped TaskType along with the consolidation, so the values a
# pre-consolidation platform sends are matched as plain strings.
_LEGACY_AGENTIC_TASK_TYPE = "agentic"
_LEGACY_TRADITIONAL_TASK_TYPE = "traditional"

# Fragment of the pre-consolidation platform's rejection body. Matched so the
# fallback still fires when /api/health reports no usable version.
_SINGLE_DATASET_CONSTRAINT_ERROR = "must be linked to exactly one dataset"


class _TaskDatasetSpec(NamedTuple):
    dataset_name: str
    dataset_schema: PutDatasetSchema
    model_problem_type: ModelProblemType


def _parse_platform_release_version(
    version: str | None,
) -> Tuple[int, int, int] | None:
    """
    /api/health's release_version is environment-sourced, so it can be absent, the
    literal "unknown", or a deploy tag with a suffix ("1.4.2594-release"). Returns
    None for anything that is not a readable major.minor.patch.
    """
    if not version:
        return None
    parts = version.strip().split("-", 1)[0].split(".")
    if len(parts) < 3 or not all(part.isdecimal() for part in parts[:3]):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _is_single_dataset_constraint_rejection(exc: ApiException) -> bool:
    # str() renders whichever of the deserialized data or the raw body is present.
    return exc.status == 400 and _SINGLE_DATASET_CONSTRAINT_ERROR in str(exc)


class TaskManagementJobExecutor:
    def __init__(
        self,
        models_client: ModelsV1Api,
        datasets_client: DatasetsV1Api,
        tasks_client: TasksV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ) -> None:
        self.models_client = models_client
        self.datasets_client = datasets_client
        self.tasks_client = tasks_client
        self.connector_constructor: ConnectorConstructor = connector_constructor
        self.logger: logging.Logger = logger

    def get_shield_connector_from_connector_id(
        self,
        connector_id: str,
    ) -> ShieldBaseConnector:
        conn: Connector = self.connector_constructor.get_connector_from_spec(
            connector_id,
        )

        if not isinstance(conn, ShieldBaseConnector):
            raise InvalidConnectorException(
                "Invalid connector, task management only works with Shield connectors.",
            )

        return conn

    def _lookup_models_task_datasets(self, model: Model) -> list[Dataset]:
        """
        Given a model, extracts its shield/task datasets. Post-consolidation a
        model carries two datasets (trace/evals + guardrails) bound to the same
        task; legacy un-migrated models carry one.
        """
        shield_dataset_refs = [
            dsr
            for dsr in model.datasets
            if dsr.dataset_connector_type == ConnectorType.SHIELD
            or dsr.dataset_connector_type == ConnectorType.ENGINE_INTERNAL
        ]

        if not shield_dataset_refs:
            raise ValueError(
                "Invalid model configuration. Cannot perform task management on models without a Shield dataset.",
            )

        return [
            self.datasets_client.get_dataset(dataset_id=dsr.dataset_id)
            for dsr in shield_dataset_refs
        ]

    @staticmethod
    def _extract_task_id_from_dataset(dataset: Dataset) -> str:
        """
        Given a dataset, extracts the task id from that dataset. Raises an error
        if the dataset does not contain a task id locator.
        """
        if not dataset.dataset_locator:
            raise ValueError(
                "Invalid dataset configuration. Cannot perform task management on models using joined datasets.",
            )

        task_id_fields = [
            f
            for f in dataset.dataset_locator.fields
            if f.key == SHIELD_DATASET_TASK_ID_FIELD
        ]
        if len(task_id_fields) != 1:
            raise ValueError(
                "Invalid dataset configuration. Cannot perform task management on Shield datasets without a task ID locator or with more than one task ID locator.",
            )
        return str(task_id_fields[0].value)

    def retrieve_task_management_resources_from_model_id(
        self,
        model_id: str,
    ) -> Tuple[Model, list[Dataset], ShieldBaseConnector, str]:
        """
        Given a scope model ID, will look up and return the Task's Datasets, ShieldConnector, and UUID of the task
        """
        # 1. fetch the model
        model = self.models_client.get_model(model_id=model_id)

        # 2. fetch the model's task datasets (two post-consolidation, one legacy)
        task_datasets = self._lookup_models_task_datasets(model=model)

        # 3. get the task ID from the dataset locators — all datasets on the
        # model must reference the same task
        task_ids = {
            self._extract_task_id_from_dataset(dataset=d) for d in task_datasets
        }
        if len(task_ids) != 1:
            raise ValueError(
                "Invalid model configuration. Cannot perform task management on models whose datasets reference different tasks.",
            )
        task_id = task_ids.pop()
        self.logger.info(f"Task found for model: {task_id}")

        # 4. get the connector for the datasets/task
        primary_dataset = task_datasets[0]
        if not primary_dataset.connector:
            raise ValueError(
                "Invalid dataset configuration. Cannot perform task management on models using joined datasets.",
            )

        conn = self.get_shield_connector_from_connector_id(
            primary_dataset.connector.id,
        )

        return model, task_datasets, conn, task_id

    def _get_task_transforms(
        self,
        connector: ShieldBaseConnector,
        task_id: str,
    ) -> list[TraceTransformResponse]:
        """
        Retrieves transforms for a task.

        Args:
            connector: Shield connector to use for querying
            task_id: Task ID to query

        Returns:
            List of TraceTransformResponse objects or empty list if fetch fails
        """
        try:
            self.logger.info(f"Fetching transforms for task {task_id}")
            transforms = connector.read_transforms(
                task_id=task_id,
                page_size=100,
            )
            self.logger.info(f"Retrieved {len(transforms)} transforms")
            return transforms
        except Exception as e:
            self.logger.warning(f"Failed to fetch transforms: {e}")
            return []

    def _get_task_continuous_evals(
        self,
        connector: ShieldBaseConnector,
        task_id: str,
    ) -> list[ContinuousEvalResponse]:
        """
        Retrieves continuous evals for a task.

        Args:
            connector: Shield connector to use for querying
            task_id: Task ID to query

        Returns:
            List of ContinuousEvalResponse objects or empty list if fetch fails
        """
        try:
            self.logger.info(f"Fetching continuous evals for task {task_id}")
            continuous_evals = connector.read_continuous_evals(
                task_id=task_id,
                page_size=100,
            )
            self.logger.info(f"Retrieved {len(continuous_evals)} continuous evals")
            return continuous_evals
        except Exception as e:
            self.logger.warning(f"Failed to fetch continuous evals: {e}")
            return []

    def _get_task_llm_evals(
        self,
        connector: ShieldBaseConnector,
        task_id: str,
    ) -> list[Eval]:
        """
        Retrieves LLM evals with their latest versions for a task.

        Args:
            connector: Shield connector to use for querying
            task_id: Task ID to query

        Returns:
            List of latest LLM eval versions or empty list if fetch fails
        """
        try:
            self.logger.info(f"Fetching LLM evals for task {task_id}")
            llm_evals_response = connector.read_llm_evals(
                task_id=task_id,
                page_size=100,
            )

            # For each eval, get the latest version
            llm_evals_with_versions: list[Eval] = []
            self.logger.info(
                f"Retrieved {len(llm_evals_response.llm_metadata)} LLM eval definitions",
            )

            for eval_metadata in llm_evals_response.llm_metadata:
                try:
                    self.logger.info(
                        f"Fetching latest version for eval: {eval_metadata.name}",
                    )
                    latest_version: Eval = connector.read_llm_eval_latest_version(
                        task_id=task_id,
                        eval_name=eval_metadata.name,
                    )
                    llm_evals_with_versions.append(latest_version)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to fetch latest version for eval {eval_metadata.name}: {e}",
                    )

            self.logger.info(
                f"Retrieved latest versions for {len(llm_evals_with_versions)} LLM evals",
            )
            return llm_evals_with_versions
        except Exception as e:
            self.logger.warning(f"Failed to fetch LLM evals: {e}")
            return []

    def upload_final_task_state(
        self,
        model_id: str,
        task: TaskResponse,
        connector: ShieldBaseConnector,
    ) -> None:
        """
        Uploads the final task state to the platform API, including eval state.

        Args:
            model_id: Model ID to upload state for
            task: Task response to upload
            connector: Shield connector to fetch eval state
        """
        # Fetch eval state components
        transforms = self._get_task_transforms(connector, task.id)
        continuous_evals = self._get_task_continuous_evals(connector, task.id)
        llm_evals = self._get_task_llm_evals(connector, task.id)

        # convert shield task response type to scope task response type since each is from a separate API client
        self.tasks_client.put_task_state_cache(
            model_id=model_id,
            put_task_state_cache_request=PutTaskStateCacheRequest(
                task=ScopeClientTypeConverter.task_response_api_to_scope_client(
                    task,
                ),
                transforms=transforms,
                continuous_evals=continuous_evals,
                evals=llm_evals,
            ),
        )
        self.logger.info(
            f"Uploaded final task state to the platform API with "
            f"{len(transforms)} transforms, {len(continuous_evals)} continuous evals, "
            f"and {len(llm_evals)} LLM evals",
        )


class _TaskRuleAdder:
    def __init__(self, connector: ShieldBaseConnector, logger: logging.Logger) -> None:
        self.connector = connector
        self.logger = logger

    def add_rules_to_task(
        self,
        task_id: str,
        rules_to_add: list[NewRuleRequest],
        rollback_on_failure: bool = True,
    ) -> None:
        created_rules = []
        try:
            for rule in rules_to_add:
                self.logger.info(f"Adding rule: {rule.name}")
                rule_resp = self.connector.add_rule_to_task(
                    task_id=task_id,
                    new_rule=rule,
                )
                created_rules.append(rule_resp)
                self.logger.info(f"Rule {rule.name} added")
        except Exception:
            if rollback_on_failure:
                self._rollback_created_rules(task_id, created_rules)
            raise

    def _rollback_created_rules(
        self,
        task_id: str,
        created_rules: list[RuleResponse],
    ) -> None:
        self.logger.warning(
            f"Error adding rules to task, rolling back {len(created_rules)} rules",
        )
        for rule in created_rules:
            self.logger.warning(f"Removing rule: {rule.name}")
            self.connector.delete_task_rule(task_id=task_id, rule_id=rule.id)
            self.logger.warning(f"Rule {rule.name} removed")
        self.logger.warning("Rollback complete")


class _TaskTraceMetricAdder:
    def __init__(
        self,
        connector: ShieldBaseConnector,
        logger: logging.Logger,
    ) -> None:
        self.connector = connector
        self.logger = logger

    def add_tracing_metrics_to_task(
        self,
        task_id: str,
        metrics_to_add: list[NewMetricRequest],
        rollback_on_failure: bool = True,
    ) -> None:
        created_metrics = []
        try:
            for metric in metrics_to_add:
                self.logger.info(f"Adding metric: {metric.name}")
                metric_resp = self.connector.add_metric_to_task(
                    task_id=task_id,
                    new_metric=metric,
                )
                created_metrics.append(metric_resp)
                self.logger.info(f"Metric {metric.name} added")
        except Exception:
            if rollback_on_failure:
                self._rollback_created_metrics(task_id, created_metrics)
            raise

    def _rollback_created_metrics(
        self,
        task_id: str,
        created_metrics: list[MetricResponse],
    ) -> None:
        self.logger.warning(
            f"Error adding metrics to task, rolling back {len(created_metrics)} metrics",
        )
        for metric in created_metrics:
            self.logger.warning(f"Removing metric: {metric.name}")
            self.connector.delete_task_metric(task_id=task_id, metric_id=metric.id)
            self.logger.warning(f"Metric {metric.name} removed")
        self.logger.warning("Rollback complete")


class _ValidationKeyManager:
    def __init__(
        self,
        conn: ShieldBaseConnector,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
    ) -> None:
        self.conn = conn
        self.tasks_client = tasks_client
        self.logger = logger

    def _create_task_validation_key_in_shield(
        self,
        task_id: str,
    ) -> PostTaskValidationAPIKey:
        api_key_resp = self.conn.create_task_validation_key(task_id)
        if not api_key_resp.key or not api_key_resp.description:
            error_msg = (
                "Api key value or description returned from shield was null. "
                "Failed to create task validation key."
            )
            self.logger.warning(error_msg)
            raise ValueError(error_msg)
        return PostTaskValidationAPIKey(
            id=api_key_resp.id,
            name=api_key_resp.description,
            key=api_key_resp.key,
        )

    def _create_task_validation_key_in_control_plane(
        self,
        model: Model,
        post_key: PostTaskValidationAPIKey,
        task_id: str,
    ) -> None:
        self.tasks_client.put_task_connection_info(
            model_id=model.id,
            put_task_connection_info=PutTaskConnectionInfo(
                api_host=self.conn.shield_external_host,
                validation_key=post_key,
            ),
        )
        self.logger.info(
            f"Created validation key for task: {model.name} with id {task_id}",
        )

    def _create_task_validation_key(self, model: Model, task_id: str) -> None:
        post_api_key = self._create_task_validation_key_in_shield(task_id)
        self._create_task_validation_key_in_control_plane(model, post_api_key, task_id)

    def _delete_task_validation_key(self, model: Model) -> None:
        try:
            curr_conn_info = self.tasks_client.get_task_connection_info(model.id)
        except arthur_client.api_bindings.exceptions.NotFoundException:
            # don't need to delete validation key if it doesn't already exist
            pass
        else:
            self.conn.delete_task_validation_key(curr_conn_info.validation_key.id)
            self.tasks_client.delete_connection_info(model.id)
            self.logger.info(
                f"Deleted existing validation key for model: {model.name} with id {model.id}.",
            )

    def replace_task_validation_key(self, model: Model, task_id: str) -> None:
        # create new key in shield
        post_key = self._create_task_validation_key_in_shield(task_id)

        # delete existing key
        self._delete_task_validation_key(model)

        # create new key in control plane
        self._create_task_validation_key_in_control_plane(model, post_key, task_id)


class _TaskDatasetAndModelCreator(_ValidationKeyManager):
    def __init__(
        self,
        task: TaskResponse,
        onboarding_identifier: str | None,
        conn: ShieldBaseConnector,
        datasets_client: DatasetsV1Api,
        models_client: ModelsV1Api,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
        legacy_task_type: str | None = None,
    ) -> None:
        self.conn = conn
        self.task = task
        self.onboarding_identifier = onboarding_identifier
        self.datasets_client = datasets_client
        self.models_client = models_client
        self.tasks_client = tasks_client
        self.logger = logger
        self.legacy_task_type = legacy_task_type

        super().__init__(self.conn, self.tasks_client, self.logger)

    def create(self) -> Tuple[Model, list[Dataset]]:
        # Post-consolidation every task carries BOTH datasets:
        #
        #   task ──┬── "<name> - traces"      (AGENTIC_TRACE: traces + evals)
        #          └── "<name> - guardrails"  (ARTHUR_SHIELD: inferences + rule results)
        #
        # Both bind to the same task via the task_id locator; one model links both.
        dataset_specs = [
            _TaskDatasetSpec(
                f"{self.task.name} - traces",
                common_to_client_put_dataset_schema(AGENTIC_TRACE_SCHEMA()),
                ModelProblemType.AGENTIC_TRACE,
            ),
            _TaskDatasetSpec(
                f"{self.task.name} - guardrails",
                common_to_client_put_dataset_schema(SHIELD_SCHEMA()),
                ModelProblemType.ARTHUR_SHIELD,
            ),
        ]

        if self._platform_supports_consolidated_task_datasets:
            try:
                return self._create_datasets_and_model(dataset_specs)
            except ApiException as e:
                if not _is_single_dataset_constraint_rejection(e):
                    raise
                # The probe read the platform as new but it enforces the old
                # constraint, so its release_version is unset or misreported.
                self.logger.warning(
                    "Platform rejected the consolidated task datasets, retrying with a single dataset",
                )

        # When the two-dataset attempt above ran, its rollback already deleted the
        # datasets it created, so this retry starts from a fresh dataset.
        legacy_problem_type = self._legacy_single_dataset_problem_type()
        legacy_spec = next(
            (
                spec
                for spec in dataset_specs
                if spec.model_problem_type == legacy_problem_type
            ),
            None,
        )
        if legacy_spec is None:
            # Only reachable if LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE is
            # changed to a problem type no task dataset uses. Say why rather than
            # letting a bare StopIteration out of next().
            raise ValueError(
                f"No task dataset is defined for problem type {legacy_problem_type}. "
                "LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE must name one of "
                f"{[spec.model_problem_type for spec in dataset_specs]}.",
            )
        # Log it: on this path the task is created without its complementary
        # dataset, and the job log is the only place that is visible.
        self.logger.warning(
            f"Creating the legacy single-dataset task shape ({legacy_problem_type.value}) "
            "because this platform predates the task dataset consolidation; the "
            "complementary dataset is not created",
        )
        # Pre-consolidation the single dataset was named after the task with no
        # suffix, so keep that name: it is what everything else on such a platform
        # looks like, and it leaves the platform's later consolidation migration a
        # clean name to derive the complementary dataset from.
        return self._create_datasets_and_model(
            [legacy_spec._replace(dataset_name=self.task.name)],
        )

    def _create_datasets_and_model(
        self,
        dataset_specs: list[_TaskDatasetSpec],
    ) -> Tuple[Model, list[Dataset]]:
        # enter rollback block so we can clean up datasets if any later creation fails
        datasets: list[Dataset] = []
        try:
            for spec in dataset_specs:
                dataset = self.datasets_client.post_connector_dataset(
                    connector_id=self.conn.connector_config.id,
                    post_dataset=PostDataset(
                        name=spec.dataset_name,
                        dataset_locator=DatasetLocator(
                            fields=[
                                DatasetLocatorField(
                                    key=SHIELD_DATASET_TASK_ID_FIELD,
                                    value=self.task.id,
                                ),
                            ],
                        ),
                        dataset_schema=spec.dataset_schema,
                        model_problem_type=spec.model_problem_type,
                    ),
                )
                self.logger.info(
                    f"Created dataset for task: {dataset.name} with id {dataset.id}",
                )
                datasets.append(dataset)

            model = self._create_task_model(datasets=datasets)
            return model, datasets
        except Exception:
            # if any dataset or model creation fails, roll back created datasets
            self.logger.warning(
                "Failed to create model for task, rolling back created datasets",
            )
            for dataset in datasets:
                self.datasets_client.delete_dataset(dataset_id=dataset.id)
            self.logger.warning("Dataset rollback complete")
            raise

    def _legacy_single_dataset_problem_type(self) -> ModelProblemType:
        # A pre-consolidation platform still sends task_type on the create-task job
        # spec, which says exactly which dataset that task used to get. The link
        # path has no equivalent signal.
        if self.legacy_task_type == _LEGACY_AGENTIC_TASK_TYPE:
            return ModelProblemType.AGENTIC_TRACE
        if self.legacy_task_type == _LEGACY_TRADITIONAL_TASK_TYPE:
            return ModelProblemType.ARTHUR_SHIELD
        return LEGACY_SINGLE_DATASET_FALLBACK_PROBLEM_TYPE

    @cached_property
    def _platform_supports_consolidated_task_datasets(self) -> bool:
        """
        Probed once per job. An unreachable or unreadable version reads as supported
        so a platform that does not publish its release version still gets the
        current shape, with the 400 fallback in create() as the safety net.
        """
        try:
            health = DefaultApi(
                self.models_client.api_client,
            ).health_check_api_health_get()
        except Exception as e:
            self.logger.warning(
                f"Could not read the platform release version from /api/health: {e}",
            )
            return True

        release_version = _parse_platform_release_version(health.release_version)
        if release_version is None:
            self.logger.warning(
                f"Platform reported an unreadable release version: {health.release_version}",
            )
            return True

        return release_version >= MIN_CONSOLIDATED_TASK_DATASETS_PLATFORM_RELEASE

    def _create_task_model(
        self,
        datasets: list[Dataset],
    ) -> Model:
        model = self.models_client.post_model(
            project_id=datasets[0].project_id,
            post_model=PostModel(
                name=self.task.name,
                description=f"This model corresponds to task {self.task.name} in connector {self.conn.connector_config.name}",
                onboarding_identifier=self.onboarding_identifier,
                dataset_ids=[dataset.id for dataset in datasets],
            ),
        )
        self.logger.info(f"Created model for task: {model.name} with id {model.id}")
        try:
            self._create_task_validation_key(model, self.task.id)
        except Exception:
            # if task validation key creation fails, we need to rollback model creation
            self.logger.warning(
                f"Failed to create validation key for task, rolling back created model {model.name} with id {model.id}",
            )
            self.models_client.delete_model(model_id=model.id)
            self.logger.warning("Model rollback complete")
            raise
        return model


class TaskCreator:
    def __init__(
        self,
        conn: ShieldBaseConnector,
        job_spec: CreateModelTaskJobSpec,
        datasets_client: DatasetsV1Api,
        models_client: ModelsV1Api,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
        legacy_task_type: str | None = None,
    ) -> None:
        self.conn = conn
        self.job_spec = job_spec
        self.datasets_client = datasets_client
        self.models_client = models_client
        self.tasks_client = tasks_client
        self.logger = logger
        self.legacy_task_type = legacy_task_type

    def create(self) -> Tuple[Model, list[Dataset], TaskResponse]:
        # create the task in shield
        task_resp = self.conn.create_task(
            name=self.job_spec.task_name,
            agent_metadata=self.job_spec.agent_metadata,
        )
        self.logger.info(
            f"Created task: {self.job_spec.task_name} with id {task_resp.id}",
        )

        # enter rollback block to delete the task if anything fails after this
        try:
            return self._add_rules_and_create_model_for_task(task_id=task_resp.id)
        except Exception:
            # failed to finish creating the task or model, roll it back
            self.logger.warning(
                f"Failed to create model for task, rolling back created task {task_resp.name} with id {task_resp.id}",
            )
            self.conn.delete_task(task_resp.id)
            self.logger.warning("Task rollback complete")
            # re-raise to propagate
            raise

    def _add_rules_and_create_model_for_task(
        self,
        task_id: str,
    ) -> Tuple[Model, list[Dataset], TaskResponse]:
        # Post-consolidation a task carries guardrail rules AND trace metrics.
        # Skip rollback on both because if there's a failure the whole task
        # will be deleted by the caller.
        rule_adder = _TaskRuleAdder(connector=self.conn, logger=self.logger)
        rule_adder.add_rules_to_task(
            task_id=task_id,
            rules_to_add=self.job_spec.initial_rules,
            rollback_on_failure=False,
        )

        trace_metric_adder = _TaskTraceMetricAdder(
            connector=self.conn,
            logger=self.logger,
        )
        trace_metric_adder.add_tracing_metrics_to_task(
            task_id=task_id,
            metrics_to_add=self.job_spec.initial_metrics,
            rollback_on_failure=False,
        )

        # get latest copy of task state to return after adding rules
        task = self.conn.read_task(task_id=task_id)

        # create the corresponding dataset and model in scope for the task
        # if these fail, let the exception propagate because we don't need to
        # delete rules individually for a task, the caller will delete the task
        dataset_model_creator = _TaskDatasetAndModelCreator(
            task=task,
            onboarding_identifier=self.job_spec.onboarding_identifier,
            conn=self.conn,
            datasets_client=self.datasets_client,
            models_client=self.models_client,
            tasks_client=self.tasks_client,
            logger=self.logger,
            legacy_task_type=self.legacy_task_type,
        )
        model, datasets = dataset_model_creator.create()
        return model, datasets, task


class ExistingTaskCreator(_ValidationKeyManager):
    def __init__(
        self,
        conn: ShieldBaseConnector,
        job_spec: CreateModelLinkTaskJobSpec,
        datasets_client: DatasetsV1Api,
        models_client: ModelsV1Api,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
    ) -> None:
        self.conn = conn
        self.job_spec = job_spec
        self.datasets_client = datasets_client
        self.models_client = models_client
        self.tasks_client = tasks_client
        self.logger = logger

        super().__init__(self.conn, self.tasks_client, self.logger)

    def link(self) -> Tuple[Model, list[Dataset], TaskResponse]:
        # fetch the task from shield
        task_resp = self.conn.read_task(task_id=self.job_spec.task_id)
        self.logger.info(f"Found task: {task_resp.name} with id {task_resp.id}")

        dataset_model_creator = _TaskDatasetAndModelCreator(
            task=task_resp,
            onboarding_identifier=self.job_spec.onboarding_identifier,
            conn=self.conn,
            datasets_client=self.datasets_client,
            models_client=self.models_client,
            tasks_client=self.tasks_client,
            logger=self.logger,
        )
        # don't use rollback here because if we fail we want the task to remain
        model, datasets = dataset_model_creator.create()
        return model, datasets, task_resp


class _TaskAndModelDeleter(_ValidationKeyManager):
    def __init__(
        self,
        conn: ShieldBaseConnector,
        datasets_client: DatasetsV1Api,
        models_client: ModelsV1Api,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
    ) -> None:
        self.conn = conn
        self.datasets_client = datasets_client
        self.models_client = models_client
        self.tasks_client = tasks_client
        self.logger = logger

        super().__init__(self.conn, self.tasks_client, self.logger)

    def _delete_task_idempotent(self, task_id: str, model: Model) -> None:
        try:
            # deactivate task API key
            self.logger.info(f"Deleting existing validation key for task.")
            self._delete_task_validation_key(model)
            self.logger.info(f"Deleting task.")
            self.conn.delete_task(task_id=task_id)
        except genai_client.exceptions.NotFoundException:
            pass

    def _delete_dataset_idempotent(self, dataset_id: str) -> None:
        try:
            self.datasets_client.delete_dataset(dataset_id=dataset_id)
        except arthur_client.api_bindings.exceptions.NotFoundException:
            pass

    def _delete_model_idempotent(self, model_id: str) -> None:
        try:
            self.models_client.delete_model(model_id=model_id)
        except arthur_client.api_bindings.exceptions.NotFoundException:
            pass

    def delete_task_and_related_resources(
        self,
        task_id: str,
        model: Model,
        datasets: list[Dataset],
    ) -> None:
        self.logger.info(f"Deleting task: {task_id}")
        self._delete_task_idempotent(task_id=task_id, model=model)
        self.logger.info(f"Task {task_id} deleted")

        # delete model in scope
        self.logger.info(f"Deleting model: {model.id}")
        self._delete_model_idempotent(model_id=model.id)
        self.logger.info(f"Model {model.id} deleted")

        # delete all of the task's datasets in scope
        for dataset in datasets:
            self.logger.info(f"Deleting dataset: {dataset.id}")
            self._delete_dataset_idempotent(dataset_id=dataset.id)
            self.logger.info(f"Dataset {dataset.id} deleted")


class CreateTaskJobExecutor(TaskManagementJobExecutor):
    def execute(
        self,
        job_spec: CreateModelTaskJobSpec,
        legacy_task_type: str | None = None,
    ) -> None:
        conn: ShieldBaseConnector = self.get_shield_connector_from_connector_id(
            str(job_spec.connector_id),
        )
        creator = TaskCreator(
            conn=conn,
            job_spec=job_spec,
            datasets_client=self.datasets_client,
            models_client=self.models_client,
            tasks_client=self.tasks_client,
            logger=self.logger,
            legacy_task_type=legacy_task_type,
        )
        model, _, task = creator.create()
        self.upload_final_task_state(
            model_id=model.id,
            task=task,
            connector=conn,
        )


class LinkTaskJobExecutor(TaskManagementJobExecutor):
    def execute(self, job_spec: CreateModelLinkTaskJobSpec) -> None:
        conn: ShieldBaseConnector = self.get_shield_connector_from_connector_id(
            str(job_spec.connector_id),
        )
        creator = ExistingTaskCreator(
            conn=conn,
            job_spec=job_spec,
            datasets_client=self.datasets_client,
            models_client=self.models_client,
            tasks_client=self.tasks_client,
            logger=self.logger,
        )
        model, _, task = creator.link()
        self.upload_final_task_state(
            model_id=model.id,
            task=task,
            connector=conn,
        )


class UpdateTaskJobExecutor(TaskManagementJobExecutor):
    def execute(self, job_spec: UpdateModelTaskRulesJobSpec) -> None:
        (
            model,
            dataset,
            connector,
            task_id,
        ) = self.retrieve_task_management_resources_from_model_id(
            model_id=str(job_spec.scope_model_id),
        )

        # add rules - if any fail to add, rollback ones that were already created
        # so we leave the task how we found it
        if job_spec.rules_to_add:
            rule_adder = _TaskRuleAdder(connector=connector, logger=self.logger)
            rule_adder.add_rules_to_task(
                task_id=task_id,
                rules_to_add=job_spec.rules_to_add,
                rollback_on_failure=True,
            )

        # the below steps should never fail unless the Shield API is down
        # in which case rolling back isn't possible

        # enable rules - this never seems to fail, even if the rule does not exist for the task
        if job_spec.rules_to_enable:
            for rule_id in job_spec.rules_to_enable:
                self.logger.info(f"Enabling rule: {rule_id}")
                connector.enable_task_rule(task_id=task_id, rule_id=str(rule_id))
                self.logger.info(f"Rule {rule_id} enabled")

        # disable rules - this never seems to fail, even if the rule does not exist for the task
        if job_spec.rules_to_disable:
            for rule_id in job_spec.rules_to_disable:
                self.logger.info(f"Disabling rule: {rule_id}")
                connector.disable_task_rule(task_id=task_id, rule_id=str(rule_id))
                self.logger.info(f"Rule {rule_id} disabled")

        # archive rules
        if job_spec.rules_to_archive:
            for rule_id in job_spec.rules_to_archive:
                self.logger.info(f"Deleting rule: {rule_id}")
                self._delete_task_rule_idempotent(
                    connector=connector,
                    task_id=task_id,
                    rule_id=str(rule_id),
                )
                self.logger.info(f"Rule {rule_id} deleted")

        # upload latest task definition
        self.logger.info(f"Fetching final task definition: {task_id}")
        shield_task_state = connector.read_task(task_id=task_id)
        self.upload_final_task_state(
            model_id=model.id,
            task=shield_task_state,
            connector=connector,
        )

    @staticmethod
    def _delete_task_rule_idempotent(
        connector: ShieldBaseConnector,
        task_id: str,
        rule_id: str,
    ) -> None:
        try:
            connector.delete_task_rule(task_id=task_id, rule_id=rule_id)
        except (
            genai_client.exceptions.NotFoundException,
            genai_client.exceptions.BadRequestException,
        ):
            pass


class DeleteTaskJobExecutor(TaskManagementJobExecutor):
    def execute(self, job_spec: DeleteModelTaskJobSpec) -> None:
        (
            model,
            datasets,
            connector,
            task_id,
        ) = self.retrieve_task_management_resources_from_model_id(
            model_id=str(job_spec.scope_model_id),
        )

        deleter = _TaskAndModelDeleter(
            connector,
            self.datasets_client,
            self.models_client,
            self.tasks_client,
            self.logger,
        )
        deleter.delete_task_and_related_resources(task_id, model, datasets)


class FetchTaskJobExecutor(TaskManagementJobExecutor):
    def execute(self, job_spec: FetchModelTaskJobSpec) -> None:
        (
            model,
            _,
            connector,
            task_id,
        ) = self.retrieve_task_management_resources_from_model_id(
            model_id=str(job_spec.scope_model_id),
        )
        self.logger.info(f"Fetching task: {task_id}")
        shield_task_state = connector.read_task(task_id=task_id)
        self.upload_final_task_state(
            model_id=model.id,
            task=shield_task_state,
            connector=connector,
        )


class RegenerateTaskValidationKeyJobExecutor(TaskManagementJobExecutor):
    def execute(self, job_spec: RegenerateTaskValidationKeyJobSpec) -> None:
        (
            model,
            _,
            connector,
            task_id,
        ) = self.retrieve_task_management_resources_from_model_id(
            model_id=str(job_spec.scope_model_id),
        )
        manager = _ValidationKeyManager(
            conn=connector,
            tasks_client=self.tasks_client,
            logger=self.logger,
        )
        self.logger.info(f"Regenerating validation key for task: {task_id}")
        manager.replace_task_validation_key(model, task_id)
