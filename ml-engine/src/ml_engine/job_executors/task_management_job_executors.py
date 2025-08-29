import logging
from typing import Tuple

import arthur_client
from arthur_client.api_bindings import (
    ConnectorType,
    CreateModelLinkTaskJobSpec,
    Dataset,
    DatasetLocator,
    DatasetLocatorField,
    DatasetsV1Api,
    Model,
    ModelProblemType,
    ModelsV1Api,
    PostDataset,
    PostModel,
    PostTaskValidationAPIKey,
    PutTaskConnectionInfo,
    PutTaskStateCacheRequest,
    RegenerateTaskValidationKeyJobSpec,
    TasksV1Api,
)
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.enums import TaskType
from arthur_common.models.schema_definitions import AGENTIC_TRACE_SCHEMA, SHIELD_SCHEMA
from arthur_common.models.task_job_specs import (
    CreateModelLinkTaskJobSpec,
    CreateModelTaskJobSpec,
    DeleteModelTaskJobSpec,
    FetchModelTaskJobSpec,
    UpdateModelTaskRulesJobSpec,
)
from connectors.connector import Connector
from connectors.shield_connector import ShieldBaseConnector

# from tools.api_client_type_converters import ScopeClientTypeConverter
from tools.connector_constructor import ConnectorConstructor
from tools.converters import common_to_client_put_dataset_schema

import genai_client.exceptions
from genai_client.models import (
    MetricResponse,
    NewMetricRequest,
    NewRuleRequest,
    RuleResponse,
    TaskResponse,
)


class InvalidConnectorException(Exception):
    pass


class _TaskManagementJobExecutor:

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

    def _lookup_models_single_shield_dataset(self, model: Model) -> Dataset:
        """
        Given a model, extracts the single shield dataset from that model. Will
        raise an error if that assumption is not valid.
        """
        shield_datasets = [
            dsr
            for dsr in model.datasets
            if dsr.dataset_connector_type == ConnectorType.SHIELD
            or dsr.dataset_connector_type == ConnectorType.ENGINE_INTERNAL
        ]

        # if the model has more than one shield dataset, raise error
        if len(shield_datasets) > 1:
            raise ValueError(
                "Invalid model configuration. Cannot perform task management on models with more than one Shield Dataset.",
            )

        task_dataset_ref = shield_datasets[0]
        return self.datasets_client.get_dataset(dataset_id=task_dataset_ref.dataset_id)

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
    ) -> Tuple[Model, Dataset, ShieldBaseConnector, str]:
        """
        Given a scope model ID, will look up and return the Task's Dataset, ShieldConnector, and UUID of the task
        """
        # 1. fetch the model
        model = self.models_client.get_model(model_id=model_id)

        # 2. fetch the model's single dataset
        task_dataset = self._lookup_models_single_shield_dataset(model=model)

        # 3. get the task ID from the dataset locator
        task_id = self._extract_task_id_from_dataset(dataset=task_dataset)
        self.logger.info(f"Task found for model: {task_id}")

        # 4. get the connector for the dataset/task
        if not task_dataset.connector:
            raise ValueError(
                "Invalid dataset configuration. Cannot perform task management on models using joined datasets.",
            )

        conn = self.get_shield_connector_from_connector_id(task_dataset.connector.id)

        return model, task_dataset, conn, task_id

    def upload_final_task_state(self, model_id: str, task: TaskResponse) -> None:
        # convert shield task response type to scope task response type since each is from a separate API client
        self.tasks_client.put_task_state_cache(
            model_id=model_id,
            put_task_state_cache_request=PutTaskStateCacheRequest(
                task=task,
            ),
        )
        self.logger.info(f"Uploaded final task state to the platform API")


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
            f"Error adding metrics to task, rolling back {len(created_metrics)} metrics"
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
    ) -> None:
        self.conn = conn
        self.task = task
        self.onboarding_identifier = onboarding_identifier
        self.datasets_client = datasets_client
        self.models_client = models_client
        self.tasks_client = tasks_client
        self.logger = logger

        super().__init__(self.conn, self.tasks_client, self.logger)

    def create(self) -> Tuple[Model, Dataset]:
        # Differentiate between agentic and shield tasks
        if self.task.is_agentic:
            dataset_schema = common_to_client_put_dataset_schema(AGENTIC_TRACE_SCHEMA())
            model_problem_type = ModelProblemType.AGENTIC_TRACE
        else:
            dataset_schema = common_to_client_put_dataset_schema(SHIELD_SCHEMA())
            model_problem_type = ModelProblemType.ARTHUR_SHIELD

        # create dataset
        dataset = self.datasets_client.post_connector_dataset(
            connector_id=self.conn.connector_config.id,
            post_dataset=PostDataset(
                name=self.task.name,
                dataset_locator=DatasetLocator(
                    fields=[
                        DatasetLocatorField(
                            key=SHIELD_DATASET_TASK_ID_FIELD,
                            value=self.task.id,
                        ),
                    ],
                ),
                dataset_schema=dataset_schema,
                model_problem_type=model_problem_type,
            ),
        )
        self.logger.info(
            f"Created dataset for task: {dataset.name} with id {dataset.id}",
        )

        # enter rollback block so we can clean up the dataset if model creation fails
        try:
            model = self._create_task_model(dataset=dataset)
            return model, dataset
        except Exception:
            # if model creation fails, we need to rollback dataset creation
            self.logger.warning(
                f"Failed to create model for task, rolling back created dataset {dataset.name} with id {dataset.id}",
            )
            self.datasets_client.delete_dataset(dataset_id=dataset.id)
            self.logger.warning("Dataset rollback complete")
            raise

    def _create_task_model(
        self,
        dataset: Dataset,
    ) -> Model:
        model = self.models_client.post_model(
            project_id=dataset.project_id,
            post_model=PostModel(
                name=self.task.name,
                description=f"This model corresponds to task {self.task.name} in connector {self.conn.connector_config.name}",
                onboarding_identifier=self.onboarding_identifier,
                dataset_ids=[dataset.id],
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
    ) -> None:
        self.conn = conn
        self.job_spec = job_spec
        self.datasets_client = datasets_client
        self.models_client = models_client
        self.tasks_client = tasks_client
        self.logger = logger

    def create(self) -> Tuple[Model, Dataset, TaskResponse]:
        # create the task in shield
        is_agentic = self.job_spec.task_type == TaskType.AGENTIC
        task_resp = self.conn.create_task(
            name=self.job_spec.task_name, is_agentic=is_agentic
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
    ) -> Tuple[Model, Dataset, TaskResponse]:
        # Add tracing metrics to an agentic task
        if self.job_spec.task_type == TaskType.AGENTIC:
            trace_metric_adder = _TaskTraceMetricAdder(
                connector=self.conn, logger=self.logger
            )
            trace_metric_adder.add_tracing_metrics_to_task(
                task_id=task_id,
                metrics_to_add=self.job_spec.initial_metrics,
                rollback_on_failure=False,
            )
        else:
            # add rules to the task in shield
            # skip rollback because if there's a failure the whole task will be deleted
            rule_adder = _TaskRuleAdder(connector=self.conn, logger=self.logger)
            rule_adder.add_rules_to_task(
                task_id=task_id,
                rules_to_add=self.job_spec.initial_rules,
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
        )
        model, dataset = dataset_model_creator.create()
        return model, dataset, task


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

    def link(self) -> Tuple[Model, Dataset, TaskResponse]:
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
        model, dataset = dataset_model_creator.create()
        return model, dataset, task_resp


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
        dataset: Dataset,
    ) -> None:
        self.logger.info(f"Deleting task: {task_id}")
        self._delete_task_idempotent(task_id=task_id, model=model)
        self.logger.info(f"Task {task_id} deleted")

        # delete model in scope
        self.logger.info(f"Deleting model: {model.id}")
        self._delete_model_idempotent(model_id=model.id)
        self.logger.info(f"Model {model.id} deleted")

        # delete dataset in scope
        self.logger.info(f"Deleting dataset: {dataset.id}")
        self._delete_dataset_idempotent(dataset_id=dataset.id)
        self.logger.info(f"Dataset {dataset.id} deleted")


