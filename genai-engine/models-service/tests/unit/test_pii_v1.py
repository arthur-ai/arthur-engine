"""PII v1 (Presidio-only) inference tests — no torch needed.

Migrated from genai-engine/tests/unit/test_pii_v1.py. The only API change is
calling `inference.pii.classify(PIIRequest)` instead of the engine's
`BinaryPIIDataClassifierV1().score(ScoreRequest)`.
"""

import pytest

from inference.pii import classify
from schemas import InferenceResult, PIIEntityTypes, PIIRequest


def _req(text: str, **kw) -> PIIRequest:
    return PIIRequest(text=text, use_v2=False, **kw)


def _entity_types(result) -> list[PIIEntityTypes]:
    return [e.entity for e in result.entities]


@pytest.mark.unit_tests
def test_happy_path():
    result = classify(_req("This has no PII data"))
    assert result.result == InferenceResult.PASS
    assert result.entities == []


@pytest.mark.unit_tests
def test_phone_number_detected():
    text = (
        "I wanted to be a firefighter when I grew up so I made my phone number "
        "914-714-1729 and thought that would help."
    )
    result = classify(_req(text))
    assert result.result == InferenceResult.FAIL
    assert PIIEntityTypes.PHONE_NUMBER in _entity_types(result)
    assert any(e.span == "914-714-1729" for e in result.entities)


@pytest.mark.unit_tests
def test_ip_address_detected():
    result = classify(_req("My IP Address is 52.124.45.113 because I talked trash on Xbox Live"))
    assert result.result == InferenceResult.FAIL
    assert PIIEntityTypes.IP_ADDRESS in _entity_types(result)
    assert any(e.span == "52.124.45.113" for e in result.entities)


@pytest.mark.unit_tests
def test_multiple_entities():
    ip = "52.124.45.113"
    phone = "914-714-1729"
    result = classify(_req(
        f"My IP Address is {ip} because I talked trash on Xbox Live and my phone number is {phone}",
    ))
    assert result.result == InferenceResult.FAIL
    types = _entity_types(result)
    assert PIIEntityTypes.IP_ADDRESS in types
    assert PIIEntityTypes.PHONE_NUMBER in types


@pytest.mark.unit_tests
def test_disable_one_entity():
    msg = "My name is Arthur. The support email is support@arthur.ai"

    result = classify(_req(msg))
    assert result.result == InferenceResult.FAIL
    types = _entity_types(result)
    assert PIIEntityTypes.EMAIL_ADDRESS in types
    assert PIIEntityTypes.PERSON in types

    result = classify(_req(msg, disabled_entities=[PIIEntityTypes.PERSON.value]))
    assert result.result == InferenceResult.FAIL
    types = _entity_types(result)
    assert PIIEntityTypes.EMAIL_ADDRESS in types
    assert PIIEntityTypes.PERSON not in types


@pytest.mark.unit_tests
def test_disable_multiple_entities():
    msg = "My name is Joe. My email is test@gmail.com. My birthday is August 17, 1995."
    result = classify(_req(
        msg,
        disabled_entities=[
            PIIEntityTypes.EMAIL_ADDRESS.value,
            PIIEntityTypes.DATE_TIME.value,
        ],
    ))
    assert result.result == InferenceResult.FAIL
    types = _entity_types(result)
    assert PIIEntityTypes.PERSON in types
    assert PIIEntityTypes.EMAIL_ADDRESS not in types
    assert PIIEntityTypes.DATE_TIME not in types


@pytest.mark.unit_tests
def test_allow_list():
    msg = (
        "Welcome to Arthur, our support email is support@arthur.ai. "
        "Feel free to call us at 123-456-789 from "
        "Monday to Friday, 9 am to 5 pm EST. Please consult Jane Doe."
    )
    no_allow = classify(_req(msg, allow_list=[]))
    assert no_allow.result == InferenceResult.FAIL
    assert PIIEntityTypes.PERSON in _entity_types(no_allow)

    with_allow = classify(_req(msg, allow_list=["Arthur"]))
    assert with_allow.result == InferenceResult.FAIL
    person_spans = [e for e in with_allow.entities if e.entity == PIIEntityTypes.PERSON]
    # Arthur should be filtered, Jane Doe should remain.
    assert all("Arthur" not in e.span for e in person_spans)
    assert any("Jane" in e.span for e in person_spans)


@pytest.mark.unit_tests
def test_threshold_filter():
    msg = "Is it possible to assess my credit score based on my SSN? My SSN is 133-21-6130."
    result = classify(_req(msg))
    assert result.result == InferenceResult.FAIL

    ssn_spans = [e for e in result.entities if e.entity == PIIEntityTypes.US_SSN]
    assert len(ssn_spans) > 0
    high_threshold = ssn_spans[0].confidence + 0.1

    filtered = classify(_req(msg, confidence_threshold=high_threshold))
    # SSN was the only PII; with a higher threshold it should drop out.
    assert all(e.entity != PIIEntityTypes.US_SSN for e in filtered.entities)
