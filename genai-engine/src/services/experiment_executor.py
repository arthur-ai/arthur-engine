"""
Service for asynchronously executing experiments in the background.

"""

import json
import logging
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from db_models import (
    DatabaseBaseEvalScore,
    DatabaseBaseExperiment,
    DatabaseBaseExperimentTestCase,
)
from db_models.prompt_experiment_models import (
    DatabasePromptExperimentTestCasePromptResult,
)
from db_models.rag_experiment_models import (
    DatabaseRagExperimentTestCaseRagResult,
)
from dependencies import db_session_context
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.base_experiment_schemas import (
    ExperimentStatus,
    TestCaseStatus,
)
from schemas.request_schemas import (
    BaseCompletionRequest,
    VariableTemplateValue,
)
from utils.trace import get_nested_value

logger = logging.getLogger(__name__)


class BaseExperimentExecutor(ABC):
    """Handles asynchronous execution of RAG experiments"""

    MAX_WORKERS = 5

    def __init__(self) -> None:
        pass

    def execute_experiment_async(self, experiment_id: str) -> None:
        """
        Start asynchronous execution of an experiment in a background thread.

        This method returns immediately after spawning the background thread.

        Args:
            experiment_id: ID of the experiment to execute
        """
        thread = threading.Thread(
            target=self._execute_experiment,
            args=(experiment_id,),
            daemon=True,
        )
        thread.start()
        logger.info(f"Started background execution for experiment {experiment_id}")

    def _execute_experiment(self, experiment_id: str) -> None:
        """
        Execute an experiment in the background with its own database session.

        Args:
            experiment_id: ID of the experiment to execute
        """
        with db_session_context() as db_session:
            self._execute_experiment_with_session(db_session, experiment_id)

    @abstractmethod
    def _get_database_experiment(
        self,
        experiment_id: str,
        session: Session,
    ) -> Optional[DatabaseBaseExperiment]:
        raise NotImplementedError

    @staticmethod
    def _update_experiment_status(
        experiment: DatabaseBaseExperiment,
        new_status: ExperimentStatus,
        db_session: Session,
        new_total_cost: Optional[float] = None,
    ) -> None:
        experiment.status = new_status
        if new_total_cost is not None:
            # truncate to 6 decimal places and store as string to prevent precision loss
            total_cost_str = f"{new_total_cost:.6f}"
            experiment.total_cost = total_cost_str

        if new_status in (ExperimentStatus.FAILED, ExperimentStatus.COMPLETED):
            experiment.finished_at = datetime.now()

        db_session.commit()
        log_msg = f"Marked experiment {experiment.id} as {new_status.value}."
        if new_total_cost:
            log_msg += f"Total cost: ${new_total_cost}."
        logger.info(log_msg)

    @staticmethod
    def _calculate_total_cost(
        test_cases: List[DatabaseBaseExperimentTestCase],
    ) -> float:
        """Calculates total cost over a list of test cases with already-populated costs."""
        total_experiment_cost = 0.0
        for test_case in test_cases:
            if test_case.total_cost:
                try:
                    total_experiment_cost += float(test_case.total_cost)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not parse test case cost: {test_case.total_cost}",
                    )
        return total_experiment_cost

    @staticmethod
    def _calculate_total_cost_eval_scores(
        eval_scores: List[DatabaseBaseEvalScore],
    ) -> float:
        """Calculates total cost for a list of eval scores"""
        total_cost = 0.0
        for eval_score in eval_scores:
            if eval_score.eval_result_cost:
                try:
                    total_cost += float(eval_score.eval_result_cost)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not parse eval cost: {eval_score.eval_result_cost}",
                    )
        return total_cost

    @abstractmethod
    def _get_db_test_cases(
        self,
        experiment_id: str,
        db_session: Session,
    ) -> List[DatabaseBaseExperimentTestCase]:
        raise NotImplementedError

    @abstractmethod
    def _get_db_test_case(
        self,
        test_case_id: str,
        db_session: Session,
    ) -> DatabaseBaseExperimentTestCase:
        raise NotImplementedError

    @staticmethod
    def _update_test_case_status(
        test_case: DatabaseBaseExperimentTestCase,
        new_status: TestCaseStatus,
        db_session: Session,
        total_cost: Optional[float] = None,
    ) -> None:
        test_case.status = new_status

        log_msg = f"Marked test case {test_case.id} as {new_status.value}."

        if total_cost is not None:
            test_case.total_cost = f"{total_cost:.6f}"
            log_msg += f" Test case has total cost ${test_case.total_cost}"

        db_session.commit()
        if new_status == TestCaseStatus.FAILED:
            logger.error(f"Test case {test_case.id} failed.")
        else:
            logger.info(log_msg)

    def _execute_experiment_with_session(
        self,
        db_session: Session,
        experiment_id: str,
    ) -> None:
        """
        Execute an experiment using the provided database session.

        Args:
            db_session: Database session
            experiment_id: ID of the experiment to execute
        """
        try:
            # Mark experiment as running
            experiment = self._get_database_experiment(experiment_id, db_session)
            self._update_experiment_status(
                experiment,
                ExperimentStatus.RUNNING,
                db_session,
            )

            # Get all test cases for this experiment
            test_cases = self._get_db_test_cases(experiment_id, db_session)

            if not test_cases:
                logger.warning(f"No test cases found for experiment {experiment_id}.")
                self._update_experiment_status(
                    experiment,
                    ExperimentStatus.COMPLETED,
                    db_session,
                    new_total_cost=0.0,
                )
                return

            # Execute test cases in parallel with worker pool
            num_workers = min(len(test_cases), self.MAX_WORKERS)
            completed_count = 0
            failed_count = 0

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all test case jobs
                futures = {
                    executor.submit(self._execute_test_case, test_case.id): test_case.id
                    for test_case in test_cases
                }

                # Wait for all test cases to complete and update progress in real-time
                for future in as_completed(futures):
                    test_case_id = futures[future]
                    try:
                        success = future.result()
                        if success:
                            completed_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(
                            f"Test case {test_case_id} raised exception: {e}",
                            exc_info=True,
                        )
                        failed_count += 1

                    # Update experiment progress after each completion (main thread, no concurrency issues)
                    experiment.completed_rows = completed_count
                    experiment.failed_rows = failed_count
                    db_session.commit()

                    logger.info(
                        f"Experiment {experiment_id} progress: "
                        f"{completed_count}/{len(test_cases)} completed, {failed_count} failed",
                    )

            # fetch refreshed experiment object
            experiment = self._get_database_experiment(experiment_id, db_session)

            # Calculate total cost across all test cases
            total_experiment_cost = self._calculate_total_cost(test_cases)

            # Calculate and set summary results now that all test cases have finished
            # called function doesn't handle committing—will happen when experiment status is updated
            self._set_summary_results(
                db_session,
                experiment,
            )

            if failed_count > 0:
                self._update_experiment_status(
                    experiment,
                    ExperimentStatus.FAILED,
                    db_session,
                    total_experiment_cost,
                )
            else:
                self._update_experiment_status(
                    experiment,
                    ExperimentStatus.COMPLETED,
                    db_session,
                    total_experiment_cost,
                )

        except Exception as e:
            logger.error(
                f"Error executing experiment {experiment_id}: {e}",
                exc_info=True,
            )
            try:
                experiment = self._get_database_experiment(experiment_id, db_session)
                if experiment:
                    self._update_experiment_status(
                        experiment,
                        ExperimentStatus.FAILED,
                        db_session,
                    )
            except Exception as commit_error:
                logger.error(
                    f"Failed to mark experiment as failed: {commit_error}",
                    exc_info=True,
                )

    def _execute_test_case(self, test_case_id: str) -> bool:
        """
        Execute a single test case including all configurations and evaluations.

        Args:
            test_case_id: ID of the test case to execute

        Returns:
            True if test case completed successfully, False otherwise
        """
        with db_session_context() as db_session:
            return self._execute_test_case_with_session(db_session, test_case_id)

    def _execute_test_case_with_session(
        self,
        db_session: Session,
        test_case_id: str,
    ) -> bool:
        """
        Execute a single test case using the provided database session.

        Args:
            db_session: Database session
            test_case_id: ID of the test case to execute

        Returns:
            True if test case completed successfully, False otherwise
        """
        try:
            # Mark test case as running
            test_case = self._get_db_test_case(test_case_id, db_session)
            if not test_case:
                logger.error(f"Test case {test_case_id} not found")
                return False

            self._update_test_case_status(test_case, TestCaseStatus.RUNNING, db_session)

            # Execute all experiment outputs (RAG searches or prompts), tracking failures but continuing
            all_outputs_passed = self._execute_experiment_outputs(db_session, test_case)

            # If any outputs failed, mark test case as failed and return
            if not all_outputs_passed:
                self._update_test_case_status(
                    test_case,
                    TestCaseStatus.FAILED,
                    db_session,
                )
                return False

            # All outputs executed successfully, now run evaluations
            self._update_test_case_status(
                test_case,
                TestCaseStatus.EVALUATING,
                db_session,
            )

            # Execute all evaluations for this test case
            all_evals_passed = self._execute_evaluations(db_session, test_case)

            # If any evaluations failed, mark test case as failed and return
            if not all_evals_passed:
                self._update_test_case_status(
                    test_case,
                    TestCaseStatus.FAILED,
                    db_session,
                )
                return False

            # Calculate total cost for this test case
            total_cost = self._calculate_total_test_case_cost(test_case)

            # Mark test case as completed and store total cost
            self._update_test_case_status(
                test_case,
                TestCaseStatus.COMPLETED,
                db_session,
                total_cost,
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing test case {test_case_id}: {e}",
                exc_info=True,
            )
            try:
                test_case = self._get_db_test_case(test_case_id, db_session)
                if test_case:
                    self._update_test_case_status(
                        test_case,
                        TestCaseStatus.FAILED,
                        db_session,
                    )
            except Exception as commit_error:
                logger.error(
                    f"Failed to mark test case as failed: {commit_error}",
                    exc_info=True,
                )
            return False

    @abstractmethod
    def _execute_experiment_outputs(
        self,
        db_session: Session,
        test_case: DatabaseBaseExperimentTestCase,
    ) -> bool:
        """
        Execute all experiment outputs for a test case (RAG searches or prompts).

        Args:
            db_session: Database session
            test_case: Test case to execute outputs for

        Returns:
            True if all outputs executed successfully, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def _execute_evaluations(
        self,
        db_session: Session,
        test_case: DatabaseBaseExperimentTestCase,
    ) -> bool:
        """
        Execute all evaluations for a test case.

        Args:
            db_session: Database session
            test_case: Test case containing results to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def _execute_evaluations_for_result(
        self,
        db_session: Session,
        test_case_result: Any,
    ) -> bool:
        """
        Execute all evaluations for a single test case result (RAG result or prompt result).

        Args:
            db_session: Database session
            test_case_result: Result object (RAG result or prompt result) to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def _calculate_total_test_case_cost(
        self,
        test_case: DatabaseBaseExperimentTestCase,
    ) -> float:
        """
        Calculate the total cost for a test case.

        Args:
            test_case: Test case to calculate cost for

        Returns:
            Total cost as a float
        """
        raise NotImplementedError

    @staticmethod
    def _extract_value_from_json_path(
        data: Dict[str, Any],
        json_path: Optional[str],
        default: str = "",
    ) -> str:
        """
        Extract a value from a dictionary using a JSON path (dot-notation).

        If json_path is provided, extracts the value at that path.
        Otherwise, returns the default value.

        Args:
            data: Dictionary to extract value from
            json_path: Optional dot-notation path (e.g., "results.0.content")
            default: Default value to return if path not found or not provided

        Returns:
            Extracted value as a string, or default if not found
        """
        if not json_path:
            return default

        try:
            value = get_nested_value(data, json_path, default=None)
            if value is None:
                logger.warning(
                    f"Could not find value in JSON path '{json_path}'. Defaulting to passing through the entire output.",
                )
                return default

            # Convert to string, handling various types
            if isinstance(value, (dict, list)):
                return json.dumps(value, indent=2)
            return str(value)
        except Exception as e:
            logger.warning(
                f"Error extracting value from JSON path '{json_path}': {e}",
            )
            return default

    @abstractmethod
    def _process_experiment_output_variable(
        self,
        test_case_result: Any,
        variable_name: str,
        json_path: Optional[str],
    ) -> str:
        """
        Extract the value for an experiment_output variable from a test case result.

        Args:
            test_case_result: The result object (prompt result or RAG result)
            variable_name: Name of the variable to extract
            json_path: Optional JSON path to extract a specific value from the output

        Returns:
            The extracted value as a string
        """
        raise NotImplementedError

    def _set_eval_input_variables(
        self,
        db_session: Session,
        eval_score: DatabaseBaseEvalScore,
        experiment: DatabaseBaseExperiment,
        test_case_result: Union[
            DatabaseRagExperimentTestCaseRagResult,
            DatabasePromptExperimentTestCasePromptResult,
        ],
    ) -> bool:
        """
        Set eval_input_variables by processing variable mappings and extracting experiment_output values.

        Args:
            db_session: Database session
            eval_score: Eval score record to update
            experiment: Experiment containing the eval config
            test_case_result: The result object (prompt result or RAG result) to extract values from

        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the eval config from the experiment to get the variable mapping with source information
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

            # Build variable map using the eval config's variable mapping to determine sources
            # Create a mapping of variable names to their current values from eval_input_variables
            stored_values = {
                var["variable_name"]: var["value"]
                for var in eval_score.eval_input_variables
            }

            variable_map = {}
            for mapping in eval_config["variable_mapping"]:
                variable_name = mapping["variable_name"]
                source = mapping["source"]

                # Check if this is an experiment_output type
                if source["type"] == "experiment_output":
                    # Extract json_path from the source if provided
                    json_path = source.get("experiment_output", {}).get("json_path")
                    # Use type-specific method to extract the value
                    variable_map[variable_name] = (
                        self._process_experiment_output_variable(
                            test_case_result,
                            variable_name,
                            json_path,
                        )
                    )
                else:
                    # It's a dataset column - get the stored value
                    variable_map[variable_name] = stored_values.get(variable_name, "")

            # Update eval_input_variables with finalized experiment_output values
            updated_eval_input_variables = []
            for var in eval_score.eval_input_variables:
                variable_name = var["variable_name"]
                updated_eval_input_variables.append(
                    {
                        "variable_name": variable_name,
                        "value": variable_map.get(variable_name, ""),
                    },
                )

            eval_score.eval_input_variables = updated_eval_input_variables
            db_session.commit()
            return True

        except Exception as e:
            logger.error(
                f"Error setting eval input variables: {e}",
                exc_info=True,
            )
            return False

    def _execute_eval_with_variable_map(
        self,
        db_session: Session,
        eval_score: DatabaseBaseEvalScore,
        experiment: DatabaseBaseExperiment,
    ) -> bool:
        """
        Execute an evaluation using the eval_score's eval_input_variables.

        This method handles the shared logic of:
        - Getting LLM client
        - Converting eval to agentic prompt
        - Executing the chat completion
        - Validating and saving results

        Args:
            db_session: Database session
            eval_score: Eval score record to populate (with eval_input_variables already set)
            experiment: Experiment containing the eval config

        Returns:
            True if eval executed successfully, False otherwise
        """
        try:
            # Convert eval_input_variables list to dict format
            variable_map = {
                var["variable_name"]: var["value"]
                for var in eval_score.eval_input_variables
            }

            # Get LLM evals repository and set model_provider_repo (required by run_llm_eval)
            model_provider_repo = ModelProviderRepository(db_session)
            llm_evals_repo = LLMEvalsRepository(db_session)
            llm_evals_repo.model_provider_repo = model_provider_repo

            # Create completion request with variables
            completion_request = BaseCompletionRequest(
                variables=[
                    VariableTemplateValue(name=k, value=v)
                    for k, v in variable_map.items()
                ],
            )

            # Use run_llm_eval which handles model support checking, structured outputs, and validation
            try:
                eval_response = llm_evals_repo.run_llm_eval(
                    task_id=experiment.task_id,
                    eval_name=eval_score.eval_name,
                    version=str(eval_score.eval_version),
                    completion_request=completion_request,
                )
            except Exception as e:
                # Handle model not supporting structured outputs, missing eval, or validation errors
                logger.error(
                    f"Error executing eval {eval_score.eval_name} v{eval_score.eval_version}: {e}",
                )
                return False

            # Save eval results to separate columns
            eval_score.eval_result_score = eval_response.score
            eval_score.eval_result_explanation = eval_response.reason
            eval_score.eval_result_cost = eval_response.cost
            db_session.commit()

            logger.info(
                f"Executed eval {eval_score.eval_name} v{eval_score.eval_version} for experiment {experiment.id}",
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing eval {eval_score.eval_name} v{eval_score.eval_version}: {e}",
                exc_info=True,
            )
            return False

    def _execute_single_eval(
        self,
        db_session: Session,
        eval_score: DatabaseBaseEvalScore,
        test_case_result: Union[
            DatabaseRagExperimentTestCaseRagResult,
            DatabasePromptExperimentTestCasePromptResult,
        ],
    ) -> bool:
        """
        Execute a single evaluation.

        Args:
            db_session: Database session
            eval_score: Eval score record to populate
            test_case_result: Result object (RAG result or prompt result) with output

        Returns:
            True if eval executed successfully, False otherwise
        """
        try:
            # Get the experiment using the test_case_result relationship
            experiment = test_case_result.test_case.experiment

            # Set eval_input_variables using shared method
            if not self._set_eval_input_variables(
                db_session,
                eval_score,
                experiment,
                test_case_result,
            ):
                return False

            # Use shared method to execute the eval (uses eval_input_variables)
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

    @abstractmethod
    def _set_summary_results(
        self,
        db_session: Session,
        experiment: DatabaseBaseExperiment,
    ) -> None:
        """
        Calculates and sets summary results for an experiment based on completed test cases.

        Args:
            db_session: Database session
            experiment: Database Experiment object

        Sets the summary results dictionary with experiment-type specific summaries.
        In implementations, make sure to handle errors elegantly so the calling experiment doesn't fail.
        """
        raise NotImplementedError
