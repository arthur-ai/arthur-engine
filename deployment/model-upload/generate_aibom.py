#!/usr/bin/env python3
"""
Generate a CycloneDX 1.6 AI Bill of Materials (AI-BOM) for Arthur's bundled models.

Arthur GenAI Engine ships a fixed set of HuggingFace guardrail and embedding models
(prompt-injection, toxicity, profanity, PII, relevance/NLI, claim-classifier embedding).
The container SBOM (Trivy) documents OS and Python packages but not these model weights;
this script produces the missing bill of materials for the models themselves.

Each model becomes a CycloneDX ``machine-learning-model`` component carrying its
HuggingFace commit SHA (pinned version), package URL, license, task, and SHA-256 file
hashes. The list of models is reused from ``download_models.DEFAULT_MODELS`` and the pinned
commit SHAs from ``models-manifest.json`` (produced by ``check_model_updates.py``), so this
script never re-hardcodes the model set.

Hash sources, in order of preference:
  * ``--models-dir`` present: SHA-256 computed locally from the downloaded files (the exact
    bytes that ship in the image).
  * otherwise, online: SHA-256 pulled from HuggingFace LFS metadata (no weight download).
  * ``--offline`` with no ``--models-dir``: identity + commit SHA only, no hashes.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from download_models import DEFAULT_MODELS

# Log to stderr so stdout stays clean for the emitted BOM / CI consumption.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

CYCLONEDX_SPEC_VERSION = "1.6"
HF_BASE_URL = "https://huggingface.co"
GENERATOR_NAME = "arthur-generate-aibom"
GENERATOR_VERSION = "1.0.0"

# Preferred primary weight file per model, used for the component-level ``hashes`` entry.
# All files still get a per-file SHA-256 recorded in ``properties``.
_PRIMARY_WEIGHT_CANDIDATES = (
    "model.safetensors",
    "pytorch_model.bin",
    "onnx/model.onnx",
)


@dataclass(frozen=True)
class GuardrailRole:
    """Human-readable purpose of a bundled model within Arthur's guardrails."""

    purpose: str
    description: str


# The one piece of new, hand-maintained knowledge: what each bundled model is for.
GUARDRAIL_ROLES: dict[str, GuardrailRole] = {
    "sentence-transformers/all-MiniLM-L12-v2": GuardrailRole(
        "claim-embedding",
        "Sentence-embedding model used for claim extraction in hallucination detection.",
    ),
    "ProtectAI/deberta-v3-base-prompt-injection-v2": GuardrailRole(
        "prompt-injection",
        "DeBERTa-v3 classifier used for prompt-injection detection.",
    ),
    "s-nlp/roberta_toxicity_classifier": GuardrailRole(
        "toxicity",
        "RoBERTa classifier used for toxicity detection.",
    ),
    "tarekziade/pardonmyai": GuardrailRole(
        "profanity",
        "ONNX-quantized classifier used for profanity detection.",
    ),
    "microsoft/deberta-v2-xlarge-mnli": GuardrailRole(
        "relevance-nli",
        "DeBERTa-v2 NLI model used for response-relevance scoring (optional).",
    ),
    "urchade/gliner_multi_pii-v1": GuardrailRole(
        "pii",
        "GLiNER NER model used for PII detection.",
    ),
    "microsoft/mdeberta-v3-base": GuardrailRole(
        "pii-base-encoder",
        "Base encoder for the GLiNER PII model.",
    ),
}


@dataclass
class ModelMetadata:
    """Enrichment pulled from HuggingFace (or empty when offline)."""

    commit_sha: str = ""
    license: str | None = None
    task: str | None = None
    # filename -> sha256 hex digest
    file_hashes: dict[str, str] | None = None


def load_manifest_commits(manifest_path: Path) -> dict[str, str]:
    """Return the ``model_commits`` map from ``models-manifest.json`` (or empty)."""
    if not manifest_path.exists():
        logger.warning(
            "Manifest not found at %s; commit SHAs will be blank",
            manifest_path,
        )
        return {}
    with open(manifest_path) as f:
        manifest = json.load(f)
    commits = manifest.get("model_commits", {})
    if not isinstance(commits, dict):
        logger.warning("Manifest %s has no valid model_commits map", manifest_path)
        return {}
    return {str(k): str(v) for k, v in commits.items()}


