import json
import logging
import os
import random
import sys

import pandas as pd
from dotenv import load_dotenv
from locust import HttpUser, between, task
from arthur_common.models.response_schemas import ValidationResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("locust")

load_dotenv()
TOKEN = os.environ.get("GENAI_ENGINE_ADMIN_KEY")
VALIDATE_RESPONSE = os.environ.get("VALIDATE_RESPONSE", False)
RULES_FILE = os.environ.get("RULES_FILE", "data/rules-min.json")
INFERENCES_FILE = os.environ.get("INFERENCES_FILE", "data/inferences-generic.json")
PROMPTS_FILE = os.environ.get("PROMPTS_FILE", None)


def load_json(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except Exception as e:
        logging.info(f"Error loading JSON from {file_path}: {e}")
        raise e


RULES = load_json(RULES_FILE)
logging.info(f"Loaded {RULES_FILE}")
INFERENCES = load_json(INFERENCES_FILE)
logging.info(f"Loaded {INFERENCES_FILE}")
PROMPTS = None
if PROMPTS_FILE:
    try:
        PROMPTS = pd.read_parquet(PROMPTS_FILE)
        VALIDATE_RESPONSE = False
        logging.info(f"Loaded {PROMPTS_FILE} with {PROMPTS.shape[0]} prompts")
    except Exception as e:
        logging.info(f"Error reading Parquet file from {PROMPTS_FILE}: {e}")
        raise e


class GenaiEngineUser(HttpUser):
    wait_time = between(
        float(os.getenv("WAIT_TIME_MIN", 0.1)),
        float(os.getenv("WAIT_TIME_MAX", 5.0)),
    )

    def on_start(self):
        if not TOKEN:
            raise Exception("API TOKEN is not set")
        self.client.headers = {"Authorization": f"Bearer {TOKEN}"}
        self.rules_ids = []
        response = self.client.post(
            "/api/v2/tasks",
            json={"name": "Performance_Test_Task"},
        )
        logging.info(f"Task creation response: {response.text}")
        if response.status_code != 200:
            raise Exception(
                f"Failed to create task: {response.status_code} {response.text}",
            )
        else:
            self.task_id = response.json()["id"]

        for rule in RULES:
            response = self.client.post(
                f"/api/v2/tasks/{self.task_id}/rules",
                json=rule,
            )
            if response.status_code != 200:
                logging.info(
                    f"Rule creation response: {response.status_code} {response.text}",
                )
                raise Exception("Failed to create rule")
            else:
                self.rules_ids.append(response.json()["id"])

    @task
    def validate(self):
        if PROMPTS is not None:
            prompt = PROMPTS.sample(n=1).iloc[0]
            prompt_text = prompt["prompt"]
        else:
            prompt = random.choice(INFERENCES)
            prompt_text = prompt["prompt"]
        response = self.client.post(
            f"/api/v2/tasks/{self.task_id}/validate_prompt",
            json={"prompt": prompt_text},
        )
        if VALIDATE_RESPONSE and response.status_code == 200:
            loaded_response = response.json()
            validation_result = ValidationResult(**loaded_response)
            inference_id = validation_result.inference_id
            self.client.post(
                f"/api/v2/tasks/{self.task_id}/validate_response/{inference_id}",
                json={"response": prompt["response"], "context": prompt["context"]},
            )

    def on_stop(self):
        for rule_id in self.rules_ids:
            self.client.patch(
                f"/api/v2/tasks/{self.task_id}/rules/{rule_id}",
                json={"enabled": False},
            )
        self.client.delete(f"/api/v2/tasks/{self.task_id}")
