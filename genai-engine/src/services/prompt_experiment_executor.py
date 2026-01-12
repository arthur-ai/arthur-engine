"""
Service for asynchronously executing prompt experiments in the background.

This module handles the execution of prompt experiments by:
1. Running prompts for each test case across multiple prompt versions
2. Executing evaluations on the prompt outputs
3. Updating experiment and test case statuses throughout execution
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db_models.prompt_experiment_models import (
    DatabasePromptExperiment,
    DatabasePromptExperimentTestCase,
    DatabasePromptExperimentTestCasePromptResult,
)
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.model_provider_repository import ModelProviderRepository
from repositories.prompt_experiment_repository import PromptExperimentRepository
from schemas.agentic_experiment_schemas import RequestTimeParameter
from schemas.base_experiment_schemas import (
    EvalResultSummary,
    TestCaseStatus,
)
from schemas.prompt_experiment_schemas import (
    PromptEvalResultSummaries,
    SummaryResults,
)
from schemas.request_schemas import PromptCompletionRequest, VariableTemplateValue
from services.experiment_executor import BaseExperimentExecutor
from services.prompt.chat_completion_service import ChatCompletionService

logger = logging.getLogger(__name__)


class PromptExperimentExecutor(BaseExperimentExecutor):
    """Handles asynchronous execution of prompt experiments"""

    def __init__(self) -> None:
        super().__init__()
        self.chat_completion_service = ChatCompletionService()

    def _get_database_experiment(
        self,
        experiment_id: str,
        session: Session,
    ) -> Optional[DatabasePromptExperiment]:
        prompt_experiment_repo = PromptExperimentRepository(session)
        try:
            return prompt_experiment_repo._get_db_experiment(experiment_id)
        except HTTPException:
            logger.error(f"Prompt experiment with ID {experiment_id} not found.")
            return None

    def _get_db_test_cases(
        self,
        experiment_id: str,
        db_session: Session,
    ) -> List[DatabasePromptExperimentTestCase]:
        prompt_experiment_repo = PromptExperimentRepository(db_session)
        return prompt_experiment_repo._get_db_test_cases(experiment_id)

    def _get_db_test_case(
        self,
        test_case_id: str,
        db_session: Session,
    ) -> Optional[DatabasePromptExperimentTestCase]:
        prompt_experiment_repo = PromptExperimentRepository(db_session)
        return prompt_experiment_repo._get_db_test_case(test_case_id)

    def _execute_experiment_outputs(
        self,
        db_session: Session,
        test_case: DatabasePromptExperimentTestCase,
        request_time_parameters: Optional[List[RequestTimeParameter]] = None,
    ) -> bool:
        """
        Execute all prompts for a test case.

        Args:
            db_session: Database session
            test_case: Test case to execute prompts for
            request_time_parameters: Optional list of request-time parameters (not used for prompt experiments)

        Returns:
            True if all prompts executed successfully, False otherwise
        """
        any_prompt_failed = False
        for prompt_result in test_case.prompt_results:
            success = self._execute_prompt(db_session, prompt_result, test_case)
            if not success:
                any_prompt_failed = True
                logger.warning(
                    f"Prompt {prompt_result.prompt_key} failed in test case {test_case.id}, continuing with other prompts",
                )
        return not any_prompt_failed

    def _calculate_total_test_case_cost(
        self,
        test_case: DatabasePromptExperimentTestCase,
    ) -> float:
        """
        Calculate the total cost for a prompt test case.
        Includes both prompt execution costs and eval costs.

        Args:
            test_case: Test case to calculate cost for

        Returns:
            Total cost as a float
        """
        total_cost = 0.0
        for prompt_result in test_case.prompt_results:
            # Add prompt execution cost
            if prompt_result.output_cost:
                try:
                    total_cost += float(prompt_result.output_cost)
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not parse prompt cost: {prompt_result.output_cost}",
                    )

            # Add eval costs
            total_cost += self._calculate_total_cost_eval_scores(
                prompt_result.eval_scores,
            )
        return total_cost

    def _set_summary_results(
        self,
        db_session: Session,
        experiment: DatabasePromptExperiment,
    ) -> None:
        """
        Calculate summary results for an experiment based on completed test cases.

        Args:
            db_session: Database session
            experiment: DatabasePromptExperiment object

        Sets summary results dictionary with prompt_eval_summaries
        """
        try:
            # Get all completed test cases with their prompt results and eval scores
            test_cases = (
                db_session.query(DatabasePromptExperimentTestCase)
                .filter_by(
                    experiment_id=experiment.id,
                    status=TestCaseStatus.COMPLETED.value,
                )
                .all()
            )

            if not test_cases:
                experiment.summary_results = SummaryResults(
                    prompt_eval_summaries=[],
                ).model_dump(
                    mode="python",
                    exclude_none=True,
                )
                return

            # Build a structure to aggregate results: {prompt_key: {(eval_name, eval_version): [scores]}}
            results_by_prompt: dict[
                str,
                dict[tuple[str, int], list[float]],
            ] = {}

            for test_case in test_cases:
                for prompt_result in test_case.prompt_results:
                    prompt_key = prompt_result.prompt_key

                    if prompt_key not in results_by_prompt:
                        results_by_prompt[prompt_key] = {}

                    for eval_score in prompt_result.eval_scores:
                        eval_key = (eval_score.eval_name, eval_score.eval_version)

                        if eval_key not in results_by_prompt[prompt_key]:
                            results_by_prompt[prompt_key][eval_key] = []

                        # Add the score if eval result exists
                        if eval_score.eval_result_score is not None:
                            results_by_prompt[prompt_key][eval_key].append(
                                eval_score.eval_result_score,
                            )

            # Build the summary structure using Pydantic models
            prompt_eval_summaries = []
            for prompt_key, eval_results in sorted(results_by_prompt.items()):
                # Parse prompt_key to get type and display name/version
                # Format: "saved:name:version" or "unsaved:auto_name"
                if prompt_key.startswith("saved:"):
                    prompt_type = "saved"
                    parts = prompt_key.split(":", 2)
                    prompt_name = parts[1] if len(parts) > 1 else prompt_key
                    prompt_version = parts[2] if len(parts) > 2 else "1"
                elif prompt_key.startswith("unsaved:"):
                    prompt_type = "unsaved"
                    parts = prompt_key.split(":", 1)
                    prompt_name = parts[1] if len(parts) > 1 else prompt_key
                    prompt_version = None  # Unsaved prompts don't have versions
                else:
                    # Fallback for legacy format
                    logger.warning(
                        f"Unexpected prompt key format: {prompt_key}",
                    )
                    continue

                eval_result_list = []
                for (eval_name, eval_version), scores in sorted(eval_results.items()):
                    # Count how many passed (score >= 0.5, assuming 0-1 scale)
                    pass_count = sum(1 for s in scores if s >= 0.5)
                    total_count = len(scores)

                    eval_result_list.append(
                        EvalResultSummary(
                            eval_name=eval_name,
                            eval_version=str(eval_version),
                            pass_count=pass_count,
                            total_count=total_count,
                        ),
                    )

                prompt_eval_summaries.append(
                    PromptEvalResultSummaries(
                        prompt_key=prompt_key,
                        prompt_type=prompt_type,
                        prompt_name=prompt_name,
                        prompt_version=prompt_version,
                        eval_results=eval_result_list,
                    ),
                )

            experiment.summary_results = SummaryResults(
                prompt_eval_summaries=prompt_eval_summaries,
            ).model_dump(mode="python", exclude_none=True)

        except Exception as e:
            logger.error(
                f"Error calculating summary results for prompt experiment {experiment.id}: {e}",
                exc_info=True,
            )
            experiment.summary_results = SummaryResults(
                prompt_eval_summaries=[],
            ).model_dump(
                mode="python",
                exclude_none=True,
            )

    def _execute_prompt(
        self,
        db_session: Session,
        prompt_result: DatabasePromptExperimentTestCasePromptResult,
        test_case: DatabasePromptExperimentTestCase,
    ) -> bool:
        """
        Execute a single prompt (saved or unsaved) and save the output.

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

            # Get or construct the prompt based on type
            if prompt_result.prompt_type == "saved":
                # Load saved prompt from repository
                prompt_repo = AgenticPromptRepository(db_session)
                try:
                    prompt = prompt_repo.get_llm_item(
                        task_id=experiment.task_id,
                        item_name=prompt_result.name,
                        item_version=str(prompt_result.version),
                    )
                except ValueError as e:
                    logger.error(
                        f"Saved prompt {prompt_result.name} v{prompt_result.version} not found: {e}",
                    )
                    return False

            elif prompt_result.prompt_type == "unsaved":
                # Construct prompt from unsaved config in experiment
                # Find the matching config by auto_name
                from schemas.agentic_prompt_schemas import AgenticPrompt

                unsaved_config = None
                for config in experiment.prompt_configs:
                    if (
                        config.get("type") == "unsaved"
                        and config.get("auto_name")
                        == prompt_result.unsaved_prompt_auto_name
                    ):
                        unsaved_config = config
                        break

                if not unsaved_config:
                    logger.error(
                        f"Unsaved prompt config '{prompt_result.unsaved_prompt_auto_name}' not found in experiment",
                    )
                    return False

                # Construct AgenticPrompt object from unsaved config
                prompt = AgenticPrompt(
                    name=unsaved_config.get("auto_name", "unsaved_prompt"),
                    messages=unsaved_config.get("messages", []),
                    model_name=unsaved_config.get("model_name"),
                    model_provider=unsaved_config.get("model_provider"),
                    version=1,  # Unsaved prompts don't have versions
                    tools=unsaved_config.get("tools"),
                    variables=unsaved_config.get("variables", []),
                    created_at=datetime.now(),
                )

            else:
                logger.error(f"Unknown prompt type: {prompt_result.prompt_type}")
                return False

            # Get LLM client
            model_provider_repo = ModelProviderRepository(db_session)
            llm_client = model_provider_repo.get_model_provider_client(
                prompt.model_provider,
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
                    msg.model_dump(mode="python", exclude_none=True),
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
                ],
            )

            response = self.chat_completion_service.run_chat_completion(
                prompt=prompt,
                llm_client=llm_client,
                completion_request=completion_request,
            )

            # Save output to separate columns
            prompt_result.output_content = (
                response.content if response.content else None
            )
            prompt_result.output_tool_calls = (
                response.tool_calls if response.tool_calls else None
            )
            prompt_result.output_cost = response.cost or ""
            db_session.commit()

            logger.info(
                f"Executed prompt {prompt_result.prompt_key} for test case {test_case.id}",
            )
            return True

        except Exception as e:
            logger.error(
                f"Error executing prompt {prompt_result.prompt_key}: {e}",
                exc_info=True,
            )
            return False

    def _execute_evaluations(
        self,
        db_session: Session,
        test_case: DatabasePromptExperimentTestCase,
    ) -> bool:
        """
        Execute all evaluations for a prompt test case.

        Args:
            db_session: Database session
            test_case: Test case containing prompt results to evaluate

        Returns:
            True if all evaluations executed successfully, False otherwise
        """
        try:
            any_eval_failed = False
            for prompt_result in test_case.prompt_results:
                success = self._execute_evaluations_for_result(
                    db_session,
                    prompt_result,
                )
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Evaluations failed for prompt {prompt_result.prompt_key} in test case {test_case.id}, continuing with other evaluations",
                    )
            return not any_eval_failed
        except Exception as e:
            logger.error(
                f"Error executing evaluations for test case {test_case.id}: {e}",
                exc_info=True,
            )
            return False

    def _execute_evaluations_for_result(
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
                    db_session,
                    eval_score,
                    prompt_result,
                )
                if not success:
                    any_eval_failed = True
                    logger.warning(
                        f"Eval {eval_score.eval_name} v{eval_score.eval_version} failed for prompt result {prompt_result.id}, continuing with other evals",
                    )

            return not any_eval_failed

        except Exception as e:
            logger.error(
                f"Error executing evaluations for prompt result {prompt_result.id}: {e}",
                exc_info=True,
            )
            return False

    def _process_experiment_output_variable(
        self,
        test_case_result: DatabasePromptExperimentTestCasePromptResult,
        variable_name: str,
        json_path: Optional[str],
    ) -> str:
        """
        Extract the value for an experiment_output variable from a prompt result.

        Args:
            test_case_result: Prompt result with output
            variable_name: Name of the variable to extract
            json_path: Not used for prompt experiments (kept for interface compatibility)

        Returns:
            The extracted value as a string
            Priority: content -> tool_calls JSON -> default message
        """
        # Get the value from prompt output
        # Priority: content -> tool_calls JSON -> default message
        if test_case_result.output_content:
            return test_case_result.output_content
        elif test_case_result.output_tool_calls:
            # If no content but tool calls exist, use JSON string of tool calls
            return json.dumps(test_case_result.output_tool_calls, indent=2)
        else:
            # If neither content nor tool calls, use default message
            return "No content was generated"
