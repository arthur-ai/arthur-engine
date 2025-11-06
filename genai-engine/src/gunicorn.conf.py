from os import environ

bind = "0.0.0.0:" + environ.get("PORT", "3030")
workers = environ.get("WORKERS", 1)
loglevel = environ.get("LOG_LEVEL", "info")
accesslog = "-"  # stdout
errorlog = "-"  # stdout
timeout = environ.get("TIMEOUT", 120)
worker_class = "uvicorn.workers.UvicornWorker"

# Graceful shutdown configuration
# Time to wait for workers to finish handling requests before forcefully terminating
graceful_timeout = int(environ.get("GRACEFUL_TIMEOUT", 30))

# Max time for graceful worker restart
max_requests = int(environ.get("MAX_REQUESTS", 0))  # 0 = disabled
max_requests_jitter = int(environ.get("MAX_REQUESTS_JITTER", 0))


def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Gunicorn master process starting")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn server is ready. Accepting connections.")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Gunicorn master process exiting")


def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"Worker {worker.pid} exited")


def pre_fork(server, worker):
    """Called just before a worker is forked."""


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")
