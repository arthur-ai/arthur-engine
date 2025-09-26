from os import environ

bind = "0.0.0.0:" + environ.get("PORT", "3030")
workers = environ.get("WORKERS", 1)
loglevel = environ.get("LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"  # stdout
timeout = environ.get("TIMEOUT", 120)
worker_class = "uvicorn.workers.UvicornWorker"
