import pytest
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.pii.classifier import BinaryPIIDataClassifier


@pytest.fixture(scope="session")
def classifier():
    """Fixture to provide a PII classifier instance.

    Using session scope to avoid reloading the expensive GLiNER model and tokenizer
    for each test, which significantly improves test execution time.
    """
    return BinaryPIIDataClassifier()


# Alternative fixture for module-scoped tests if needed
@pytest.fixture(scope="module")
def classifier_module():
    """Module-scoped fixture for PII classifier instance."""
    return BinaryPIIDataClassifier()


@pytest.mark.unit_tests
def test_classifier_happy_path(classifier):
    """Test that clean text without PII passes."""
    score_request = ScoreRequest(
        scoring_text="This has no PII data",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.PASS
    assert result.details is None


@pytest.mark.unit_tests
def test_classifier_sad_path(classifier):
    """Test that text with phone number is detected."""
    score_request = ScoreRequest(
        scoring_text="I wanted to be a firefighter when I grew up so I made my phone number 914-714-1729 and thought that would help.",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert "PII found in data: " in result.details.message
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results
    assert result.details.pii_entities is not None
    entity_spans = result.details.pii_entities
    assert entity_spans[0].entity == PIIEntityTypes.PHONE_NUMBER
    assert entity_spans[0].span == "914-714-1729"


@pytest.mark.unit_tests
def test_classifier_ip(classifier):
    """Test that IP addresses are detected."""
    score_request = ScoreRequest(
        scoring_text="My IP Address is 52.124.45.113 because I talked trash on Xbox Live",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert "PII found in data: " in result.details.message
    assert PIIEntityTypes.IP_ADDRESS in result.details.pii_results
    assert result.details.pii_entities is not None
    entity_spans = result.details.pii_entities
    assert entity_spans[0].entity == PIIEntityTypes.IP_ADDRESS
    assert entity_spans[0].span == "52.124.45.113"


@pytest.mark.unit_tests
def test_classifier_multiple_entities(classifier):
    """Test detection of multiple entity types in one text."""
    ip_address = "52.124.45.113"
    phone_number = "914-714-1729"

    score_request = ScoreRequest(
        scoring_text=f"My IP Address is {ip_address} because I talked trash on Xbox Live and my phone number is {phone_number}",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.IP_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results
    assert result.details.pii_entities is not None
    entity_spans = result.details.pii_entities
    ip_address_spans = [span for span in entity_spans if span.span == ip_address]
    phone_number_spans = [span for span in entity_spans if span.span == phone_number]
    assert ip_address_spans[0].entity == PIIEntityTypes.IP_ADDRESS
    assert phone_number_spans[0].entity == PIIEntityTypes.PHONE_NUMBER


@pytest.mark.parametrize(
    "text,expected_entity,expected_span",
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
@pytest.mark.unit_tests
def test_entity_detection(classifier, text, expected_entity, expected_span):
    """Test detection of various PII entity types."""
    score_request = ScoreRequest(
        scoring_text=text,
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert expected_entity in result.details.pii_results
    assert result.details.pii_entities is not None

    entity_spans = [
        span for span in result.details.pii_entities if span.entity == expected_entity
    ]
    assert len(entity_spans) > 0
    assert entity_spans[0].span == expected_span


@pytest.mark.unit_tests
def test_person_name_detection(classifier):
    """Test person name detection."""
    score_request = ScoreRequest(
        scoring_text="Hello, my name is John Smith and I work with Jane Doe.",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert result.details.pii_entities is not None
    person_spans = [
        span
        for span in result.details.pii_entities
        if span.entity == PIIEntityTypes.PERSON
    ]
    assert len(person_spans) >= 2  # Should detect both names
    person_names = [span.span for span in person_spans]
    assert "John Smith" in person_names or "John" in person_names
    assert "Jane Doe" in person_names or "Jane" in person_names


@pytest.mark.unit_tests
def test_empty_text(classifier):
    """Test with empty text."""
    score_request = ScoreRequest(
        scoring_text="",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.PASS
    assert result.details is None


@pytest.mark.unit_tests
def test_very_long_text(classifier):
    """Test with very long text to test chunking."""
    # Reduced from 100 to 20 repetitions to speed up test execution
    long_text = "This is a very long text. " * 20 + "My email is test@example.com."
    score_request = ScoreRequest(
        scoring_text=long_text,
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results


@pytest.mark.unit_tests
def test_pii_config_disable_one_entity(classifier):
    """Test disabling a single entity type."""
    message = "My name is Arthur. The support email is support@arthur.ai"

    # Test without disabled entities
    score_request = ScoreRequest(scoring_text=message, rule_type=RuleType.PII_DATA)
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PERSON in result.details.pii_results

    # Test with PERSON disabled
    disabled_pii_entities = [PIIEntityTypes.PERSON.value]
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        disabled_pii_entities=disabled_pii_entities,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PERSON not in result.details.pii_results


@pytest.mark.unit_tests
def test_pii_config_disable_multiple_entities(classifier):
    """Test disabling multiple entity types."""
    message = (
        "My name is Joe. My email is test@gmail.com. My birthday is August 17, 1995."
    )

    # Test with EMAIL and DATE disabled
    disabled_pii_entities = [
        PIIEntityTypes.EMAIL_ADDRESS.value,
        PIIEntityTypes.DATE_TIME.value,
    ]
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        disabled_pii_entities=disabled_pii_entities,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert PIIEntityTypes.EMAIL_ADDRESS not in result.details.pii_results
    assert PIIEntityTypes.DATE_TIME not in result.details.pii_results


@pytest.mark.unit_tests
def test_pii_config_disable_no_entities(classifier):
    """Test with empty disabled entities list."""
    message = "My name is Joe. You can reach me at support@arthur.ai"

    score_request = ScoreRequest(scoring_text=message, rule_type=RuleType.PII_DATA)
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PERSON in result.details.pii_results


@pytest.mark.unit_tests
def test_pii_config_allow_list(classifier):
    """Test allow list functionality."""
    message = (
        "Welcome to Arthur, our support email is support@arthur.ai. Feel free to call us at 123-456-789 from "
        + "Monday to Friday, 9 am to 5 pm EST. Please consult Jane Doe."
    )

    # Test without allow list
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=[],
    )
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results

    # Test with allow list
    score_request_with_allow_list = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=["Arthur"],
    )

    result_with_allow_list = classifier.score(score_request_with_allow_list)

    assert result_with_allow_list.result == RuleResultEnum.FAIL
    # Person names should be filtered out by allow list
    person_spans = [
        span
        for span in result_with_allow_list.details.pii_entities
        if span.entity == PIIEntityTypes.PERSON
    ]
    assert len(person_spans) == 1
    assert "Jane" in person_spans[0].span


@pytest.mark.unit_tests
def test_pii_config_allow_list_multiple_values(classifier):
    """Test allow list with multiple values."""
    message = "Please email us at support@test.com. Ask for Joe or Wendy."

    # Test without allow list
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=[],
    )
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results

    # Test with allow list
    score_request_with_allow_list = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        allow_list=["support@test.com", "Joe"],
    )

    result_with_allow_list = classifier.score(score_request_with_allow_list)

    assert result_with_allow_list.result == RuleResultEnum.FAIL
    # Should still detect Wendy as person and test.com as URL
    assert PIIEntityTypes.PERSON in result_with_allow_list.details.pii_results

    # Check that Joe and support@test.com are filtered out
    person_spans = [
        span
        for span in result_with_allow_list.details.pii_entities
        if span.entity == PIIEntityTypes.PERSON
    ]
    email_spans = [
        span
        for span in result_with_allow_list.details.pii_entities
        if span.entity == PIIEntityTypes.EMAIL_ADDRESS
    ]

    for span in person_spans:
        assert span.span != "Joe"
    for span in email_spans:
        assert span.span != "support@test.com"


@pytest.mark.unit_tests
def test_pii_config_threshold_specified(classifier):
    """Test confidence threshold functionality."""
    message = "Is it possible to assess my credit score based on my SSN? My SSN is 133-21-6130."

    # Test without threshold
    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.US_SSN in result.details.pii_results

    # Get the confidence of the detected SSN
    ssn_spans = [
        span
        for span in result.details.pii_entities
        if span.entity == PIIEntityTypes.US_SSN
    ]
    assert len(ssn_spans) > 0
    ssn_confidence = ssn_spans[0].confidence

    # Test with threshold higher than the detected confidence
    high_threshold = ssn_confidence + 0.1
    score_request_with_threshold = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        pii_confidence_threshold=high_threshold,
    )

    result_with_threshold = classifier.score(score_request_with_threshold)

    # Should pass since confidence is below threshold
    assert result_with_threshold.result == RuleResultEnum.PASS


@pytest.mark.unit_tests
def test_pii_config_low_threshold(classifier):
    """Test with very low confidence threshold."""
    message = "My SSN is 700-12-4352"

    score_request = ScoreRequest(
        scoring_text=message,
        rule_type=RuleType.PII_DATA,
        pii_confidence_threshold=0.1,
    )

    result = classifier.score(score_request)

    # Should still detect SSN with low threshold
    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.US_SSN in result.details.pii_results


@pytest.mark.unit_tests
def test_special_characters(classifier):
    """Test with special characters and separators."""
    score_request = ScoreRequest(
        scoring_text="Email: test@example.com | Phone: (555) 123-4567 | IP: 192.168.1.1",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results
    assert PIIEntityTypes.IP_ADDRESS in result.details.pii_results


@pytest.mark.unit_tests
def test_unicode_characters(classifier):
    """Test with unicode characters."""
    score_request = ScoreRequest(
        scoring_text="Contact José García at josé.garcía@empresa.com",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results


@pytest.mark.unit_tests
def test_mixed_case(classifier):
    """Test with mixed case text."""
    score_request = ScoreRequest(
        scoring_text="EMAIL: Test@EXAMPLE.com PHONE: 555-123-4567",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results


@pytest.mark.unit_tests
def test_invalid_email_format(classifier):
    """Test with invalid email format mixed with valid."""
    score_request = ScoreRequest(
        scoring_text="This is not an email: test@ and this is: valid@example.com",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    # Should only detect the valid email
    email_spans = [
        span
        for span in result.details.pii_entities
        if span.entity == PIIEntityTypes.EMAIL_ADDRESS
    ]
    assert len(email_spans) == 1
    assert email_spans[0].span == "valid@example.com"


@pytest.mark.unit_tests
def test_overlapping_entities(classifier):
    """Test handling of overlapping entity spans."""
    score_request = ScoreRequest(
        scoring_text="My name is John and my email is john@example.com",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    # Should handle overlapping spans properly
    assert result.details.pii_entities is not None


@pytest.mark.parametrize(
    "text_length,repetitions",
    [
        ("short", 0),  # No repetition for short text
        ("medium", 5),  # 5 repetitions for medium text
        ("long", 15),  # 15 repetitions for long text
    ],
)
@pytest.mark.unit_tests
def test_text_performance(classifier, text_length, repetitions):
    """Test performance with different text lengths."""
    base_text = "This is a text with some PII. "
    if repetitions > 0:
        text = base_text * repetitions + "Email: test@example.com"
    else:
        text = "Email: test@example.com"

    score_request = ScoreRequest(
        scoring_text=text,
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results


@pytest.mark.unit_tests
def test_crypto_address_false_positives(classifier):
    """Test that non-crypto strings are not detected as crypto addresses."""
    score_request = ScoreRequest(
        scoring_text="This is not a crypto address: wallet123 or crypto_key or apple_pay, but this has a name John Doe.",
        rule_type=RuleType.PII_DATA,
    )

    result = classifier.score(score_request)

    # Should not detect crypto addresses in strings containing excluded keywords
    crypto_spans = [
        span
        for span in result.details.pii_entities
        if span.entity == PIIEntityTypes.CRYPTO
    ]

    # If any crypto addresses are detected, they should not contain excluded keywords
    for span in crypto_spans:
        excluded_keywords = ["wallet", "crypto", "key", "apple", "pay"]
        assert not any(keyword in span.span.lower() for keyword in excluded_keywords)


# New tests for validation whitelists
@pytest.mark.unit_tests
def test_phone_number_validation_whitelist(classifier):
    """Test that descriptive phone number text is filtered out by validation whitelist."""
    # These should NOT be detected as phone numbers due to validation whitelist
    test_cases = [
        "Please call my phone number",
        "Enter your phone number here",
        "What is your mobile number?",
        "Call me on my telephone",
        "Dial the customer service hotline",
        "Text message support",
        "My phone is broken",
        "Ring my number",
        "Contact telephone support",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        # Should pass (no PII detected) or not contain phone numbers
        if result.result == RuleResultEnum.FAIL:
            phone_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.PHONE_NUMBER
            ]
            assert (
                len(phone_spans) == 0
            ), f"Phone number incorrectly detected in: {text}"


@pytest.mark.unit_tests
def test_email_validation_whitelist(classifier):
    """Test that descriptive email text is filtered out by validation whitelist."""
    test_cases = [
        "Send me an email",
        "What is your email address?",
        "Check your inbox for mail",
        "Email support for help",
        "Contact us via email",
        "Your mail account",
        "Compose a message",
        "Reply to this email",
        "Forward the message",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        if result.result == RuleResultEnum.FAIL:
            email_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.EMAIL_ADDRESS
            ]
            assert len(email_spans) == 0, f"Email incorrectly detected in: {text}"


@pytest.mark.unit_tests
def test_location_validation_whitelist(classifier):
    """Test that descriptive location text is filtered out by validation whitelist."""
    test_cases = [
        "What is your address?",
        "Enter your location here",
        "Where do you live?",
        "My home address is unknown",
        "Work address required",
        "Mailing address needed",
        "Shipping address information",
        "Current address verification",
        "Where are you located?",
        "This place is nice",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        if result.result == RuleResultEnum.FAIL:
            location_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.LOCATION
            ]
            assert len(location_spans) == 0, f"Location incorrectly detected in: {text}"


@pytest.mark.unit_tests
def test_credit_card_validation_whitelist(classifier):
    """Test that descriptive credit card text is filtered out by validation whitelist."""
    test_cases = [
        "Enter your credit card number",
        "Debit card information required",
        "Payment card details",
        "Visa or Mastercard accepted",
        "Credit card expires soon",
        "Card security code needed",
        "American Express billing",
        "Card account number",
        "Payment information",
        "Your card number",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        if result.result == RuleResultEnum.FAIL:
            cc_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.CREDIT_CARD
            ]
            assert len(cc_spans) == 0, f"Credit card incorrectly detected in: {text}"


@pytest.mark.unit_tests
def test_crypto_validation_whitelist(classifier):
    """Test that descriptive crypto text is filtered out by validation whitelist."""
    test_cases = [
        "Enter your wallet address",
        "Crypto payment information",
        "Bitcoin wallet details",
        "Ethereum key required",
        "Apple Pay transaction",
        "Google Pay account",
        "PayPal payment method",
        "Venmo transfer",
        "Zelle payment",
        "CashApp transaction",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        if result.result == RuleResultEnum.FAIL:
            crypto_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.CRYPTO
            ]
            assert (
                len(crypto_spans) == 0
            ), f"Crypto address incorrectly detected in: {text}"


@pytest.mark.unit_tests
def test_bank_account_validation_whitelist(classifier):
    """Test that descriptive bank account text is filtered out by validation whitelist."""
    test_cases = [
        "Enter your account number",
        "Bank account information",
        "Routing number required",
        "Checking account details",
        "Savings account number",
        "Your bank details",
        "Account number field",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        if result.result == RuleResultEnum.FAIL:
            bank_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.US_BANK_NUMBER
            ]
            assert len(bank_spans) == 0, f"Bank account incorrectly detected in: {text}"


@pytest.mark.unit_tests
def test_person_name_validation_whitelist(classifier):
    """Test that generic person terms are filtered out by validation whitelist."""
    test_cases = [
        "My friend is coming",
        "His wife called",
        "The bartender served drinks",
        "Our doctor is great",
        "Their lawyer helped",
        "My best friend",
        "The nurse was kind",
        "Some doctors agree",
        "Three teachers attended",
        "A good friend of mine",
        "My ex-husband",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        if result.result == RuleResultEnum.FAIL:
            person_spans = [
                span
                for span in result.details.pii_entities
                if span.entity == PIIEntityTypes.PERSON
            ]
            # These should not be detected as person names due to generic terms
            generic_terms = [
                "friend",
                "wife",
                "bartender",
                "doctor",
                "lawyer",
                "nurse",
                "teacher",
                "husband",
            ]
            for span in person_spans:
                for term in generic_terms:
                    assert (
                        term not in span.span.lower()
                    ), f"Generic term '{term}' incorrectly detected as person name in: {text}"


@pytest.mark.unit_tests
def test_possessive_patterns_validation(classifier):
    """Test that possessive patterns are properly filtered out."""
    test_cases = [
        "Call my phone when ready",
        "Send the email to us",
        "Visit our website today",
        "Check your address book",
        "Update his contact info",
        "Their location is unknown",
    ]

    for text in test_cases:
        score_request = ScoreRequest(
            scoring_text=text,
            rule_type=RuleType.PII_DATA,
        )
        result = classifier.score(score_request)

        # These should generally pass or have very limited detections due to possessive patterns
        if result.result == RuleResultEnum.FAIL:
            # Should not contain generic possessive references
            for entity in result.details.pii_entities:
                possessive_words = ["my", "your", "his", "her", "our", "their", "the"]
                span_lower = entity.span.lower()
                assert not any(
                    poss in span_lower for poss in possessive_words
                ), f"Possessive pattern incorrectly detected: {entity.span} in {text}"


@pytest.mark.unit_tests
def test_valid_vs_invalid_entities(classifier):
    """Test that valid entities are detected while invalid descriptive text is not."""
    # Valid entities that should be detected
    valid_text = "Contact John Smith at john.smith@company.com or call my phone number 555-123-4567. Visit https://example.com"

    score_request = ScoreRequest(
        scoring_text=valid_text,
        rule_type=RuleType.PII_DATA,
    )
    result = classifier.score(score_request)

    assert result.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PERSON in result.details.pii_results
    assert PIIEntityTypes.EMAIL_ADDRESS in result.details.pii_results
    assert PIIEntityTypes.PHONE_NUMBER in result.details.pii_results

    # Invalid descriptive text that should NOT be detected
    invalid_text = "Please enter your phone number, email address, and home address in the form below"

    score_request = ScoreRequest(
        scoring_text=invalid_text,
        rule_type=RuleType.PII_DATA,
    )
    result = classifier.score(score_request)

    # Should pass since it's just descriptive text
    assert result.result == RuleResultEnum.PASS


@pytest.mark.parametrize(
    "text, expected_spans",
    [
        ("my email is arthur@gmail.com", ["arthur@gmail.com"]),
        ("contact me at test@hotmail.com today", ["test@hotmail.com"]),
        ("test.user@yahoo.com is my login", ["test.user@yahoo.com"]),
        ("send to a@b.com and cc me at c@d.org", ["a@b.com", "c@d.org"]),
        (
            "try first.last@company.co.uk or alt@company.io",
            ["first.last@company.co.uk", "alt@company.io"],
        ),
        ("foo.bar+spam@sub.domain.com", ["foo.bar+spam@sub.domain.com"]),
        ("Please email ME@Example.COM for info", ["ME@Example.COM"]),
        ("email: <foo@bar.com>;", ["foo@bar.com"]),
        ("something@not_an_email", []),
        ("test@@example.com", []),
        ("@missingusername.com", []),
        ("missingdomain@", []),
        ("this is an email", []),
        ("please check your inbox", []),
        ("send me a reply", []),
        ("gmail.com is just a domain", []),
        ("hotmail.com is popular", []),
        ("visit http://mail.com for info", []),
        ("forward this message to your manager", []),
        ("create a new account today", []),
        ("subscribe to our newsletter", []),
        ("your username will be saved", []),
        ("he wrote me a long letter", []),
        ("I will mail the package tomorrow", []),
        ("their contact address is on file", []),
    ],
)
def test_email_detection(classifier, text, expected_spans):
    disabled_pii_entities = [
        entity.value
        for entity in PIIEntityTypes
        if entity != PIIEntityTypes.EMAIL_ADDRESS
    ]

    score_request = ScoreRequest(
        scoring_text=text,
        rule_type=RuleType.PII_DATA,
        disabled_pii_entities=disabled_pii_entities,
    )

    result = classifier.score(score_request)

    if len(expected_spans) == 0:
        assert result.result == RuleResultEnum.PASS
    else:
        assert result.result == RuleResultEnum.FAIL

        entities = result.details.pii_entities
        spans = []
        for entity in entities:
            assert entity.entity == PIIEntityTypes.EMAIL_ADDRESS
            spans.append(entity.span)

        assert spans == expected_spans
