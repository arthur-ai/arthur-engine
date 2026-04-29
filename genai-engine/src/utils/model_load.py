"""Slim model loader — relevance-only.

After the models-service extraction:
- prompt_injection / toxicity / profanity / GLiNER / Presidio / claim_filter
  loaders all moved to arthur-engine/models-service.
- bert-score and the relevance reranker (microsoft/deberta-v2-xlarge-mnli)
  stay here because the relevance metric uses scorer/llm_client and can't be
  cleanly extracted without that dependency moving too.

Keep this file lean. Anything not relevance-related belongs in the service.
"""

import os
from functools import wraps
from multiprocessing import get_context
from typing import Callable

# Disable tokenizer parallelism — avoids fork warnings under uvicorn workers.
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import requests
import torch
from bert_score import BERTScorer
from huggingface_hub import hf_hub_download
from huggingface_hub.constants import ENDPOINT as DEFAULT_HUGGINGFACE_CO_URL
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TextClassificationPipeline,
)

from custom_types import P, T
from utils import constants
from utils.classifiers import get_device
from utils.utils import (
    get_env_var,
    get_logger,
    relevance_models_enabled,
    skip_model_loading,
)

logger = get_logger(__name__)

__location__ = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODELS_DIR = os.path.join(__location__, "models")

# Kept for dependencies.py — still chooses PII v1 vs v2 client-side based on this.
USE_PII_MODEL_V2 = (
    get_env_var(constants.GENAI_ENGINE_USE_PII_MODEL_V2_ENV_VAR) == "true"
)

# ---------------------------------------------------------------------------
# Path resolution + downloader
# ---------------------------------------------------------------------------


def get_models_dir() -> str:
    models_dir = get_env_var(
        constants.MODEL_STORAGE_PATH_ENV_VAR,
        default=DEFAULT_MODELS_DIR,
    )
    return models_dir if models_dir is not None else DEFAULT_MODELS_DIR


def get_local_model_path(model_name: str) -> str:
    local_path = os.path.join(get_models_dir(), model_name)
    if os.path.exists(local_path):
        logger.info(f"Using local model from: {local_path}")
        return local_path
    logger.info(f"Local model not found at {local_path}, will use HuggingFace Hub")
    return model_name


def download_file_from_url(url: str, model_name: str, filename: str, local_dir: str) -> None:
    file_path = os.path.join(local_dir, filename)
    file_dir = os.path.dirname(file_path)
    if file_dir:
        os.makedirs(file_dir, exist_ok=True)
    download_url = f"{url}/{model_name}/{filename}"
    response = requests.get(download_url)
    response.raise_for_status()
    with open(file_path, "wb") as f:
        f.write(response.content)


def download_file(args: tuple[str, str]) -> None:
    model_name, filename = args
    model_repository_url = str(
        get_env_var(
            constants.MODEL_REPOSITORY_URL_ENV_VAR,
            default=DEFAULT_HUGGINGFACE_CO_URL,
        ),
    )
    local_model_dir = os.path.join(get_models_dir(), model_name)
    os.makedirs(local_model_dir, exist_ok=True)
    try:
        if model_repository_url == DEFAULT_HUGGINGFACE_CO_URL:
            hf_hub_download(repo_id=model_name, filename=filename, local_dir=local_model_dir)
        else:
            download_file_from_url(model_repository_url, model_name, filename, local_model_dir)
        logger.debug(f"Downloaded {filename} to {local_model_dir}")
    except Exception as e:
        logger.warning(f"Failed to download {filename} from {model_repository_url}/{model_name}: {e}")


def get_models_to_download() -> dict[str, list[str]]:
    """Only the relevance reranker remains — everything else moved to the
    models service. Gated on relevance_models_enabled()."""
    models_to_download: dict[str, list[str]] = {}
    if relevance_models_enabled():
        models_to_download["microsoft/deberta-v2-xlarge-mnli"] = [
            "config.json",
            "pytorch_model.bin",
            "spm.model",
            "tokenizer_config.json",
        ]
    else:
        logger.info("Skipping relevance models download — ENABLE_RELEVANCE_MODELS is False")
    return models_to_download


