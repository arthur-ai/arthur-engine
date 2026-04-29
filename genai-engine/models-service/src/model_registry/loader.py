"""Singleton model loaders.

Migrated from genai-engine/src/utils/model_load.py, narrowed to the models
this service actually serves. Differences from the engine version:

1. No bert-score / relevance-reranker loaders — those stay in genai-engine
   because the relevance metric depends on scorer/llm_client.
2. No `USE_PII_MODEL_V2` env gate — the engine forwards `use_v2` per request,
   so both PII paths are warmed whenever the GLiNER weights are available.
3. Per-model status tracking for /v1/ready: each loader records its state
   (`loading`/`loaded`/`failed`) in MODEL_STATUS so callers can poll readiness
   without guessing from health alone.

Each `get_*` function is a process-level singleton: first call materializes
the model, subsequent calls return the cached instance. `warm_all()` is
called from server.py's lifespan to load everything at startup.
"""

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Literal

import torch
from gliner import GLiNER, GLiNERConfig
from presidio_analyzer import AnalyzerEngine
from sentence_transformers import SentenceTransformer
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TextClassificationPipeline,
    pipeline,
)
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

import config as svc_config
from inference.device import get_device
from model_registry.classifier_arch import Classifier, LogisticRegressionModel
from model_registry.registry import (
    CLAIM_CLASSIFIER_EMBEDDING,
    GLINER_PII,
    PROFANITY,
    PROMPT_INJECTION,
    TOXICITY,
)

# Disable tokenizer parallelism — avoids fork warnings under uvicorn workers.
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = logging.getLogger(__name__)

# Static asset paths live alongside the check that owns them, mirroring
# genai-engine's scorer/checks/<check>/ layout.
from inference.claim_filter.claim_classifier import WEIGHTS_PATH as CLAIM_CLASSIFIER_PTH
from inference.pii.gliner import CONFIG_PATH as GLINER_CONFIG_PATH


# ---------------------------------------------------------------------------
# Status tracking — surfaced via /v1/ready
# ---------------------------------------------------------------------------

ModelStatus = Literal["loaded", "loading", "failed"]
MODEL_STATUS: dict[str, ModelStatus] = {}
MODEL_LOADED_AT: dict[str, str] = {}
_status_lock = threading.Lock()


def _set_status(name: str, status: ModelStatus) -> None:
    with _status_lock:
        MODEL_STATUS[name] = status
        if status == "loaded":
            MODEL_LOADED_AT[name] = datetime.now(timezone.utc).isoformat()


def _resolve_path(hf_repo: str) -> str:
    """Look for baked weights under MODEL_STORAGE_PATH; fall back to the HF
    Hub repo id (which only resolves over the network — fine for local dev,
    blocked by HF_HUB_OFFLINE=1 in the Docker image)."""
    local = os.path.join(svc_config.MODEL_STORAGE_PATH, hf_repo)
    if os.path.exists(local):
        return local
    logger.info("Local weights for %s not found; will use HF Hub id", hf_repo)
    return hf_repo


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_CLAIM_EMBEDDING: SentenceTransformer | None = None
_CLAIM_CLASSIFIER: Classifier | None = None
_PROMPT_INJECTION_MODEL: PreTrainedModel | None = None
_PROMPT_INJECTION_TOKENIZER: PreTrainedTokenizerBase | None = None
_PROMPT_INJECTION_PIPELINE: TextClassificationPipeline | None = None
_TOXICITY_MODEL: AutoModelForSequenceClassification | None = None
_TOXICITY_TOKENIZER: PreTrainedTokenizerBase | None = None
_TOXICITY_PIPELINE: TextClassificationPipeline | None = None
_PROFANITY_PIPELINE: TextClassificationPipeline | None = None
_GLINER_TOKENIZER: PreTrainedTokenizerBase | None = None
_GLINER_MODEL: GLiNER | None = None
_PRESIDIO: AnalyzerEngine | None = None
_SPACY_DATE_NLP: Any = None  # spacy.Language; use Any to dodge circular type imports


# ---------------------------------------------------------------------------
# Claim classifier (sentence-transformers + local logreg .pth)
# ---------------------------------------------------------------------------


def get_claim_classifier_embedding_model() -> SentenceTransformer | None:
    global _CLAIM_EMBEDDING
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _CLAIM_EMBEDDING is None:
        name = CLAIM_CLASSIFIER_EMBEDDING.name
        _set_status(name, "loading")
        try:
            _CLAIM_EMBEDDING = SentenceTransformer(
                _resolve_path(CLAIM_CLASSIFIER_EMBEDDING.hf_repo),
                device=get_device(),
            )
            _set_status(name, "loaded")
        except Exception:
            _set_status(name, "failed")
            raise
    return _CLAIM_EMBEDDING


