import os
from logging import getLogger
from multiprocessing import Pool

# Disable tokenizers parallelism to avoid fork warnings in threaded environments
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import torch
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase

from utils.classifiers import get_device

logger = getLogger(__name__)

CLAIM_CLASSIFIER_EMBEDDING_MODEL = None
PROMPT_INJECTION_MODEL = None
PROMPT_INJECTION_TOKENIZER = None
TOXICITY_MODEL = None
TOXICITY_TOKENIZER = None
RELEVANCE_MODEL = None
RELEVANCE_TOKENIZER = None
TOXICITY_CLASSIFIER = None
PROFANITY_CLASSIFIER = None


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
        "microsoft/deberta-xlarge-mnli": [
            "config.json",
            "model.safetensors",
            "special_tokens_map.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "vocab.json",
        ],
    }

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


def get_claim_classifier_embedding_model():
    global CLAIM_CLASSIFIER_EMBEDDING_MODEL
    if not CLAIM_CLASSIFIER_EMBEDDING_MODEL:
        CLAIM_CLASSIFIER_EMBEDDING_MODEL = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L12-v2",
        )
    return CLAIM_CLASSIFIER_EMBEDDING_MODEL


def get_prompt_injection_model():
    global PROMPT_INJECTION_MODEL
    if PROMPT_INJECTION_MODEL is None:
        PROMPT_INJECTION_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
            weights_only=False,
        )
    return PROMPT_INJECTION_MODEL


def get_prompt_injection_tokenizer():
    global PROMPT_INJECTION_TOKENIZER
    if PROMPT_INJECTION_TOKENIZER is None:
        PROMPT_INJECTION_TOKENIZER = AutoTokenizer.from_pretrained(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
            weights_only=False,
        )
    return PROMPT_INJECTION_TOKENIZER


def get_toxicity_model():
    global TOXICITY_MODEL
    if not TOXICITY_MODEL:
        TOXICITY_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "s-nlp/roberta_toxicity_classifier",
            weights_only=False,
        )
    return TOXICITY_MODEL


def get_toxicity_tokenizer():
    global TOXICITY_TOKENIZER
    if not TOXICITY_TOKENIZER:
        TOXICITY_TOKENIZER = AutoTokenizer.from_pretrained(
            "s-nlp/roberta_toxicity_classifier",
            weights_only=False,
            model_max_length=None,
        )
    return TOXICITY_TOKENIZER


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


def get_relevance_model():
    global RELEVANCE_MODEL
    if not RELEVANCE_MODEL:
        RELEVANCE_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "microsoft/deberta-xlarge-mnli",
            weights_only=False,
        )
    return RELEVANCE_MODEL


def get_relevance_tokenizer():
    global RELEVANCE_TOKENIZER
    if not RELEVANCE_TOKENIZER:
        RELEVANCE_TOKENIZER = AutoTokenizer.from_pretrained(
            "microsoft/deberta-xlarge-mnli",
            weights_only=False,
        )
    return RELEVANCE_TOKENIZER
