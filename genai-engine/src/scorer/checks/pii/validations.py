"""
PII Entity Validation Functions.

This module provides validation functions for different PII entity types to filter out
descriptive text that shouldn't be considered actual PII data.

The validation strategy follows these principles:
1. Whitelist Filtering: Remove text containing descriptive keywords (e.g., "enter your phone number")
2. Possessive Pattern Detection: Filter possessive constructs (e.g., "my email", "his address")
3. Format Validation: Ensure minimum structural requirements are met
4. Context Analysis: Check for linguistic patterns that indicate non-PII text

Each validator follows a consistent pipeline:
- Input sanitization and basic checks
- Descriptive keyword filtering
- Possessive pattern detection
- Format/structure validation
- Entity-specific validation rules
"""

import ipaddress
import os
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass
from typing import Callable, Optional, Set

# Global cache for generic name exclusions
_generic_name_exclusions: Set[str] | None = None


def get_generic_name_exclusions() -> Set[str]:
    """Load generic name exclusions from text file."""
    global _generic_name_exclusions
    if _generic_name_exclusions is None:
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        exclusions_file = os.path.join(current_dir, "generic_name_exclusions.txt")
        _generic_name_exclusions = set()

        try:
            with open(exclusions_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines
                    if line:
                        _generic_name_exclusions.add(line.lower())
        except FileNotFoundError:
            # Fallback to empty set if file not found
            _generic_name_exclusions = set()

    return _generic_name_exclusions


# ========================================
# VALIDATION CONFIGURATION FRAMEWORK
# ========================================


@dataclass
class ValidationConfig:
    """Configuration for entity validation pipelines."""

    # Core filtering keywords
    descriptive_keywords: Set[str]
    entity_keywords: Set[str]

    # Optional filtering parameters
    use_descriptive_keywords_fallback: bool = True

    # Format requirements
    min_length: int = 5
    required_chars: Optional[str] = None
    min_digits: int = 0

    # Optional pattern filters
    action_verbs: Optional[Set[str]] = None
    question_words: Optional[Set[str]] = None

    # Custom validation function
    custom_validator: Optional[Callable[[str], bool]] = None

    # Pre-processing function (for cleaning/normalization)
    preprocessor: Optional[Callable[[str], str]] = None


# ========================================
# CORE VALIDATION PIPELINE
# ========================================


def validate_pii_entity(text: str, config: ValidationConfig) -> bool:
    """
    Generic validation pipeline for PII entities.

    This function implements the standard validation pipeline that all entity
    validators follow, reducing code duplication while maintaining flexibility.

    Args:
        text: The text to validate
        config: ValidationConfig specifying the validation rules

    Returns:
        True if the text appears to be valid PII of the specified type
    """
    # Step 1: Input sanitization
    text = text.strip()
    if not text:
        return False

    # Step 2: Optional preprocessing
    if config.preprocessor:
        text = config.preprocessor(text)

    # Step 3: Descriptive keyword filtering
    if contains_descriptive_keywords(
        text,
        config.descriptive_keywords,
        config.use_descriptive_keywords_fallback,
    ):
        return False

    # Step 4: Possessive pattern detection
    if contains_possessive_patterns(text, config.entity_keywords):
        return False

    # Step 5: Format requirements validation
    if not meets_minimum_format_requirements(
        text,
        config.min_length,
        config.required_chars,
        config.min_digits,
    ):
        return False

    # Step 6: Optional action-directed pattern filtering
    if config.action_verbs and contains_action_directed_patterns(
        text,
        config.action_verbs,
    ):
        return False

    # Step 7: Optional question pattern filtering
    if config.question_words and contains_question_patterns(
        text,
        config.question_words,
    ):
        return False

    # Step 8: Custom validation (entity-specific logic)
    if config.custom_validator and not config.custom_validator(text):
        return False

    return True


# ========================================
# CORE VALIDATION HELPER FUNCTIONS
# ========================================


def contains_descriptive_keywords(
    text: str,
    descriptive_keywords: Set[str],
    use_fallback: bool = True,
) -> bool:
    """Check if text contains descriptive keywords that indicate it's not actual PII."""
    lowered = text.lower()

    for keyword in descriptive_keywords:
        if " " in keyword:
            # Multi-word keywords should match exactly
            if keyword in lowered:
                return True
        else:
            # Single-word keywords should match as whole words when possible
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                return True
            elif use_fallback and keyword in lowered:
                return True

    return False


def contains_possessive_patterns(text: str, entity_keywords: Set[str]) -> bool:
    """Check if text contains possessive patterns like 'my phone' or 'his address'."""
    lowered = text.lower()
    possessive_indicators = {
        "my",
        "your",
        "his",
        "her",
        "their",
        "our",
        "the",
        "a",
        "an",
    }

    for possessive in possessive_indicators:
        for entity_word in entity_keywords:
            pattern = rf"\b{re.escape(possessive)}\s+{re.escape(entity_word)}\b"
            if re.search(pattern, lowered):
                return True

    return False


def meets_minimum_format_requirements(
    text: str,
    min_length: int = 5,
    required_chars: Optional[str] = None,
    min_digits: int = 0,
) -> bool:
    """Check if text meets minimum format requirements for being valid PII."""
    if len(text) < min_length:
        return False

    if required_chars:
        for char in required_chars:
            if char not in text:
                return False

    if min_digits > 0:
        digit_count = sum(1 for c in text if c.isdigit())
        if digit_count < min_digits:
            return False

    return True


def contains_action_directed_patterns(text: str, action_verbs: Set[str]) -> bool:
    """Detect action-directed patterns like 'call me' or 'text us'."""
    lowered = text.lower()
    personal_pronouns = {"me", "us", "him", "her", "them"}

    for verb in action_verbs:
        for pronoun in personal_pronouns:
            if re.search(rf"\b{re.escape(verb)}\s+{re.escape(pronoun)}\b", lowered):
                return True

    return False


def contains_question_patterns(text: str, question_words: Set[str]) -> bool:
    """Detect question patterns like 'where do you live?' or 'what is your address?'."""
    lowered = text.lower()

    for question_word in question_words:
        if re.search(
            rf"\b{re.escape(question_word)}\s+(do|did|are|is|was|will)\b",
            lowered,
        ):
            return True

    return False


# ========================================
# ENTITY-SPECIFIC CUSTOM VALIDATORS
# ========================================


def _validate_email_structure(text: str) -> bool:
    """Validate the structural format of an email address with unicode support."""
    if text.count("@") != 1:
        return False

    local_part, domain_part = text.split("@")

    if len(local_part) == 0 or len(local_part) > 64:
        return False

    if len(domain_part) == 0 or len(domain_part) > 255:
        return False

    if "." not in domain_part:
        return False

    domain_parts = domain_part.split(".")
    if len(domain_parts) < 2:
        return False

    tld = domain_parts[-1]
    if len(tld) < 2 or not tld.isalpha():
        return False

    return True


def _validate_credit_card_format(text: str) -> bool:
    """Validate credit card number format."""
    # Remove spaces and hyphens
    cleaned = re.sub(r"[\s\-]", "", text)

    # Must be all digits with reasonable length
    return cleaned.isdigit() and 13 <= len(cleaned) <= 19


def _validate_crypto_format(text: str) -> bool:
    """Validate crypto wallet address format."""
    # No spaces, alphanumeric only, minimum length
    return bool(
        " " not in text
        and re.fullmatch(r"[a-zA-Z0-9]+", text)
        and len(re.sub(r"[^\w\d]", "", text)) >= 25,
    )


def _validate_bank_account_format(text: str) -> bool:
    """Validate bank account number format."""
    cleaned = text.replace(" ", "").replace("-", "")
    return bool(re.fullmatch(r"\d{8,17}", cleaned))


def _validate_url_format(value: str) -> bool:
    """Validate URL format with unicode support."""
    if is_ip(value):
        return False

    try:
        # Add scheme if missing
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
            if "." in value and not value.startswith(".") and not value.endswith("."):
                value = "http://" + value
            else:
                return False

        result = urllib.parse.urlparse(value)

        if not result.scheme or not result.netloc:
            return False

        valid_schemes = {
            "http",
            "https",
            "ftp",
            "ftps",
            "sftp",
            "ws",
            "wss",
            "file",
            "mailto",
            "tel",
        }
        if result.scheme.lower() not in valid_schemes:
            return False

        host = result.netloc.split(":")[0]

        if is_ip(host):
            return True

        # Domain validation
        if "." not in host or len(host) < 3:
            return False

        if re.match(r"^[a-zA-Z0-9.\-_]+$", host, re.ASCII):
            return True

        # Unicode domain support
        try:
            host.encode("idna")
            return True
        except (UnicodeError, UnicodeDecodeError):
            return False

    except (ValueError, AttributeError):
        return False


def _validate_location_keywords(text: str) -> bool:
    """Check if text is just generic location keywords."""
    lowered = text.lower()
    location_keywords = {
        "street",
        "road",
        "avenue",
        "drive",
        "lane",
        "court",
        "place",
        "way",
        "boulevard",
        "circle",
        "square",
        "plaza",
        "terrace",
        "trail",
        "park",
        "city",
        "town",
        "state",
        "country",
        "zip",
        "postal",
        "code",
    }

    tokens = lowered.split()
    return not (
        len(tokens) <= 2 and all(token in location_keywords for token in tokens)
    )


# ========================================
# ENTITY VALIDATION CONFIGURATIONS
# ========================================


def get_validation_configs() -> dict[str, ValidationConfig]:
    """Define validation configurations for all entity types."""
    return {
        "phone": ValidationConfig(
            descriptive_keywords={
                "phone",
                "number",
                "call",
                "text",
                "message",
                "mobile",
                "cellular",
                "landline",
                "office",
                "home",
                "work",
                "fax",
                "toll-free",
                "voip",
                "contact",
                "dial",
                "ring",
                "telephone",
                "tel",
                "reach",
                "extension",
                "ext",
                "hotline",
                "helpline",
                "customer service",
                "support",
            },
            entity_keywords={"phone", "number", "tel", "telephone", "mobile", "cell"},
            min_length=7,
            min_digits=7,
            action_verbs={"call", "text", "dial"},
        ),
        "email": ValidationConfig(
            descriptive_keywords={
                "email",
                "e-mail",
                "mail",
                "address",
                "contact",
                "send",
                "message",
                "inbox",
                "outbox",
                "compose",
                "reply",
                "forward",
                "account",
                "username",
                "login",
                "signup",
                "register",
                "subscribe",
            },
            entity_keywords={"email", "e-mail", "mail", "account"},
            min_length=5,
            required_chars="@",
            action_verbs={"send", "contact", "reach"},
            custom_validator=_validate_email_structure,
            use_descriptive_keywords_fallback=False,
        ),
        "location": ValidationConfig(
            descriptive_keywords={
                "address",
                "location",
                "place",
                "where",
                "here",
                "there",
                "somewhere",
                "anywhere",
                "everywhere",
                "nowhere",
                "home address",
                "work address",
                "mailing address",
                "shipping address",
                "billing address",
                "physical address",
                "street address",
                "residential address",
                "business address",
                "office address",
                "current address",
                "permanent address",
                "temporary address",
                "forwarding address",
                "postal address",
                "email address",
                "web address",
                "website address",
                "url address",
            },
            entity_keywords={"address", "location", "place", "home", "work", "office"},
            min_length=5,
            question_words={"where"},
            custom_validator=_validate_location_keywords,
        ),
        "credit_card": ValidationConfig(
            descriptive_keywords={
                "credit",
                "card",
                "number",
                "debit",
                "payment",
                "visa",
                "mastercard",
                "american express",
                "amex",
                "discover",
                "account",
                "billing",
                "expires",
                "expiry",
                "expiration",
                "cvv",
                "cvc",
                "security",
                "code",
            },
            entity_keywords={"card", "credit", "debit", "payment", "account", "number"},
            min_length=13,
            custom_validator=_validate_credit_card_format,
        ),
        "crypto": ValidationConfig(
            descriptive_keywords={
                "wallet",
                "address",
                "crypto",
                "key",
                "bitcoin",
                "ethereum",
                "payment",
                "apple",
                "google",
                "pay",
                "paypal",
                "venmo",
                "zelle",
                "cashapp",
            },
            entity_keywords={"wallet", "address", "crypto", "key"},
            min_length=25,
            custom_validator=_validate_crypto_format,
        ),
        "bank_account": ValidationConfig(
            descriptive_keywords={
                "account",
                "bank",
                "number",
                "routing",
                "checking",
                "savings",
            },
            entity_keywords={"account", "bank", "number"},
            min_length=8,
            min_digits=8,
            preprocessor=lambda x: x.replace(" ", "").replace("-", ""),
            custom_validator=_validate_bank_account_format,
        ),
        "url": ValidationConfig(
            descriptive_keywords=set(),  # URLs don't typically have descriptive keywords that interfere
            entity_keywords=set(),  # URLs don't have possessive patterns
            min_length=3,
            custom_validator=_validate_url_format,
        ),
    }


# ========================================
# SPECIALIZED NAME VALIDATION
# ========================================

# [Name validation functions remain complex due to linguistic pattern matching]
# These are kept separate as they require specialized pattern detection


def get_linguistic_pattern_categories() -> dict[str, Set[str]]:
    """Define linguistic pattern categories for name validation."""
    return {
        "possessive_pronouns": {"my", "your", "his", "her", "its", "our", "their"},
        "determiners": {"the", "a", "an", "this", "that", "these", "those"},
        "quantifiers": {
            "some",
            "many",
            "few",
            "several",
            "all",
            "most",
            "any",
            "every",
            "each",
            "both",
            "either",
            "neither",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "twenty",
            "thirty",
            "forty",
            "fifty",
            "hundred",
            "thousand",
        },
        "descriptive_adjectives": {
            "best",
            "good",
            "old",
            "new",
            "young",
            "little",
            "big",
            "dear",
            "beloved",
            "former",
            "current",
            "ex",
            "late",
            "eldest",
            "oldest",
            "youngest",
            "middle",
            "step",
            "half",
            "foster",
            "adopted",
            "biological",
            "close",
            "distant",
        },
        "possessive_indicators": {"mine", "yours", "hers", "ours", "theirs"},
        "non_name_qualifiers": {
            "some",
            "any",
            "every",
            "each",
            "all",
            "many",
            "few",
            "several",
        },
        "non_name_endings": {
            "person",
            "individual",
            "people",
            "individuals",
            "someone",
            "somebody",
            "anyone",
            "anybody",
        },
        "non_name_singles": {
            "someone",
            "somebody",
            "anyone",
            "anybody",
            "everyone",
            "everybody",
            "nobody",
            "person",
            "individual",
        },
    }


def contains_pronoun_generic_patterns(text: str, generic_exclusions: Set[str]) -> bool:
    """Check if text contains pronoun + generic term patterns that should be excluded."""
    tokens = text.lower().split()
    if len(tokens) < 2:
        return False

    patterns = get_linguistic_pattern_categories()

    # Apply pattern detection strategies
    return any(
        [
            _detect_possessive_generic_pattern(tokens, patterns, generic_exclusions),
            _detect_determiner_generic_pattern(tokens, patterns, generic_exclusions),
            _detect_quantifier_generic_pattern(tokens, patterns, generic_exclusions),
            _detect_of_possessive_pattern(tokens, patterns, generic_exclusions),
            _detect_compound_generic_pattern(tokens, generic_exclusions),
            _detect_generic_dominance_pattern(tokens, patterns, generic_exclusions),
        ],
    )


def _detect_possessive_generic_pattern(
    tokens: list[str],
    patterns: dict[str, Set[str]],
    generic_exclusions: Set[str],
) -> bool:
    """Detect possessive pronoun + [adjective] + generic term patterns."""
    if tokens[0] not in patterns["possessive_pronouns"]:
        return False
    remaining = tokens[1:]
    if all(t in generic_exclusions for t in remaining):
        return True
    if len(remaining) >= 2 and remaining[0] in patterns["descriptive_adjectives"]:
        return all(t in generic_exclusions for t in remaining[1:])
    return False


def _detect_determiner_generic_pattern(
    tokens: list[str],
    patterns: dict[str, Set[str]],
    generic_exclusions: Set[str],
) -> bool:
    """Detect determiner + [adjective] + generic term patterns."""
    if tokens[0] not in patterns["determiners"]:
        return False
    remaining = tokens[1:]
    if all(t in generic_exclusions for t in remaining):
        return True
    if len(remaining) >= 2 and remaining[0] in patterns["descriptive_adjectives"]:
        if len(remaining) >= 4 and remaining[2] == "of":
            return (
                remaining[1] in generic_exclusions
                and remaining[3] in patterns["possessive_indicators"]
            )
        return all(t in generic_exclusions for t in remaining[1:])
    if len(remaining) >= 3 and remaining[1] == "of":
        return (
            remaining[0] in generic_exclusions
            and remaining[2] in patterns["possessive_indicators"]
        )
    return False


def _detect_quantifier_generic_pattern(
    tokens: list[str],
    patterns: dict[str, Set[str]],
    generic_exclusions: Set[str],
) -> bool:
    """Detect quantifier + [adjective] + generic term patterns."""
    if tokens[0] not in patterns["quantifiers"]:
        return False
    remaining = tokens[1:]
    if all(t in generic_exclusions for t in remaining):
        return True
    if len(remaining) >= 2 and remaining[0] in patterns["descriptive_adjectives"]:
        return all(t in generic_exclusions for t in remaining[1:])
    return False


def _detect_of_possessive_pattern(
    tokens: list[str],
    patterns: dict[str, Set[str]],
    generic_exclusions: Set[str],
) -> bool:
    """Detect generic term + 'of' + possessive patterns."""
    if len(tokens) < 3 or tokens[1] != "of":
        return False
    return tokens[0] in generic_exclusions and (
        tokens[2] in patterns["possessive_pronouns"]
        or tokens[2] in patterns["possessive_indicators"]
    )


def _detect_compound_generic_pattern(
    tokens: list[str],
    generic_exclusions: Set[str],
) -> bool:
    """Detect compound generic term patterns."""
    return len(tokens) == 2 and all(t in generic_exclusions for t in tokens)


def _detect_generic_dominance_pattern(
    tokens: list[str],
    patterns: dict[str, Set[str]],
    generic_exclusions: Set[str],
) -> bool:
    """Detect patterns where generic terms dominate the phrase."""
    generic_count = sum(1 for t in tokens if t in generic_exclusions)
    non_generic_count = len(tokens) - generic_count

    if generic_count > 0 and non_generic_count <= 1 and non_generic_count == 1:
        non_generic_token = next(t for t in tokens if t not in generic_exclusions)
        linguistic_markers = (
            patterns["determiners"]
            | patterns["possessive_pronouns"]
            | patterns["quantifiers"]
            | patterns["descriptive_adjectives"]
            | patterns["possessive_indicators"]
            | {"of"}
        )
        return non_generic_token in linguistic_markers
    return False


# ========================================
# PUBLIC ENTITY VALIDATION FUNCTIONS
# ========================================


def is_phone_number(text: str) -> bool:
    """Validate that a string is an actual phone number, not descriptive text."""
    return validate_pii_entity(text, get_validation_configs()["phone"])


def is_email_address(text: str) -> bool:
    """Validate that a string is an actual email address, not descriptive text."""
    return validate_pii_entity(text, get_validation_configs()["email"])


def is_location(text: str) -> bool:
    """Validate that a string is an actual location/address, not descriptive text."""
    return validate_pii_entity(text, get_validation_configs()["location"])


def is_credit_card(text: str) -> bool:
    """Validate that a string is an actual credit card number, not descriptive text."""
    return validate_pii_entity(text, get_validation_configs()["credit_card"])


def is_crypto(text: str) -> bool:
    """Validate that a string is an actual crypto wallet address, not descriptive text."""
    return validate_pii_entity(text, get_validation_configs()["crypto"])


def is_bank_account_number(text: str) -> bool:
    """Validate that a string is an actual bank account number, not descriptive text."""
    return validate_pii_entity(text, get_validation_configs()["bank_account"])


def is_url(value: str) -> bool:
    """Validate that a string is a valid URL."""
    if not value or not value.strip():
        return False
    return validate_pii_entity(value, get_validation_configs()["url"])


def is_name(text: str) -> bool:
    """Validate that text represents an actual proper name, not generic terms."""
    text = text.strip()
    if not text:
        return False

    # Preserve unicode characters with conservative normalization
    text = unicodedata.normalize("NFC", text)

    lowered = text.lower()
    generic_exclusions = get_generic_name_exclusions()

    # Filter out direct generic term matches
    if lowered in generic_exclusions:
        return False

    # Apply sophisticated pattern matching for generic constructs
    if contains_pronoun_generic_patterns(text, generic_exclusions):
        return False

    # Filter out phrases where all parts are generic terms
    tokens = lowered.split()

    all_generic = True
    all_contain_digits = True

    for token in tokens:
        if not all_generic and not all_contain_digits:
            break

        if token not in generic_exclusions:
            all_generic = False

        if not any(c.isdigit() for c in token):
            all_contain_digits = False

    if all_generic or all_contain_digits:
        return False

    # Apply additional name-specific validations
    patterns = get_linguistic_pattern_categories()

    # Reject very short single tokens
    if len(tokens) == 1 and len(text) <= 2:
        return False

    # Filter out multi-word patterns with non-name qualifiers or endings
    if len(tokens) >= 2:
        if (
            tokens[0] in patterns["non_name_qualifiers"]
            or tokens[-1] in patterns["non_name_endings"]
        ):
            return False

    # Filter out problematic single-word cases
    if len(tokens) == 1:
        if (len(text) == 1 and not text.isupper()) or lowered in patterns[
            "non_name_singles"
        ]:
            return False

    return True


def is_ssn(value: str) -> bool:
    """Validate Social Security Number format."""
    return bool(re.fullmatch(r"\d{3}-\d{2}-\d{4}|\d{9}", value))


def is_ip(value: str) -> bool:
    """Validate IP address format (IPv4 or IPv6)."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
