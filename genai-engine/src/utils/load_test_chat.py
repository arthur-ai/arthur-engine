import concurrent
import os
import random
import time
import uuid

import httpx

"""
Modify each of the below variables to your liking and then run this script.
"""
# Number of chat "clients" to simulate
TOTAL_AGENTS = 10
# Enable / disable this rule type for chat
ENABLE_PROMPT_INJECTION = True
ENABLE_SENSITIVE_DATA = True
ENABLE_HALLUCINATION_V2 = True

# Host to run against
HOST = "http://localhost:8000"
# Number of back and forths until the client ends. One prompt / one response is a conversation length of 1
CONVERSATION_LENGTH = 8
AUTHORIZED_HEADERS = {
    "Authorization": f"Bearer {os.environ.get('GENAI_ENGINE_AUTH_API_KEY')}",
}

"""
Default rule definitions, prompt list below.
"""

PROMPTS = [
    "Tell me a short story about a place called Iceland",
    "Tell me a short story about a place called Algeria",
    "Tell me a short story about a place called France",
]

SENSITIVE_DATA_RULE_BODY = {
    "name": "Sensitive Data Rule",
    "type": "ModelSensitiveDataRule",
    "apply_to_prompt": True,
    "apply_to_response": False,
    "config": {
        "examples": [
            {"example": "John has O negative blood group", "result": True},
            {
                "example": "Most og the people have A positive blood group",
                "result": False,
            },
        ],
    },
}

PROMPT_INJECTION_RULE_BODY = {
    "name": "Prompt Injection Rule",
    "type": "PromptInjectionRule",
    "apply_to_prompt": True,
    "apply_to_response": False,
}

HALLUCINATION_V2_RULE_BODY = {
    "name": "Hallucination Rule",
    "type": "ModelHallucinationRuleV2",
    "apply_to_prompt": False,
    "apply_to_response": True,
}


class ChatAgent:
    def __init__(
        self,
        id,
        server_url,
        prompt_delay_seconds=10.0,
        conversation_length=5,
    ):
        self.id = id
        self.prompt_delay_seconds = prompt_delay_seconds
        self.conversation_length = conversation_length
        self.client = httpx.Client(base_url=server_url, timeout=60)
        self.converation_id = str(uuid.uuid4())

    def run_agent(self):
        # Start delay so every agent doesn't go at once:
        time.sleep(random.random() * self.prompt_delay_seconds)
        for i in range(self.conversation_length):
            self.post_chat()
            print("Pausing Agent %s..." % self.id)
            time.sleep(self.prompt_delay_seconds)
            print("Resuming Agent %s..." % self.id)

    def post_chat(self):
        request = {
            "user_prompt": get_random_prompt(),
            "conversation_id": self.converation_id,
            "file_ids": [],
        }
        resp = self.client.post("/api/chat/", json=request, headers=AUTHORIZED_HEADERS)
        print("Chat returned in %5d seconds" % resp.elapsed.total_seconds())
        if resp.status_code != 200:
            print("Chat request failed with status code %d" % resp.status_code)
            print("Response body: %s" % resp.json())
        return resp


def get_random_prompt():
    return random.choice(PROMPTS)


def create_rule(body, client, task_id):
    resp = client.post(
        "/api/v2/tasks/%s/rules" % task_id,
        json=body,
        headers=AUTHORIZED_HEADERS,
    )
    if resp.status_code != 200:
        raise ValueError("Could not create rule.")
    else:
        print(resp.json())
    return resp


def update_chat_config(client, task_id):
    uri = "/api/v2/configuration"
    config = {"chat_task_id": task_id}
    resp = client.post(
        uri,
        json=config,
        headers=AUTHORIZED_HEADERS,
    )
    if resp.status_code != 200:
        raise ValueError("Could not update config.")
    else:
        print(resp.json())
    return resp


def create_chat_task(
    server_url,
    sensitive_data=True,
    prompt_injection=True,
    hallucination_v2=True,
):
    client = httpx.Client(base_url=server_url)
    request = {}
    request["name"] = "Chat Task"

    # Create Task:
    resp = client.post(
        "/api/v2/tasks",
        json=request,
        headers=AUTHORIZED_HEADERS,
    )
    task_id = resp.json()["id"]
    print(task_id)

    # Associate Rules
    if sensitive_data:
        create_rule(SENSITIVE_DATA_RULE_BODY, client, task_id)
    if prompt_injection:
        create_rule(PROMPT_INJECTION_RULE_BODY, client, task_id)
    if hallucination_v2:
        create_rule(HALLUCINATION_V2_RULE_BODY, client, task_id)

    # Update Config
    update_chat_config(client, task_id)

    return task_id


if __name__ == "__main__":
    url = HOST

    create_chat_task(
        url,
        sensitive_data=ENABLE_SENSITIVE_DATA,
        prompt_injection=ENABLE_PROMPT_INJECTION,
        hallucination_v2=ENABLE_HALLUCINATION_V2,
    )
    print("====================================")
    print("Created Chat Task, running agents...")
    print("====================================")

    agents = []
    for i in range(TOTAL_AGENTS):
        agents.append(ChatAgent(i, url, conversation_length=CONVERSATION_LENGTH))

    thread_futures = []
    print(agents)
    with concurrent.futures.ThreadPoolExecutor(max_workers=TOTAL_AGENTS) as executor:
        for agent in agents:
            print(agent)
            future = executor.submit(agent.run_agent)
            thread_futures.append(future)
    for future in thread_futures:
        future.result()
