import os

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from enum import Enum
from typing import Set

load_dotenv()

GENAI_ENGINE_API_KEY = os.getenv("GENAI_ENGINE_API_KEY")
GENAI_ENGINE_BASEURL = os.getenv("GENAI_ENGINE_BASEURL") + "/api/v2"
GENAI_ENGINE_TASK_ID = os.getenv("GENAI_ENGINE_TASK_ID")

mcp = FastMCP(
    name="arthur-engine-mcp",
    instructions="""
        This server provides functionality to interact with the Arthur Engine API, a platform that provides LLM guardrails.
        To setup guardrails we create tasks that have subsequent rules (e.g. toxicity, hallucination, etc.)
    """,
)

class RuleTypesEnum(Enum):
    SENSITIVE_DATA = "ModelSensitiveDataRule"
    REGEX = "RegexRule"
    KEYWORD = "KeywordRule"
    PROMPT_INJECTION = "PromptInjectionRule"
    HALLUCINATION = "ModelHallucinationRuleV2"
    PII = "PIIDataRule"
    TOXICITY = "ToxicityRule"

RULE_TYPE_TO_ENUM = {e.value: e for e in RuleTypesEnum}
RULE_TYPE_NAMES = {
    "ModelSensitiveDataRule": "Sensitive Data",
    "RegexRule": "Regex",
    "KeywordRule": "Keyword",
    "PromptInjectionRule": "Prompt Injection",
    "ModelHallucinationRuleV2": "Hallucination",
    "PIIDataRule": "PII",
    "ToxicityRule": "Toxicity",
}


def validate_prompt(prompt, task_id):
    validate_prompt_url = f"{GENAI_ENGINE_BASEURL}/tasks/{task_id}/validate_prompt"
    return requests.post(
        validate_prompt_url,
        json={"prompt": prompt, "conversation_id": "1", "user_id": "1"},
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )


def validate_response(llm_response, context, task_id):
    validate_prompt_response = validate_prompt(context, task_id)

    if validate_prompt_response.status_code != 200:
        return "Failed to validate prompt"

    validate_prompt_response_json = validate_prompt_response.json()
    inference_id = validate_prompt_response_json["inference_id"]
    validate_response_url = (
        f"{GENAI_ENGINE_BASEURL}/tasks/{task_id}/validate_response/{inference_id}"
    )
    return requests.post(
        validate_response_url,
        json={"response": llm_response, "context": context},
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )


@mcp.tool
def run_guardrails_on_prompt(user_input_text: str, rule_types: Set[RuleTypesEnum]):
    """
    Checks specific guardrails over a user's input. This should be called before generating any response for the user.
    If this check fails, you should not respond to a user's request and you should only respond with the returned response text of this function.

    Parameters:
        user_input_text (str) - The user's input text.
        rule_types (Set[RuleTypesEnum]) - The guardrails to run.

    IMPORTANT: Only include rule types the user **explicitly names** in `rule_types`. 
    Do NOT include any rule types not explicitly named by the user unless a user doesn't specify any rule types.

    Examples:
        user_input_text: "Tell me a joke and check this prompt for toxicity" -> ONLY CHECK FOR TOXICITY
        user_input_text: "Tell me a joke" -> CHECK FOR ALL GUARDRAILS
        user_input_text: "Tell me a joke and check this prompt for toxicity and PII" -> ONLY CHECK FOR TOXICITY AND PII
    """
    response = validate_prompt(user_input_text, GENAI_ENGINE_TASK_ID)
    if response.status_code != 200:
        return f"Failed to validate prompt: {response.status_code} {response.text}"

    response_json = response.json()

    if "rule_results" not in response_json:
        return f"Failed to find rule_results in prompt response: {response.status_code} {response.text}"

    rule_results = response_json["rule_results"]
    failed_rules = []

    for rule_result in rule_results:
        enum_rule_type = RULE_TYPE_TO_ENUM[rule_result["rule_type"]]

        if rule_result["result"] != "Pass" and enum_rule_type in rule_types:
            rule_name = RULE_TYPE_NAMES[rule_result["rule_type"]]
            failed_rules.append(rule_name)

    if len(failed_rules) == 0:
        return f"All rules passed!"

    return f"Failed rules: {', '.join(failed_rules)}"


