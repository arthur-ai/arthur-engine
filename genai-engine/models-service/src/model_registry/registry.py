"""HuggingFace model registry.

Single source of truth for which HF repos we vendor and which files we pull
from each. The model→files map is migrated from
genai-engine/src/utils/model_load.py:get_models_to_download. Each entry pins
a specific revision so builds are reproducible — bump on intentional upgrades.

Consumers:
- scripts/download_models.py: build-time bake into the runtime image.
- src/model_registry/loader.py: runtime resolution from MODEL_STORAGE_PATH.

spaCy en_core_web_lg is NOT in this registry — it ships as a pip wheel
declared in pyproject.toml, not via HF Hub.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelEntry:
    """One HuggingFace repo we vendor into the image."""

    hf_repo: str
    files: tuple[str, ...]
    # Pinned commit hash or tag. None means "track main" (not for production).
    revision: str | None = None
    # Optional human label surfaced in /v1/models.
    name: str = field(default="")

    def __post_init__(self) -> None:
        # Default `name` to the repo's last segment if not provided.
        if not self.name:
            object.__setattr__(self, "name", self.hf_repo.split("/")[-1])


# Always downloaded ----------------------------------------------------------

CLAIM_CLASSIFIER_EMBEDDING = ModelEntry(
    name="claim_classifier_embedding",
    hf_repo="sentence-transformers/all-MiniLM-L12-v2",
    revision=None,  # TODO: pin before going to prod
    files=(
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
    ),
)

PROMPT_INJECTION = ModelEntry(
    name="prompt_injection",
    hf_repo="ProtectAI/deberta-v3-base-prompt-injection-v2",
    revision=None,
    files=(
        "added_tokens.json",
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "spm.model",
        "tokenizer_config.json",
        "tokenizer.json",
    ),
)

TOXICITY = ModelEntry(
    name="toxicity",
    hf_repo="s-nlp/roberta_toxicity_classifier",
    revision=None,
    files=(
        "config.json",
        "merges.txt",
        "pytorch_model.bin",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "vocab.json",
    ),
)

PROFANITY = ModelEntry(
    name="profanity",
    hf_repo="tarekziade/pardonmyai",
    revision=None,
    files=(
        "onnx/model.onnx",
        "onnx/model_quantized.onnx",
        "config.json",
        "model.safetensors",
        "quantize_config.json",
        "special_tokens_map.json",
        "tokenizer_config.json",
        "tokenizer.json",
        "vocab.txt",
    ),
)

# PII v2 only — engine sends use_v2=true to opt in --------------------------

GLINER_PII = ModelEntry(
    name="gliner_pii",
    hf_repo="urchade/gliner_multi_pii-v1",
    revision=None,
    files=(
        "gliner_config.json",
        "pytorch_model.bin",
    ),
)

GLINER_TOKENIZER_BACKEND = ModelEntry(
    name="gliner_tokenizer_backend",
    hf_repo="microsoft/mdeberta-v3-base",
    revision=None,
    files=(
        "config.json",
        "generator_config.json",
        "pytorch_model.bin",
        "pytorch_model.generator.bin",
        "spm.model",
        "tf_model.h5",
        "tokenizer_config.json",
    ),
)


ALL_MODELS: tuple[ModelEntry, ...] = (
    CLAIM_CLASSIFIER_EMBEDDING,
    PROMPT_INJECTION,
    TOXICITY,
    PROFANITY,
    GLINER_PII,
    GLINER_TOKENIZER_BACKEND,
)


def files_to_download() -> list[tuple[str, str, str | None]]:
    """Flatten ALL_MODELS into (repo, filename, revision) tuples for the
    downloader script's multiprocess pool."""
    return [
        (model.hf_repo, filename, model.revision)
        for model in ALL_MODELS
        for filename in model.files
    ]
