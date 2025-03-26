import pytest
from pydantic import ValidationError
from schemas.enums import RuleType
from schemas.request_schemas import NewRuleRequest, PasswordResetRequest


@pytest.mark.parametrize(
    "input_data, expected_rule_type",
    [
        (
            {
                "name": "Sensitive Data Rule",
                "type": RuleType.MODEL_SENSITIVE_DATA.value,
                "apply_to_prompt": True,
                "apply_to_response": False,
                "config": {
                    "examples": [
                        {
                            "example": "John has O negative blood group",
                            "result": True,
                        },
                        {
                            "example": "Most og the people have A positive blood group",
                            "result": False,
                        },
                    ],
                },
            },
            RuleType.MODEL_SENSITIVE_DATA.value,
        ),
        (
            {
                "name": "SSN Regex Rule",
                "type": RuleType.REGEX.value,
                "apply_to_prompt": True,
                "apply_to_response": True,
                "config": {
                    "regex_patterns": [
                        "\\d{3}-\\d{2}-\\d{4}",
                        "\\d{5}-\\d{6}-\\d{7}",
                    ],
                },
            },
            RuleType.REGEX.value,
        ),
        (
            {
                "name": "Blocked Keywords Rule",
                "type": RuleType.KEYWORD.value,
                "apply_to_prompt": True,
                "apply_to_response": True,
                "config": {"keywords": ["Blocked_Keyword_1", "Blocked_Keyword_2"]},
            },
            RuleType.KEYWORD.value,
        ),
        (
            {
                "name": "Toxicity Rule",
                "type": RuleType.TOXICITY.value,
                "apply_to_prompt": True,
                "apply_to_response": True,
                "config": {"threshold": 0.5},
            },
            RuleType.TOXICITY.value,
        ),
        (
            {
                "name": "PII Rule",
                "type": RuleType.PII_DATA.value,
                "apply_to_prompt": True,
                "apply_to_response": True,
                "config": {
                    "disabled_pii_entities": [
                        "EMAIL_ADDRESS",
                        "PHONE_NUMBER",
                    ],
                    "confidence_threshold": "0.5",
                    "allow_list": ["arthur.ai", "Arthur"],
                },
            },
            RuleType.PII_DATA.value,
        ),
    ],
)
@pytest.mark.unit_tests
def test_new_rule_set_config_type(input_data, expected_rule_type):
    new_rule_request = NewRuleRequest(**input_data)
    assert new_rule_request.type == expected_rule_type


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "input_password",
    ["zxcasdqwe", "ZXCASDQWE", "123456789", '!@#$%^&*()-+?_=,<>/"', "ZXCasd123", "1"],
)
def test_password_meets_security_fails_validation(input_password):
    with pytest.raises(ValidationError):
        request_body = PasswordResetRequest(password=input_password)


@pytest.mark.unit_tests
def test_password_meets_security():
    request_body = PasswordResetRequest(password="123zxcASD!@#")
    assert request_body.password == "123zxcASD!@#"
