"""
Service for asynchronously executing prompt experiments in the background.

This module handles the execution of prompt experiments by:
1. Running prompts for each test case across multiple prompt versions
2. Executing evaluations on the prompt outputs
3. Updating experiment and test case statuses throughout execution
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from db_models.prompt_experiment_models import (
    DatabasePromptExperiment,
    DatabasePromptExperimentTestCase,
    DatabasePromptExperimentTestCasePromptResult,
    DatabasePromptExperimentTestCasePromptResultEvalScore,
)
from dependencies import get_db_session
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.llm_eval_schemas import LLMEval, ReasonedScore
from schemas.prompt_experiment_schemas import (
    EvalResult,
    ExperimentStatus,
    PromptEvalSummary,
    SummaryResults,
    TestCaseStatus,
)
from schemas.request_schemas import PromptCompletionRequest, VariableTemplateValue
from services.prompt.chat_completion_service import ChatCompletionService

logger = logging.getLogger(__name__)


@contextmanager
def db_session_context():
    """
    Context manager for database sessions using the FastAPI dependency.

    Usage:
        with db_session_context() as session:
            # use session
    """
    session_gen = get_db_session()
    session = next(session_gen)
    try:
        yield session
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


class ExperimentExecutor:
    """Handles asynchronous execution of prompt experiments"""

    MAX_WORKERS = 5

    def __init__(self):
        self.chat_completion_service = ChatCompletionService()

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

    def _execute_experiment_with_session(
        self, db_session: Session, experiment_id: str
    ) -> None:
        """
        Execute an experiment using the provided database session.

        Args:
            db_session: Database session
            experiment_id: ID of the experiment to execute
        """
        try:
            # Mark experiment as running
            experiment = (
                db_session.query(DatabasePromptExperiment)
                .filter_by(id=experiment_id)
                .first()
            )
            if not experiment:
                logger.error(f"Experiment {experiment_id} not found")
                return

            experiment.status = ExperimentStatus.RUNNING.value
            db_session.commit()
            logger.info(f"Marked experiment {experiment_id} as running")

            # Get all test cases for this experiment
            test_cases = (
                db_session.query(DatabasePromptExperimentTestCase)
                .filter_by(experiment_id=experiment_id)
                .all()
            )

            if not test_cases:
                logger.warning(f"No test cases found for experiment {experiment_id}")
                experiment.status = ExperimentStatus.COMPLETED.value
                db_session.commit()
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
                    experiment.summary_results = self._calculate_summary_results(
                        db_session, experiment_id
                    )
                    db_session.commit()

                    logger.info(
                        f"Experiment {experiment_id} progress: "
                        f"{completed_count}/{len(test_cases)} completed, {failed_count} failed"
                    )

            # Mark experiment as completed or failed based on final counts
            experiment = (
                db_session.query(DatabasePromptExperiment)
                .filter_by(id=experiment_id)
                .first()
            )
            if failed_count > 0:
                experiment.status = ExperimentStatus.FAILED.value
                logger.warning(
                    f"Experiment {experiment_id} completed with {failed_count} failed test cases"
                )
            else:
                experiment.status = ExperimentStatus.COMPLETED.value
                logger.info(f"Experiment {experiment_id} completed successfully")

            db_session.commit()

        except Exception as e:
            logger.error(
                f"Error executing experiment {experiment_id}: {e}", exc_info=True
            )
            try:
                experiment = (
                    db_session.query(DatabasePromptExperiment)
                    .filter_by(id=experiment_id)
                    .first()
                )
                if experiment:
                    experiment.status = ExperimentStatus.FAILED.value
                    db_session.commit()
            except Exception as commit_error:
                logger.error(
                    f"Failed to mark experiment as failed: {commit_error}",
                    exc_info=True,
                )

    def _execute_test_case(self, test_case_id: str) -> bool:
        """
        Execute a single test case including all prompt versions and evaluations.

        Args:
            test_case_id: ID of the test case to execute

        Returns:
            True if test case completed successfully, False otherwise
        """
        with db_session_context() as db_session:
            return self._execute_test_case_with_session(db_session, test_case_id)

    def _execute_test_case_with_session(
        self, db_session: Session, test_case_id: str
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
            test_case = (
                db_session.query(DatabasePromptExperimentTestCase)
                .filter_by(id=test_case_id)
                .first()
            )
            if not test_case:
                logger.error(f"Test case {test_case_id} not found")
                return False

            test_case.status = TestCaseStatus.RUNNING.value
            db_session.commit()
            logger.info(f"Marked test case {test_case_id} as running")

            # Execute all prompts, tracking failures but continuing
            any_prompt_failed = False
            for prompt_result in test_case.prompt_results:
                success = self._execute_prompt(db_session, prompt_result, test_case)
                if not success:
                    any_prompt_failed = True
                    logger.warning(
                        f"Prompt {prompt_result.name} v{prompt_result.version} failed in test case {test_case_id}, continuing with other prompts"
                    )

            # If any prompts failed, mark test case as failed and return
            if any_prompt_failed:
                test_case.status = TestCaseStatus.FAILED.value
                db_session.commit()
                logger.error(
                    f"Test case {test_case_id} failed due to prompt execution failures"
                )
                return False

            # All prompts executed successfully, now run evaluations
            test_case.status = TestCaseStatus.EVALUATING.value
            db_session.commit()
            logger.info(f"Test case {test_case_id} moving to evaluation phase")

            # Execute all evaluations, tracking failures but continuing
            any_eval_failed = False
            for prompt_result in test_case.prompt_results:
                success = self._execute_evaluations(db_session, prompt_result)
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Evaluations failed for prompt {prompt_result.name} v{prompt_result.version} in test case {test_case_id}, continuing with other evaluations"
                    )

            # If any evaluations failed, mark test case as failed and return
            if any_eval_failed:
                test_case.status = TestCaseStatus.FAILED.value
                db_session.commit()
                logger.error(
                    f"Test case {test_case_id} failed due to evaluation failures"
                )
                return False

            # Mark test case as completed
            test_case.status = TestCaseStatus.COMPLETED.value
            db_session.commit()
            logger.info(f"Test case {test_case_id} completed successfully")
            return True

        except Exception as e:
            logger.error(
                f"Error executing test case {test_case_id}: {e}", exc_info=True
            )
            try:
                test_case = (
                    db_session.query(DatabasePromptExperimentTestCase)
                    .filter_by(id=test_case_id)
                    .first()
                )
                if test_case:
                    test_case.status = TestCaseStatus.FAILED.value
                    db_session.commit()
            except Exception as commit_error:
                logger.error(
                    f"Failed to mark test case as failed: {commit_error}", exc_info=True
                )
            return False

    def _calculate_summary_results(
        self,
        db_session: Session,
        experiment_id: str,
    ) -> Dict[str, Any]:
        """
        Calculate summary results for an experiment based on completed test cases.

        Args:
            db_session: Database session
            experiment_id: ID of the experiment

        Returns:
            Summary results dictionary with prompt_eval_summaries
        """
        try:
            # Get all completed test cases with their prompt results and eval scores
            test_cases = (
                db_session.query(DatabasePromptExperimentTestCase)
                .filter_by(
                    experiment_id=experiment_id, status=TestCaseStatus.COMPLETED.value
                )
                .all()
            )

            if not test_cases:
                return SummaryResults(prompt_eval_summaries=[]).model_dump(
                    mode="python", exclude_none=True
                )

            # Build a structure to aggregate results: {(prompt_name, prompt_version): {(eval_name, eval_version): [scores]}}
            results_by_prompt: Dict[tuple, Dict[tuple, list]] = {}

            for test_case in test_cases:
                for prompt_result in test_case.prompt_results:
                    prompt_key = (prompt_result.name, prompt_result.version)

                    if prompt_key not in results_by_prompt:
                        results_by_prompt[prompt_key] = {}

                    for eval_score in prompt_result.eval_scores:
                        eval_key = (eval_score.eval_name, eval_score.eval_version)

                        if eval_key not in results_by_prompt[prompt_key]:
                            results_by_prompt[prompt_key][eval_key] = []

                        # Add the score if eval results exist
                        if eval_score.eval_results:
                            score = eval_score.eval_results.get("score")
                            if score is not None:
                                results_by_prompt[prompt_key][eval_key].append(score)

            # Build the summary structure using Pydantic models
            prompt_eval_summaries = []
            for (prompt_name, prompt_version), eval_results in sorted(
                results_by_prompt.items()
            ):
                eval_result_list = []
                for (eval_name, eval_version), scores in sorted(eval_results.items()):
                    # Count how many passed (score >= 0.5, assuming 0-1 scale)
                    pass_count = sum(1 for s in scores if s >= 0.5)
                    total_count = len(scores)

                    eval_result_list.append(
                        EvalResult(
                            eval_name=eval_name,
                            eval_version=str(eval_version),
                            pass_count=pass_count,
                            total_count=total_count,
                        )
                    )

                prompt_eval_summaries.append(
                    PromptEvalSummary(
                        prompt_name=prompt_name,
                        prompt_version=str(prompt_version),
                        eval_results=eval_result_list,
                    )
                )

            return SummaryResults(
                prompt_eval_summaries=prompt_eval_summaries
            ).model_dump(mode="python", exclude_none=True)

        except Exception as e:
            logger.error(
                f"Error calculating summary results for experiment {experiment_id}: {e}",
                exc_info=True,
            )
            return SummaryResults(prompt_eval_summaries=[]).model_dump(
                mode="python", exclude_none=True
            )

    def _execute_prompt(
        self,
        db_session: Session,
        prompt_result: DatabasePromptExperimentTestCasePromptResult,
        test_case: DatabasePromptExperimentTestCase,
    ) -> bool:
        """
        Execute a single prompt and save the output.

        Args:
            db_session: Database session
            prompt_result: Prompt result record to populate
            test_case: Test case containing input variables

        Returns:
            True if prompt executed successfully, False otherwise
        """
        try:
            # Get the experiment using the test_case relationship
            experiment = test_case.experiment

            # Get the prompt using repository
            prompt_repo = AgenticPromptRepository(db_session)
            try:
                prompt = prompt_repo.get_llm_item(
                    task_id=experiment.task_id,
                    item_name=prompt_result.name,
                    item_version=str(prompt_result.version),
                )
            except ValueError as e:
                logger.error(
                    f"Prompt {prompt_result.name} v{prompt_result.version} not found: {e}"
                )
                return False

            # Get LLM client
            model_provider_repo = ModelProviderRepository(db_session)
            llm_client = model_provider_repo.get_model_provider_client(
                prompt.model_provider
            )

            # Build variable map from test case input variables
            variable_map = {
                var["variable_name"]: var["value"]
                for var in test_case.prompt_input_variables
            }

            # Render the prompt
            rendered_messages = self.chat_completion_service.replace_variables(
                variable_map=variable_map,
                messages=prompt.messages,
            )

            # Convert messages to dictionaries for JSON serialization
            # Handle both dict objects and Pydantic/OpenAI message objects
            messages_as_dicts = []
            for msg in rendered_messages:
                # Pydantic model
                messages_as_dicts.append(
                    msg.model_dump(mode="python", exclude_none=True)
                )

            rendered_prompt_text = json.dumps(messages_as_dicts, indent=2)

            # Save rendered prompt
            prompt_result.rendered_prompt = rendered_prompt_text
            db_session.commit()

            # Execute the prompt
            completion_request = PromptCompletionRequest(
                variables=[
                    VariableTemplateValue(name=k, value=v)
                    for k, v in variable_map.items()
                ]
            )

            response = self.chat_completion_service.run_chat_completion(
                prompt=prompt,
                llm_client=llm_client,
                completion_request=completion_request,
            )

            # Save output - convert response model to dict
            prompt_result.output = response.model_dump(mode="python", exclude_none=True)
            db_session.commit()

            logger.info(
                f"Executed prompt {prompt_result.name} v{prompt_result.version} for test case {test_case.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing prompt {prompt_result.name} v{prompt_result.version}: {e}",
                exc_info=True,
            )
            return False

    def _execute_evaluations(
        self,
        db_session: Session,
        prompt_result: DatabasePromptExperimentTestCasePromptResult,
    ) -> bool:
        """
        Execute all evaluations for a prompt result.

        Args:
            db_session: Database session
            prompt_result: Prompt result with output to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        try:
            # Execute all eval scores using the relationship, tracking failures but continuing
            any_eval_failed = False
            for eval_score in prompt_result.eval_scores:
                success = self._execute_single_eval(
                    db_session, eval_score, prompt_result
                )
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Eval {eval_score.eval_name} v{eval_score.eval_version} failed for prompt result {prompt_result.id}, continuing with other evals"
                    )

            return not any_eval_failed

        except Exception as e:
            logger.error(
                f"Error executing evaluations for prompt result {prompt_result.id}: {e}",
                exc_info=True,
            )
            return False

    def _execute_single_eval(
        self,
        db_session: Session,
        eval_score: DatabasePromptExperimentTestCasePromptResultEvalScore,
        prompt_result: DatabasePromptExperimentTestCasePromptResult,
    ) -> bool:
        """
        Execute a single evaluation.

        Args:
            db_session: Database session
            eval_score: Eval score record to populate
            prompt_result: Prompt result with output

        Returns:
            True if eval executed successfully, False otherwise
        """
        try:
            # Get the experiment using the prompt_result relationship
            experiment = prompt_result.test_case.experiment

            # Get the eval using repository
            llm_evals_repo = LLMEvalsRepository(db_session)
            try:
                llm_eval = llm_evals_repo.get_llm_item(
                    task_id=experiment.task_id,
                    item_name=eval_score.eval_name,
                    item_version=str(eval_score.eval_version),
                )
            except ValueError as e:
                logger.error(
                    f"Eval {eval_score.eval_name} v{eval_score.eval_version} not found: {e}"
                )
                return False

            # Find the eval config from the experiment to get the variable mapping with source information
            eval_config = None
            for config in experiment.eval_configs:
                if config["name"] == eval_score.eval_name and str(
                    config["version"]
                ) == str(eval_score.eval_version):
                    eval_config = config
                    break

            if not eval_config:
                logger.error(
                    f"Eval config for {eval_score.eval_name} v{eval_score.eval_version} not found in experiment"
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
                    # Get the value from prompt output
                    if prompt_result.output:
                        variable_map[variable_name] = prompt_result.output.get(
                            "content", ""
                        )
                    else:
                        logger.error(
                            f"Prompt output not available for eval variable {variable_name}"
                        )
                        return False
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
                        "value": variable_map[variable_name],
                    }
                )
            eval_score.eval_input_variables = updated_eval_input_variables
            db_session.commit()

            # Get LLM client
            model_provider_repo = ModelProviderRepository(db_session)
            llm_client = model_provider_repo.get_model_provider_client(
                llm_eval.model_provider
            )

            # Convert eval to agentic prompt
            agentic_prompt = llm_evals_repo.from_llm_eval_to_agentic_prompt(
                llm_eval=llm_eval,
                response_format=ReasonedScore,
            )

            # Execute the eval
            completion_request = PromptCompletionRequest(
                variables=[
                    VariableTemplateValue(name=k, value=v)
                    for k, v in variable_map.items()
                ],
                stream=False,
                strict=True,
            )

            llm_model_response = (
                self.chat_completion_service.run_chat_completion_raw_response(
                    agentic_prompt,
                    llm_client,
                    completion_request,
                )
            )

            if not llm_model_response.structured_output_response:
                logger.error(f"No structured output from eval {eval_score.eval_name}")
                return False

            if not isinstance(
                llm_model_response.structured_output_response, ReasonedScore
            ):
                logger.error(
                    f"Unexpected structured output type from eval {eval_score.eval_name}"
                )
                return False

            # Save eval results
            eval_score.eval_results = {
                "score": llm_model_response.structured_output_response.score,
                "reason": llm_model_response.structured_output_response.reason,
                "cost": llm_model_response.cost,
            }
            db_session.commit()

            logger.info(
                f"Executed eval {eval_score.eval_name} v{eval_score.eval_version} for prompt result {prompt_result.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing eval {eval_score.eval_name} v{eval_score.eval_version}: {e}",
                exc_info=True,
            )
            return False