def compute_local_hashes(
    models_dir: Path,
    model_id: str,
    filenames: list[str],
) -> dict[str, str]:
    """Compute SHA-256 for each downloaded model file present under ``models_dir``."""
    hashes: dict[str, str] = {}
    for filename in filenames:
        file_path = models_dir / model_id / filename
        if not file_path.is_file():
            logger.warning("Missing file for local hashing: %s", file_path)
            continue
        digest = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        hashes[filename] = digest.hexdigest()
    return hashes


def fetch_hf_metadata(model_id: str, want_hashes: bool) -> ModelMetadata:
    """Fetch commit SHA, license, task and LFS SHA-256 hashes from HuggingFace."""
    from huggingface_hub import HfApi

    api = HfApi()
    meta = ModelMetadata()
    try:
        info = api.model_info(model_id, files_metadata=want_hashes)
    except Exception as e:  # network / auth / not-found — degrade gracefully
        logger.warning("Could not fetch HuggingFace metadata for %s: %s", model_id, e)
        return meta

    meta.commit_sha = getattr(info, "sha", "") or ""
    meta.task = getattr(info, "pipeline_tag", None)

    card_data = getattr(info, "card_data", None) or getattr(info, "cardData", None)
    if card_data is not None:
        meta.license = getattr(card_data, "license", None)
        if meta.license is None and isinstance(card_data, dict):
            meta.license = card_data.get("license")

    if want_hashes:
        file_hashes: dict[str, str] = {}
        for sibling in getattr(info, "siblings", None) or []:
            lfs = getattr(sibling, "lfs", None)
            sha256 = getattr(lfs, "sha256", None) if lfs is not None else None
            if sha256:
                file_hashes[sibling.rfilename] = sha256
        meta.file_hashes = file_hashes
    return meta


def _pick_primary_hash(
    filenames: list[str],
    file_hashes: dict[str, str],
) -> str | None:
    """Return the SHA-256 of the primary weight file, if we have it."""
    for candidate in _PRIMARY_WEIGHT_CANDIDATES:
        if candidate in file_hashes:
            return file_hashes[candidate]
    # Fall back to any hash we do have, preferring a bundled file.
    for filename in filenames:
        if filename in file_hashes:
            return file_hashes[filename]
    return None


def build_component(
    model_id: str,
    filenames: list[str],
    metadata: ModelMetadata,
) -> dict[str, Any]:
    """Build a single CycloneDX ``machine-learning-model`` component."""
    group, _, name = model_id.partition("/")
    role = GUARDRAIL_ROLES.get(model_id)
    file_hashes = metadata.file_hashes or {}

    component: dict[str, Any] = {
        "type": "machine-learning-model",
        "bom-ref": model_id,
        "group": group,
        "name": name,
        "publisher": group,
        "externalReferences": [
            {"type": "distribution", "url": f"{HF_BASE_URL}/{model_id}"},
        ],
    }

    if metadata.commit_sha:
        component["version"] = metadata.commit_sha
        component["purl"] = f"pkg:huggingface/{model_id}@{metadata.commit_sha}"
    else:
        component["purl"] = f"pkg:huggingface/{model_id}"

    if role is not None:
        component["description"] = role.description

    primary_hash = _pick_primary_hash(filenames, file_hashes)
    if primary_hash:
        component["hashes"] = [{"alg": "SHA-256", "content": primary_hash}]

    if metadata.license:
        component["licenses"] = [{"license": {"name": metadata.license}}]

    if metadata.task:
        component["modelCard"] = {"modelParameters": {"task": metadata.task}}

    # Properties: guardrail role + per-file SHA-256 for full provenance.
    properties: list[dict[str, str]] = []
    if role is not None:
        properties.append({"name": "arthur:guardrail:purpose", "value": role.purpose})
    for filename in filenames:
        properties.append({"name": f"arthur:file:{filename}", "value": "bundled"})
        if filename in file_hashes:
            properties.append(
                {
                    "name": f"arthur:file:{filename}:sha256",
                    "value": file_hashes[filename],
                },
            )
    component["properties"] = properties
    return component


