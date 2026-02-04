#!/usr/bin/env python3
"""
Upload pre-downloaded models to cloud storage or filesystem.

This unified script supports multiple storage backends:
- S3 (AWS)
- GCS (Google Cloud Storage)
- Filesystem (Kubernetes PVC)

The backend is selected via the STORAGE_BACKEND environment variable.

Environment variables:
    STORAGE_BACKEND: Storage backend to use (s3, gcs, or filesystem) (required)

    # S3 backend:
    S3_BUCKET: Target S3 bucket name (required for s3 backend)
    S3_PREFIX: Prefix for S3 keys (optional, default: empty)

    # GCS backend:
    GCS_BUCKET: Target GCS bucket name (required for gcs backend)
    GCS_PREFIX: Prefix for GCS object names (optional, default: empty)
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON (optional, uses Workload Identity if unset)

    # Filesystem backend:
    SOURCE_DIR: Source directory containing models (optional, default: /models)
    TARGET_DIR: Target directory (mounted volume) (optional, default: /models-output)

    # Common:
    MODELS_DIR: Local directory containing models (optional, default: /models)
    LOG_LEVEL: Logging level (optional, default: INFO)
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Protocol

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """Protocol for storage backend implementations."""

    def upload_file(self, local_path: Path, remote_key: str) -> bool:
        """Upload a single file to the storage backend."""
        ...

    def get_backend_name(self) -> str:
        """Get the name of the storage backend."""
        ...


class S3Backend:
    """S3 storage backend implementation."""

    def __init__(self, bucket: str, prefix: str = ""):
        """Initialize S3 backend."""
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as e:
            raise ImportError(
                "boto3 is required for S3 backend. Install with: poetry add boto3",
            ) from e

        self.boto3 = boto3
        self.ClientError = ClientError
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = self.boto3.client("s3")

    def upload_file(self, local_path: Path, remote_key: str) -> bool:
        """Upload a single file to S3."""
        try:
            # Add prefix if configured
            s3_key = f"{self.prefix}/{remote_key}" if self.prefix else remote_key
            s3_key = s3_key.replace("\\", "/")

            # Check if file already exists in S3 with same size
            try:
                response = self.client.head_object(Bucket=self.bucket, Key=s3_key)
                s3_size = response.get("ContentLength", 0)
                local_size = local_path.stat().st_size

                if s3_size == local_size:
                    logger.info(f"⏭️  Skipping {s3_key} (already exists with same size)")
                    return True
            except self.ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise

            # Upload file
            logger.info(
                f"⬆️  Uploading {s3_key} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)",
            )
            self.client.upload_file(str(local_path), self.bucket, s3_key)
            return True

        except self.ClientError as e:
            logger.error(f"❌ Failed to upload {s3_key}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading {remote_key}: {e}")
            return False

    def get_backend_name(self) -> str:
        """Get the name of the storage backend."""
        return f"S3 (bucket: {self.bucket})"


class GCSBackend:
    """Google Cloud Storage backend implementation."""

    def __init__(self, bucket: str, prefix: str = ""):
        """Initialize GCS backend."""
        try:
            from google.api_core import exceptions
            from google.cloud import storage
        except ImportError as e:
            raise ImportError(
                "google-cloud-storage is required for GCS backend. "
                "Install with: poetry add google-cloud-storage",
            ) from e

        self.exceptions = exceptions
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket)

    def upload_file(self, local_path: Path, remote_key: str) -> bool:
        """Upload a single file to GCS."""
        try:
            # Add prefix if configured
            blob_name = f"{self.prefix}/{remote_key}" if self.prefix else remote_key
            blob_name = blob_name.replace("\\", "/")

            blob = self.bucket.blob(blob_name)

            # Check if blob already exists with same size
            if blob.exists():
                blob.reload()
                remote_size = blob.size
                local_size = local_path.stat().st_size
                if remote_size == local_size:
                    logger.info(
                        f"⏭️  Skipping {blob_name} (already exists with same size)",
                    )
                    return True

            # Upload file
            logger.info(
                f"⬆️  Uploading {blob_name} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)",
            )
            blob.upload_from_filename(str(local_path))
            return True

        except self.exceptions.GoogleAPIError as e:
            logger.error(f"❌ Failed to upload {blob_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading {remote_key}: {e}")
            return False

    def get_backend_name(self) -> str:
        """Get the name of the storage backend."""
        return f"GCS (bucket: {self.bucket_name})"


class FilesystemBackend:
    """Filesystem storage backend implementation (for Kubernetes PVC)."""

    def __init__(self, target_dir: Path):
        """Initialize filesystem backend."""
        self.target_dir = target_dir
        if not self.target_dir.exists():
            logger.info(f"Creating target directory: {self.target_dir}")
            self.target_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(self, local_path: Path, remote_key: str) -> bool:
        """Copy a single file to target directory."""
        try:
            target_path = self.target_dir / remote_key

            # Create parent directories if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists with same size
            if target_path.exists():
                source_size = local_path.stat().st_size
                target_size = target_path.stat().st_size

                if source_size == target_size:
                    logger.info(
                        f"⏭️  Skipping {remote_key} (already exists with same size)",
                    )
                    return True

            # Copy file
            file_size_mb = local_path.stat().st_size / 1024 / 1024
            logger.info(f"📋 Copying {remote_key} ({file_size_mb:.2f} MB)")
            shutil.copy2(local_path, target_path)
            return True

        except Exception as e:
            logger.error(f"❌ Failed to copy {remote_key}: {e}")
            return False

    def get_backend_name(self) -> str:
        """Get the name of the storage backend."""
        return f"Filesystem (target: {self.target_dir})"


def post_process_models(target_dir: Path) -> None:
    """
    Post-process copied models to fix common issues.

    Only relevant for filesystem backend (K8s/OpenShift).

    Args:
        target_dir: Target directory where models were copied
    """
    logger.info("🔧 Starting post-processing of models...")

    # GLiNER model needs config.json (transformers convention)
    # but we only download gliner_config.json, so copy it
    gliner_model_dir = target_dir / "urchade" / "gliner_multi_pii-v1"
    gliner_config = gliner_model_dir / "gliner_config.json"
    config_json = gliner_model_dir / "config.json"

    # Update model_name to local path in both config files
    local_model_path = "/home/nonroot/models/microsoft/mdeberta-v3-base"

    if gliner_config.exists():
        try:
            # Read and update gliner_config.json
            with open(gliner_config, "r") as f:
                gliner_data = json.load(f)

            if gliner_data.get("model_name") != local_model_path:
                logger.info(
                    f"📝 Updating model_name in gliner_config.json to '{local_model_path}'",
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
            else:
                with open(config_json, "r") as f:
                    config_data = json.load(f)

                if config_data.get("model_name") != local_model_path:
                    logger.info(f"📝 Updating model_name in config.json")
                    config_data["model_name"] = local_model_path
                    with open(config_json, "w") as f:
                        json.dump(config_data, f, indent=2)
                    logger.info("✅ Updated config.json")

        except Exception as e:
            logger.warning(f"⚠️  Failed to update GLiNER config files: {e}")
    else:
        logger.info("⏭️  Skipping GLiNER post-processing (config not found)")

    logger.info("✅ Post-processing complete")


def create_backend(backend_type: str) -> StorageBackend:
    """
    Create storage backend based on configuration.

    Args:
        backend_type: Type of backend (s3, gcs, or filesystem)

    Returns:
        StorageBackend instance

    Raises:
        ValueError: If backend type is invalid or required config is missing
    """
    backend_type = backend_type.lower()

    if backend_type == "s3":
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise ValueError(
                "S3_BUCKET environment variable is required for S3 backend",
            )
        prefix = os.getenv("S3_PREFIX", "").strip("/")
        return S3Backend(bucket, prefix)

    elif backend_type == "gcs":
        bucket = os.getenv("GCS_BUCKET")
        if not bucket:
            raise ValueError(
                "GCS_BUCKET environment variable is required for GCS backend",
            )
        prefix = os.getenv("GCS_PREFIX", "").strip("/")
        return GCSBackend(bucket, prefix)

    elif backend_type == "filesystem":
        target_dir = Path(os.getenv("TARGET_DIR", "/models-output"))
        return FilesystemBackend(target_dir)

    else:
        raise ValueError(
            f"Invalid STORAGE_BACKEND: {backend_type}. "
            "Must be one of: s3, gcs, filesystem",
        )


def upload_models(
    models_dir: Path,
    backend: StorageBackend,
) -> dict[str, int]:
    """
    Upload all models from local directory to storage backend.

    Args:
        models_dir: Local directory containing models
        backend: Storage backend to upload to

    Returns:
        Dict with upload statistics
    """
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
        remote_key = str(relative_path).replace("\\", "/")

        success = backend.upload_file(file_path, remote_key)

        if success:
            stats["uploaded"] += 1
        else:
            stats["failed"] += 1

    return stats


def main() -> int:
    """Main entry point."""
    # Get storage backend configuration
    backend_type = os.getenv("STORAGE_BACKEND")
    if not backend_type:
        logger.error(
            "STORAGE_BACKEND environment variable is required. "
            "Must be one of: s3, gcs, filesystem",
        )
        return 1

    # Get models directory
    models_dir = Path(os.getenv("MODELS_DIR", "/models"))
    if backend_type.lower() == "filesystem":
        # For filesystem backend, SOURCE_DIR overrides MODELS_DIR
        models_dir = Path(os.getenv("SOURCE_DIR", models_dir))

    # Create storage backend
    try:
        backend = create_backend(backend_type)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except ImportError as e:
        logger.error(f"Dependency error: {e}")
        return 1

    logger.info("=" * 60)
    logger.info("Arthur Model Repository - Upload Task")
    logger.info("=" * 60)
    logger.info(f"Backend:    {backend.get_backend_name()}")
    logger.info(f"Source Dir: {models_dir}")
    logger.info("=" * 60)

    # Upload models
    stats = upload_models(models_dir, backend)

    # Post-process for filesystem backend
    if backend_type.lower() == "filesystem":
        target_dir = Path(os.getenv("TARGET_DIR", "/models-output"))
        post_process_models(target_dir)

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
