from fastmcp import FastMCP
import requests
from dotenv import load_dotenv
import os

load_dotenv()

GENAI_ENGINE_API_KEY = os.getenv('GENAI_ENGINE_API_KEY')
GENAI_ENGINE_BASEURL = os.getenv('GENAI_ENGINE_BASEURL') + "/api/v2"

mcp = FastMCP(
    name="arthur-engine-mcp",
    instructions="""
        This server provides functionality to interact with the Arthur Engine API, a platform that provides LLM guardrails.
        To setup guardrails we create tasks that have subsequent rules (e.g. toxicity, hallucination, etc.)
    """,
)

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
        headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"}
    )

    if task_response.status_code == 200:
        task_response_json = task_response.json()
        task_id = task_response_json['id']

        rule_url = f"{GENAI_ENGINE_BASEURL}/tasks/{task_id}/rules"
        rule_response = requests.post(
            rule_url, 
            json={
                "name": rule_name, 
                "type": "ToxicityRule", 
                "apply_to_prompt": apply_to_prompt, 
                "apply_to_response": apply_to_response,
                "config": {"threshold": toxicity_threshold},
            }, 
            headers={"Authorization": f"Bearer {GENAI_ENGINE_API_KEY}"}
        )

        if rule_response.status_code == 200:
            rule_response_json = rule_response.json()
            rule_id = rule_response_json['id']
            return f"Toxicity task created with ID: {task_id} and rule ID: {rule_id}"
        else:
            return f"Failed to create rule: {rule_response.status_code} {rule_response.text}"
    
    return f"Failed to create task: {task_response.status_code} {task_response.text}"

if __name__ == "__main__":
    mcp.run()