def get_claim_classifier() -> Classifier | None:
    """Compose the SentenceTransformer with the trained logreg head.

    The .pth file is shipped alongside this module — it's small (~1 MB) and
    not in the HF registry.
    """
    global _CLAIM_CLASSIFIER
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _CLAIM_CLASSIFIER is not None:
        return _CLAIM_CLASSIFIER

    embedding = get_claim_classifier_embedding_model()
    if embedding is None:
        return None

    _set_status("claim_classifier", "loading")
    try:
        with open(CLAIM_CLASSIFIER_PTH, "rb") as f:
            state_dict = torch.load(
                f,
                map_location=torch.device(get_device()),
                weights_only=False,
            )
        head = (
            LogisticRegressionModel(
                input_size=state_dict["linear.weight"].shape[1],
                num_classes=3,
            )
            .to(get_device())
            .to(torch.float64)
        )
        head.load_state_dict(state_dict)
        head.eval()

        # Label map mirrors ClaimClassifierResultEnum (lowercase values).
        _CLAIM_CLASSIFIER = Classifier(
            transformer_model=embedding,
            classifier=head,
            label_map={"claim": 0, "nonclaim": 1, "dialog": 2},
        )
        _set_status("claim_classifier", "loaded")
    except Exception:
        _set_status("claim_classifier", "failed")
        raise
    return _CLAIM_CLASSIFIER


# ---------------------------------------------------------------------------
# Prompt injection
# ---------------------------------------------------------------------------


def get_prompt_injection_model() -> PreTrainedModel | None:
    global _PROMPT_INJECTION_MODEL
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _PROMPT_INJECTION_MODEL is None:
        _PROMPT_INJECTION_MODEL = AutoModelForSequenceClassification.from_pretrained(
            _resolve_path(PROMPT_INJECTION.hf_repo),
            weights_only=False,
        )
    return _PROMPT_INJECTION_MODEL


def get_prompt_injection_tokenizer() -> PreTrainedTokenizerBase | None:
    global _PROMPT_INJECTION_TOKENIZER
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _PROMPT_INJECTION_TOKENIZER is None:
        _PROMPT_INJECTION_TOKENIZER = AutoTokenizer.from_pretrained(
            _resolve_path(PROMPT_INJECTION.hf_repo),
            weights_only=False,
        )
    return _PROMPT_INJECTION_TOKENIZER


def get_prompt_injection_classifier() -> TextClassificationPipeline | None:
    global _PROMPT_INJECTION_PIPELINE
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _PROMPT_INJECTION_PIPELINE is not None:
        return _PROMPT_INJECTION_PIPELINE

    name = PROMPT_INJECTION.name
    _set_status(name, "loading")
    try:
        model = get_prompt_injection_model()
        tokenizer = get_prompt_injection_tokenizer()
        if model is None or tokenizer is None:
            _set_status(name, "failed")
            return None
        _PROMPT_INJECTION_PIPELINE = TextClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            max_length=512,
            truncation=True,
            device=torch.device(get_device()),
        )
        _set_status(name, "loaded")
    except Exception:
        _set_status(name, "failed")
        raise
    return _PROMPT_INJECTION_PIPELINE


# ---------------------------------------------------------------------------
# Toxicity
# ---------------------------------------------------------------------------


def get_toxicity_model() -> AutoModelForSequenceClassification | None:
    global _TOXICITY_MODEL
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _TOXICITY_MODEL is None:
        _TOXICITY_MODEL = AutoModelForSequenceClassification.from_pretrained(
            _resolve_path(TOXICITY.hf_repo),
            weights_only=False,
        )
    return _TOXICITY_MODEL


def get_toxicity_tokenizer() -> PreTrainedTokenizerBase | None:
    global _TOXICITY_TOKENIZER
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _TOXICITY_TOKENIZER is None:
        _TOXICITY_TOKENIZER = AutoTokenizer.from_pretrained(
            _resolve_path(TOXICITY.hf_repo),
            weights_only=False,
            model_max_length=None,
        )
    return _TOXICITY_TOKENIZER


def get_toxicity_classifier() -> TextClassificationPipeline | None:
    global _TOXICITY_PIPELINE
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _TOXICITY_PIPELINE is not None:
        return _TOXICITY_PIPELINE

    name = TOXICITY.name
    _set_status(name, "loading")
    try:
        model = get_toxicity_model()
        tokenizer = get_toxicity_tokenizer()
        if model is None or tokenizer is None:
            _set_status(name, "failed")
            return None
        _TOXICITY_PIPELINE = pipeline(
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            top_k=99999,
            truncation=True,
            max_length=512,
            device=torch.device(get_device()),
        )
        _set_status(name, "loaded")
    except Exception:
        _set_status(name, "failed")
        raise
    return _TOXICITY_PIPELINE


