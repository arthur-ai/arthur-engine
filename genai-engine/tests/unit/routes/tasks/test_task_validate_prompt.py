import random
from unittest.mock import patch

import pytest
from arthur_common.models.enums import RuleType

from tests.clients.base_test_client import GenaiEngineTestClientBase
from utils import constants


@pytest.mark.unit_tests
def test_validate_response_which_was_already_validated(
    client: GenaiEngineTestClientBase,
):
    task_name = str(random.random())
    client.create_rule("", rule_type=RuleType.REGEX)
    _, task_response = client.create_task(task_name)
    _, prompt_result = client.create_prompt(
        "cool prompt for this test", task_id=task_response.id
    )
    status_code_success, _ = client.create_response(
        prompt_result.inference_id,
        "cool response for this test",
        task_id=task_response.id,
    )
    assert status_code_success == 200
    status_code_error, response_result = client.create_response(
        prompt_result.inference_id,
        "cool response for this test",
        task_id=task_response.id,
    )
    assert status_code_error == 400
    assert response_result["detail"] == constants.ERROR_CANNOT_VALIDATE_INFERENCE_TWICE


@pytest.mark.unit_tests
def test_response_validation_rejects_inference_from_another_task(client):
    _, owner = client.create_task()
    _, other = client.create_task()
    _, prompt = client.create_prompt("prompt", task_id=owner.id)
    with patch("services.guardrails.validation.capture_judge_context") as capture:
        status, response = client.create_response(
            prompt.inference_id, "response", task_id=other.id
        )
    assert status == 404
    assert response["detail"] == "Inference not found"
    capture.assert_not_called()
