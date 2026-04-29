"""Regex-driven profanity detection used by the toxicity scorer."""

from inference.toxicity.profanity.detect import detect_profanity

__all__ = ["detect_profanity"]
