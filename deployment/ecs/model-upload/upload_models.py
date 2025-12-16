#!/usr/bin/env python3
"""
Upload pre-downloaded models to S3.

This script uploads all model files from a local directory to an S3 bucket,
preserving the directory structure.

Environment variables:
    S3_BUCKET: Target S3 bucket name (required)
    S3_PREFIX: Prefix for S3 keys (optional, default: empty)
    MODELS_DIR: Local directory containing models (optional, default: /models)
"""

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def get_s3_client() -> "S3Client":
    """Create S3 client."""
    return boto3.client("s3")


def upload_file(
    s3_client: "S3Client",
    local_path: Path,
    bucket: str,
    s3_key: str,
) -> bool:
    """
    Upload a single file to S3.

    Args:
        s3_client: Boto3 S3 client
        local_path: Local file path
        bucket: S3 bucket name
        s3_key: S3 object key

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if file already exists in S3 with same size
        try:
            response = s3_client.head_object(Bucket=bucket, Key=s3_key)
            s3_size = response.get("ContentLength", 0)
            local_size = local_path.stat().st_size

            if s3_size == local_size:
                logger.info(f"⏭️  Skipping {s3_key} (already exists with same size)")
                return True
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise

        # Upload file
        logger.info(
            f"⬆️  Uploading {s3_key} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)",
        )
        s3_client.upload_file(str(local_path), bucket, s3_key)
        return True

    except ClientError as e:
        logger.error(f"❌ Failed to upload {s3_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error uploading {s3_key}: {e}")
        return False


def upload_models(
    models_dir: Path,
    bucket: str,
    prefix: str = "",
) -> dict[str, int]:
    """
    Upload all models from local directory to S3.

    Args:
        models_dir: Local directory containing models
        bucket: S3 bucket name
        prefix: Optional prefix for S3 keys

    Returns:
        Dict with upload statistics
    """
    s3_client = get_s3_client()

    stats = {
        "total": 0,
        "uploaded": 0,
        "skipped": 0,
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
        s3_key = f"{prefix}/{relative_path}" if prefix else str(relative_path)
        # Normalize path separators for S3
        s3_key = s3_key.replace("\\", "/")

        success = upload_file(s3_client, file_path, bucket, s3_key)

        if success:
            stats["uploaded"] += 1
        else:
            stats["failed"] += 1

    return stats


def main() -> int:
    """Main entry point."""
    # Get configuration from environment
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        logger.error("S3_BUCKET environment variable is required")
        return 1

    prefix = os.getenv("S3_PREFIX", "").strip("/")
    models_dir = Path(os.getenv("MODELS_DIR", "/models"))

    logger.info("=" * 60)
    logger.info("Arthur Model Repository - S3 Upload Task")
    logger.info("=" * 60)
    logger.info(f"S3 Bucket: {bucket}")
    logger.info(f"S3 Prefix: {prefix or '(none)'}")
    logger.info(f"Models Dir: {models_dir}")
    logger.info("=" * 60)

    # Upload models
    stats = upload_models(models_dir, bucket, prefix)

    # Print summary
    logger.info("=" * 60)
    logger.info("UPLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files:    {stats['total']}")
    logger.info(f"Uploaded:       {stats['uploaded']}")
    logger.info(f"Failed:         {stats['failed']}")
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
