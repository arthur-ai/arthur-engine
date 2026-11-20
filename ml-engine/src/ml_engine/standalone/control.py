"""An HTTP API for asking the standalone engine to scan a source now, and for seeing
where each scan stands. Off unless the engine is given a token.

    GET  /scans       every (source, config) pair: running, waiting, or when it is next due
    POST /scans/run   {"source_id": ..., "config_name": ...}: make the source's pairs --
                      or the one named -- due now. 202 with where each stands, 404 if
                      none match.

Both need `Authorization: Bearer <token>`, the token given as ML_ENGINE_CONTROL_TOKEN or
in the file ML_ENGINE_CONTROL_TOKEN_FILE names. The API can only bring a
configured scan forward: it takes no config, no credentials and no destination, so the
worst a caller holding the token can do is scan the configured sources more often than
the schedule would, and a pair already running is never started twice.

IT LISTENS ON EVERY INTERFACE. Its caller is a dashboard in another container, so
loopback would not reach it; the token is what keeps anyone else out. Publish the port
only to what needs it.
"""

import hmac
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, TypeGuard

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue
from werkzeug.serving import BaseWSGIServer, make_server

if TYPE_CHECKING:
    from standalone.agent import ScanState, StandaloneDiscoveryAgent

logger = logging.getLogger(__name__)

TOKEN_ENV_VAR = "ML_ENGINE_CONTROL_TOKEN"
TOKEN_FILE_ENV_VAR = "ML_ENGINE_CONTROL_TOKEN_FILE"
PORT_ENV_VAR = "ML_ENGINE_CONTROL_PORT"
HOST_ENV_VAR = "ML_ENGINE_CONTROL_HOST"
DEFAULT_PORT = 7494
DEFAULT_HOST = "0.0.0.0"
# Long enough that it cannot be guessed; `openssl rand -hex 32` gives 64.
MIN_TOKEN_LENGTH = 32
# A request body is two short strings.
MAX_BODY_BYTES = 4096
# Source IDs are UUIDs and config names are short; anything longer is not one.
MAX_FIELD_LENGTH = 200


class ControlServer:
    """Serves the control API for `agent` in a daemon thread, from `start` until the
    process exits or `stop`."""

    def __init__(
        self,
        agent: "StandaloneDiscoveryAgent",
        token: str,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        if len(token) < MIN_TOKEN_LENGTH:
            raise ValueError(
                f"the control token must be at least {MIN_TOKEN_LENGTH} characters",
            )
        self._agent = agent
        self._token = token.encode("utf-8")
        self.host = host
        self.port = port
        self.app = self._build_app()
        self._server: Optional[BaseWSGIServer] = None

    def start(self) -> None:
        self._server = make_server(self.host, self.port, self.app, threaded=True)
        self.port = self._server.server_port  # the real one, when asked for port 0
        threading.Thread(
            target=self._server.serve_forever,
            name="control-api",
            daemon=True,
        ).start()
        logger.info(f"Control API listening on {self.host}:{self.port}")

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

    def _authorized(self) -> bool:
        scheme, _, given = request.headers.get("Authorization", "").partition(" ")
        return scheme.lower() == "bearer" and hmac.compare_digest(
            given.strip().encode("utf-8"),
            self._token,
        )

    def _build_app(self) -> Flask:
        app = Flask(__name__)
        app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

        @app.before_request
        def _require_token() -> Optional[ResponseReturnValue]:
            if not self._authorized():
                return (
                    jsonify(error="a valid bearer token is required"),
                    401,
                    {"WWW-Authenticate": "Bearer"},
                )
            return None

        @app.get("/scans")
        def scans() -> ResponseReturnValue:
            return jsonify(scans=[_describe(s) for s in self._agent.scan_states()])

        @app.post("/scans/run")
        def run() -> ResponseReturnValue:
            body = request.get_json(silent=True)
            if not isinstance(body, dict):
                return jsonify(error="the body must be a JSON object"), 400
            source_id = body.get("source_id")
            config_name = body.get("config_name")
            if not _field(source_id):
                return jsonify(error="source_id is required"), 400
            if config_name is not None and not _field(config_name):
                return jsonify(error="config_name must be a non-empty string"), 400
            states = self._agent.run_now(source_id, config_name)
            if not states:
                return jsonify(error="no configured scan matches"), 404
            return jsonify(scans=[_describe(s) for s in states]), 202

        return app


def control_from_env(agent: "StandaloneDiscoveryAgent") -> Optional[ControlServer]:
    """The control server the environment asks for, or None when it gives no token.

    A token too short, a token file that cannot be read, or a port that is not one stops
    the engine with a message naming the variable, as a bad config file does, rather than
    running without the API the deployment expects. No message quotes the token.
    """
    token = os.getenv(TOKEN_ENV_VAR, "").strip()
    named = TOKEN_ENV_VAR
    token_file = os.getenv(TOKEN_FILE_ENV_VAR, "").strip()
    if token and token_file:
        raise SystemExit(f"Set {TOKEN_ENV_VAR} or {TOKEN_FILE_ENV_VAR}, not both")
    if token_file:
        named = f"The file {TOKEN_FILE_ENV_VAR} names"
        try:
            token = Path(token_file).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as e:
            reason = getattr(e, "strerror", None) or "not UTF-8"
            raise SystemExit(
                f"Cannot read {TOKEN_FILE_ENV_VAR} ({token_file}): {reason}",
            ) from None
    if not token:
        if token_file:
            raise SystemExit(f"{named} is empty")
        return None
    if len(token) < MIN_TOKEN_LENGTH:
        raise SystemExit(
            f"{named} must hold at least {MIN_TOKEN_LENGTH} characters; "
            f"`openssl rand -hex 32` makes a token",
        )
    raw_port = os.getenv(PORT_ENV_VAR, "").strip() or str(DEFAULT_PORT)
    if not raw_port.isdigit() or not 0 < int(raw_port) < 65536:
        raise SystemExit(f"{PORT_ENV_VAR} must be a port number")
    host = os.getenv(HOST_ENV_VAR, "").strip() or DEFAULT_HOST
    return ControlServer(agent, token, host=host, port=int(raw_port))


def _field(value: Any) -> TypeGuard[str]:
    return isinstance(value, str) and 0 < len(value) <= MAX_FIELD_LENGTH


def _describe(state: "ScanState") -> dict[str, Any]:
    return {
        "source_id": state.source_id,
        "source_name": state.source_name,
        "vendor": state.vendor,
        "config_name": state.config_name,
        "status": state.status,
        "last_started_at": _iso(state.last_started_at),
        "next_due_at": _iso(state.next_due_at),
    }


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None
