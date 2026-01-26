#!/usr/bin/env python3
"""
Download models from Hugging Face Hub for airgapped deployment.

This script downloads all required models and saves them to a local directory
with the structure expected by the model repository server.
"""

import argparse
import json
import logging
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


def download_file(
    model_name: str,
    filename: str,
    output_dir: Path,
) -> tuple[str, str, bool, str]:
    """
    Download a single file from Hugging Face Hub.

    Args:
        model_name: The HF model repository name (e.g., 'sentence-transformers/all-MiniLM-L12-v2')
        filename: The file to download
        output_dir: Base directory to save models

    Returns:
        Tuple of (model_name, filename, success, message)
    """
    try:
        # Download to HF cache first
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
) -> dict[str, dict[str, any]]:
    """
    Download all specified models.

    Args:
        models: Dict mapping model names to lists of files
        output_dir: Base directory to save models
        max_workers: Number of parallel downloads

    Returns:
        Dict with download results
    """
    results: dict[str, dict[str, any]] = {
        "successful": [],
        "failed": [],
        "total_files": 0,
        "downloaded_files": 0,
    }

    # Prepare download tasks
    tasks = []
    for model_name, filenames in models.items():
        for filename in filenames:
            tasks.append((model_name, filename))

    results["total_files"] = len(tasks)
    logger.info(f"Downloading {len(tasks)} files from {len(models)} models...")

    # Download in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(download_file, model, file, output_dir): (model, file)
            for model, file in tasks
        }

        for future in as_completed(futures):
            model_name, filename, success, message = future.result()

            if success:
                results["downloaded_files"] += 1
                results["successful"].append(
                    {"model": model_name, "file": filename, "message": message},
                )
                logger.info(f"✓ {model_name}/{filename}")
            else:
                results["failed"].append(
                    {"model": model_name, "file": filename, "error": message},
                )
                logger.error(f"✗ {model_name}/{filename}: {message}")

    return results


def load_models_config(config_path: str) -> dict[str, list[str]]:
    """Load models configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def main():
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
        "--include-relevance",
        action="store_true",
        default=True,
        help="Include relevance models (microsoft/deberta-v2-xlarge-mnli)",
    )
    parser.add_argument(
        "--exclude-relevance",
        action="store_true",
        help="Exclude relevance models to reduce image size",
    )

    args = parser.parse_args()

    # Load models configuration
    if args.config:
        logger.info(f"Loading models configuration from: {args.config}")
        models = load_models_config(args.config)
    else:
        logger.info("Using default models configuration")
        models = DEFAULT_MODELS.copy()

    # Handle relevance models
    if args.exclude_relevance and "microsoft/deberta-v2-xlarge-mnli" in models:
        logger.info("Excluding relevance models (microsoft/deberta-v2-xlarge-mnli)")
        del models["microsoft/deberta-v2-xlarge-mnli"]

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {args.output_dir}")

    # Download models
    results = download_models(models, args.output_dir, args.workers)

    # Print summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Total files: {results['total_files']}")
    print(f"Downloaded:  {results['downloaded_files']}")
    print(f"Failed:      {len(results['failed'])}")
    print("=" * 60)

    if results["failed"]:
        print("\nFailed downloads:")
        for item in results["failed"]:
            print(f"  - {item['model']}/{item['file']}: {item['error']}")
        sys.exit(1)

    print("\n✓ All models downloaded successfully!")

    # Save manifest
    manifest_path = args.output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "models": list(models.keys()),
                "files": results["successful"],
            },
            f,
            indent=2,
        )
    logger.info(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
