from os import environ

from gunicorn.arbiter import Arbiter

from utils.model_load import download_models

bind = "0.0.0.0:" + environ.get("PORT", "3030")
workers = environ.get("WORKERS", 1)
loglevel = environ.get("LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"  # stdout
timeout = environ.get("TIMEOUT", 120)
worker_class = "uvicorn.workers.UvicornWorker"


def on_starting(server: Arbiter) -> None:
    server.log.info("Downloading models...")
    try:
        download_models(int(workers))
    except Exception as e:
        server.log.error(f"Error downloading models: {e}")
        raise e
    server.log.info("Models downloaded.")
