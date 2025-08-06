import os
from enum import Enum
from typing import List

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

GENAI_ENGINE_API_KEY = os.getenv("GENAI_ENGINE_API_KEY")
GENAI_ENGINE_BASEURL = os.getenv("GENAI_ENGINE_BASEURL") + "/api/v2"

mcp = FastMCP(
    name="arthur-admin-mcp",
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

def create_task_and_add_rule(task_name: str, rule_name: str, rule_type: str, apply_to_prompt: bool, apply_to_response: bool, config: dict = None):
    task_url = f"{GENAI_ENGINE_BASEURL}/task"
    task_response = requests.post(
        task_url,
        json={"name": task_name},
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )

    if task_response.status_code != 200:
        return f"Failed to create task: {task_response.status_code} {task_response.text}"

    task_response_json = task_response.json()
    task_id = task_response_json["id"]
    return add_rule_to_task(task_id, rule_name, rule_type, apply_to_prompt, apply_to_response, config)

def find_task_id_by_name(task_name: str):
    task_search_url = f"{GENAI_ENGINE_BASEURL}/tasks/search?sort=desc&page_size=10&page=0"
    task_response = requests.post(
        task_search_url,
        json={"name": task_name},
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )

    if task_response.status_code != 200:
        return "", f"Failed to find task: {task_response.status_code} {task_response.text}",

    task_response_json = task_response.json()
    tasks = task_response_json["tasks"]

    if len(tasks) == 0:
        return "", f"No task found with name: {task_name}"

    return tasks[0]["id"], ""

def add_rule_to_task(task_id: str, rule_name: str, rule_type: str, apply_to_prompt: bool, apply_to_response: bool, config: dict = None):
    rule_url = f"{GENAI_ENGINE_BASEURL}/tasks/{task_id}/rules"

    data = {
        "name": rule_name,
        "type": rule_type,
        "apply_to_prompt": apply_to_prompt,
        "apply_to_response": apply_to_response,
    }

    if config is not None:
        data["config"] = config

    rule_response = requests.post(
        rule_url,
        json=data,
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"},
    )

    if rule_response.status_code == 200:
        rule_response_json = rule_response.json()
        rule_id = rule_response_json["id"]
        return f"Successfully added prompt injection rule to task: {task_id} with rule ID: {rule_id}"

    return f"Failed to create rule: {rule_response.status_code} {rule_response.text}"

def add_rule_to_task_by_name(task_name: str, rule_name: str, rule_type: str, apply_to_prompt: bool, apply_to_response: bool, config: dict = None):
    task_id, err_msg = find_task_id_by_name(task_name)
    if task_id == "":
        return err_msg

    return add_rule_to_task(task_id, rule_name, rule_type, apply_to_prompt, apply_to_response, config)

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
    return create_task_and_add_rule(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.TOXICITY.value,
        apply_to_prompt=apply_to_prompt,
        apply_to_response=apply_to_response,
        config={"threshold": toxicity_threshold},
    )

@mcp.tool
def create_prompt_injection_task(
    task_name: str = "PromptInjectionTask",
    rule_name: str = "Prompt Injection Rule",
):
    """
    Creates a task in the Arthur Engine which has a prompt injection rule applied to it.
    All parameters are optional and have default values.

    Parameters:
        task_name (str) - The name of the task to create.
        rule_name (str) - The name of the rule to create.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    return create_task_and_add_rule(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.PROMPT_INJECTION.value,
        apply_to_prompt=True,
        apply_to_response=False,
    )

@mcp.tool
def create_hallucination_task(
    task_name: str = "HallucinationTask",
    rule_name: str = "Hallucination Rule",
):
    """
    Creates a task in the Arthur Engine which has a prompt injection rule applied to it.
    All parameters are optional and have default values.

    Parameters:
        task_name (str) - The name of the task to create.
        rule_name (str) - The name of the rule to create.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    return create_task_and_add_rule(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.HALLUCINATION.value,
        apply_to_prompt=False,
        apply_to_response=True,
    )

@mcp.tool
def create_pii_task(
    task_name: str = "PIITask",
    rule_name: str = "PII Rule",
    apply_to_prompt: bool = True,
    apply_to_response: bool = True,
    confidence_threshold: float = 0.5,
    disabled_pii_entities: List[str] = [],
    allow_list: List[str] = [],
):
    """
    Creates a task in the Arthur Engine which has a prompt injection rule applied to it.
    All parameters are optional and have default values.

    Parameters:
        task_name (str) - The name of the task to create.
        rule_name (str) - The name of the rule to create.
        apply_to_prompt (bool) - Whether to apply the rule to the prompt.
        apply_to_response (bool) - Whether to apply the rule to the response.
        confidence_threshold (float) - The confidence threshold for the rule.
        disabled_pii_entities (List[str]) - An optionallist of strings that correspond to PII entities a user wants to disable.
        allow_list (List[str]) - An optional list of strings that correspond to PII entities a user wants to allow.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    config = {"confidence_threshold": confidence_threshold}

    if len(disabled_pii_entities) > 0:
        config["disabled_pii_entities"] = disabled_pii_entities

    if len(allow_list) > 0:
        config["allow_list"] = allow_list

    return create_task_and_add_rule(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.PII.value,
        apply_to_prompt=apply_to_prompt,
        apply_to_response=apply_to_response,
        config=config,
    )


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
    return add_rule_to_task_by_name(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.PROMPT_INJECTION.value,
        apply_to_prompt=True,
        apply_to_response=False,
    )

@mcp.tool
def add_toxicity_rule_to_task(
    task_name: str,
    rule_name: str = "Toxicity Rule",
    apply_to_prompt: bool = True,
    apply_to_response: bool = True,
    threshold: float = 0.5,
):
    """
    Adds a toxicity rule for an existing task in the Arthur Engine.

    Parameters:
        rule_name (str) - The name of the rule to create.
        task_name (str) - The name of the task to add the rule to.
        apply_to_prompt (bool) - Whether to apply the rule to the prompt.
        apply_to_response (bool) - Whether to apply the rule to the response.
        threshold (float) - The threshold for the toxicity rule.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    return add_rule_to_task_by_name(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.TOXICITY.value,
        apply_to_prompt=apply_to_prompt,
        apply_to_response=apply_to_response,
        config={"threshold": threshold},
    )

@mcp.tool
def add_hallucination_rule_to_task(
    task_name: str,
    rule_name: str = "Hallucination Rule",
):
    """
    Adds a hallucination rule for an existing task in the Arthur Engine.

    Parameters:
        rule_name (str) - The name of the rule to create.
        task_name (str) - The name of the task to add the rule to.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    return add_rule_to_task_by_name(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.HALLUCINATION.value,
        apply_to_prompt=False,
        apply_to_response=True,
    )

@mcp.tool
def add_regex_rule_to_task(
    task_name: str,
    regex_patterns: List[str],
    apply_to_prompt: bool = True,
    apply_to_response: bool = True,
    rule_name: str = "Regex Rule",
):
    """
    Adds a regex rule for an existing task in the Arthur Engine.

    Parameters:
        task_name (str) - The name of the task to add the rule to.
        regex_patterns (List[str]) - A list of strings that correspond to regex patterns to match.
        apply_to_prompt (bool) - Whether to apply the rule to the prompt.
        apply_to_response (bool) - Whether to apply the rule to the response.
        rule_name (str) - The name of the rule to create.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    if len(regex_patterns) == 0:
        return "No regex patterns found. Please provide at least one regex pattern to continue."

    return add_rule_to_task_by_name(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.REGEX.value,
        apply_to_prompt=apply_to_prompt,
        apply_to_response=apply_to_response,
        config={"regex_patterns": regex_patterns},
    )

@mcp.tool
def add_keyword_rule_to_task(
    task_name: str,
    keywords: List[str],
    apply_to_prompt: bool = True,
    apply_to_response: bool = True,
    rule_name: str = "Blocked Keywords Rule",
):
    """
    Adds a keywords rule for an existing task in the Arthur Engine.

    Parameters:
        task_name (str) - The name of the task to add the rule to.
        keywords (List[str]) - A list of strings that correspond to keywords a user wants to block.
        apply_to_prompt (bool) - Whether to apply the rule to the prompt.
        apply_to_response (bool) - Whether to apply the rule to the response.
        rule_name (str) - The name of the rule to create.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    if len(keywords) == 0:
        return "No keywords found. Please provide at least one keyword to continue."

    return add_rule_to_task_by_name(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.KEYWORD.value,
        apply_to_prompt=apply_to_prompt,
        apply_to_response=apply_to_response,
        config={"keywords": keywords},
    )

@mcp.tool
def add_pii_rule_to_task(
    task_name: str,
    apply_to_prompt: bool = True,
    apply_to_response: bool = True,
    rule_name: str = "PII Rule",
    confidence_threshold: float = 0.5,
    disabled_pii_entities: List[str] = [],
    allow_list: List[str] = [],
):
    """
    Adds a keywords rule for an existing task in the Arthur Engine.

    Parameters:
        task_name (str) - The name of the task to add the rule to.
        apply_to_prompt (bool) - Whether to apply the rule to the prompt.
        apply_to_response (bool) - Whether to apply the rule to the response.
        rule_name (str) - The name of the rule to create.
        confidence_threshold (float) - The confidence threshold for the rule.
        disabled_pii_entities (List[str]) - An optionallist of strings that correspond to PII entities a user wants to disable.
        allow_list (List[str]) - An optional list of strings that correspond to PII entities a user wants to allow.

    Returns:
        str - The ID of the task and rule created and the status of the request.
    """
    config = {"confidence_threshold": confidence_threshold}

    if len(disabled_pii_entities) > 0:
        config["disabled_pii_entities"] = disabled_pii_entities

    if len(allow_list) > 0:
        config["allow_list"] = allow_list

    return add_rule_to_task_by_name(
        task_name=task_name,
        rule_name=rule_name,
        rule_type=RuleTypesEnum.PII.value,
        apply_to_prompt=apply_to_prompt,
        apply_to_response=apply_to_response,
        config=config,
    )

if __name__ == "__main__":
    mcp.run()
