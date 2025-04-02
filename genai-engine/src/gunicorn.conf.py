from os import environ

from gunicorn.arbiter import Arbiter
from utils.model_load import (
    get_claim_classifier_embedding_model,
    get_prompt_injection_model,
    get_prompt_injection_tokenizer,
    get_toxicity_model,
    get_toxicity_tokenizer,
)

bind = "0.0.0.0:" + environ.get("PORT", "3000")
workers = environ.get("WORKERS", 1)
loglevel = environ.get("LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"  # stdout
timeout = environ.get("TIMEOUT", 60)
worker_class = "uvicorn.workers.UvicornWorker"


def on_starting(server: Arbiter) -> None:
    server.log.info("Loading models...")
    try:
        get_claim_classifier_embedding_model()
        get_prompt_injection_model()
        get_prompt_injection_tokenizer()
        get_toxicity_model()
        get_toxicity_tokenizer()
    except Exception as e:
        server.log.error(f"Error loading models: {e}")
        raise e
    server.log.info("Models loaded")
