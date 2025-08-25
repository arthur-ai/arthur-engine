import os
from functools import wraps
from logging import getLogger
from multiprocessing import Pool

# Disable tokenizers parallelism to avoid fork warnings in threaded environments
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
from bert_score import BERTScorer
from gliner import GLiNER, GLiNERConfig
from huggingface_hub import hf_hub_download
from presidio_analyzer import AnalyzerEngine
from sentence_transformers import SentenceTransformer
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TextClassificationPipeline,
    pipeline,
)
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase

from utils import constants
from utils.classifiers import get_device
from utils.utils import get_env_var, relevance_models_enabled

logger = getLogger(__name__)

__location__ = os.path.dirname(os.path.abspath(__file__))

GLINER_CONFIG_PATH = os.path.join(
    __location__,
    "../scorer/checks/pii/gliner/gliner_tokenizer_config.json",
)

USE_PII_MODEL_V2 = (
    get_env_var(constants.GENAI_ENGINE_USE_PII_MODEL_V2_ENV_VAR) == "true"
)

CLAIM_CLASSIFIER_EMBEDDING_MODEL = None
PROMPT_INJECTION_MODEL = None
PROMPT_INJECTION_TOKENIZER = None
PROMPT_INJECTION_CLASSIFIER = None
TOXICITY_MODEL = None
TOXICITY_TOKENIZER = None
RELEVANCE_MODEL = None
RELEVANCE_TOKENIZER = None
TOXICITY_CLASSIFIER = None
PROFANITY_CLASSIFIER = None
BERT_SCORER = None
RELEVANCE_RERANKER = None
PII_GLINER_MODEL = None
PII_GLINER_TOKENIZER = None
PII_PRESIDIO_ANALYZER = None


