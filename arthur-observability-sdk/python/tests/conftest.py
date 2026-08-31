"""
Pytest configuration and shared fixtures for arthur-observability-sdk tests.
"""

import sys
from pathlib import Path

# scripts/instrumentor_registry.py is the single source of truth for the
# instrumentor declarations, shared with the CI verification job.  Make it
# importable from the test suite rather than duplicating the parser here.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
