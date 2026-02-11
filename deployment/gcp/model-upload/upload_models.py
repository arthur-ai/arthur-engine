#!/usr/bin/env python3
"""
Upload pre-downloaded models to Google Cloud Storage (GCS).

This script uploads all model files from a local directory to a GCS bucket,
preserving the directory structure.

Environment variables:
    GCS_BUCKET: Target GCS bucket name (required)
    GCS_PREFIX: Prefix for GCS object names (optional, default: empty)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional, uses Workload Identity if unset)
"""

import json
import logging
import os
import sys
from pathlib import Path

from google.api_core import exceptions
from google.cloud import storage

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def get_storage_client() -> storage.Client:
    """Create GCS client (uses GOOGLE_APPLICATION_CREDENTIALS or default credentials)."""
    return storage.Client()


def upload_file(
    client: storage.Client,
    local_path: Path,
    bucket_name: str,
    blob_name: str,
) -> bool:
    """
    Upload a single file to GCS.

    Args:
        client: Google Cloud Storage client
        local_path: Local file path
        bucket_name: GCS bucket name
        blob_name: GCS object name (key)

    Returns:
        True if successful, False otherwise
    """
    try:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Check if blob already exists with same size
        if blob.exists():
            blob.reload()
            remote_size = blob.size
            local_size = local_path.stat().st_size
            if remote_size == local_size:
                logger.info(f"⏭️  Skipping {blob_name} (already exists with same size)")
                return True

        # Upload file
        logger.info(
            f"⬆️  Uploading {blob_name} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)",
        )
        blob.upload_from_filename(str(local_path))
        return True

    except exceptions.GoogleAPIError as e:
        logger.error(f"❌ Failed to upload {blob_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error uploading {blob_name}: {e}")
        return False


def upload_models(
    models_dir: Path,
    bucket_name: str,
    prefix: str = "",
) -> dict[str, int]:
    """
    Upload all models from local directory to GCS.

    Args:
        models_dir: Local directory containing models
        bucket_name: GCS bucket name
        prefix: Optional prefix for GCS object names

    Returns:
        Dict with upload statistics
    """
    client = get_storage_client()

    stats = {
        "total": 0,
        "uploaded": 0,
        "failed": 0,
    }

    if not models_dir.exists():
        logger.error(f"Models directory does not exist: {models_dir}")
        return stats

    # Find all files
    files = list(models_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    stats["total"] = len(files)

    logger.info(f"Found {len(files)} files to upload")

    for file_path in files:
        relative_path = file_path.relative_to(models_dir)
        blob_name = f"{prefix}/{relative_path}" if prefix else str(relative_path)
        # Normalize path separators for GCS
        blob_name = blob_name.replace("\\", "/")

        success = upload_file(client, file_path, bucket_name, blob_name)

        if success:
            stats["uploaded"] += 1
        else:
            stats["failed"] += 1

    return stats


def post_process_models(
    models_dir: Path,
    bucket_name: str,
    prefix: str,
) -> bool:
    """
    Create and upload config.json to GCS for the GLiNER model.

    Reads gliner_config.json from local filesystem, updates model_name,
    and uploads as config.json to GCS.

    Args:
        models_dir: Local directory containing models
        bucket_name: GCS bucket name
        prefix: GCS prefix for object names

    Returns:
        True if successful, False otherwise
    """
    logger.info("🔧 Creating config.json in GCS...")

    # Path to gliner_config.json file
    gliner_config_path = (
        models_dir / "urchade" / "gliner_multi_pii-v1" / "gliner_config.json"
    )

    if not gliner_config_path.exists():
        logger.error(f"❌ gliner_config.json not found at {gliner_config_path}")
        return False

    try:
        # Read existing gliner_config.json
        logger.info(f"📖 Reading gliner_config.json from {gliner_config_path}")
        with open(gliner_config_path, "r") as f:
            config_data = json.load(f)

        # Update model_name with prefix
        if prefix:
            new_model_name = f"/home/nonroot/{prefix}/microsoft/mdeberta-v3-base"
        else:
            new_model_name = "/home/nonroot/microsoft/mdeberta-v3-base"
        old_model_name = config_data.get("model_name", "")
        config_data["model_name"] = new_model_name

        logger.info(
            f"📝 Updating model_name from '{old_model_name}' to '{new_model_name}'",
        )

        # Upload to GCS
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        json_content = json.dumps(config_data, indent=2)

        # Construct base GCS blob path parts
        blob_path_parts = []
        if prefix:
            blob_path_parts.append(prefix.strip("/"))
        blob_path_parts.extend(["urchade", "gliner_multi_pii-v1"])

        # Upload as config.json
        config_blob_name = "/".join(blob_path_parts + ["config.json"])
        logger.info(
            f"📤 Uploading config.json to gs://{bucket_name}/{config_blob_name}",
        )
        config_blob = bucket.blob(config_blob_name)
        config_blob.upload_from_string(json_content, content_type="application/json")
        logger.info("✅ Successfully created config.json in GCS")

        # Upload as gliner_config.json to the same GCS path
        gliner_config_blob_name = "/".join(blob_path_parts + ["gliner_config.json"])
        gliner_config_blob = bucket.blob(gliner_config_blob_name)

        # Check if gliner_config.json already exists (will be overwritten)
        if gliner_config_blob.exists():
            logger.info(
                f"🔄 Replacing existing gliner_config.json at gs://{bucket_name}/{gliner_config_blob_name}",
            )
        else:
            logger.info(
                f"📤 Uploading gliner_config.json to gs://{bucket_name}/{gliner_config_blob_name}",
            )

        gliner_config_blob.upload_from_string(
            json_content,
            content_type="application/json",
        )
        logger.info("✅ Successfully created/updated gliner_config.json in GCS")

        return True

    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse gliner_config.json: {e}")
        return False
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return False
    except exceptions.GoogleAPIError as e:
        logger.error(f"❌ Failed to upload config.json to GCS: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error creating config.json: {e}")
        return False


def main() -> int:
    """Main entry point."""
    # Get configuration from environment
    bucket = os.getenv("GCS_BUCKET")
    if not bucket:
        logger.error("GCS_BUCKET environment variable is required")
        return 1

    prefix = os.getenv("GCS_PREFIX", "").strip("/")
    models_dir = Path(os.getenv("MODELS_DIR", "/models"))

    logger.info("=" * 60)
    logger.info("Arthur Model Repository - GCS Upload Task")
    logger.info("=" * 60)
    logger.info(f"GCS Bucket: {bucket}")
    logger.info(f"GCS Prefix: {prefix or '(none)'}")
    logger.info(f"Models Dir: {models_dir}")
    logger.info("=" * 60)

    # Upload models
    # stats = upload_models(models_dir, bucket, prefix)

    # Post-process models (fix common issues)
    post_process_success = post_process_models(models_dir, bucket, prefix)

    # Print summary
    logger.info("=" * 60)
    logger.info("UPLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files:    {stats['total']}")
    logger.info(f"Uploaded:       {stats['uploaded']}")
    logger.info(f"Failed:         {stats['failed']}")
    logger.info(f"Post-processing: {post_process_success}")
    logger.info("=" * 60)

    if stats["failed"] > 0:
        logger.error("❌ Some files failed to upload")
        return 1

    if stats["total"] == 0:
        logger.warning("⚠️  No files found to upload")
        return 1

    logger.info("✅ All models uploaded successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
