from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from arthur_common.models.enums import RuleType

from db_models import DatabaseOrganization, DatabaseTask
from services.guardrails.judge_executor import JudgeContext
from tests.clients.base_test_client import override_get_db_session
from tests.clients.unit_test_client import get_genai_engine_test_client
from utils.constants import DEFAULT_ORG_ID

pytestmark = pytest.mark.unit_tests


def test_guardrail_route_matrix_attribution_and_response_contract(
    without_leftover_default_rules,
):
    client = get_genai_engine_test_client()
    org_id = uuid4()
    status, rule = client.create_rule("global sensitive", RuleType.MODEL_SENSITIVE_DATA)
    assert status == 200
    status, hallucination_rule = client.create_rule(
        "global hallucination", RuleType.MODEL_HALLUCINATION_V2
    )
    assert status == 200
    status, task = client.create_task()
    assert status == 200
    with override_get_db_session() as session:
        session.add(
            DatabaseOrganization(
                id=org_id, name=f"guardrail-{org_id}", created_at=datetime.now()
            )
        )
        session.query(DatabaseTask).filter(DatabaseTask.id == task.id).update(
            {"org_id": org_id}
        )
        session.commit()
    try:
        with patch(
            "services.guardrails.validation.capture_judge_context",
            side_effect=lambda owner: JudgeContext(
                org_id=owner, model="selected-judge"
            ),
        ) as capture:
            status, taskless = client.create_prompt("prompt")
            assert status == 200
            capture.assert_called_once_with(DEFAULT_ORG_ID)
            capture.reset_mock()
            status, _ = client.create_response(
                taskless.inference_id,
                "response",
                context="context",
                model_name="model-under-evaluation",
            )
            assert status == 200
            capture.assert_called_once_with(DEFAULT_ORG_ID)
            capture.reset_mock()
            status, prompt = client.create_prompt("prompt", task_id=task.id)
            assert status == 200
            capture.assert_called_once_with(org_id)
            capture.reset_mock()
            status, response = client.create_response(
                prompt.inference_id,
                "response",
                task_id=task.id,
                context="context",
                model_name="model-under-evaluation",
            )
            assert status == 200
            assert response.model_name == "model-under-evaluation"
            capture.assert_called_once_with(org_id)
            capture.reset_mock()
            status, prompt = client.create_prompt("another prompt", task_id=task.id)
            assert status == 200
            capture.reset_mock()
            status, response = client.create_response(
                prompt.inference_id,
                "response",
                context="context",
                model_name="model-under-evaluation",
            )
            assert status == 200
            assert response.model_name == "model-under-evaluation"
            capture.assert_called_once_with(org_id)
            capture.reset_mock()
            status, _ = client.builtin_validate(
                prompt="prompt",
                checks=[
                    {
                        "name": "inline sensitive",
                        "type": RuleType.MODEL_SENSITIVE_DATA.value,
                        "apply_to_prompt": True,
                        "apply_to_response": False,
                        "config": {
                            "examples": [{"example": "private", "result": True}]
                        },
                    }
                ],
            )
            assert status == 200
            capture.assert_called_once_with(DEFAULT_ORG_ID)
    finally:
        client.delete_task(task.id)
        client.delete_default_rule(rule.id)
        client.delete_default_rule(hallucination_rule.id)
