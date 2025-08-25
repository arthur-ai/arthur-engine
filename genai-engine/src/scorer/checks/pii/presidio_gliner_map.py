from typing import List


class PresidioGlinerMapper:
    """Maps between Presidio and GLiNER entity types."""

    # Mapping from Presidio entity types to GLiNER entity types
    PRESIDIO_TO_GLINER = {
        "CREDIT_CARD": "credit card number",
        "CRYPTO": "crypto wallet",
        "DATE_TIME": "date time",
        "EMAIL_ADDRESS": "email address",
        "IBAN_CODE": "iban",
        "IP_ADDRESS": "ip address",
        "NRP": "nationality religion politics",
        "LOCATION": "address",
        "PERSON": "person",
        "PHONE_NUMBER": "phone number",
        "MEDICAL_LICENSE": "medical license number",
        "URL": "url",
        "US_BANK_NUMBER": "bank account number",
        "US_DRIVER_LICENSE": "driver's license number",
        "US_ITIN": "tax identification number",
        "US_PASSPORT": "passport number",
        "US_SSN": "social security number",
    }

    # Reverse mapping from GLiNER to Presidio
    GLINER_TO_PRESIDIO = {v: k for k, v in PRESIDIO_TO_GLINER.items()}

    @classmethod
    def presidio_to_gliner(cls, tag: str) -> str:
        """Convert Presidio entity type to GLiNER entity type."""
        return cls.PRESIDIO_TO_GLINER.get(tag, tag.lower())

    @classmethod
    def gliner_to_presidio(cls, tag: str) -> str:
        """Convert GLiNER entity type to Presidio entity type."""
        return cls.GLINER_TO_PRESIDIO.get(tag.lower(), tag.upper())

    @classmethod
    def map_presidio_tags(cls, tags: List[str]) -> List[str]:
        """Convert a list of Presidio tags to GLiNER tags."""
        return [cls.presidio_to_gliner(tag) for tag in tags]

    @classmethod
    def map_gliner_tags(cls, tags: List[str]) -> List[str]:
        """Convert a list of GLiNER tags to Presidio tags."""
        return [cls.gliner_to_presidio(tag) for tag in tags]