def log_model_loading(model_name: str, global_var_name: str = None):
    """Decorator to add logging around model loading functions"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
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


def download_file(args):
    model_name, filename = args
    try:
        hf_hub_download(model_name, filename)
        logger.info(f"Downloaded {filename} from {model_name}")
    except Exception as e:
        logger.info(f"Failed to download {filename} from {model_name}: {e}")


def download_models(num_of_process: int):
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
    }

    # Only download relevance models if they are enabled
    if relevance_models_enabled():
        models_to_download["microsoft/deberta-v2-xlarge-mnli"] = [
            "config.json",
            "pytorch_model.bin",
            "spm.model",
            "model.safetensors",
            "tokenizer_config.json",
            "tokenizer.json",
        ]
    else:
        logger.info(
            "Skipping relevance models download - ENABLE_RELEVANCE_MODELS is False",
        )

    # Prepare a list of tasks (model_name, filename pairs)
    tasks = [
        (model_name, filename)
        for model_name, filenames in models_to_download.items()
        for filename in filenames
    ]

    # Use multiprocessing Pool to download files in parallel
    with Pool(
        processes=num_of_process,
    ) as pool:  # Adjust 'processes' based on your CPU cores
        pool.map(download_file, tasks)


@log_model_loading(
    "claim classifier embedding model",
    "CLAIM_CLASSIFIER_EMBEDDING_MODEL",
)
def get_claim_classifier_embedding_model():
    global CLAIM_CLASSIFIER_EMBEDDING_MODEL
    if not CLAIM_CLASSIFIER_EMBEDDING_MODEL:

        CLAIM_CLASSIFIER_EMBEDDING_MODEL = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L12-v2",
        )
    return CLAIM_CLASSIFIER_EMBEDDING_MODEL


@log_model_loading("prompt injection model", "PROMPT_INJECTION_MODEL")
def get_prompt_injection_model():
    global PROMPT_INJECTION_MODEL
    if PROMPT_INJECTION_MODEL is None:

        PROMPT_INJECTION_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
            weights_only=False,
        )

    return PROMPT_INJECTION_MODEL


@log_model_loading("prompt injection tokenizer", "PROMPT_INJECTION_TOKENIZER")
def get_prompt_injection_tokenizer():
    global PROMPT_INJECTION_TOKENIZER
    if PROMPT_INJECTION_TOKENIZER is None:
        PROMPT_INJECTION_TOKENIZER = AutoTokenizer.from_pretrained(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
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

    global PROMPT_INJECTION_CLASSIFIER
    if PROMPT_INJECTION_CLASSIFIER is None:
        PROMPT_INJECTION_CLASSIFIER = TextClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            max_length=512,
            truncation=True,
            device=torch.device(get_device()),
        )
    return PROMPT_INJECTION_CLASSIFIER


@log_model_loading("toxicity model", "TOXICITY_MODEL")
def get_toxicity_model():
    global TOXICITY_MODEL
    if not TOXICITY_MODEL:
        TOXICITY_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "s-nlp/roberta_toxicity_classifier",
            weights_only=False,
        )
    return TOXICITY_MODEL


@log_model_loading("toxicity tokenizer", "TOXICITY_TOKENIZER")
def get_toxicity_tokenizer():
    global TOXICITY_TOKENIZER
    if not TOXICITY_TOKENIZER:
        TOXICITY_TOKENIZER = AutoTokenizer.from_pretrained(
            "s-nlp/roberta_toxicity_classifier",
            weights_only=False,
            model_max_length=None,
        )
    return TOXICITY_TOKENIZER


@log_model_loading("toxicity classifier pipeline", "TOXICITY_CLASSIFIER")
def get_toxicity_classifier(
    model: AutoModelForSequenceClassification | None,
    tokenizer: AutoTokenizer | None,
):
    if not model:
        model = get_toxicity_model()
    if not tokenizer:
        tokenizer = get_toxicity_tokenizer()

    global TOXICITY_CLASSIFIER
    if TOXICITY_CLASSIFIER is None:
        TOXICITY_CLASSIFIER = pipeline(
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
def get_profanity_classifier():
    global PROFANITY_CLASSIFIER
    if PROFANITY_CLASSIFIER is None:
        PROFANITY_CLASSIFIER = pipeline(
            "text-classification",
            model="tarekziade/pardonmyai",
            top_k=99999,
            truncation=True,
            max_length=512,
            device=torch.device(get_device()),
        )
    return PROFANITY_CLASSIFIER


def get_harmful_request_classifier(
    model: PreTrainedModel | None,
    tokenizer: PreTrainedTokenizerBase | None,
):
    if not model or not tokenizer:
        return None


@log_model_loading("relevance model", "RELEVANCE_MODEL")
def get_relevance_model():
    global RELEVANCE_MODEL
    if not RELEVANCE_MODEL:
        RELEVANCE_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "microsoft/deberta-v2-xlarge-mnli",
            weights_only=False,
            torch_dtype=torch.float16,
        )
    return RELEVANCE_MODEL


@log_model_loading("relevance tokenizer", "RELEVANCE_TOKENIZER")
def get_relevance_tokenizer():
    global RELEVANCE_TOKENIZER
    if not RELEVANCE_TOKENIZER:
        RELEVANCE_TOKENIZER = AutoTokenizer.from_pretrained(
            "microsoft/deberta-v2-xlarge-mnli",
            weights_only=False,
        )
    return RELEVANCE_TOKENIZER


@log_model_loading("BERT scorer model", "BERT_SCORER")
def get_bert_scorer():
    """Get or create a shared BERT scorer instance for relevance metrics"""
    global BERT_SCORER

    # Check if relevance models are enabled
    if not relevance_models_enabled():
        logger.info("BERT scorer disabled - ENABLE_RELEVANCE_MODELS is False")
        return None

    if BERT_SCORER is None:
        BERT_SCORER = BERTScorer(
            model_type="microsoft/deberta-v2-xlarge-mnli",
            use_fast_tokenizer=True,
            num_layers=17,
        )

    return BERT_SCORER


@log_model_loading("relevance reranker pipeline", "RELEVANCE_RERANKER")
def get_relevance_reranker():
    """Get or create a shared relevance reranker pipeline instance"""
    global RELEVANCE_RERANKER

    # Check if relevance models are enabled
    if not relevance_models_enabled():
        logger.info("Relevance reranker disabled - ENABLE_RELEVANCE_MODELS is False")
        return None

    if RELEVANCE_RERANKER is None:

        model = get_relevance_model()
        tokenizer = get_relevance_tokenizer()
        RELEVANCE_RERANKER = TextClassificationPipeline(
            model=model,
            tokenizer=tokenizer,
            device=torch.device(get_device()),
            torch_dtype=torch.float16,
        )
    return RELEVANCE_RERANKER


@log_model_loading("gliner tokenizer")
def get_gliner_tokenizer():
    global PII_GLINER_TOKENIZER
    if USE_PII_MODEL_V2 and PII_GLINER_TOKENIZER is None:
        config = GLiNERConfig.from_json_file(GLINER_CONFIG_PATH)
        PII_GLINER_TOKENIZER = AutoTokenizer.from_pretrained(config.model_name)
    return PII_GLINER_TOKENIZER


@log_model_loading("gliner model")
def get_gliner_model():
    global PII_GLINER_MODEL
    if USE_PII_MODEL_V2 and PII_GLINER_MODEL is None:
        PII_GLINER_MODEL = GLiNER.from_pretrained(
            "urchade/gliner_multi_pii-v1",
            config=GLiNERConfig.from_json_file(GLINER_CONFIG_PATH),
            tokenizer=get_gliner_tokenizer(),
            load_tokenizer=False,
            local_files_only=False,
        ).to(get_device())
        PII_GLINER_MODEL.eval()
    return PII_GLINER_MODEL


@log_model_loading("presidio analyzer")
def get_presidio_analyzer():
    global PII_PRESIDIO_ANALYZER
    if PII_PRESIDIO_ANALYZER is None:
        PII_PRESIDIO_ANALYZER = AnalyzerEngine()
    return PII_PRESIDIO_ANALYZER
