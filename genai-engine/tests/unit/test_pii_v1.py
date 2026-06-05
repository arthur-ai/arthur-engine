from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType

from schemas.scorer_schemas import ScoreRequest
from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1
from scorer.checks.pii.presidio_gliner_map import PresidioGlinerMapper


@pytest.mark.unit_tests
def test_pii_classifier_v1_happy_path():
    classifier = BinaryPIIDataClassifierV1()

    score_request = ScoreRequest(
        scoring_text="This has no PII data",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.PASS
    assert result.details is None


@pytest.mark.unit_tests
def test_pii_classifier_v1_sad_path():
    classifier = BinaryPIIDataClassifierV1()

    score_request = ScoreRequest(
        scoring_text="I wanted to be a firefighter when I grew up so I made my phone number 914-714-1729 and thought that would help.",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert "PII found in data: " in result.details.message
    assert PIIEntityTypes.PHONE_NUMBER in result.details.message
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results
    assert result.details.pii_entities is not None
    entity_spans = result.details.pii_entities
    assert entity_spans[0].entity == PIIEntityTypes.PHONE_NUMBER
    assert entity_spans[0].span == "914-714-1729"


@pytest.mark.unit_tests
def test_pii_classifier_v1_ip():
    classifier = BinaryPIIDataClassifierV1()

    score_request = ScoreRequest(
        scoring_text="My IP Address is 52.124.45.113 because I talked trash on Xbox Live",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert "PII found in data: " in result.details.message
    assert PIIEntityTypes.IP_ADDRESS in result.details.message
    assert PIIEntityTypes.IP_ADDRESS in result.details.pii_results
    assert result.details.pii_entities is not None
    entity_spans = result.details.pii_entities
    assert entity_spans[0].entity == PIIEntityTypes.IP_ADDRESS
    assert entity_spans[0].span == "52.124.45.113"


@pytest.mark.unit_tests
def test_pii_classifier_v1_multiple_entities():
    classifier = BinaryPIIDataClassifierV1()

    ip_address = "52.124.45.113"
    phone_number = "914-714-1729"

    score_request = ScoreRequest(
        scoring_text=f"My IP Address is {ip_address} because I talked trash on Xbox Live and my phone number is {phone_number}",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert "PII found in data: " in result.details.message
    assert PIIEntityTypes.IP_ADDRESS in result.details.message
    assert PIIEntityTypes.PHONE_NUMBER in result.details.message
    assert PIIEntityTypes.IP_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results
    assert result.details.pii_entities is not None
    entity_spans = result.details.pii_entities
    ip_address = [span for span in entity_spans if span.span == ip_address]
    phone_numbers = [span for span in entity_spans if span.span == phone_number]
    assert ip_address[0].entity == PIIEntityTypes.IP_ADDRESS
    assert phone_numbers[0].entity == PIIEntityTypes.PHONE_NUMBER


@pytest.mark.unit_tests
def test_pii_classifier_v1_config_disable_one_entity():
    classifier = BinaryPIIDataClassifierV1()

    message = "My name is Arthur. The support email is support@arthur.ai"
    # 1 - make sure PII is flagged for PERSON, URL, EMAIL
    score_request = ScoreRequest(scoring_text=message, rule_type=RuleType.PII_DATA)
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.pii_results == [
        PIIEntityTypes.EMAIL_ADDRESS,
        PIIEntityTypes.PERSON,
        PIIEntityTypes.URL,
    ]

    # 2 - disable PERSON and make sure PII is flagged only for URL, EMAIL
    disabled_pii_entities = [PIIEntityTypes.PERSON]
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        disabled_pii_entities=disabled_pii_entities,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.pii_results == [
        PIIEntityTypes.EMAIL_ADDRESS,
        PIIEntityTypes.URL,
    ]


@pytest.mark.unit_tests
def test_pii_v1_config_disable_multiple_entities():
    classifier = BinaryPIIDataClassifierV1()

    message = (
        "My name is Joe. My email is test@gmail.com. My birthday is August 17, 1995."
    )

    # 1 - make sure PII is flagged for PERSON, URL, EMAIL
    score_request = ScoreRequest(scoring_text=message, rule_type=RuleType.PII_DATA)
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.pii_results == [
        PIIEntityTypes.EMAIL_ADDRESS,
        PIIEntityTypes.PERSON,
        PIIEntityTypes.DATE_TIME,
        PIIEntityTypes.URL,
    ]

    # 2 - disable EMAIL + DATE and make sure PII is flagged only for URL, PERSON
    disabled_pii_entities = [PIIEntityTypes.EMAIL_ADDRESS, PIIEntityTypes.DATE_TIME]
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        disabled_pii_entities=disabled_pii_entities,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.pii_results == [PIIEntityTypes.PERSON, PIIEntityTypes.URL]


@pytest.mark.unit_tests
def test_pii_v1_config_disable_no_entities():
    classifier = BinaryPIIDataClassifierV1()

    message = (
        "My name is Joe. My email is test@gmail.com. My birthday is August 17, 1995."
    )

    # 1 - feed empty list which means we disable nothing
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        disabled_pii_entities=[],
    )
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.pii_results == [
        PIIEntityTypes.EMAIL_ADDRESS,
        PIIEntityTypes.PERSON,
        PIIEntityTypes.DATE_TIME,
        PIIEntityTypes.URL,
    ]


def test_pii_v1_config_allow_list():
    classifier = BinaryPIIDataClassifierV1()

    message = (
        "Welcome to Arthur, our support email is support@arthur.ai. Feel free to call us at 123-456-789 from "
        + "Monday to Friday, 9 am to 5 pm EST. Please consult Jane Doe."
    )
    # 1 - feed allow list with empty value 'Arthur' and allow_list of 'Arthur'
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=[],
    )
    score_request_non_pii_allow_list = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=["Arthur", "Jane Doe"],
    )

    result = classifier.score(score_request)
    result_non_pii_allow_list = classifier.score(score_request_non_pii_allow_list)

    # Verify that 'Arthur' is indeed 'PERSON' PII in first result with no exclude list
    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    for entity_span in result.details.pii_entities:
        if entity_span.entity == PIIEntityTypes.PERSON:
            assert entity_span.span in ["Arthur", "Jane Doe"]

    # Verify that 'Arthur' is indeed 'PERSON' PII but not in results since its in our exclude list
    assert result_non_pii_allow_list.result == RuleResultEnum.FAIL
    assert result_non_pii_allow_list.details.pii_results == [
        PIIEntityTypes.EMAIL_ADDRESS,  # support@arthur.ai
        PIIEntityTypes.DATE_TIME,  # Monday to Friday
        PIIEntityTypes.DATE_TIME,  # 9 am to 5 pm EST
        PIIEntityTypes.URL,  # arthur.ai
    ]


def test_pii_v1_config_allow_list_multiple_values():
    classifier = BinaryPIIDataClassifierV1()

    message = "Please email us at support@test.com. Ask for Joe or Wendy."
    # 1 - feed allow list with empty value and allow_list of 'support@test.com', 'Joe'
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=[],
    )
    score_request_non_pii_allow_list = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=["support@test.com", "Joe"],
    )

    result = classifier.score(score_request)
    result_non_pii_allow_list = classifier.score(score_request_non_pii_allow_list)

    # Verify that 'Joe' and 'Wendy' is 'PERSON' PII and support@test.com is 'EMAIL' in first result with no exclude list
    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    for entity_span in result.details.pii_entities:
        if entity_span.entity == PIIEntityTypes.PERSON:
            assert entity_span.span in ["Joe", "Wendy"]
        elif entity_span.entity == PIIEntityTypes.EMAIL_ADDRESS:
            assert entity_span.span in ["support@test.com"]

    # Verify that 'Joe' and 'support@test.com' are not in results

    assert result_non_pii_allow_list.result == RuleResultEnum.FAIL
    assert result_non_pii_allow_list.details.pii_results == [
        PIIEntityTypes.PERSON,  # Wendy
        PIIEntityTypes.URL,  # test.com
    ]

    for entity_span in result_non_pii_allow_list.details.pii_entities:
        if entity_span.entity == PIIEntityTypes.PERSON:
            assert entity_span.span == "Wendy"


