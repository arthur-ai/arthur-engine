import os
from functools import wraps
from multiprocessing import get_context
from typing import Callable

# Disable tokenizers parallelism to avoid fork warnings in threaded environments
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import requests
import torch
from bert_score import BERTScorer
from gliner import GLiNER, GLiNERConfig
from huggingface_hub import hf_hub_download
from huggingface_hub.constants import ENDPOINT as DEFAULT_HUGGINGFACE_CO_URL
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

# Default local directory for storing downloaded models
DEFAULT_MODELS_DIR = os.path.join(__location__, "models")

GLINER_CONFIG_PATH = os.path.join(
    __location__,
    "../scorer/checks/pii/gliner/gliner_tokenizer_config.json",
)

USE_PII_MODEL_V2 = (
    get_env_var(constants.GENAI_ENGINE_USE_PII_MODEL_V2_ENV_VAR) == "true"
)


def get_models_dir() -> str:
    """Get the directory where models are stored.

    Uses MODEL_STORAGE_PATH env var if set, otherwise defaults to ./models
    """
    models_dir = get_env_var(
        constants.MODEL_STORAGE_PATH_ENV_VAR,
        default=DEFAULT_MODELS_DIR,
    )
    return models_dir if models_dir is not None else DEFAULT_MODELS_DIR


def get_local_model_path(model_name: str) -> str:
    """Get the local filesystem path for a model.

    Args:
        model_name: The model identifier (e.g., "sentence-transformers/all-MiniLM-L12-v2")

    Returns:
        The local path where the model is stored
    """
    models_dir = get_models_dir()
    local_path = os.path.join(models_dir, model_name)

    if os.path.exists(local_path):
        logger.info(f"Using local model from: {local_path}")
        return local_path

    # Fall back to the model name for HuggingFace Hub
    logger.info(f"Local model not found at {local_path}, will use HuggingFace Hub")
    return model_name


CLAIM_CLASSIFIER_EMBEDDING_MODEL = None
PROMPT_INJECTION_MODEL: PreTrainedModel | None = None
PROMPT_INJECTION_TOKENIZER: PreTrainedTokenizerBase | None = None
PROMPT_INJECTION_CLASSIFIER: TextClassificationPipeline | None = None
TOXICITY_MODEL: AutoModelForSequenceClassification | None = None
TOXICITY_TOKENIZER: PreTrainedTokenizerBase | None = None
RELEVANCE_MODEL: AutoModelForSequenceClassification | None = None
RELEVANCE_TOKENIZER: AutoTokenizer | None = None
TOXICITY_CLASSIFIER: TextClassificationPipeline | None = None
PROFANITY_CLASSIFIER = None
BERT_SCORER: BERTScorer | None = None
RELEVANCE_RERANKER: TextClassificationPipeline | None = None
PII_GLINER_MODEL = None
PII_GLINER_TOKENIZER: PreTrainedTokenizerBase | None = None
PII_PRESIDIO_ANALYZER = None


