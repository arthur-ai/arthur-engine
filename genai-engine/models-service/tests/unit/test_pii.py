"""PII v2 (Presidio + GLiNER + spaCy) inference tests — needs real models.

Migrated from genai-engine/tests/unit/test_pii.py. Same coverage shape, same
expected behaviors, just calling `inference.pii.classify(PIIRequest)`
directly instead of going through the engine's RuleScorer wrapper.

Marked `real_models` because GLiNER + spaCy + the deberta tokenizer are
required for v2 to function. Fast CI can skip with `-m "not real_models"`.
"""

import pytest

from inference.pii import classify
from schemas import InferenceResult, PIIEntityTypes, PIIRequest

pytestmark = pytest.mark.real_models


def _req(text: str, **kw) -> PIIRequest:
    return PIIRequest(text=text, use_v2=True, **kw)


def _types(result) -> set[PIIEntityTypes]:
    return {e.entity for e in result.entities}


def test_happy_path():
    result = classify(_req("This has no PII data"))
    assert result.result == InferenceResult.PASS
    assert result.entities == []


def test_phone_number():
    text = (
        "I wanted to be a firefighter when I grew up so I made my phone number "
        "914-714-1729 and thought that would help."
    )
    result = classify(_req(text))
    assert result.result == InferenceResult.FAIL
    assert PIIEntityTypes.PHONE_NUMBER in _types(result)
    phones = [e.span for e in result.entities if e.entity == PIIEntityTypes.PHONE_NUMBER]
    assert "914-714-1729" in phones


def test_ip_address():
    result = classify(_req("My IP Address is 52.124.45.113 because I talked trash on Xbox Live"))
    assert result.result == InferenceResult.FAIL
    assert PIIEntityTypes.IP_ADDRESS in _types(result)


def test_multiple_entities():
    ip = "52.124.45.113"
    phone = "914-714-1729"
    result = classify(_req(
        f"My IP Address is {ip} because I talked trash on Xbox Live and my phone number is {phone}",
    ))
    assert result.result == InferenceResult.FAIL
    types = _types(result)
    assert PIIEntityTypes.IP_ADDRESS in types
    assert PIIEntityTypes.PHONE_NUMBER in types


@pytest.mark.parametrize(
    "text,expected,span",
    [
        (
            "Please contact me at john.doe@example.com for more information.",
            PIIEntityTypes.EMAIL_ADDRESS,
            "john.doe@example.com",
        ),
        (
            "My social security number is 700-12-4352, please keep it secret.",
            PIIEntityTypes.US_SSN,
            "700-12-4352",
        ),
        (
            "My credit card number is 4111-1111-1111-1111.",
            PIIEntityTypes.CREDIT_CARD,
            "4111-1111-1111-1111",
        ),
        (
            "Visit our website at https://www.example.com for more details.",
            PIIEntityTypes.URL,
            "https://www.example.com",
        ),
    ],
)
def test_entity_detection(text, expected, span):
    result = classify(_req(text))
    assert result.result == InferenceResult.FAIL
    assert expected in _types(result)
    assert any(e.span == span for e in result.entities if e.entity == expected)


def test_person_name():
    result = classify(_req("Hello, my name is John Smith and I work with Jane Doe."))
    assert result.result == InferenceResult.FAIL
    assert PIIEntityTypes.PERSON in _types(result)
    persons = [e.span for e in result.entities if e.entity == PIIEntityTypes.PERSON]
    assert any("John" in p for p in persons)
    assert any("Jane" in p for p in persons)


def test_empty_text():
    result = classify(_req(""))
    assert result.result == InferenceResult.PASS


def test_disable_entity():
    msg = "My name is Arthur. The support email is support@arthur.ai"

    full = classify(_req(msg))
    assert PIIEntityTypes.PERSON in _types(full)
    assert PIIEntityTypes.EMAIL_ADDRESS in _types(full)

    no_person = classify(_req(msg, disabled_entities=[PIIEntityTypes.PERSON.value]))
    assert PIIEntityTypes.EMAIL_ADDRESS in _types(no_person)
    assert PIIEntityTypes.PERSON not in _types(no_person)


def test_allow_list():
    msg = (
        "Welcome to Arthur, our support email is support@arthur.ai. "
        "Feel free to call us at 123-456-789 from Monday to Friday, "
        "9 am to 5 pm EST. Please consult Jane Doe."
    )
    no_allow = classify(_req(msg, allow_list=[]))
    assert PIIEntityTypes.PERSON in _types(no_allow)

    with_allow = classify(_req(msg, allow_list=["Arthur"]))
    person_spans = [e for e in with_allow.entities if e.entity == PIIEntityTypes.PERSON]
    assert all("Arthur" not in e.span for e in person_spans)
    assert any("Jane" in e.span for e in person_spans)


def test_threshold_filter():
    msg = "Is it possible to assess my credit score based on my SSN? My SSN is 133-21-6130."
    result = classify(_req(msg))
    assert PIIEntityTypes.US_SSN in _types(result)

    ssn_conf = next(e.confidence for e in result.entities if e.entity == PIIEntityTypes.US_SSN)
    higher = classify(_req(msg, confidence_threshold=ssn_conf + 0.1))
    assert all(e.entity != PIIEntityTypes.US_SSN for e in higher.entities)


@pytest.mark.parametrize(
    "text",
    [
        "The meeting is scheduled for October 15th at 2pm.",
        "The conference starts on January 20th, 2025 in Chicago.",
        "Let's meet on Thursday to discuss the proposal.",
        "The invoice date is 01/15/2025 as shown on the document.",
        "I was born on 03/14/1990 in Seattle.",
        "The financial report for Q3 2024 shows strong growth.",
        "Our office will be closed on Christmas day.",
    ],
)
def test_datetime_detected(text):
    result = classify(_req(text))
    assert result.result == InferenceResult.FAIL
    assert PIIEntityTypes.DATE_TIME in _types(result)


@pytest.mark.parametrize(
    "text",
    [
        "I'll get back to you next week with an update.",
        "We talked about this recently during our team meeting.",
        "Give me a minute to think about your proposal.",
        "We have daily standup meetings with the team.",
    ],
)
def test_datetime_not_detected_for_relative_phrases(text):
    result = classify(_req(text))
    if result.result == InferenceResult.FAIL:
        assert PIIEntityTypes.DATE_TIME not in _types(result)


@pytest.mark.parametrize(
    "text",
    [
        "Please call my phone number",
        "Enter your phone number here",
        "Dial the customer service hotline",
    ],
)
def test_phone_validation_whitelist(text):
    result = classify(_req(text))
    if result.result == InferenceResult.FAIL:
        phones = [e for e in result.entities if e.entity == PIIEntityTypes.PHONE_NUMBER]
        assert phones == [], f"Phone wrongly detected in: {text}"


@pytest.mark.parametrize(
    "text",
    [
        "Send me an email",
        "What is your email address?",
        "Forward the message",
    ],
)
def test_email_validation_whitelist(text):
    result = classify(_req(text))
    if result.result == InferenceResult.FAIL:
        emails = [e for e in result.entities if e.entity == PIIEntityTypes.EMAIL_ADDRESS]
        assert emails == [], f"Email wrongly detected in: {text}"
