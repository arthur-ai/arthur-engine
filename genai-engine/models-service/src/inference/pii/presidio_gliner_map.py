"""Presidio ↔ GLiNER entity-type mapping.

Migrated verbatim from genai-engine/src/scorer/checks/pii/presidio_gliner_map.py.

Presidio uses upper-snake-case entity tags ("CREDIT_CARD", "EMAIL_ADDRESS").
GLiNER takes free-text labels at predict time ("credit card number", "email
address"). The PII v2 pipeline routes some entities through Presidio and
others through GLiNER, then normalizes back to Presidio tags before merging
the spans — this class provides the bidirectional translation.
"""


class PresidioGlinerMapper:
    PRESIDIO_TO_GLINER = {
        "CREDIT_CARD": "credit card number",
        "CRYPTO": "crypto wallet",
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
    GLINER_TO_PRESIDIO = {v: k for k, v in PRESIDIO_TO_GLINER.items()}

    @classmethod
    def presidio_to_gliner(cls, tag: str) -> str:
        return cls.PRESIDIO_TO_GLINER.get(tag, tag.lower())

    @classmethod
    def gliner_to_presidio(cls, tag: str) -> str:
        return cls.GLINER_TO_PRESIDIO.get(tag.lower(), tag.upper())