def log_model_loading(
    model_name: str,
    global_var_name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add logging around model loading functions"""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check if model is already loaded
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


def download_file_from_url(
    url: str,
    model_name: str,
    filename: str,
    local_dir: str,
) -> None:
    """Download a file from a custom URL to a local directory."""
    # Create subdirectories if needed (e.g., for "1_Pooling/config.json")
    file_path = os.path.join(local_dir, filename)
    file_dir = os.path.dirname(file_path)
    if file_dir:
        os.makedirs(file_dir, exist_ok=True)

    # Construct URL: {base_url}/{model_name}/{filename}
    download_url = f"{url}/{model_name}/{filename}"
    response = requests.get(download_url)
    response.raise_for_status()
    with open(file_path, "wb") as f:
        f.write(response.content)


def download_file(args: tuple[str, str]) -> None:
    """Download a single model file."""
    model_name, filename = args
    model_repository_url = str(
        get_env_var(
            constants.MODEL_REPOSITORY_URL_ENV_VAR,
            default=DEFAULT_HUGGINGFACE_CO_URL,
        ),
    )
    models_dir = get_models_dir()
    local_model_dir = os.path.join(models_dir, model_name)

    # Ensure the model directory exists
    os.makedirs(local_model_dir, exist_ok=True)

    try:
        if model_repository_url == DEFAULT_HUGGINGFACE_CO_URL:
            hf_hub_download(
                repo_id=model_name,
                filename=filename,
                local_dir=local_model_dir,
            )
        else:
            download_file_from_url(
                url=model_repository_url,
                model_name=model_name,
                filename=filename,
                local_dir=local_model_dir,
            )
        logger.debug(
            f"Downloaded {filename} to {local_model_dir} from {model_repository_url}",
        )
    except Exception as e:
        logger.warning(
            f"Failed to download {filename} from {model_repository_url}/{model_name}: {e}",
        )


def get_models_to_download() -> dict[str, list[str]]:
    models_to_download = {
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
        "tarekziade/pardonmyai": [
            "onnx/model.onnx",
            "onnx/model_quantized.onnx",
            "config.json",
            "model.safetensors",
            "quantize_config.json",
            "special_tokens_map.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "vocab.txt",
        ],
    }
    if relevance_models_enabled():
        models_to_download["microsoft/deberta-v2-xlarge-mnli"] = [
            "config.json",
            "pytorch_model.bin",
            "spm.model",
            "tokenizer_config.json",
        ]
    else:
        logger.info(
            "Skipping relevance models download - ENABLE_RELEVANCE_MODELS is False",
        )
    if USE_PII_MODEL_V2:
        models_to_download["urchade/gliner_multi_pii-v1"] = [
            "gliner_config.json",
            "pytorch_model.bin",
        ]
        models_to_download["microsoft/mdeberta-v3-base"] = [
            "config.json",
            "generator_config.json",
            "pytorch_model.bin",
            "pytorch_model.generator.bin",
            "spm.model",
            "tf_model.h5",
            "tokenizer_config.json",
        ]
    return models_to_download


def download_models(num_of_process: int) -> None:
    if skip_model_loading():
        logger.info(
            "Skipping model downloads - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return
    models_to_download = get_models_to_download()
    tasks = [
        (model_name, filename)
        for model_name, filenames in models_to_download.items()
        for filename in filenames
    ]
    # Use initializer to set up logging in spawned processes
    logger.warning("Downloading models... this may take a while")
    with get_context("spawn").Pool(
        processes=num_of_process,
    ) as pool:
        pool.map(download_file, tasks)


@log_model_loading(
    "claim classifier embedding model",
    "CLAIM_CLASSIFIER_EMBEDDING_MODEL",
)
def get_claim_classifier_embedding_model() -> SentenceTransformer | None:
    if skip_model_loading():
        logger.info(
            "Skipping claim classifier embedding model - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global CLAIM_CLASSIFIER_EMBEDDING_MODEL
    if not CLAIM_CLASSIFIER_EMBEDDING_MODEL:
        model_path = get_local_model_path("sentence-transformers/all-MiniLM-L12-v2")
        CLAIM_CLASSIFIER_EMBEDDING_MODEL = SentenceTransformer(model_path)
    return CLAIM_CLASSIFIER_EMBEDDING_MODEL


@log_model_loading("prompt injection model", "PROMPT_INJECTION_MODEL")
def get_prompt_injection_model() -> PreTrainedModel | None:
    if skip_model_loading():
        logger.info(
            "Skipping prompt injection model - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global PROMPT_INJECTION_MODEL
    if PROMPT_INJECTION_MODEL is None:
        model_path = get_local_model_path(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
        )
        PROMPT_INJECTION_MODEL = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            weights_only=False,
        )
    return PROMPT_INJECTION_MODEL


@log_model_loading("prompt injection tokenizer", "PROMPT_INJECTION_TOKENIZER")
def get_prompt_injection_tokenizer() -> PreTrainedTokenizerBase | None:
    if skip_model_loading():
        logger.info(
            "Skipping prompt injection tokenizer - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global PROMPT_INJECTION_TOKENIZER
    if PROMPT_INJECTION_TOKENIZER is None:
        model_path = get_local_model_path(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
        )
        PROMPT_INJECTION_TOKENIZER = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            model_path,
            weights_only=False,
        )
    return PROMPT_INJECTION_TOKENIZER


@log_model_loading("prompt injection classifier", "PROMPT_INJECTION_CLASSIFIER")
def get_prompt_injection_classifier(
    model: PreTrainedModel | None,
    tokenizer: PreTrainedTokenizerBase | None,
) -> TextClassificationPipeline | None:
    """Loads in the prompt injection binary classifier"""
    if model is None:
        model = get_prompt_injection_model()
    if tokenizer is None:
        tokenizer = get_prompt_injection_tokenizer()

    # If model loading is skipped, both model and tokenizer will be None
    if model is None or tokenizer is None:
        return None

    global PROMPT_INJECTION_CLASSIFIER
    if PROMPT_INJECTION_CLASSIFIER is None:
        PROMPT_INJECTION_CLASSIFIER = TextClassificationPipeline(  # type: ignore[no-untyped-call]
            model=model,
            tokenizer=tokenizer,
            max_length=512,
            truncation=True,
            device=torch.device(get_device()),
        )
    return PROMPT_INJECTION_CLASSIFIER


@log_model_loading("toxicity model", "TOXICITY_MODEL")
def get_toxicity_model() -> AutoModelForSequenceClassification | None:
    if skip_model_loading():
        logger.info(
            "Skipping toxicity model - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global TOXICITY_MODEL
    if not TOXICITY_MODEL:
        model_path = get_local_model_path("s-nlp/roberta_toxicity_classifier")
        TOXICITY_MODEL = AutoModelForSequenceClassification.from_pretrained(
            model_path,
            weights_only=False,
        )
    return TOXICITY_MODEL


@log_model_loading("toxicity tokenizer", "TOXICITY_TOKENIZER")
def get_toxicity_tokenizer() -> PreTrainedTokenizerBase | None:
    if skip_model_loading():
        logger.info(
            "Skipping toxicity tokenizer - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global TOXICITY_TOKENIZER
    if not TOXICITY_TOKENIZER:
        model_path = get_local_model_path("s-nlp/roberta_toxicity_classifier")
        TOXICITY_TOKENIZER = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            model_path,
            weights_only=False,
            model_max_length=None,
        )
    return TOXICITY_TOKENIZER


@log_model_loading("toxicity classifier pipeline", "TOXICITY_CLASSIFIER")
def get_toxicity_classifier(
    model: AutoModelForSequenceClassification | None,
    tokenizer: PreTrainedTokenizerBase | None,
) -> TextClassificationPipeline | None:
    if not model:
        model = get_toxicity_model()
    if not tokenizer:
        tokenizer = get_toxicity_tokenizer()

    # If model loading is skipped, both model and tokenizer will be None
    if model is None or tokenizer is None:
        return None

    global TOXICITY_CLASSIFIER
    if TOXICITY_CLASSIFIER is None:
        TOXICITY_CLASSIFIER = pipeline(  # type: ignore[call-overload]
            "text-classification",
            model=model,
            tokenizer=tokenizer,
            top_k=99999,
            truncation=True,
            max_length=512,
            device=torch.device(get_device()),
        )
    return TOXICITY_CLASSIFIER


@log_model_loading("profanity classifier", "PROFANITY_CLASSIFIER")
def get_profanity_classifier() -> TextClassificationPipeline | None:
    if skip_model_loading():
        logger.info(
            "Skipping profanity classifier - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global PROFANITY_CLASSIFIER
    if PROFANITY_CLASSIFIER is None:
        model_path = get_local_model_path("tarekziade/pardonmyai")
        PROFANITY_CLASSIFIER = pipeline(
            "text-classification",
            model=model_path,
            top_k=99999,
            truncation=True,
            max_length=512,
            device=torch.device(get_device()),
        )
    return PROFANITY_CLASSIFIER


def get_harmful_request_classifier(
    model: PreTrainedModel | None,
    tokenizer: PreTrainedTokenizerBase | None,
) -> None:
    if not model or not tokenizer:
        return None


@log_model_loading("relevance model", "RELEVANCE_MODEL")
def get_relevance_model() -> AutoModelForSequenceClassification | None:
    if skip_model_loading():
        logger.info(
            "Skipping relevance model - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
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
        logger.info(
            "Skipping relevance tokenizer - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global RELEVANCE_TOKENIZER
    if not RELEVANCE_TOKENIZER:
        model_path = get_local_model_path("microsoft/deberta-v2-xlarge-mnli")
        RELEVANCE_TOKENIZER = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            model_path,
            weights_only=False,
        )
    return RELEVANCE_TOKENIZER


@log_model_loading("BERT scorer model", "BERT_SCORER")
def get_bert_scorer() -> BERTScorer | None:
    """Get or create a shared BERT scorer instance for relevance metrics"""
    if skip_model_loading():
        logger.info(
            "Skipping BERT scorer - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None

    global BERT_SCORER

    # Check if relevance models are enabled
    if not relevance_models_enabled():
        logger.info("BERT scorer disabled - ENABLE_RELEVANCE_MODELS is False")
        return None

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
    """Get or create a shared relevance reranker pipeline instance"""
    if skip_model_loading():
        logger.info(
            "Skipping relevance reranker - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None

    global RELEVANCE_RERANKER

    # Check if relevance models are enabled
    if not relevance_models_enabled():
        logger.info("Relevance reranker disabled - ENABLE_RELEVANCE_MODELS is False")
        return None

    if RELEVANCE_RERANKER is None:

        model = get_relevance_model()
        tokenizer = get_relevance_tokenizer()

        # If model loading is skipped, both model and tokenizer will be None
        if model is None or tokenizer is None:
            return None

        RELEVANCE_RERANKER = TextClassificationPipeline(  # type: ignore[no-untyped-call]
            model=model,
            tokenizer=tokenizer,
            device=torch.device(get_device()),
            torch_dtype=torch.float16,
        )
    return RELEVANCE_RERANKER


@log_model_loading("gliner tokenizer")
def get_gliner_tokenizer() -> PreTrainedTokenizerBase | None:
    if skip_model_loading():
        logger.info(
            "Skipping gliner tokenizer - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None

    global PII_GLINER_TOKENIZER

    # Check if Gliner is enabled
    if not USE_PII_MODEL_V2:
        logger.info("Gliner disabled - GENAI_ENGINE_USE_PII_MODEL_V2 is false")
        return None

    if USE_PII_MODEL_V2 and PII_GLINER_TOKENIZER is None:
        config = GLiNERConfig.from_json_file(GLINER_CONFIG_PATH)
        # Resolve model_name to local path (e.g., "microsoft/mdeberta-v3-base" -> local path)
        tokenizer_model_path = get_local_model_path(config.model_name)
        logger.info(
            f"Using local tokenizer from: {tokenizer_model_path} instead of {config.model_name}",
        )
        PII_GLINER_TOKENIZER = AutoTokenizer.from_pretrained(  # type: ignore[no-untyped-call]
            tokenizer_model_path,
        )
    return PII_GLINER_TOKENIZER


@log_model_loading("gliner model")
def get_gliner_model() -> GLiNER | None:
    if skip_model_loading():
        logger.info(
            "Skipping gliner model - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None

    global PII_GLINER_MODEL

    # Check if Gliner is enabled
    if not USE_PII_MODEL_V2:
        logger.info("Gliner disabled - GENAI_ENGINE_USE_PII_MODEL_V2 is false")
        return None

    if PII_GLINER_MODEL is None:
        model_path = get_local_model_path("urchade/gliner_multi_pii-v1")
        # Check if local model exists to set local_files_only appropriately
        local_files_only = (
            os.path.exists(model_path) and model_path != "urchade/gliner_multi_pii-v1"
        )
        PII_GLINER_MODEL = GLiNER.from_pretrained(
            model_path,
            config=GLiNERConfig.from_json_file(GLINER_CONFIG_PATH),
            tokenizer=get_gliner_tokenizer(),
            load_tokenizer=False,
            local_files_only=local_files_only,
        ).to(get_device())
        PII_GLINER_MODEL.eval()
    return PII_GLINER_MODEL


@log_model_loading("presidio analyzer")
def get_presidio_analyzer() -> AnalyzerEngine | None:
    if skip_model_loading():
        logger.info(
            "Skipping presidio analyzer - GENAI_ENGINE_SKIP_MODEL_LOADING is True",
        )
        return None
    global PII_PRESIDIO_ANALYZER
    if PII_PRESIDIO_ANALYZER is None:
        PII_PRESIDIO_ANALYZER = AnalyzerEngine()
    return PII_PRESIDIO_ANALYZER
