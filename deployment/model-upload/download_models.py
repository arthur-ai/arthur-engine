#!/usr/bin/env python3
"""
Download models from Hugging Face Hub for airgapped deployment.

This script downloads all required models and saves them to a local directory
with the structure expected by the model repository server.
"""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from huggingface_hub import hf_hub_download

try:
    from huggingface_hub.errors import HfHubHTTPError, RepositoryNotFoundError
except ImportError:
    # Older versions of huggingface_hub
    from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Default models configuration - matches genai-engine requirements
DEFAULT_MODELS: dict[str, list[str]] = {
    "sentence-transformers/all-MiniLM-L12-v2": [
        "1_Pooling/config.json",
        "config.json",
        "config_sentence_transformers.json",
        "model.safetensors",
        "modules.json",
        "sentence_bert_config.json",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "tokenizer.json",
        "vocab.txt",
    ],
    "ProtectAI/deberta-v3-base-prompt-injection-v2": [
        "added_tokens.json",
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "spm.model",
        "tokenizer_config.json",
        "tokenizer.json",
    ],
    "s-nlp/roberta_toxicity_classifier": [
        "config.json",
        "merges.txt",
        "pytorch_model.bin",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "vocab.json",
    ],
    "microsoft/deberta-v2-xlarge-mnli": [
        "config.json",
        "pytorch_model.bin",
        "spm.model",
        "tokenizer_config.json",
    ],
    "urchade/gliner_multi_pii-v1": [
        "gliner_config.json",
        "pytorch_model.bin",
    ],
    "microsoft/mdeberta-v3-base": [
        "config.json",
        "generator_config.json",
        "pytorch_model.bin",
        "pytorch_model.generator.bin",
        "spm.model",
        "tf_model.h5",
        "tokenizer_config.json",
    ],
    "tarekziade/pardonmyai": [
        "config.json",
        "model.safetensors",
        "onnx/model_quantized.onnx",
        "onnx/model.onnx",
        "quantize_config.json",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "tokenizer.json",
        "vocab.txt",
    ],
}

TIKTOKEN_ENCODINGS = ["cl100k_base", "p50k_base", "r50k_base", "o200k_base"]


def download_file(
    model_name: str,
    filename: str,
    output_dir: Path,
) -> tuple[str, str, bool, str]:
    """Download a single file from Hugging Face Hub."""
    try:
        cached_path = hf_hub_download(
            repo_id=model_name,
            filename=filename,
            local_dir=output_dir / model_name,
            local_dir_use_symlinks=False,
        )
        return (model_name, filename, True, f"Downloaded to {cached_path}")
    except RepositoryNotFoundError:
        return (model_name, filename, False, f"Repository not found: {model_name}")
    except HfHubHTTPError as e:
        return (model_name, filename, False, f"HTTP error: {e}")
    except Exception as e:
        return (model_name, filename, False, f"Error: {e}")


def download_models(
    models: dict[str, list[str]],
    output_dir: Path,
    max_workers: int = 4,
) -> dict[str, list[dict[str, str]] | int]:
    """Download all specified models in parallel."""
    results: dict[str, list[dict[str, str]] | int] = {
        "successful": [],
        "failed": [],
        "total_files": 0,
        "downloaded_files": 0,
    }

    tasks = [
        (model_name, filename)
        for model_name, filenames in models.items()
        for filename in filenames
    ]
    results["total_files"] = len(tasks)
    logger.info(f"Downloading {len(tasks)} files from {len(models)} models...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_file, model, file, output_dir): (model, file)
            for model, file in tasks
        }
        for future in as_completed(futures):
            model_name, filename, success, message = future.result()
            if success:
                results["downloaded_files"] += 1  # type: ignore[operator]
                results["successful"].append(  # type: ignore[union-attr]
                    {"model": model_name, "file": filename, "message": message},
                )
                logger.info(f"✓ {model_name}/{filename}")
            else:
                results["failed"].append(  # type: ignore[union-attr]
                    {"model": model_name, "file": filename, "error": message},
                )
                logger.error(f"✗ {model_name}/{filename}: {message}")

    return results


def download_tiktoken_encodings(output_dir: Path) -> dict[str, list[str]]:
    """Download tiktoken encoding files for airgapped k8s/PVC deployment.

    Files are cached using tiktoken's SHA1-hashed filename scheme so they are
    picked up automatically at runtime when TIKTOKEN_CACHE_DIR points here.
    """
    import tiktoken

    tiktoken_dir = output_dir / "tiktoken"
    tiktoken_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_dir)

    results: dict[str, list[str]] = {"successful": [], "failed": []}
    for encoding_name in TIKTOKEN_ENCODINGS:
        try:
            tiktoken.get_encoding(encoding_name)
            logger.info(f"✓ tiktoken/{encoding_name}")
            results["successful"].append(encoding_name)
        except Exception as e:
            logger.error(f"✗ tiktoken/{encoding_name}: {e}")
            results["failed"].append(encoding_name)
    return results


def load_models_config(config_path: str) -> dict[str, list[str]]:
    """Load models configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Hugging Face models for airgapped deployment",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("/models"),
        help="Output directory for downloaded models (default: /models)",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="JSON file with models configuration (optional, uses defaults if not provided)",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of parallel download workers (default: 4)",
    )
    parser.add_argument(
        "--exclude-relevance",
        action="store_true",
        help="Exclude relevance models (microsoft/deberta-v2-xlarge-mnli) to reduce image size",
    )
    parser.add_argument(
        "--include-tiktoken",
        action="store_true",
        default=False,
        help="Also download tiktoken encodings (required for airgapped k8s/PVC deployments)",
    )
    args = parser.parse_args()

    if args.config:
        logger.info(f"Loading models configuration from: {args.config}")
        models = load_models_config(args.config)
    else:
        logger.info("Using default models configuration")
        models = DEFAULT_MODELS.copy()

    if args.exclude_relevance and "microsoft/deberta-v2-xlarge-mnli" in models:
        logger.info("Excluding relevance models (microsoft/deberta-v2-xlarge-mnli)")
        del models["microsoft/deberta-v2-xlarge-mnli"]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {args.output_dir}")

    results = download_models(models, args.output_dir, args.workers)

    tiktoken_results: dict[str, list[str]] | None = None
    if args.include_tiktoken:
        logger.info("Downloading tiktoken encoding files...")
        tiktoken_results = download_tiktoken_encodings(args.output_dir)

    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total files: {results['total_files']}")
    print(f"Downloaded:  {results['downloaded_files']}")
    print(f"Failed:      {len(results['failed'])}")  # type: ignore[arg-type]
    if tiktoken_results is not None:
        print(
            f"Tiktoken encodings: {len(tiktoken_results['successful'])}/{len(TIKTOKEN_ENCODINGS)}",
        )
    print("=" * 60)

    failed = bool(results["failed"]) or bool(
        tiktoken_results and tiktoken_results["failed"],
    )
    if failed:
        if results["failed"]:
            print("\nFailed model downloads:")
            for item in results["failed"]:  # type: ignore[union-attr]
                print(f"  - {item['model']}/{item['file']}: {item['error']}")
        if tiktoken_results and tiktoken_results["failed"]:
            print("\nFailed tiktoken encodings:")
            for name in tiktoken_results["failed"]:
                print(f"  - {name}")
        sys.exit(1)

    if tiktoken_results is not None:
        print("\n✓ All models and tiktoken encodings downloaded successfully!")
    else:
        print("\n✓ All models downloaded successfully!")

    manifest_path = args.output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(
            {"models": list(models.keys()), "files": results["successful"]},
            f,
            indent=2,
        )
    logger.info(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