@pytest.mark.unit_tests
def test_pii_classifier_v1_drops_name_with_digits():
    classifier = BinaryPIIDataClassifierV1()

    score_request = ScoreRequest(
        scoring_text="The agent User 4 helped me with Order 7423 yesterday.",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    if result.result == RuleResultEnum.FAIL:
        person_spans = [
            span.span
            for span in result.details.pii_entities
            if span.entity == PIIEntityTypes.PERSON
        ]
        assert all(
            not any(ch.isdigit() for ch in span) for span in person_spans
        ), f"PERSON spans containing digits were not filtered: {person_spans}"


@pytest.mark.unit_tests
def test_pii_classifier_v1_keeps_clean_names():
    classifier = BinaryPIIDataClassifierV1()

    score_request = ScoreRequest(
        scoring_text="John Smith called yesterday to confirm.",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results


def test_pii_v1_config_trehsold_specified():
    classifier = BinaryPIIDataClassifierV1()

    message = "Is it possible to assess my credit score based on my SSN? My SSN is 133-21-6130."
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert result.details.pii_results == [
        PIIEntityTypes.US_SSN,  # SSN 123-45-6789
    ]
    test_threshold = 0.0
    for entity_span in result.details.pii_entities:
        if entity_span.entity == PIIEntityTypes.US_SSN:
            test_threshold = entity_span.confidence + 0.01
        else:
            test_threshold = 0.5

    # Run it again, specifying a PII test_pii_threshold of 0.5
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        pii_confidence_threshold=test_threshold,
    )

    result = classifier.score(score_request)

    # No PII should be flagged since our only PII is less than our treshold
    assert result.result == RuleResultEnum.PASS


@pytest.mark.unit_tests
@patch("scorer.checks.pii.classifier_v1.get_gliner_tokenizer")
@patch("scorer.checks.pii.classifier_v1.get_gliner_model")
@patch("scorer.checks.pii.classifier_v1.AnalyzerEngine")
def test_pii_v1_entity_routing(
    mock_analyzer_engine,
    mock_get_gliner,
    mock_get_tokenizer,
):
    """Test that US_PASSPORT only goes through GLiNER and all other entities only go through Presidio"""
    # Setup analyzer mock
    mock_analyzer = MagicMock()
    mock_analyzer.analyze = MagicMock(return_value=[])
    mock_analyzer_engine.return_value = mock_analyzer

    # Setup gliner mock
    mock_gliner_model = MagicMock()
    mock_gliner_model.predict_entities = MagicMock(return_value=[])
    mock_get_gliner.return_value = mock_gliner_model

    # Mock tokenizer with proper encoding structure
    mock_encoding = MagicMock()
    mock_encoding.__getitem__ = lambda self, key: {
        "input_ids": [1, 2, 3, 4, 5],
        "offset_mapping": [(0, 4), (5, 9), (10, 14), (15, 19), (20, 27)],
    }[key]
    mock_encoding.word_ids = MagicMock(return_value=[0, 1, 2, 3, 4])

    mock_tokenizer = MagicMock()
    mock_tokenizer.return_value = mock_encoding
    mock_get_tokenizer.return_value = mock_tokenizer

    classifier = BinaryPIIDataClassifierV1()

    # Verify the mocks are set correctly and we are not using the actual models
    assert classifier.gliner_model is mock_gliner_model
    assert classifier.analyzer is mock_analyzer

    test_text = "Test text for entity routing"
    score_request = ScoreRequest(
        scoring_text=test_text,
        rule_type=RuleType.PII_DATA,
    )

    classifier.score(score_request)

    # Verify Presidio was called with all entities EXCEPT US_PASSPORT
    assert mock_analyzer.analyze.called
    presidio_entities = mock_analyzer.analyze.call_args.kwargs["entities"]

    all_entity_values = PIIEntityTypes.values()
    for entity in all_entity_values:
        if entity == PIIEntityTypes.US_PASSPORT.value:
            assert entity not in presidio_entities
        else:
            assert entity in presidio_entities

    # Verify GLiNER predict_entities was called
    assert mock_gliner_model.predict_entities.called

    gliner_labels = []
    for call_item in mock_gliner_model.predict_entities.call_args_list:
        gliner_labels.extend(call_item.kwargs.get("labels", []))

    passport_gliner = PresidioGlinerMapper.presidio_to_gliner(
        PIIEntityTypes.US_PASSPORT.value,
    )
    assert passport_gliner in gliner_labels
    assert len(set(gliner_labels)) == 1
