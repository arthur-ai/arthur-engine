from os import environ

bind = "0.0.0.0:" + environ.get("PORT", "3000")
workers = environ.get("WORKERS", 1)
loglevel = environ.get("LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"  # stdout
timeout = environ.get("TIMEOUT", 60)
worker_class = "uvicorn.workers.UvicornWorker"