def download_models(num_of_process: int) -> None:
    if skip_model_loading():
        logger.info("Skipping model downloads — GENAI_ENGINE_SKIP_MODEL_LOADING is True")
        return
    models_to_download = get_models_to_download()
    if not models_to_download:
        return
    tasks = [
        (model_name, filename)
        for model_name, filenames in models_to_download.items()
        for filename in filenames
    ]
    logger.warning("Downloading models... this may take a while")
    with get_context("spawn").Pool(processes=num_of_process) as pool:
        pool.map(download_file, tasks)


# ---------------------------------------------------------------------------
# Loader decorator + relevance singletons
# ---------------------------------------------------------------------------

BERT_SCORER: BERTScorer | None = None
RELEVANCE_MODEL: AutoModelForSequenceClassification | None = None
RELEVANCE_TOKENIZER: AutoTokenizer | None = None
RELEVANCE_RERANKER: TextClassificationPipeline | None = None


def log_model_loading(
    model_name: str,
    global_var_name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if global_var_name and globals().get(global_var_name) is not None:
                logger.info(f"{model_name} already loaded.")
                return func(*args, **kwargs)
            logger.info(f"Loading {model_name}...")
            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ {model_name} loaded successfully")
                return result
            except Exception as e:
                logger.error(f"❌ Failed to load {model_name}: {e}")
                raise
        return wrapper
    return decorator


@log_model_loading("relevance model", "RELEVANCE_MODEL")
def get_relevance_model() -> AutoModelForSequenceClassification | None:
    if skip_model_loading():
        return None
    global RELEVANCE_MODEL
    if not RELEVANCE_MODEL:
        model_path = get_local_model_path("microsoft/deberta-v2-xlarge-mnli")
        RELEVANCE_MODEL = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            weights_only=False,
            torch_dtype=torch.float16,
        )
    return RELEVANCE_MODEL


@log_model_loading("relevance tokenizer", "RELEVANCE_TOKENIZER")
def get_relevance_tokenizer() -> AutoTokenizer | None:
    if skip_model_loading():
        return None
    global RELEVANCE_TOKENIZER
    if not RELEVANCE_TOKENIZER:
        model_path = get_local_model_path("microsoft/deberta-v2-xlarge-mnli")
        RELEVANCE_TOKENIZER = AutoTokenizer.from_pretrained(
            model_path,
            weights_only=False,
        )
    return RELEVANCE_TOKENIZER


@log_model_loading("BERT scorer model", "BERT_SCORER")
def get_bert_scorer() -> BERTScorer | None:
    if skip_model_loading():
        return None
    if not relevance_models_enabled():
        logger.info("BERT scorer disabled — ENABLE_RELEVANCE_MODELS is False")
        return None
    global BERT_SCORER
    if BERT_SCORER is None:
        model_path = get_local_model_path("microsoft/deberta-v2-xlarge-mnli")
        BERT_SCORER = BERTScorer(
            model_type=model_path,
            use_fast_tokenizer=True,
            num_layers=17,
        )
    return BERT_SCORER


@log_model_loading("relevance reranker pipeline", "RELEVANCE_RERANKER")
def get_relevance_reranker() -> TextClassificationPipeline | None:
    if skip_model_loading():
        return None
    if not relevance_models_enabled():
        logger.info("Relevance reranker disabled — ENABLE_RELEVANCE_MODELS is False")
        return None
    global RELEVANCE_RERANKER
    if RELEVANCE_RERANKER is None:
        model = get_relevance_model()
        tokenizer = get_relevance_tokenizer()
        if model is None or tokenizer is None:
            return None
        RELEVANCE_RERANKER = TextClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            device=torch.device(get_device()),
            torch_dtype=torch.float16,
        )
    return RELEVANCE_RERANKER
