from arthur_common.models.enums import RuleResultEnum
from langchain_core.messages import HumanMessage
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer
from services.guardrails.judge_executor import JudgeContext, JudgeEvaluation


def create_examples_template() -> PromptTemplate:
    """Creates a prompt template for format examples"""
    return PromptTemplate(
        template="output: {hint} {output}\nanswer: {answer}\n",
        input_variables=["hint", "output", "answer"],
    )


def sensitive_data_with_examples_template() -> FewShotPromptTemplate:
    """Creates the sensitive data with custom examples template"""
    prefix = """
    The following are sets of outputs from an LLM and answers from a test that determines whether the output contains
    any sensitive data.\n {hint} Anything else is irrelevant. The answers
    are always either 'yes' or 'no' depending on whether the output contains sensitive data.\nHere are some examples:\n"
    """
    suffix = """
    "\noutput:{hint} {prompt}\nanswer: "
    """
    dynamic_prompt = FewShotPromptTemplate(
        prefix=prefix,
        example_prompt=create_examples_template(),
        examples=[],
        suffix=suffix,
        input_variables=["prompt", "hint"],
    )

    return dynamic_prompt


class SensitiveDataCustomExamples(RuleScorer):
    def score(
        self, request: ScoreRequest, judge_context: JudgeContext | None = None
    ) -> RuleScore:
        """Scores for sensitive data with custom examples"""
        if not request.examples:
            raise ValueError("Need to provide examples to run this sensitive data rule")

        # Convert examples to correct format
        examples = request.examples
        formatted_examples = []

        # catch for none or empty hints
        if request.hint is None or request.hint == "":
            hint_sentence = ""
        else:
            hint_sentence = (
                f"The sensitive data you are looking for is {request.hint}. "
            )

        for example_config in examples:
            output_dic = {
                "hint": hint_sentence,
                "output": example_config.exampleInput,
                "answer": (
                    "yes"
                    if example_config.ruleOutput.result == RuleResultEnum.FAIL
                    else "no"
                ),
            }
            formatted_examples.append(output_dic)

        # Add the examples to the dynamic prompt
        dynamic_prompt = sensitive_data_with_examples_template()
        dynamic_prompt.examples = formatted_examples

        # Format and score the dynamic prompt
        evaluation = JudgeEvaluation(judge_context)
        try:
            result = evaluation.complete(
                [
                    HumanMessage(
                        content=dynamic_prompt.format(
                            prompt=request.user_prompt, hint=hint_sentence
                        )
                    )
                ],
                "sensitive data check",
            )
        except Exception as e:
            return evaluation.unavailable(e)
        content = result.text
        token_consumption = result.tokens
        if "yes" in content.lower():
            return RuleScore(
                result=RuleResultEnum.FAIL,
                prompt_tokens=token_consumption.prompt_tokens,
                completion_tokens=token_consumption.completion_tokens,
            )
        return RuleScore(
            result=RuleResultEnum.PASS,
            prompt_tokens=token_consumption.prompt_tokens,
            completion_tokens=token_consumption.completion_tokens,
        )
