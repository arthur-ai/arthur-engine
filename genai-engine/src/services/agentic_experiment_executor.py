"""
Service for asynchronously executing agentic experiments in the background.

This module handles the execution of agentic experiments by:
1. Rendering HTTP requests from templates for each test case
2. Making HTTP requests to agent endpoints
3. Waiting for traces to appear in the database (linked via session_id)
4. Running transforms on traces
5. Executing evaluations on transform outputs
6. Updating experiment and test case statuses throughout execution
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import requests
from arthur_common.models.common_schemas import PaginationParameters
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from db_models.agentic_experiment_models import (
    DatabaseAgenticExperiment,
    DatabaseAgenticExperimentTestCase,
    DatabaseAgenticExperimentTestCaseAgenticResult,
)
from repositories.agentic_experiment_repository import AgenticExperimentRepository
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.agentic_experiment_schemas import (
    AgenticEvalRef,
    AgenticEvalResultSummaries,
    AgenticSummaryResults,
    HttpTemplate,
    RequestTimeParameter,
    TemplateVariableMapping,
)
from schemas.base_experiment_schemas import (
    EvalResultSummary,
    TestCaseStatus,
)
from services.experiment_executor import BaseExperimentExecutor
from services.prompt.chat_completion_service import ChatCompletionService
from utils.constants import AGENT_EXPERIMENT_SESSION_PREFIX
from utils.transform_executor import execute_transform

logger = logging.getLogger(__name__)

# Maximum time to wait for a trace to appear (in seconds)
MAX_TRACE_WAIT_TIME = 300  # 5 minutes
# Polling interval for checking trace existence (in seconds)
TRACE_POLL_INTERVAL = 2  # 2 seconds


class AgenticExperimentExecutor(BaseExperimentExecutor):
    """Handles execution of agentic experiments"""

    def __init__(self) -> None:
        super().__init__()
        # Reuse ChatCompletionService for template variable rendering
        self.chat_completion_service = ChatCompletionService()

    def _get_database_experiment(
        self,
        experiment_id: str,
        session: Session,
    ) -> Optional[DatabaseAgenticExperiment]:
        agentic_experiment_repo = AgenticExperimentRepository(session)
        try:
            return agentic_experiment_repo._get_db_experiment(experiment_id)
        except HTTPException:
            logger.error(
                f"Agentic experiment with ID {experiment_id} not found.",
            )
            return None

    def _get_db_test_cases(
        self,
        experiment_id: str,
        db_session: Session,
        status_filter: Optional[TestCaseStatus] = None,
    ) -> List[DatabaseAgenticExperimentTestCase]:
        agentic_experiment_repo = AgenticExperimentRepository(db_session)
        return agentic_experiment_repo._get_db_test_cases(experiment_id, status_filter)

    def _get_db_test_case(
        self,
        test_case_id: str,
        db_session: Session,
    ) -> Optional[DatabaseAgenticExperimentTestCase]:
        agentic_experiment_repo = AgenticExperimentRepository(db_session)
        return agentic_experiment_repo._get_db_test_case(test_case_id)

    def _execute_experiment_outputs(
        self,
        db_session: Session,
        test_case: DatabaseAgenticExperimentTestCase,
        request_time_parameters: Optional[List[RequestTimeParameter]] = None,
    ) -> bool:
        """
        Execute HTTP request for a test case.

        Args:
            db_session: Database session
            test_case: Test case to execute HTTP request for
            request_time_parameters: Optional dict of request-time parameters to use during execution

        Returns:
            True if HTTP request executed successfully, False otherwise
        """
        try:
            # Get the agentic result (should exist from test case creation)
            agentic_result = test_case.agentic_result
            if not agentic_result:
                logger.error(
                    f"Agentic result not found for test case {test_case.id}",
                )
                return False

            # Execute the HTTP request
            success = self._execute_http_request(
                db_session,
                agentic_result,
                test_case,
                request_time_parameters,
            )
            return success
        except Exception as e:
            logger.error(
                f"Error executing HTTP request for test case {test_case.id}: {e}",
                exc_info=True,
            )
            return False

    def _calculate_total_test_case_cost(
        self,
        test_case: DatabaseAgenticExperimentTestCase,
    ) -> float:
        """
        Calculate the total cost for an agentic test case.
        Note: HTTP requests don't have cost tracking, so we only sum eval costs.

        Args:
            test_case: Test case to calculate cost for

        Returns:
            Total cost as a float
        """
        total_cost = 0.0
        if test_case.agentic_result:
            # Add eval costs
            total_cost += self._calculate_total_cost_eval_scores(
                test_case.agentic_result.eval_scores,
            )
        return total_cost

    def _generate_variable_value(
        self,
        generator_type: str,
        variable_name: str,
    ) -> Optional[str]:
        """
        Generate a value for a variable based on the generator type.

        Args:
            generator_type: Type of generator (e.g., "uuid")
            variable_name: Name of the variable (for logging)

        Returns:
            Generated value as a string, or None if generator_type is not supported
        """
        if generator_type == "uuid":
            return str(uuid4())
        else:
            logger.warning(
                f"Unknown generator_type '{generator_type}' for variable '{variable_name}', skipping",
            )
            return None

    def _build_variable_map(
        self,
        test_case: DatabaseAgenticExperimentTestCase,
        experiment: DatabaseAgenticExperiment,
        request_time_parameters: Optional[List[RequestTimeParameter]] = None,
    ) -> Dict[str, str]:
        """
        Build variable map from test case input variables, request-time parameters, and generated variables.
        Also updates test_case.template_input_variables with generated values so they are persisted.

        Args:
            test_case: Test case with template_input_variables (will be updated with generated values)
            experiment: Experiment with template_variable_mapping
            request_time_parameters: Optional list of request-time parameters
                (name field should match variable_name in template_variable_mapping)

        Returns:
            Dictionary mapping variable names to values
        """
        variable_map = {}

        # Add variables from test case input (dataset columns)
        for var in test_case.template_input_variables:
            variable_map[var["variable_name"]] = var["value"]

        # Load template variable mappings to find which variables need generation or request-time parameters
        template_mappings = [
            TemplateVariableMapping.model_validate(mapping)
            for mapping in experiment.template_variable_mapping
        ]

        # Generate values for generated variables and add to test case
        # Reuse existing generated values if already present (from previous call), otherwise generate new ones
        for mapping in template_mappings:
            if mapping.source.type == "generated":
                variable_name = mapping.variable_name

                # Check if this generated variable already exists in template_input_variables
                # (from a previous call to _build_variable_map)
                existing_value = None
                for var in test_case.template_input_variables:
                    if var["variable_name"] == variable_name:
                        existing_value = var["value"]
                        break

                if existing_value:
                    # Reuse the existing generated value (e.g., from first call)
                    generated_value = existing_value
                else:
                    # Generate a new value (first time this variable is being generated)
                    generated_value = self._generate_variable_value(
                        mapping.source.generator_type,
                        variable_name,
                    )
                    if generated_value is None:
                        continue

                    # Add to test case template_input_variables for persistence
                    test_case.template_input_variables.append(
                        {
                            "variable_name": variable_name,
                            "value": generated_value,
                        },
                    )
                    # Flag the JSON column as modified so SQLAlchemy detects the change
                    flag_modified(test_case, "template_input_variables")

                # Add to variable map (use existing or newly generated value)
                variable_map[variable_name] = generated_value

        # Add request-time parameters by looking up values from template_variable_mapping
        if request_time_parameters:
            # Convert list to dict for easier lookup by name
            request_time_params_dict = {
                param.name: param.value for param in request_time_parameters
            }
            for mapping in template_mappings:
                if mapping.source.type == "request_time_parameter":
                    # Use variable_name to look up the parameter value
                    variable_name = mapping.variable_name
                    if variable_name in request_time_params_dict:
                        # Map the variable_name to the parameter value
                        variable_map[variable_name] = request_time_params_dict[
                            variable_name
                        ]

        return variable_map

    def _render_http_template(
        self,
        http_template: HttpTemplate,
        variable_map: Dict[str, str],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Render HTTP template with variable substitution.

        Args:
            http_template: HTTP template configuration
            variable_map: Dictionary mapping variable names to values
            session_id: Optional session ID to include in the request headers

        Returns:
            Dictionary with rendered url, headers, and body (body is a string)
        """
        # Render URL
        rendered_url = self.chat_completion_service._replace_variables_in_text(
            variable_map,
            http_template.endpoint_url,
        )

        # Render headers
        rendered_headers = {}
        for header in http_template.headers:
            rendered_name = self.chat_completion_service._replace_variables_in_text(
                variable_map,
                header.name,
            )
            rendered_value = self.chat_completion_service._replace_variables_in_text(
                variable_map,
                header.value,
            )
            rendered_headers[rendered_name] = rendered_value

        # Render request body (it's already a string with template variables)
        rendered_body = self.chat_completion_service._replace_variables_in_text(
            variable_map,
            http_template.request_body,
        )

        # Add session_id to headers if provided
        if session_id:
            rendered_headers["X-Session-Id"] = session_id

        return {
            "url": rendered_url,
            "headers": rendered_headers,
            "body": rendered_body,
        }

    def _execute_http_request(
        self,
        db_session: Session,
        agentic_result: DatabaseAgenticExperimentTestCaseAgenticResult,
        test_case: DatabaseAgenticExperimentTestCase,
        request_time_parameters: Optional[List[RequestTimeParameter]] = None,
    ) -> bool:
        """
        Execute HTTP request to agent endpoint and wait for trace.

        Args:
            db_session: Database session
            agentic_result: Agentic result record to populate
            test_case: Test case containing input variables
            request_time_parameters: Optional dict of request-time parameters to use during execution

        Returns:
            True if HTTP request executed successfully and trace found, False otherwise
        """
        try:
            experiment = test_case.experiment

            # Load HTTP template from experiment
            http_template = HttpTemplate.model_validate(experiment.http_template)

            # Generate a unique session_id to link request to trace
            session_id = f"{AGENT_EXPERIMENT_SESSION_PREFIX}-{uuid4()}"

            # Build variable map from test case and request-time parameters
            # WARNING: do not include request-time parameters yet because we want to store the rendered request
            # in the DB WITHOUT these sensitive values
            variable_map = self._build_variable_map(
                test_case,
                experiment,
                request_time_parameters=None,
            )

            # Render HTTP template with variables (include session_id)
            rendered_request = self._render_http_template(
                http_template,
                variable_map,
                session_id,
            )

            # Save request details to database (without request-time parameters)
            # WARNING: REQUEST-TIME PARAMETERS MUST BE SANITIZED FROM THESE DETAILS. THEY SHOULD NOT BE EVALUATED
            # BEFORE THIS POINT.
            agentic_result.request_url = rendered_request["url"]
            agentic_result.request_headers = rendered_request["headers"]
            agentic_result.request_body = rendered_request[
                "body"
            ]  # body is now a string
            db_session.commit()

            # Make HTTP request - at this point, render the sensitive request time parameters to include in the request
            # request_time_parameters is already a List[RequestTimeParameter] or None
            variable_map = self._build_variable_map(
                test_case,
                experiment,
                request_time_parameters=request_time_parameters,
            )
            rendered_request = self._render_http_template(
                http_template,
                variable_map,
                session_id,
            )

            try:
                # Determine content type and send body appropriately
                # If body looks like JSON, set Content-Type header and send as data
                # Otherwise send as-is
                headers_for_request = dict(rendered_request["headers"])
                body_str = rendered_request["body"]

                # Try to parse as JSON to determine if we should set Content-Type
                try:
                    json.loads(body_str)
                    # If it's valid JSON, set Content-Type if not already set
                    if "Content-Type" not in headers_for_request:
                        headers_for_request["Content-Type"] = "application/json"
                except (json.JSONDecodeError, ValueError):
                    # Not valid JSON, don't set Content-Type (let requests handle it)
                    pass

                response = requests.post(
                    rendered_request["url"],
                    headers=headers_for_request,
                    data=body_str,
                    timeout=300,  # 5 minute timeout
                )
                status_code = response.status_code
                try:
                    response_body = response.json()
                except ValueError:
                    # If response is not JSON, use text
                    response_body = {"text": response.text}
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"HTTP request failed for test case {test_case.id}: {e}",
                )
                agentic_result.response_output = {
                    "status_code": None,
                    "response_body": {"error": str(e)},
                    "trace_id": None,
                }
                db_session.commit()
                return False

            if not response.ok:
                # mark response as failed if response code is not 2XX or 3XX
                logger.error(
                    f"HTTP request failed for test case {test_case.id}: status code was {response.status_code}",
                )
                agentic_result.response_output = {
                    "status_code": response.status_code,
                    "response_body": {"error": str(response.reason)},
                    "trace_id": None,
                }
                db_session.commit()
                return False

            # Wait for trace to appear in database
            trace_id = self._wait_for_trace(
                db_session,
                session_id,
            )

            if not trace_id:
                logger.warning(
                    f"Trace not found for session_id {session_id} after waiting",
                )
                agentic_result.response_output = {
                    "status_code": status_code,
                    "response_body": response_body,
                    "trace_id": None,
                }
                db_session.commit()
                return False

            # Save response and trace_id
            agentic_result.response_output = {
                "status_code": status_code,
                "response_body": response_body,
                "trace_id": trace_id,
            }
            db_session.commit()

            logger.info(
                f"Executed HTTP request for test case {test_case.id}, trace_id: {trace_id}",
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing HTTP request for test case {test_case.id}: {e}",
                exc_info=True,
            )
            return False

    @staticmethod
    def _wait_for_trace(
        db_session: Session,
        session_id: str,
    ) -> Optional[str]:
        """
        Wait for trace to appear in database linked by session_id.

        Args:
            db_session: Database session
            session_id: Session ID to link request to trace

        Returns:
            Trace ID if found, None otherwise
        """
        tasks_metrics_repo = TasksMetricsRepository(db_session)
        metrics_repo = MetricRepository(db_session)
        span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)

        start_time = time.time()
        while time.time() - start_time < MAX_TRACE_WAIT_TIME:
            try:
                # Query traces by session_id
                # Use get_session_traces which queries by session_id
                pagination_params = PaginationParameters(
                    page=0,
                    page_size=10,
                    sort="desc",
                )
                count, traces = span_repo.get_session_traces(
                    session_id=session_id,
                    pagination_parameters=pagination_params,
                )

                if traces and len(traces) > 0:
                    # Return the first trace ID
                    return traces[0].trace_id

            except Exception as e:
                logger.warning(
                    f"Error querying traces for session_id {session_id}: {e}",
                )

            # Wait before polling again
            time.sleep(TRACE_POLL_INTERVAL)

        logger.warning(
            f"Trace not found for session_id {session_id} after {MAX_TRACE_WAIT_TIME} seconds",
        )
        return None

    def _execute_evaluations(
        self,
        db_session: Session,
        test_case: DatabaseAgenticExperimentTestCase,
    ) -> bool:
        """
        Execute all evaluations for an agentic test case.

        Args:
            db_session: Database session
            test_case: Test case containing agentic result to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        try:
            if not test_case.agentic_result:
                logger.error(
                    f"Agentic result not found for test case {test_case.id}",
                )
                return False

            success = self._execute_evaluations_for_result(
                db_session,
                test_case.agentic_result,
            )
            return success
        except Exception as e:
            logger.error(
                f"Error executing evaluations for test case {test_case.id}: {e}",
                exc_info=True,
            )
            return False

    def _execute_evaluations_for_result(
        self,
        db_session: Session,
        agentic_result: DatabaseAgenticExperimentTestCaseAgenticResult,
    ) -> bool:
        """
        Execute all evaluations for an agentic result.

        Args:
            db_session: Database session
            agentic_result: Agentic result with trace to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        try:
            # Execute all eval scores using the relationship, tracking failures but continuing
            any_eval_failed = False
            for eval_score in agentic_result.eval_scores:
                success = self._execute_single_eval(
                    db_session,
                    eval_score,
                    agentic_result,
                )
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Eval {eval_score.eval_name} v{eval_score.eval_version} failed for agentic result {agentic_result.id}, continuing with other evals",
                    )

            return not any_eval_failed

        except Exception as e:
            logger.error(
                f"Error executing evaluations for agentic result {agentic_result.id}: {e}",
                exc_info=True,
            )
            return False

    def _execute_single_eval(
        self,
        db_session: Session,
        eval_score: Any,  # DatabaseAgenticExperimentTestCaseAgenticResultEvalScore
        agentic_result: DatabaseAgenticExperimentTestCaseAgenticResult,
    ) -> bool:
        """
        Execute a single evaluation.

        Args:
            db_session: Database session
            eval_score: Eval score record to populate
            agentic_result: Agentic result with trace

        Returns:
            True if eval executed successfully, False otherwise
        """
        try:
            # Get the experiment using the agentic_result relationship
            experiment = agentic_result.test_case.experiment

            # Get trace_id from agentic_result
            trace_id = agentic_result.response_output.get("trace_id")
            if not trace_id:
                logger.error(
                    f"No trace_id found for agentic result {agentic_result.id}",
                )
                return False

            # Find the eval config from the experiment
            eval_config = None
            for config in experiment.eval_configs:
                if config["name"] == eval_score.eval_name and str(
                    config["version"],
                ) == str(eval_score.eval_version):
                    eval_config = config
                    break

            if not eval_config:
                logger.error(
                    f"Eval config for {eval_score.eval_name} v{eval_score.eval_version} not found in experiment",
                )
                return False

            # Validate and fix eval config structure if needed (handle deserialization issues)
            # Convert eval_config to AgenticEvalRef to ensure correct structure
            try:
                validated_eval_ref = AgenticEvalRef.model_validate(eval_config)
                # Convert back to dict for compatibility with existing code
                eval_config = validated_eval_ref.model_dump(mode="python")
            except Exception as e:
                logger.warning(
                    f"Failed to validate eval config structure for {eval_score.eval_name}, using as-is: {e}",
                )

            # Get transform for this eval
            transform_id = eval_config.get("transform_id")
            if not transform_id:
                logger.error(
                    f"Transform ID not found in eval config for {eval_score.eval_name}",
                )
                return False

            # Get trace
            tasks_metrics_repo = TasksMetricsRepository(db_session)
            metrics_repo = MetricRepository(db_session)
            span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)

            trace = span_repo.get_trace_by_id(
                trace_id=trace_id,
                include_metrics=False,
                compute_new_metrics=False,
            )

            if not trace:
                logger.error(f"Trace {trace_id} not found")
                return False

            # Get transform definition
            transform_repo = TraceTransformRepository(db_session)
            transform = transform_repo.get_transform_by_id(transform_id)
            if not transform:
                logger.error(f"Transform {transform_id} not found")
                return False

            # Execute transform on trace
            transform_results = execute_transform(trace, transform.definition)

            # Build variable map from eval variable mappings
            variable_map = self._build_eval_variable_map(
                eval_config,
                agentic_result.test_case,
                transform_results.variables,
                agentic_result,
            )

            # Set eval_input_variables
            eval_input_variables = [
                {"variable_name": name, "value": value}
                for name, value in variable_map.items()
            ]
            eval_score.eval_input_variables = eval_input_variables
            db_session.commit()

            # Execute eval using shared method
            return self._execute_eval_with_variable_map(
                db_session,
                eval_score,
                experiment,
            )

        except Exception as e:
            logger.error(
                f"Error executing eval {eval_score.eval_name} v{eval_score.eval_version}: {e}",
                exc_info=True,
            )
            return False

    def _build_eval_variable_map(
        self,
        eval_config: Dict[str, Any],
        test_case: DatabaseAgenticExperimentTestCase,
        transform_variables: List[Any],  # List[VariableTemplateValue]
        agentic_result: DatabaseAgenticExperimentTestCaseAgenticResult,
    ) -> Dict[str, str]:
        """
        Build variable map for eval from dataset columns and transform variables.

        Args:
            eval_config: Eval configuration with variable_mapping
            test_case: Test case with template_input_variables
            transform_variables: Variables extracted from transform

        Returns:
            Dictionary mapping variable names to values
        """
        variable_map = {}

        # Create a map of transform variable names to values
        transform_var_map = {var.name: var.value for var in transform_variables}

        # Process each variable mapping in the eval config
        for mapping in eval_config.get("variable_mapping", []):
            variable_name = mapping["variable_name"]
            source = mapping["source"]

            if source["type"] == "dataset_column":
                # Get value from test case input variables
                column_name = source["dataset_column"]["name"]
                for var in test_case.template_input_variables:
                    if var["variable_name"] == variable_name:
                        variable_map[variable_name] = var["value"]
                        break
            elif source["type"] == "experiment_output":
                # Agentic experiments only support transform variables (not json_path)
                # The experiment_output should be a TransformVariableExperimentOutputSource
                experiment_output = source.get("experiment_output", {})

                # For agentic experiments, experiment_output is always a TransformVariableExperimentOutputSource
                # The type field may be missing in stored JSON, so check for transform_variable_name directly
                transform_var_name = experiment_output.get("transform_variable_name")

                if transform_var_name:
                    if transform_var_name in transform_var_map:
                        variable_map[variable_name] = transform_var_map[
                            transform_var_name
                        ]
                    else:
                        available_vars = list(transform_var_map.keys())
                        logger.warning(
                            f"Transform variable '{transform_var_name}' not found in transform results. "
                            f"Available variables: {available_vars}. "
                            f"Eval variable '{variable_name}' will be set to empty string.",
                        )
                        variable_map[variable_name] = ""
                else:
                    # No transform_variable_name found - check if it's the wrong structure
                    if "json_path" in experiment_output:
                        logger.error(
                            f"Invalid experiment_output structure for agentic experiment eval variable '{variable_name}'. "
                            f"Found json_path structure: {experiment_output}. "
                            "Agentic experiments only support transform variables, not json_path. "
                            "The eval config may have been incorrectly serialized. "
                            "Expected structure: {{'type': 'transform_variable', 'transform_variable_name': '...'}}",
                        )
                    else:
                        logger.error(
                            f"Missing transform_variable_name in experiment_output for eval variable '{variable_name}'. "
                            f"experiment_output structure: {experiment_output}. "
                            "Agentic experiments only support transform variables. "
                            "Expected structure: {{'type': 'transform_variable', 'transform_variable_name': '...'}}",
                        )
                    variable_map[variable_name] = ""

        return variable_map

    def _process_experiment_output_variable(
        self,
        test_case_result: DatabaseAgenticExperimentTestCaseAgenticResult,
        variable_name: str,
        json_path: Optional[str],
    ) -> str:
        """
        Extract the value for an experiment_output variable from an agentic result.

        Args:
            test_case_result: Agentic result with response_output
            variable_name: Name of the variable to extract
            json_path: Not used for agentic experiments (kept for interface compatibility).
                Agentic experiments only support transform variables, not JSON path extraction.

        Returns:
            The extracted value as a string (full response body as JSON)
        """
        if not test_case_result.response_output:
            logger.warning(
                "No response output included at this stage in the experiment.",
            )
            return ""

        response_body = test_case_result.response_output.get("response_body", {})

        # Agentic experiments don't support JSON path - return full response as JSON string
        return json.dumps(response_body, indent=2)

    def _set_summary_results(
        self,
        db_session: Session,
        experiment: DatabaseAgenticExperiment,
    ) -> None:
        """
        Calculate summary results for an experiment based on completed test cases.

        Args:
            db_session: Database session
            experiment: DatabaseAgenticExperiment object

        Sets summary results dictionary with agentic_eval_summaries
        """
        try:
            # Get all completed test cases with their agentic results and eval scores
            test_cases = self._get_db_test_cases(
                experiment.id,
                db_session,
                TestCaseStatus.COMPLETED,
            )

            if not test_cases:
                experiment.summary_results = AgenticSummaryResults(
                    eval_summaries=[],
                ).model_dump(mode="json", exclude_none=True)
                return

            # Build a structure to aggregate results: {(eval_name, eval_version): [scores]}
            # Also track transform_id for each eval
            results_by_eval: dict[tuple[str, int], list[float]] = {}
            transform_ids_by_eval: dict[tuple[str, int], str] = {}

            for test_case in test_cases:
                if not test_case.agentic_result:
                    continue

                for eval_score in test_case.agentic_result.eval_scores:
                    eval_key = (eval_score.eval_name, eval_score.eval_version)

                    if eval_key not in results_by_eval:
                        results_by_eval[eval_key] = []
                        # Get transform_id from eval config
                        transform_id = None
                        for config in experiment.eval_configs:
                            if config["name"] == eval_score.eval_name and str(
                                config["version"],
                            ) == str(eval_score.eval_version):
                                transform_id = config.get("transform_id")
                                break
                        if transform_id:
                            transform_ids_by_eval[eval_key] = transform_id

                    # Add the score if eval result exists
                    if eval_score.eval_result_score is not None:
                        results_by_eval[eval_key].append(eval_score.eval_result_score)

            # Build the summary structure using Pydantic models
            eval_summaries = []
            for (eval_name, eval_version), scores in sorted(results_by_eval.items()):
                # Count how many passed (score >= 0.5, assuming 0-1 scale)
                pass_count = sum(1 for s in scores if s >= 0.5)
                total_count = len(scores)

                # Get transform_id for this eval
                transform_id = transform_ids_by_eval.get((eval_name, eval_version))
                if not transform_id:
                    logger.warning(
                        f"Transform ID not found for eval {eval_name} v{eval_version}, skipping summary",
                    )
                    continue

                # Create EvalResultSummary
                eval_result_summary = EvalResultSummary(
                    eval_name=eval_name,
                    eval_version=str(eval_version),
                    pass_count=pass_count,
                    total_count=total_count,
                )

                eval_summaries.append(
                    AgenticEvalResultSummaries(
                        eval_name=eval_name,
                        eval_version=str(eval_version),
                        transform_id=transform_id,
                        eval_results=[eval_result_summary],
                    ),
                )

            experiment.summary_results = AgenticSummaryResults(
                eval_summaries=eval_summaries,
            ).model_dump(mode="json", exclude_none=True)

        except Exception as e:
            logger.error(
                f"Error calculating summary results for agentic experiment {experiment.id}: {e}",
                exc_info=True,
            )
            experiment.summary_results = AgenticSummaryResults(
                eval_summaries=[],
            ).model_dump(mode="json", exclude_none=True)
