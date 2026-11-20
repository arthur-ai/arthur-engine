import random

import pytest
from arthur_common.models.enums import RuleType

from tests.clients.base_test_client import GenaiEngineTestClientBase
from utils import constants


@pytest.mark.unit_tests
def test_validate_response_which_was_already_validated(
    client: GenaiEngineTestClientBase,
):
    task_name = str(random.random())
    _, task_response = client.create_task(task_name)
    client.create_rule("", rule_type=RuleType.REGEX, task_id=task_response.id)
    _, prompt_result = client.create_prompt(
        "cool prompt for this test",
        task_id=task_response.id,
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
