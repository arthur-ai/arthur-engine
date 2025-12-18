#!/usr/bin/env python3
"""
Check for model updates on Hugging Face Hub.

This script compares the current commit hashes of models on HuggingFace
with a stored manifest to determine if any models have been updated.
"""

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

from huggingface_hub import HfApi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Models to check - must match DEFAULT_MODELS in download_models.py
MODELS = [
    "sentence-transformers/all-MiniLM-L12-v2",
    "ProtectAI/deberta-v3-base-prompt-injection-v2",
    "s-nlp/roberta_toxicity_classifier",
    "microsoft/deberta-v2-xlarge-mnli",
    "urchade/gliner_multi_pii-v1",
    "tarekziade/pardonmyai",
]


def get_model_commits() -> dict[str, str]:
    """
    Get the latest commit hash for each model from HuggingFace.

    Returns:
        Dict mapping model name to its latest commit SHA
    """
    api = HfApi()
    commits = {}

    for model in MODELS:
        try:
            info = api.model_info(model)
            sha = info.sha or ""
            commits[model] = sha
            logger.info(f"✓ {model}: {sha[:12]}")
        except Exception as e:
            logger.error(f"✗ {model}: {e}")
            # Use empty string for models that can't be fetched
            # This ensures we still get a unique hash
            commits[model] = ""

    return commits


def compute_combined_hash(commits: dict[str, str]) -> str:
    """
    Compute a combined hash from all model commit hashes.

    This creates a single deterministic hash that represents
    the current state of all models.
    """
    # Sort by model name for deterministic ordering
    combined = "".join(commits[k] for k in sorted(commits.keys()))
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def load_manifest(manifest_path: Path) -> dict | None:
    """Load the existing models manifest."""
    if not manifest_path.exists():
        return None
    with open(manifest_path) as f:
        return json.load(f)


def save_manifest(manifest_path: Path, commits: dict[str, str], combined_hash: str):
    """Save the models manifest."""
    manifest = {
        "combined_hash": combined_hash,
        "model_commits": commits,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Check for Hugging Face model updates",
    )
    parser.add_argument(
        "--manifest",
        "-m",
        type=Path,
        default=Path(__file__).parent / "models-manifest.json",
        help="Path to models manifest file (default: models-manifest.json in same dir)",
    )
    parser.add_argument(
        "--update",
        "-u",
        action="store_true",
        help="Update the manifest file with current model commits",
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["json", "text", "github"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    logger.info("Fetching current model commits from HuggingFace...")
    current_commits = get_model_commits()
    current_hash = compute_combined_hash(current_commits)

    logger.info(f"\nCurrent combined hash: {current_hash}")

    # Load existing manifest
    existing_manifest = load_manifest(args.manifest)

    if existing_manifest:
        existing_hash = existing_manifest.get("combined_hash", "")
        has_updates = current_hash != existing_hash

        if has_updates:
            logger.info("\n🔄 Models have been updated!")
            # Show which models changed
            existing_commits = existing_manifest.get("model_commits", {})
            for model in MODELS:
                old = existing_commits.get(model, "N/A")[:12]
                new = current_commits.get(model, "N/A")[:12]
                if old != new:
                    logger.info(f"  Changed: {model}")
                    logger.info(f"    Old: {old}")
                    logger.info(f"    New: {new}")
        else:
            logger.info("\n✓ No model updates detected")
    else:
        logger.info("\n⚠ No existing manifest found - treating as new")
        has_updates = True
        existing_hash = ""

    # Update manifest if requested
    if args.update:
        save_manifest(args.manifest, current_commits, current_hash)

    # Output results
    result = {
        "has_updates": has_updates,
        "current_hash": current_hash,
        "existing_hash": existing_hash,
        "model_commits": current_commits,
    }

    if args.output == "json":
        print(json.dumps(result, indent=2))
    elif args.output == "github":
        # GitHub Actions output format
        print(f"has_updates={'true' if has_updates else 'false'}")
        print(f"current_hash={current_hash}")
        print(f"existing_hash={existing_hash}")
    else:
        print(f"\nResult: {'BUILD REQUIRED' if has_updates else 'NO BUILD NEEDED'}")

    # Exit with code 0 if updates, 1 if no updates (for CI scripting)
    # Note: We exit 0 on updates so the build proceeds
    sys.exit(0)


if __name__ == "__main__":
    main()
