#!/usr/bin/env python3
"""CLI entrypoint for the runtime weight downloader.

Thin wrapper around `models.downloader.download_all`. Useful for
pre-populating a host volume before the first container start, or for
running offline cache prep in CI. Server startup also calls into the same
module; this script is just the out-of-band path.

Usage:
    PYTHONPATH=src python scripts/download_models.py --workers 4
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent.parent / "src"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        help="Override MODEL_STORAGE_PATH for this run.",
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    if args.output_dir:
        os.environ["MODEL_STORAGE_PATH"] = args.output_dir

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    from models.downloader import download_all  # imported after env override

    download_all(workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
