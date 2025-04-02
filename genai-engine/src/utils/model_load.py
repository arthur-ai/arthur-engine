from logging import getLogger

from sentence_transformers import SentenceTransformer
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    RobertaForSequenceClassification,
    RobertaTokenizer,
)

logger = getLogger(__name__)

CLAIM_CLASSIFIER_EMBEDDING_MODEL = None
PROMPT_INJECTION_MODEL = None
PROMPT_INJECTION_TOKENIZER = None
TOXICITY_MODEL = None
TOXICITY_TOKENIZER = None


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
        TOXICITY_MODEL = RobertaForSequenceClassification.from_pretrained(
            "s-nlp/roberta_toxicity_classifier",
            weights_only=False,
        )
    return TOXICITY_MODEL


def get_toxicity_tokenizer():
    global TOXICITY_TOKENIZER
    if not TOXICITY_TOKENIZER:
        TOXICITY_TOKENIZER = RobertaTokenizer.from_pretrained(
            "s-nlp/roberta_toxicity_classifier",
            weights_only=False,
        )
    return TOXICITY_TOKENIZER
