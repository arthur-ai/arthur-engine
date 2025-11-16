"""
Service for asynchronously executing prompt experiments in the background.

This module handles the execution of prompt experiments by:
1. Running prompts for each test case across multiple prompt versions
2. Executing evaluations on the prompt outputs
3. Updating experiment and test case statuses throughout execution
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from schemas.prompt_experiment_schemas import ExperimentStatus, TestCaseStatus
from schemas.request_schemas import PromptCompletionRequest
from services.prompt.chat_completion_service import ChatCompletionService

logger = logging.getLogger(__name__)


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
        db_session = get_db_session()

        try:
            # Mark experiment as running
            experiment = db_session.query(DatabasePromptExperiment).filter_by(id=experiment_id).first()
            if not experiment:
                logger.error(f"Experiment {experiment_id} not found")
                return

            experiment.status = ExperimentStatus.RUNNING.value
            db_session.commit()
            logger.info(f"Marked experiment {experiment_id} as running")

            # Get all test cases for this experiment
            test_cases = db_session.query(DatabasePromptExperimentTestCase).filter_by(
                experiment_id=experiment_id
            ).all()

            if not test_cases:
                logger.warning(f"No test cases found for experiment {experiment_id}")
                experiment.status = ExperimentStatus.COMPLETED.value
                db_session.commit()
                return

            # Execute test cases in parallel with worker pool
            num_workers = min(len(test_cases), self.MAX_WORKERS)
            failed_test_cases = 0

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                # Submit all test case jobs
                futures = {
                    executor.submit(self._execute_test_case, test_case.id): test_case.id
                    for test_case in test_cases
                }

                # Wait for all test cases to complete
                for future in as_completed(futures):
                    test_case_id = futures[future]
                    try:
                        success = future.result()
                        if not success:
                            failed_test_cases += 1
                    except Exception as e:
                        logger.error(f"Test case {test_case_id} raised exception: {e}", exc_info=True)
                        failed_test_cases += 1

            # Mark experiment as completed or failed
            experiment = db_session.query(DatabasePromptExperiment).filter_by(id=experiment_id).first()
            if failed_test_cases > 0:
                experiment.status = ExperimentStatus.FAILED.value
                logger.warning(f"Experiment {experiment_id} completed with {failed_test_cases} failed test cases")
            else:
                experiment.status = ExperimentStatus.COMPLETED.value
                logger.info(f"Experiment {experiment_id} completed successfully")

            db_session.commit()

        except Exception as e:
            logger.error(f"Error executing experiment {experiment_id}: {e}", exc_info=True)
            try:
                experiment = db_session.query(DatabasePromptExperiment).filter_by(id=experiment_id).first()
                if experiment:
                    experiment.status = ExperimentStatus.FAILED.value
                    db_session.commit()
            except Exception as commit_error:
                logger.error(f"Failed to mark experiment as failed: {commit_error}", exc_info=True)
        finally:
            db_session.close()

    def _execute_test_case(self, test_case_id: str) -> bool:
        """
        Execute a single test case including all prompt versions and evaluations.

        Args:
            test_case_id: ID of the test case to execute

        Returns:
            True if test case completed successfully, False otherwise
        """
        db_session = get_db_session()

        try:
            # Mark test case as running
            test_case = db_session.query(DatabasePromptExperimentTestCase).filter_by(id=test_case_id).first()
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
                    logger.warning(f"Prompt {prompt_result.name} v{prompt_result.version} failed in test case {test_case_id}, continuing with other prompts")

            # If any prompts failed, mark test case as failed and return
            if any_prompt_failed:
                test_case.status = TestCaseStatus.FAILED.value
                db_session.commit()
                logger.error(f"Test case {test_case_id} failed due to prompt execution failures")
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
                    logger.warning(f"Evaluations failed for prompt {prompt_result.name} v{prompt_result.version} in test case {test_case_id}, continuing with other evaluations")

            # If any evaluations failed, mark test case as failed and return
            if any_eval_failed:
                test_case.status = TestCaseStatus.FAILED.value
                db_session.commit()
                logger.error(f"Test case {test_case_id} failed due to evaluation failures")
                return False

            # Mark test case as completed
            test_case.status = TestCaseStatus.COMPLETED.value
            db_session.commit()
            logger.info(f"Test case {test_case_id} completed successfully")

            return True

        except Exception as e:
            logger.error(f"Error executing test case {test_case_id}: {e}", exc_info=True)
            try:
                test_case = db_session.query(DatabasePromptExperimentTestCase).filter_by(id=test_case_id).first()
                if test_case:
                    test_case.status = TestCaseStatus.FAILED.value
                    db_session.commit()
            except Exception as commit_error:
                logger.error(f"Failed to mark test case as failed: {commit_error}", exc_info=True)
            return False
        finally:
            db_session.close()

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
            # Get the experiment to find the task_id
            experiment = db_session.query(DatabasePromptExperiment).filter_by(
                id=test_case.experiment.id if hasattr(test_case, 'experiment') else None
            ).first()

            if not experiment:
                # Fallback: query by test case's experiment_id
                test_case_full = db_session.query(DatabasePromptExperimentTestCase).filter_by(
                    id=test_case.id
                ).first()
                if test_case_full:
                    experiment = db_session.query(DatabasePromptExperiment).filter_by(
                        id=test_case_full.experiment_id
                    ).first()

            if not experiment:
                logger.error(f"Could not find experiment for test case {test_case.id}")
                return False

            # Get the prompt using repository
            prompt_repo = AgenticPromptRepository(db_session)
            try:
                prompt = prompt_repo.get_llm_item(
                    task_id=experiment.task_id,
                    item_name=prompt_result.name,
                    item_version=str(prompt_result.version),
                )
            except ValueError as e:
                logger.error(f"Prompt {prompt_result.name} v{prompt_result.version} not found: {e}")
                return False

            # Get LLM client
            model_provider_repo = ModelProviderRepository(db_session)
            llm_client = model_provider_repo.get_model_provider_client(prompt.model_provider)

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
            rendered_prompt_text = "\n".join([msg.get("content", "") for msg in rendered_messages])

            # Save rendered prompt
            prompt_result.rendered_prompt = rendered_prompt_text
            db_session.commit()

            # Execute the prompt
            completion_request = PromptCompletionRequest(
                variables=[
                    {"variable_name": k, "variable_value": v}
                    for k, v in variable_map.items()
                ]
            )

            response = self.chat_completion_service.run_chat_completion(
                prompt=prompt,
                llm_client=llm_client,
                completion_request=completion_request,
            )

            # Save output
            prompt_result.output = {
                "content": response.content,
                "tool_calls": response.tool_calls if response.tool_calls else [],
                "cost": response.cost,
            }
            db_session.commit()

            logger.info(f"Executed prompt {prompt_result.name} v{prompt_result.version} for test case {test_case.id}")
            return True

        except Exception as e:
            logger.error(f"Error executing prompt {prompt_result.name} v{prompt_result.version}: {e}", exc_info=True)
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
            # Execute all eval scores using the relationship
            for eval_score in prompt_result.eval_scores:
                success = self._execute_single_eval(db_session, eval_score, prompt_result)
                if not success:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error executing evaluations for prompt result {prompt_result.id}: {e}", exc_info=True)
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
            # Get the experiment to find the task_id
            test_case = db_session.query(DatabasePromptExperimentTestCase).filter_by(
                id=prompt_result.test_case_id
            ).first()

            if not test_case:
                logger.error(f"Could not find test case for prompt result {prompt_result.id}")
                return False

            experiment = db_session.query(DatabasePromptExperiment).filter_by(
                id=test_case.experiment_id
            ).first()

            if not experiment:
                logger.error(f"Could not find experiment for test case {test_case.id}")
                return False

            # Get the eval using repository
            llm_evals_repo = LLMEvalsRepository(db_session)
            try:
                llm_eval = llm_evals_repo.get_llm_item(
                    task_id=experiment.task_id,
                    item_name=eval_score.eval_name,
                    item_version=str(eval_score.eval_version),
                )
            except ValueError as e:
                logger.error(f"Eval {eval_score.eval_name} v{eval_score.eval_version} not found: {e}")
                return False

            # Build variable map from eval input variables
            # Some variables come from dataset, some from experiment output
            variable_map = {}
            for var in eval_score.eval_input_variables:
                variable_name = var["variable_name"]

                # Check if this is an experiment_output type
                if var.get("source", {}).get("type") == "experiment_output":
                    # Get the value from prompt output
                    if prompt_result.output:
                        variable_map[variable_name] = prompt_result.output.get("content", "")
                    else:
                        logger.error(f"Prompt output not available for eval variable {variable_name}")
                        return False
                else:
                    # It's a dataset column or static value
                    variable_map[variable_name] = var.get("value", "")

            # Get LLM client
            model_provider_repo = ModelProviderRepository(db_session)
            llm_client = model_provider_repo.get_model_provider_client(llm_eval.model_provider)

            # Convert eval to agentic prompt
            agentic_prompt = llm_evals_repo.from_llm_eval_to_agentic_prompt(
                llm_eval=llm_eval,
                response_format=ReasonedScore,
            )

            # Execute the eval
            completion_request = PromptCompletionRequest(
                variables=[
                    {"variable_name": k, "variable_value": v}
                    for k, v in variable_map.items()
                ],
                stream=False,
                strict=True,
            )

            llm_model_response = self.chat_completion_service.run_chat_completion_raw_response(
                agentic_prompt,
                llm_client,
                completion_request,
            )

            if not llm_model_response.structured_output_response:
                logger.error(f"No structured output from eval {eval_score.eval_name}")
                return False

            if not isinstance(llm_model_response.structured_output_response, ReasonedScore):
                logger.error(f"Unexpected structured output type from eval {eval_score.eval_name}")
                return False

            # Save eval results
            eval_score.eval_results = {
                "score": llm_model_response.structured_output_response.score,
                "reason": llm_model_response.structured_output_response.reason,
                "cost": float(llm_model_response.cost),
            }
            db_session.commit()

            logger.info(f"Executed eval {eval_score.eval_name} v{eval_score.eval_version} for prompt result {prompt_result.id}")
            return True

        except Exception as e:
            logger.error(f"Error executing eval {eval_score.eval_name} v{eval_score.eval_version}: {e}", exc_info=True)
            return False
