"""Runtime model-weight downloader.

Migrated from genai-engine's `download_models()` flow in
src/utils/model_load.py. Pulls every (repo, filename) pair declared in
`model_registry.registry` into MODEL_STORAGE_PATH on container start so the loaders
in `model_registry.loader` find files on disk.

The previous build-time bake-in worked but produced a 14 GB image and
broke GLiNER's offline path (see the Dockerfile note); this matches the
engine's pattern instead — empty directory in the image, downloaded at
startup, persisted across restarts via a mounted volume.
"""

import logging
import os
from multiprocessing import get_context
from pathlib import Path

from huggingface_hub import hf_hub_download

import config as svc_config
from model_registry.registry import files_to_download

logger = logging.getLogger(__name__)


def _download_one(args: tuple[str, str, str | None, str]) -> None:
    repo, filename, revision, output_dir = args
    local_dir = Path(output_dir) / repo
    local_dir.mkdir(parents=True, exist_ok=True)
    target = local_dir / filename
    if target.exists():
        # Already pulled in a previous container start (volume-mounted).
        return
    try:
        hf_hub_download(
            repo_id=repo,
            filename=filename,
            revision=revision,
            local_dir=str(local_dir),
        )
    except Exception as e:
        # Mirror the engine's behavior: log and continue. The loader will
        # fail loudly if a critical file is missing at warm time.
        logger.warning("Failed to download %s/%s: %s", repo, filename, e)


def download_all(workers: int = 4) -> None:
    """Pull every registry-declared file into MODEL_STORAGE_PATH.

    Skipped entirely when MODELS_SERVICE_SKIP_LOADING=true.
    """
    if svc_config.SKIP_MODEL_LOADING:
        logger.info("Skipping weight downloads — MODELS_SERVICE_SKIP_LOADING=true")
        return

    output_dir = svc_config.MODEL_STORAGE_PATH
    os.makedirs(output_dir, exist_ok=True)

    tasks = [(repo, fn, rev, output_dir) for repo, fn, rev in files_to_download()]
    logger.info(
        "Downloading %d weight files into %s (workers=%d)",
        len(tasks),
        output_dir,
        workers,
    )

    with get_context("spawn").Pool(processes=workers) as pool:
        pool.map(_download_one, tasks)

    logger.info("Weight downloads complete.")
