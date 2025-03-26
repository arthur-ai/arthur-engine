import fcntl
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def reset_on_failure(global_var_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            global_vars = globals()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                if global_var_name in global_vars:
                    global_vars[global_var_name] = None
                return None

        return wrapper

    return decorator


def with_lock(lock_file_path):
    def decorator(download_func):
        @wraps(download_func)
        def wrapper(*args, **kwargs):
            with open(lock_file_path, "w") as lock_file:
                try:
                    # Attempt to acquire an exclusive lock (non-blocking)
                    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return download_func(*args, **kwargs)
                except BlockingIOError:
                    logger.warning(f"Lock is already held for {lock_file_path}.")
                    return None
                except Exception as e:
                    logger.error(f"Failed to download model: {e}")
                    return None
                finally:
                    # Release the lock
                    try:
                        fcntl.flock(lock_file, fcntl.LOCK_UN)
                    except Exception as e:
                        logger.error(f"Failed to release lock: {e}")

        return wrapper

    return decorator
