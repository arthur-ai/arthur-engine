"""Retrying a vendor call that failed for a reason that passes.

For connectors that page through a vendor's REST API, where one dropped connection
or 503 on page 40 of a long scan should not end it. Used by the Jamf and Splunk
clients.
"""

import random
from typing import Optional

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_CAP_SECONDS = 30.0


def backoff_seconds(attempt: int, retry_after: Optional[str]) -> float:
    """Honour Retry-After when the vendor sends one, else exponential with jitter.

    Jittered because a fleet-wide job retrying on a fixed schedule is a thundering
    herd against the customer's own server.
    """
    if retry_after:
        try:
            return min(float(retry_after), BACKOFF_CAP_SECONDS)
        except ValueError:
            pass
    window = min(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), BACKOFF_CAP_SECONDS)
    return random.uniform(0, window)