@mcp.tool
def run_guardrails_on_response(llm_response_text: str, context: str, rule_types: Set[RuleTypesEnum]):
    """
    Checks specific guardrails over an LLM's response. This should always be called before returning a response to the user.
    If this check fails, you should not respond to a user's request and you should only respond with the returned response text of this function.

    Parameters:
        llm_response_text (str) - The generated response from the LLM.
        context (str) - The context that led to this response. If you do not use any context, you can pass in the original prompt.
        rule_types (Set[RuleTypesEnum]) - The guardrails to run.

    IMPORTANT: Only include rule types the user **explicitly names** in `rule_types`. 
    Do NOT include any rule types not explicitly named by the user unless a user doesn't specify any rule types.

    Examples:
        User's Request: "Tell me a joke and check it for toxicity" -> ONLY CHECK FOR TOXICITY
        User's Request: "Tell me a joke" -> CHECK FOR ALL GUARDRAILS
        User's Request: "Tell me a joke and check the response for toxicity and PII" -> ONLY CHECK FOR TOXICITY AND PII
    """
    response = validate_response(llm_response_text, context, GENAI_ENGINE_TASK_ID)
    if response.status_code != 200:
        return f"Failed to validate response: {response.status_code} {response.text}"

    response_json = response.json()

    if "rule_results" not in response_json:
        return f"Failed to find rule_results in response: {response.status_code} {response.text}"

    rule_results = response_json["rule_results"]
    failed_rules = []

    for rule_result in rule_results:
        enum_rule_type = RULE_TYPE_TO_ENUM[rule_result["rule_type"]]

        if rule_result["result"] != "Pass" and enum_rule_type in rule_types:
            rule_name = RULE_TYPE_NAMES[rule_result["rule_type"]]
            failed_rules.append(rule_name)

    if len(failed_rules) == 0:
        return f"All rules passed!"

    return f"Failed rules: {', '.join(failed_rules)}"


@mcp.tool
def create_toxicity_task(
    task_name: str = "ToxicityTask",
    rule_name: str = "Toxicity Rule",
    apply_to_prompt: bool = True,
    apply_to_response: bool = True,
    toxicity_threshold: float = 0.5,
):
    """
    Creates a task in the Arthur Engine which has a toxicity rule applied to it.
    All parameters are optional and have default values.

    Parameters:
        task_name (str) - The name of the task to create.
        rule_name (str) - The name of the rule to create.
        apply_to_prompt (bool) - Whether to apply the rule to the prompt.
        apply_to_response (bool) - Whether to apply the rule to the response.
        toxicity_threshold (float) - The threshold for the toxicity rule.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    task_url = GENAI_ENGINE_BASEURL + "/task"
    task_response = requests.post(
        task_url,
        json={"name": task_name},
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )

    if task_response.status_code == 200:
        task_response_json = task_response.json()
        task_id = task_response_json["id"]

        rule_url = f"{GENAI_ENGINE_BASEURL}/tasks/{task_id}/rules"
        rule_response = requests.post(
            rule_url,
            json={
                "name": rule_name,
                "type": RuleTypesEnum.TOXICITY.value,
                "apply_to_prompt": apply_to_prompt,
                "apply_to_response": apply_to_response,
                "config": {"threshold": toxicity_threshold},
            },
            headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
        )

        if rule_response.status_code == 200:
            rule_response_json = rule_response.json()
            rule_id = rule_response_json["id"]
            return f"Toxicity task created with ID: {task_id} and rule ID: {rule_id}"
        else:
            return f"Failed to create rule: {rule_response.status_code} {rule_response.text}"

    return f"Failed to create task: {task_response.status_code} {task_response.text}"


@mcp.tool
def add_prompt_injection_rule_to_task(
    task_name: str,
    rule_name: str = "Prompt Injection Rule",
):
    """
    Adds a prompt injection rule for an existing task in the Arthur Engine.

    Parameters:
        rule_name (str) - The name of the rule to create.
        task_name (str) - The name of the task to add the rule to.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    task_search_url = f"{GENAI_ENGINE_BASEURL}/tasks/search?sort=desc&page_size=10&page=0"
    task_response = requests.post(
        task_search_url,
        json={"name": task_name},
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )

    if task_response.status_code != 200:
        return f"Failed to find task: {task_response.status_code} {task_response.text}"

    task_response_json = task_response.json()
    tasks = task_response_json["tasks"]

    if len(tasks) == 0:
        return f"No task found with name: {task_name}"

    task_id = tasks[0]["id"]
    rule_url = f"{GENAI_ENGINE_BASEURL}/tasks/{task_id}/rules"
    rule_response = requests.post(
        rule_url,
        json={
            "name": rule_name,
            "type": RuleTypesEnum.PROMPT_INJECTION.value,
            "apply_to_prompt": True,
            "apply_to_response": False,
        },
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )

    if rule_response.status_code == 200:
        rule_response_json = rule_response.json()
        rule_id = rule_response_json["id"]
        return f"Successfully added prompt injection rule to task: {task_id} with rule ID: {rule_id}"
    
    return f"Failed to create rule: {rule_response.status_code} {rule_response.text}"

if __name__ == "__main__":
    mcp.run()
