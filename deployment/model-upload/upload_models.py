#!/usr/bin/env python3
"""
Transfer pre-downloaded models to storage backend.

Supports three backends selected via the BACKEND environment variable:
  s3  — upload to AWS S3 (ECS deployments)
  gcs — upload to Google Cloud Storage (GCP Cloud Run)
  pvc — copy to mounted PersistentVolume (Kubernetes/OpenShift)

Environment variables (all backends):
    BACKEND:    Storage backend: s3, gcs, or pvc (default: s3)
    MODELS_DIR: Local directory containing downloaded models (default: /models)
    LOG_LEVEL:  Logging level (default: INFO)

S3-specific:
    S3_BUCKET: Target S3 bucket name (required)
    S3_PREFIX: Prefix for S3 keys (optional)

GCS-specific:
    GCS_BUCKET:          Target GCS bucket name (required)
    GCS_PREFIX:          Prefix for GCS object names (optional)
    CONTAINER_MODELS_DIR: Mount path where consumer pods access models (default: /models-storage)

PVC-specific:
    TARGET_DIR: Target directory on the mounted volume (default: /models-output)
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BACKEND = os.environ.get("BACKEND", "s3")


# ── S3 backend ────────────────────────────────────────────────────────────────


def _run_s3(models_dir: Path) -> dict[str, int]:
    import boto3
    from botocore.exceptions import ClientError

    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        logger.error("S3_BUCKET environment variable is required")
        sys.exit(1)
    prefix = os.getenv("S3_PREFIX", "").strip("/")

    logger.info(f"S3 Bucket: {bucket}")
    logger.info(f"S3 Prefix: {prefix or '(none)'}")

    s3 = boto3.client("s3")
    stats: dict[str, int] = {"total": 0, "transferred": 0, "skipped": 0, "failed": 0}
    files = [f for f in models_dir.rglob("*") if f.is_file()]
    stats["total"] = len(files)
    logger.info(f"Found {len(files)} files to upload")

    for file_path in files:
        relative_path = file_path.relative_to(models_dir)
        s3_key = f"{prefix}/{relative_path}" if prefix else str(relative_path)
        s3_key = s3_key.replace("\\", "/")

        try:
            try:
                response = s3.head_object(Bucket=bucket, Key=s3_key)
                if response.get("ContentLength", 0) == file_path.stat().st_size:
                    logger.info(f"⏭️  Skipping {s3_key} (already exists with same size)")
                    stats["skipped"] += 1
                    continue
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise

            logger.info(
                f"⬆️  Uploading {s3_key} ({file_path.stat().st_size / 1024 / 1024:.2f} MB)",
            )
            s3.upload_file(str(file_path), bucket, s3_key)
            stats["transferred"] += 1

        except Exception as e:
            logger.error(f"❌ Failed to upload {s3_key}: {e}")
            stats["failed"] += 1

    return stats


# ── GCS backend ───────────────────────────────────────────────────────────────


def _run_gcs(models_dir: Path) -> dict[str, int]:
    from google.cloud import storage

    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        logger.error("GCS_BUCKET environment variable is required")
        sys.exit(1)
    prefix = os.getenv("GCS_PREFIX", "").strip("/")
    container_models_dir = os.getenv("CONTAINER_MODELS_DIR", "/models-storage")

    logger.info(f"GCS Bucket: {bucket_name}")
    logger.info(f"GCS Prefix: {prefix or '(none)'}")

    client = storage.Client()
    stats: dict[str, int] = {"total": 0, "transferred": 0, "skipped": 0, "failed": 0}
    files = [f for f in models_dir.rglob("*") if f.is_file()]
    stats["total"] = len(files)
    logger.info(f"Found {len(files)} files to upload")

    for file_path in files:
        relative_path = file_path.relative_to(models_dir)
        blob_name = f"{prefix}/{relative_path}" if prefix else str(relative_path)
        blob_name = blob_name.replace("\\", "/")

        try:
            bkt = client.bucket(bucket_name)
            blob = bkt.blob(blob_name)

            if blob.exists():
                blob.reload()
                if blob.size == file_path.stat().st_size:
                    logger.info(
                        f"⏭️  Skipping {blob_name} (already exists with same size)",
                    )
                    stats["skipped"] += 1
                    continue

            logger.info(
                f"⬆️  Uploading {blob_name} ({file_path.stat().st_size / 1024 / 1024:.2f} MB)",
            )
            blob.upload_from_filename(str(file_path))
            stats["transferred"] += 1

        except Exception as e:
            logger.error(f"❌ Failed to upload {blob_name}: {e}")
            stats["failed"] += 1

    _post_process_gcs(models_dir, bucket_name, prefix, container_models_dir)
    return stats


def _post_process_gcs(
    models_dir: Path,
    bucket_name: str,
    prefix: str,
    container_models_dir: str,
) -> None:
    """Create/update config.json for the GLiNER model in GCS."""
    from google.cloud import storage

    logger.info("🔧 Post-processing GLiNER config in GCS...")
    gliner_config_path = (
        models_dir / "urchade" / "gliner_multi_pii-v1" / "gliner_config.json"
    )

    if not gliner_config_path.exists():
        logger.error(f"❌ gliner_config.json not found at {gliner_config_path}")
        return

    try:
        with open(gliner_config_path) as f:
            config_data = json.load(f)

        new_model_name = f"{container_models_dir}/microsoft/mdeberta-v3-base"
        old_model_name = config_data.get("model_name", "")
        config_data["model_name"] = new_model_name
        logger.info(f"📝 Updating model_name: '{old_model_name}' → '{new_model_name}'")

        json_content = json.dumps(config_data, indent=2)
        client = storage.Client()
        bkt = client.bucket(bucket_name)
        blob_base = "/".join(filter(None, [prefix, "urchade", "gliner_multi_pii-v1"]))

        for filename in ("config.json", "gliner_config.json"):
            blob = bkt.blob(f"{blob_base}/{filename}")
            blob.upload_from_string(json_content, content_type="application/json")
            logger.info(f"✅ Uploaded gs://{bucket_name}/{blob_base}/{filename}")

    except Exception as e:
        logger.error(f"❌ Failed to post-process GLiNER config: {e}")


# ── PVC backend ───────────────────────────────────────────────────────────────


def _run_pvc(models_dir: Path) -> dict[str, int]:
    target_dir = Path(os.getenv("TARGET_DIR", "/models-output"))
    logger.info(f"Target Dir: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {"total": 0, "transferred": 0, "skipped": 0, "failed": 0}
    files = [f for f in models_dir.rglob("*") if f.is_file()]
    stats["total"] = len(files)
    logger.info(f"Found {len(files)} files to copy")

    for file_path in files:
        relative_path = file_path.relative_to(models_dir)
        target_path = target_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if (
                target_path.exists()
                and target_path.stat().st_size == file_path.stat().st_size
            ):
                logger.info(
                    f"⏭️  Skipping {relative_path} (already exists with same size)",
                )
                stats["skipped"] += 1
                continue

            file_size_mb = file_path.stat().st_size / 1024 / 1024
            logger.info(f"📋 Copying {relative_path} ({file_size_mb:.2f} MB)")
            shutil.copy2(file_path, target_path)
            stats["transferred"] += 1

        except Exception as e:
            logger.error(f"❌ Failed to copy {relative_path}: {e}")
            stats["failed"] += 1

    _post_process_pvc(target_dir)
    return stats


def _post_process_pvc(target_dir: Path) -> None:
    """Create config.json for GLiNER model and update model_name to local mount path."""
    logger.info("🔧 Post-processing GLiNER model config...")
    gliner_model_dir = target_dir / "urchade" / "gliner_multi_pii-v1"
    gliner_config = gliner_model_dir / "gliner_config.json"
    config_json = gliner_model_dir / "config.json"
    local_model_path = f"/home/nonroot{target_dir}/microsoft/mdeberta-v3-base"

    if not gliner_config.exists():
        logger.error(f"❌ gliner_config.json not found at {gliner_config}")
        return

    try:
        with open(gliner_config) as f:
            gliner_data = json.load(f)

        if gliner_data.get("model_name") != local_model_path:
            gliner_data["model_name"] = local_model_path
            with open(gliner_config, "w") as f:
                json.dump(gliner_data, f, indent=2)
            logger.info(
                f"📝 Updated model_name in gliner_config.json to '{local_model_path}'",
            )
        else:
            logger.info("⏭️  gliner_config.json already has correct model_name")

        if not config_json.exists():
            shutil.copy2(gliner_config, config_json)
            logger.info("✅ Created config.json for GLiNER model")

    except Exception as e:
        logger.error(f"❌ Failed to post-process GLiNER config: {e}")

    logger.info("✅ Post-processing complete")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    models_dir = Path(os.getenv("MODELS_DIR", "/models"))

    if not models_dir.exists():
        logger.error(f"Models directory does not exist: {models_dir}")
        return 1

    backends = {"s3": _run_s3, "gcs": _run_gcs, "pvc": _run_pvc}
    if BACKEND not in backends:
        logger.error(f"Unknown backend: {BACKEND!r}. Must be one of: {list(backends)}")
        return 1

    logger.info("=" * 60)
    logger.info(f"Arthur Model Repository - {BACKEND.upper()} Transfer Task")
    logger.info("=" * 60)
    logger.info(f"Backend:    {BACKEND}")
    logger.info(f"Models Dir: {models_dir}")
    logger.info("=" * 60)

    stats = backends[BACKEND](models_dir)

    logger.info("=" * 60)
    logger.info("TRANSFER SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files:  {stats['total']}")
    logger.info(f"Transferred:  {stats['transferred']}")
    logger.info(f"Skipped:      {stats['skipped']}")
    logger.info(f"Failed:       {stats['failed']}")
    logger.info("=" * 60)

    if stats["failed"] > 0:
        logger.error("❌ Some files failed to transfer")
        return 1

    if stats["total"] == 0:
        logger.warning("⚠️  No files found to transfer")
        return 1

    logger.info("✅ All models transferred successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
