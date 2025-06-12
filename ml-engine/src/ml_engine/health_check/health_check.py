import threading
import time

from flask import Flask, jsonify
from flask.typing import ResponseReturnValue


class MLEngineHealthCheck:
    """
    This class exposes a http health check API on the configured port.

    The /health API returns 200 if there has been a liveness_ping in the last check_in_seconds interval.
    """

    def __init__(self, check_in_seconds: int = 600, port: int = 7492):
        self.port = port
        self.check_in_seconds = check_in_seconds
        self.last_check_in_time = time.time()
        self.thread = threading.Thread(target=self._run_flask_endpoint, daemon=True)

    def _run_flask_endpoint(self) -> None:
        """
        This function is meant to be called in a thread. It will block running the Flask server.
        """
        app = Flask(__name__)

        @app.route("/health", methods=["GET"])
        def health_check() -> ResponseReturnValue:
            # check if there has been a liveness ping in the last self.unhealthy_seconds
            if time.time() - self.last_check_in_time > self.check_in_seconds:
                unhealthy_response = {
                    "status": "unhealthy",
                    "last_check_in_time": self.last_check_in_time,
                }
                return jsonify(unhealthy_response), 500
            else:
                healthy_response = {
                    "status": "ok",
                    "last_check_in_time": self.last_check_in_time,
                }
                return jsonify(healthy_response)

        app.run(host="127.0.0.1", port=self.port, use_reloader=False)

    def start_server(self) -> None:
        self.thread.start()

    def liveness_ping(self) -> None:
        self.last_check_in_time = time.time()