class CreateTaskJobExecutor(_TaskManagementJobExecutor):

    def execute(self, job_spec: CreateModelTaskJobSpec) -> None:
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
        )
        model, _, task = creator.create()
        self.upload_final_task_state(
            model_id=model.id,
            task=task,
        )


class LinkTaskJobExecutor(_TaskManagementJobExecutor):

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
        )


class UpdateTaskJobExecutor(_TaskManagementJobExecutor):

    def execute(self, job_spec: UpdateModelTaskRulesJobSpec) -> None:
        model, dataset, connector, task_id = (
            self.retrieve_task_management_resources_from_model_id(
                model_id=str(job_spec.scope_model_id),
            )
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
        self.upload_final_task_state(model.id, shield_task_state)

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


class DeleteTaskJobExecutor(_TaskManagementJobExecutor):

    def execute(self, job_spec: DeleteModelTaskJobSpec) -> None:
        model, dataset, connector, task_id = (
            self.retrieve_task_management_resources_from_model_id(
                model_id=str(job_spec.scope_model_id),
            )
        )

        deleter = _TaskAndModelDeleter(
            connector,
            self.datasets_client,
            self.models_client,
            self.tasks_client,
            self.logger,
        )
        deleter.delete_task_and_related_resources(task_id, model, dataset)


class FetchTaskJobExecutor(_TaskManagementJobExecutor):

    def execute(self, job_spec: FetchModelTaskJobSpec) -> None:
        model, _, connector, task_id = (
            self.retrieve_task_management_resources_from_model_id(
                model_id=str(job_spec.scope_model_id),
            )
        )
        self.logger.info(f"Fetching task: {task_id}")
        shield_task_state = connector.read_task(task_id=task_id)
        self.upload_final_task_state(model.id, shield_task_state)


class RegenerateTaskValidationKeyJobExecutor(_TaskManagementJobExecutor):

    def execute(self, job_spec: RegenerateTaskValidationKeyJobSpec) -> None:
        model, _, connector, task_id = (
            self.retrieve_task_management_resources_from_model_id(
                model_id=str(job_spec.scope_model_id),
            )
        )
        manager = _ValidationKeyManager(
            conn=connector,
            tasks_client=self.tasks_client,
            logger=self.logger,
        )
        self.logger.info(f"Regenerating validation key for task: {task_id}")
        manager.replace_task_validation_key(model, task_id)