def get_profanity_classifier() -> TextClassificationPipeline | None:
    global _PROFANITY_PIPELINE
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _PROFANITY_PIPELINE is not None:
        return _PROFANITY_PIPELINE

    name = PROFANITY.name
    _set_status(name, "loading")
    try:
        _PROFANITY_PIPELINE = pipeline(
            "text-classification",
            model=_resolve_path(PROFANITY.hf_repo),
            top_k=99999,
            truncation=True,
            max_length=512,
            device=torch.device(get_device()),
        )
        _set_status(name, "loaded")
    except Exception:
        _set_status(name, "failed")
        raise
    return _PROFANITY_PIPELINE


# ---------------------------------------------------------------------------
# PII — GLiNER + Presidio + spaCy
# ---------------------------------------------------------------------------


def get_gliner_tokenizer() -> PreTrainedTokenizerBase | None:
    global _GLINER_TOKENIZER
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _GLINER_TOKENIZER is None:
        config = GLiNERConfig.from_json_file(GLINER_CONFIG_PATH)
        _GLINER_TOKENIZER = AutoTokenizer.from_pretrained(_resolve_path(config.model_name))
    return _GLINER_TOKENIZER


def get_gliner_model() -> GLiNER | None:
    global _GLINER_MODEL
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _GLINER_MODEL is not None:
        return _GLINER_MODEL

    name = GLINER_PII.name
    _set_status(name, "loading")
    try:
        model_path = _resolve_path(GLINER_PII.hf_repo)
        # Only force local-only when the path actually resolved to disk.
        local_files_only = os.path.exists(model_path) and model_path != GLINER_PII.hf_repo
        _GLINER_MODEL = GLiNER.from_pretrained(
            model_path,
            config=GLiNERConfig.from_json_file(GLINER_CONFIG_PATH),
            tokenizer=get_gliner_tokenizer(),
            load_tokenizer=False,
            local_files_only=local_files_only,
        ).to(get_device())
        _GLINER_MODEL.eval()
        _set_status(name, "loaded")
    except Exception:
        _set_status(name, "failed")
        raise
    return _GLINER_MODEL


def get_presidio_analyzer() -> AnalyzerEngine | None:
    global _PRESIDIO
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _PRESIDIO is not None:
        return _PRESIDIO

    _set_status("presidio", "loading")
    try:
        _PRESIDIO = AnalyzerEngine()
        _set_status("presidio", "loaded")
    except Exception:
        _set_status("presidio", "failed")
        raise
    return _PRESIDIO


def get_spacy_date_nlp() -> Any:
    """spaCy en_core_web_lg pipeline with date_spacy registered. Used by PII v2.

    en_core_web_lg ships as a pip package (see pyproject.toml), so it doesn't
    go through the HF registry. Importing date_spacy registers `find_dates`
    as a spaCy component name.
    """
    global _SPACY_DATE_NLP
    if svc_config.SKIP_MODEL_LOADING:
        return None
    if _SPACY_DATE_NLP is not None:
        return _SPACY_DATE_NLP

    _set_status("spacy_date_nlp", "loading")
    try:
        import spacy
        import date_spacy  # noqa: F401 — registers the find_dates component

        # Exclude NER to avoid entity-type conflicts with date_spacy.
        nlp = spacy.load("en_core_web_lg", exclude=["ner"])
        nlp.add_pipe("find_dates")
        _SPACY_DATE_NLP = nlp
        _set_status("spacy_date_nlp", "loaded")
    except Exception:
        _set_status("spacy_date_nlp", "failed")
        raise
    return _SPACY_DATE_NLP


# ---------------------------------------------------------------------------
# Lifespan helpers
# ---------------------------------------------------------------------------


def warm_all() -> None:
    """Eager-load every model. Called from server.py lifespan so the first
    request is fast. Failures are logged but don't crash startup — /v1/ready
    surfaces the failure status to callers."""
    loaders = (
        ("claim_classifier_embedding", get_claim_classifier_embedding_model),
        ("claim_classifier", get_claim_classifier),
        ("prompt_injection", get_prompt_injection_classifier),
        ("toxicity", get_toxicity_classifier),
        ("profanity", get_profanity_classifier),
        ("gliner_pii", get_gliner_model),
        ("presidio", get_presidio_analyzer),
        ("spacy_date_nlp", get_spacy_date_nlp),
    )
    for name, loader in loaders:
        try:
            loader()
        except Exception as e:
            logger.exception("Failed to warm %s: %s", name, e)


def all_loaded() -> bool:
    with _status_lock:
        return bool(MODEL_STATUS) and all(s == "loaded" for s in MODEL_STATUS.values())


def status_snapshot() -> dict[str, ModelStatus]:
    with _status_lock:
        return dict(MODEL_STATUS)


def loaded_at_snapshot() -> dict[str, str]:
    with _status_lock:
        return dict(MODEL_LOADED_AT)
