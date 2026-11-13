"""A fake Wiz tenant for local and CI end-to-end runs of the Wiz discovery connector.

Not shipped: the engine image and wheel carry src/ml_engine only. See
docs/standalone-discovery.md, "Testing against a fake Wiz".
"""

from .server import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, FAULTS, FakeWiz

__all__ = ["DEFAULT_CLIENT_ID", "DEFAULT_CLIENT_SECRET", "FAULTS", "FakeWiz"]
