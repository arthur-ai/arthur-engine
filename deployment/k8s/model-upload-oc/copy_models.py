#!/usr/bin/env python3
"""
Copy pre-downloaded models to a persistent volume.

This script copies all model files from a local directory to a mounted volume,
preserving the directory structure. This is for Kubernetes/OpenShift deployments
where models are stored in a PersistentVolume instead of S3.

Environment variables:
    SOURCE_DIR: Source directory containing models (optional, default: /models)
    TARGET_DIR: Target directory (mounted volume) (optional, default: /models-output)
    LOG_LEVEL: Logging level (optional, default: INFO)
"""

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def copy_file(
    source_path: Path,
    target_path: Path,
) -> bool:
    """
    Copy a single file to target directory.

    Args:
        source_path: Source file path
        target_path: Target file path

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create parent directories if they don't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file already exists with same size
        if target_path.exists():
            source_size = source_path.stat().st_size
            target_size = target_path.stat().st_size

            if source_size == target_size:
                logger.info(
                    f"⏭️  Skipping {target_path} (already exists with same size)",
                )
                return True

        # Copy file
        file_size_mb = source_path.stat().st_size / 1024 / 1024
        logger.info(
            f"📋 Copying {target_path.relative_to(target_path.parents[-1])} ({file_size_mb:.2f} MB)",
        )
        shutil.copy2(source_path, target_path)
        return True

    except Exception as e:
        logger.error(f"❌ Failed to copy {target_path}: {e}")
        return False


def copy_models(
    source_dir: Path,
    target_dir: Path,
) -> dict[str, int]:
    """
    Copy all models from source directory to target directory.

    Args:
        source_dir: Source directory containing models
        target_dir: Target directory (mounted volume)

    Returns:
        Dict with copy statistics
    """
    stats = {
        "total": 0,
        "copied": 0,
        "skipped": 0,
        "failed": 0,
    }

    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        return stats

    if not target_dir.exists():
        logger.info(f"Creating target directory: {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)

    # Find all files
    files = list(source_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    stats["total"] = len(files)

    logger.info(f"Found {len(files)} files to copy")

    for file_path in files:
        relative_path = file_path.relative_to(source_dir)
        target_path = target_dir / relative_path

        success = copy_file(file_path, target_path)

        if success:
            if (
                target_path.exists()
                and target_path.stat().st_size == file_path.stat().st_size
            ):
                stats["copied"] += 1
            else:
                stats["skipped"] += 1
        else:
            stats["failed"] += 1

    return stats


def post_process_models(target_dir: Path) -> None:
    """
    Post-process copied models to fix common issues.

    Args:
        target_dir: Target directory where models were copied
    """
    import json

    logger.info("🔧 Starting post-processing of models...")

    # GLiNER model needs config.json (transformers convention)
    # but we only download gliner_config.json, so copy it
    gliner_model_dir = target_dir / "urchade" / "gliner_multi_pii-v1"
    gliner_config = gliner_model_dir / "gliner_config.json"
    config_json = gliner_model_dir / "config.json"

    logger.info(f"Checking GLiNER model directory: {gliner_model_dir}")
    logger.info(f"  - Directory exists: {gliner_model_dir.exists()}")

    if gliner_model_dir.exists():
        logger.info(f"  - Files in directory: {list(gliner_model_dir.iterdir())}")
        logger.info(f"  - gliner_config.json exists: {gliner_config.exists()}")
        logger.info(f"  - config.json exists: {config_json.exists()}")

    # Update model_name to local path in both config files
    # The path is where models will be mounted at runtime in genai-engine pods
    local_model_path = f"/home/nonroot{target_dir}/microsoft/mdeberta-v3-base"

    if gliner_config.exists():
        try:
            # Read and update gliner_config.json
            with open(gliner_config, "r") as f:
                gliner_data = json.load(f)

            if gliner_data.get("model_name") != local_model_path:
                logger.info(
                    f"📝 Updating model_name in gliner_config.json from '{gliner_data.get('model_name')}' to '{local_model_path}'",
                )
                gliner_data["model_name"] = local_model_path
                with open(gliner_config, "w") as f:
                    json.dump(gliner_data, f, indent=2)
                logger.info("✅ Updated gliner_config.json")
            else:
                logger.info("⏭️  gliner_config.json already has correct model_name")

            # Create or update config.json
            if not config_json.exists():
                logger.info(
                    "📋 Creating config.json from gliner_config.json for GLiNER model",
                )
                shutil.copy2(gliner_config, config_json)
                logger.info("✅ Created config.json for GLiNER model")

            # Update config.json if it exists
            if config_json.exists():
                with open(config_json, "r") as f:
                    config_data = json.load(f)

                if config_data.get("model_name") != local_model_path:
                    logger.info(
                        f"📝 Updating model_name in config.json from '{config_data.get('model_name')}' to '{local_model_path}'",
                    )
                    config_data["model_name"] = local_model_path
                    with open(config_json, "w") as f:
                        json.dump(config_data, f, indent=2)
                    logger.info("✅ Updated config.json")
                else:
                    logger.info("⏭️  config.json already has correct model_name")

        except Exception as e:
            logger.error(f"⚠️  Failed to update GLiNER config files: {e}")
    elif not gliner_config.exists():
        logger.error(
            f"⚠️  Skipping GLiNER config updates: gliner_config.json not found at {gliner_config}",
        )

    logger.info("✅ Post-processing complete")


def main() -> int:
    """Main entry point."""
    # Get configuration from environment
    source_dir = Path(os.getenv("SOURCE_DIR", "/models"))
    target_dir = Path(os.getenv("TARGET_DIR", "/model-storage"))

    logger.info("=" * 60)
    logger.info("Arthur Model Repository - Volume Copy Task")
    logger.info("=" * 60)
    logger.info(f"Source Dir: {source_dir}")
    logger.info(f"Target Dir: {target_dir}")
    logger.info("=" * 60)

    # Copy models
    stats = copy_models(source_dir, target_dir)

    # Post-process models (fix common issues)
    post_process_models(target_dir)

    # Print summary
    logger.info("=" * 60)
    logger.info("COPY SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files:    {stats['total']}")
    logger.info(f"Copied:         {stats['copied']}")
    logger.info(f"Skipped:        {stats['skipped']}")
    logger.info(f"Failed:         {stats['failed']}")
    logger.info("=" * 60)

    if stats["failed"] > 0:
        logger.error("❌ Some files failed to copy")
        return 1

    if stats["total"] == 0:
        logger.warning("⚠️  No files found to copy")
        return 1

    logger.info("✅ All models copied successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
