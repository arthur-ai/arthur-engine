"""Tests for the CycloneDX AI-BOM generator.

All tests run fully offline (no HuggingFace network access): the generator is exercised
via ``build_bom`` with ``offline=True`` and a synthetic commit map, plus a temporary
``models-dir`` for local SHA-256 hashing.
"""

import hashlib
import json
from pathlib import Path

import generate_aibom as gen
from download_models import DEFAULT_MODELS

# Deterministic, git-SHA-shaped fake commits (40 hex chars) — one distinct per model.
FAKE_COMMITS = {
    model_id: hashlib.sha1(model_id.encode()).hexdigest() for model_id in DEFAULT_MODELS
}


def test_guardrail_roles_cover_all_bundled_models():
    """Every bundled model must have a documented guardrail role."""
    for model_id in DEFAULT_MODELS:
        assert model_id in gen.GUARDRAIL_ROLES, f"missing role for {model_id}"


def test_offline_bom_is_valid_cyclonedx():
    bom = gen.build_bom(
        models=DEFAULT_MODELS,
        manifest_commits=FAKE_COMMITS,
        engine_version="1.2.3",
        models_dir=None,
        offline=True,
        include_timestamp=False,
    )

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.6"
    assert bom["metadata"]["component"]["version"] == "1.2.3"
    assert "timestamp" not in bom["metadata"]

    ml = [c for c in bom["components"] if c["type"] == "machine-learning-model"]
    assert len(ml) == len(DEFAULT_MODELS)

    by_ref = {c["bom-ref"]: c for c in ml}
    for model_id in DEFAULT_MODELS:
        component = by_ref[model_id]
        group, _, name = model_id.partition("/")
        assert component["group"] == group
        assert component["name"] == name
        assert component["version"] == FAKE_COMMITS[model_id]
        assert (
            component["purl"] == f"pkg:huggingface/{model_id}@{FAKE_COMMITS[model_id]}"
        )
        assert (
            component["externalReferences"][0]["url"]
            == f"https://huggingface.co/{model_id}"
        )


def test_offline_omits_network_enrichment():
    """Offline with no models-dir: no license, task, or file hashes."""
    bom = gen.build_bom(
        models=DEFAULT_MODELS,
        manifest_commits=FAKE_COMMITS,
        engine_version="1.0",
        models_dir=None,
        offline=True,
        include_timestamp=False,
    )
    for component in bom["components"]:
        assert "licenses" not in component
        assert "hashes" not in component
        assert "modelCard" not in component


def test_timestamp_included_when_requested():
    bom = gen.build_bom(
        models=DEFAULT_MODELS,
        manifest_commits=FAKE_COMMITS,
        engine_version="1.0",
        models_dir=None,
        offline=True,
        include_timestamp=True,
    )
    assert bom["metadata"]["timestamp"].endswith("Z")


def test_local_file_hashes(tmp_path):
    """With a models-dir, per-file SHA-256 is computed and the primary weight hashed."""
    model_id = "s-nlp/roberta_toxicity_classifier"
    filenames = DEFAULT_MODELS[model_id]

    expected: dict[str, str] = {}
    for filename in filenames:
        file_path = tmp_path / model_id / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = f"content-of-{filename}".encode()
        file_path.write_bytes(content)
        expected[filename] = hashlib.sha256(content).hexdigest()

    bom = gen.build_bom(
        models={model_id: filenames},
        manifest_commits=FAKE_COMMITS,
        engine_version="1.0",
        models_dir=tmp_path,
        offline=True,  # stay offline; local hashing does not need the network
        include_timestamp=False,
    )

    component = bom["components"][0]
    properties = {p["name"]: p["value"] for p in component["properties"]}
    for filename, digest in expected.items():
        assert properties[f"arthur:file:{filename}:sha256"] == digest

    # Component-level hash is the primary weight file (pytorch_model.bin for RoBERTa).
    assert component["hashes"][0]["alg"] == "SHA-256"
    assert component["hashes"][0]["content"] == expected["pytorch_model.bin"]


def test_cli_writes_output(tmp_path, monkeypatch):
    output = tmp_path / "aibom.cdx.json"
    manifest = Path(gen.__file__).parent / "models-manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "generate_aibom.py",
            "--offline",
            "--no-timestamp",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )
    assert gen.main() == 0

    document = json.loads(output.read_text())
    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == "1.6"
    assert len(document["components"]) == len(DEFAULT_MODELS)