def build_bom(
    models: dict[str, list[str]],
    manifest_commits: dict[str, str],
    engine_version: str | None,
    models_dir: Path | None,
    offline: bool,
    include_timestamp: bool,
) -> dict[str, Any]:
    """Assemble the full CycloneDX 1.6 AI-BOM document."""
    components: list[dict[str, Any]] = []
    for model_id in sorted(models):
        filenames = sorted(models[model_id])
        metadata = ModelMetadata(commit_sha=manifest_commits.get(model_id, ""))

        # Local hashes are authoritative for the bytes that ship.
        if models_dir is not None:
            metadata.file_hashes = compute_local_hashes(models_dir, model_id, filenames)

        if not offline:
            want_hashes = models_dir is None
            hf_meta = fetch_hf_metadata(model_id, want_hashes=want_hashes)
            if not metadata.commit_sha:
                metadata.commit_sha = hf_meta.commit_sha
            metadata.license = hf_meta.license
            metadata.task = hf_meta.task
            if metadata.file_hashes is None:
                metadata.file_hashes = hf_meta.file_hashes

        if not metadata.commit_sha:
            logger.warning("No commit SHA for %s; version will be omitted", model_id)

        components.append(build_component(model_id, filenames, metadata))

    component_block: dict[str, Any] = {
        "type": "application",
        "bom-ref": "arthur-genai-engine-models",
        "name": "arthur-genai-engine-models",
    }
    # None for the committed catalog copy: it documents the bundled models, which do not
    # change with the engine version, so stamping it made the file churn every release.
    if engine_version is not None:
        component_block["version"] = engine_version

    metadata_block: dict[str, Any] = {
        "component": component_block,
        "tools": {
            "components": [
                {
                    "type": "application",
                    "name": GENERATOR_NAME,
                    "version": GENERATOR_VERSION,
                },
            ],
        },
    }
    if include_timestamp:
        metadata_block["timestamp"] = (
            datetime.datetime.now(datetime.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "version": 1,
        "metadata": metadata_block,
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a CycloneDX AI-BOM for Arthur's bundled models",
    )
    parser.add_argument(
        "--manifest",
        "-m",
        type=Path,
        default=Path(__file__).parent / "models-manifest.json",
        help="Path to models-manifest.json (source of pinned commit SHAs)",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=None,
        help="Directory of downloaded models; enables local SHA-256 hashing",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("aibom.cdx.json"),
        help="Output path for the CycloneDX AI-BOM (default: aibom.cdx.json)",
    )
    parser.add_argument(
        "--engine-version",
        default=os.environ.get("VERSION", "unknown"),
        help="Version stamped into metadata.component (default: $VERSION or 'unknown')",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip all HuggingFace network calls (no license/task/LFS-hash enrichment)",
    )
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Omit metadata.timestamp for stable, diff-friendly committed output",
    )
    parser.add_argument(
        "--no-engine-version",
        action="store_true",
        help=(
            "Omit metadata.component.version for stable, diff-friendly committed "
            "output. Note that --engine-version defaults to $VERSION, so this flag "
            "is the only way to suppress the stamp in CI"
        ),
    )
    args = parser.parse_args()

    manifest_commits = load_manifest_commits(args.manifest)

    if args.models_dir is not None and not args.models_dir.is_dir():
        logger.error("Models directory does not exist: %s", args.models_dir)
        return 1

    logger.info(
        "Generating AI-BOM for %d models (offline=%s, local-hashes=%s)",
        len(DEFAULT_MODELS),
        args.offline,
        args.models_dir is not None,
    )
    bom = build_bom(
        models=DEFAULT_MODELS,
        manifest_commits=manifest_commits,
        engine_version=None if args.no_engine_version else args.engine_version,
        models_dir=args.models_dir,
        offline=args.offline,
        include_timestamp=not args.no_timestamp,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(bom, f, indent=2, sort_keys=False)
        f.write("\n")
    logger.info(
        "AI-BOM written to %s (%d components)",
        args.output,
        len(bom["components"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
