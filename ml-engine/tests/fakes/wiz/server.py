"""A fake Wiz tenant: the token endpoint and the GraphQL API, as the connector uses them.

Every GraphQL request is parsed, validated and executed by graphql-core against the
pruned copy of Wiz's real schema in tests/unit/discovery/fixtures/wiz, so a document
or variable Wiz would reject is rejected here too. Resolvers serve `tenant.json`
(synthetic ids only) and honour the filters the connector sends; any other filter
is refused rather than ignored, so a connector change cannot pass against data the
fake never filtered.

Error shapes follow the client's reading of Wiz (see the docstring of
discovery/cloud/wiz/client.py): `errors[].extensions.code`, often with HTTP 200. The
`FAULTS` reproduce the failures the connector handles. Needs only the standard
library and graphql-core, so it also runs in a bare Python container.
"""

import base64
import binascii
import functools
import json
import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlsplit

from graphql import (
    GraphQLEnumType,
    GraphQLError,
    GraphQLSchema,
    GraphQLSyntaxError,
    build_schema,
    execute_sync,
    parse,
    validate,
)

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = (
    HERE.parents[1]
    / "unit"
    / "discovery"
    / "fixtures"
    / "wiz"
    / "wiz-schema.pruned.graphql"
)
TENANT_PATH = HERE / "tenant.json"

DEFAULT_CLIENT_ID = "fake-wiz-client-id"
DEFAULT_CLIENT_SECRET = "fake-wiz-client-secret"
AUDIENCE = "wiz-api"
MAX_FIRST = 500

# The service account's scopes, and what each query needs one of.
DEFAULT_SCOPES = frozenset({"read:resources", "read:inventory"})
REQUIRED_SCOPES = {
    "cloudResourcesV2": ("read:resources", "read:all"),
    "hostedTechnologies": ("read:inventory", "read:all"),
}

FAULTS = {
    "none": "serve normally",
    "bad-credentials": "the token endpoint refuses every client id and secret (401)",
    "missing-scope": "the service account lacks read:inventory, so hostedTechnologies "
    "is refused UNAUTHORIZED",
    "forbidden-ip": "every GraphQL call is refused FORBIDDEN_IP (403)",
    "rate-limit-once": "the first GraphQL call is HTTP 429 RATE_LIMIT_EXCEEDED with "
    "Retry-After, then normal",
    "rate-limit-in-200": "the first GraphQL call is HTTP 200 carrying "
    "RATE_LIMIT_EXCEEDED, then normal",
    "repeated-cursor": "cloudResourcesV2 hands back the same endCursor on every page",
}

log = logging.getLogger("fake_wiz")


@functools.cache
def load_schema(path: Path = SCHEMA_PATH) -> GraphQLSchema:
    return build_schema(path.read_text(encoding="utf-8"))


def load_tenant(path: Path = TENANT_PATH) -> dict[str, Any]:
    """The tenant's nodes, shaped as the schema returns them."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    resources, technologies = raw["resources"], raw["technologies"]
    hosted = []
    for sighting in raw["hostedTechnologies"]:
        technology = technologies[sighting["technology"]]
        resource = resources[sighting["resource"]]
        version = sighting.get("version")
        hosted.append(
            {
                "id": sighting["id"],
                # Wiz's own form: "<technology> (<resource name>)".
                "name": f"{technology['name']} ({resource['name']})",
                "firstSeen": sighting["firstSeen"],
                "updatedAt": sighting["updatedAt"],
                "versionDetails": {"version": version} if version else None,
                "technology": technology,
                "resource": resource,
            },
        )
    return {"cloudResourcesV2": raw["cloudResources"], "hostedTechnologies": hosted}


def _error(message: str, code: str, **extra: Any) -> dict[str, Any]:
    return {"message": message, "extensions": {"code": code}, **extra}


@dataclass
class _Answer:
    status: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)


class FakeWiz:
    """One fake tenant on one port. `start()` serves it on a daemon thread."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        client_id: str = DEFAULT_CLIENT_ID,
        client_secret: str = DEFAULT_CLIENT_SECRET,
        page_size: int = MAX_FIRST,
        fault: str = "none",
        token_lifetime: int = 3600,
        retry_after: str = "1",
        tenant: Optional[dict[str, Any]] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.page_size = max(1, min(page_size, MAX_FIRST))
        self.token_lifetime = token_lifetime
        self.retry_after = retry_after
        self.schema = load_schema()
        entity_type = self.schema.get_type("GraphEntityType")
        assert isinstance(entity_type, GraphQLEnumType)
        self.entity_types = frozenset(entity_type.values)
        self.tenant = tenant if tenant is not None else load_tenant()
        self._lock = threading.Lock()
        self._tokens: dict[str, float] = {}
        self.fault = "none"
        self._fault_spent = False
        self.set_fault(fault)
        # (path, GraphQL root field or None, HTTP status), in arrival order.
        self.requests: list[tuple[str, Optional[str], int]] = []
        # GraphQL variables as received, per root field.
        self.variables: list[tuple[str, dict[str, Any]]] = []
        # Whatever a standalone engine's webhook destination POSTed to /_sink.
        self.sink_events: list[Any] = []
        self._server = ThreadingHTTPServer((host, port), _handler_for(self))
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host!s}:{port}"

    def start(self) -> "FakeWiz":
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": 0.05},
            name="fake-wiz",
            daemon=True,
        )
        self._thread.start()
        return self

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def __enter__(self) -> "FakeWiz":
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.stop()

    def set_fault(self, fault: str) -> None:
        if fault not in FAULTS:
            raise ValueError(f"unknown fault {fault!r}; one of {', '.join(FAULTS)}")
        with self._lock:
            self.fault = fault
            self._fault_spent = False

    def reset(self) -> None:
        with self._lock:
            self.requests.clear()
            self.variables.clear()
            self.sink_events.clear()
            self._tokens.clear()
            self._fault_spent = False

    def roots_requested(self) -> list[Optional[str]]:
        return [root for path, root, _ in self.requests if path == "/graphql"]

    @property
    def scopes(self) -> frozenset[str]:
        if self.fault == "missing-scope":
            return DEFAULT_SCOPES - {"read:inventory"}
        return DEFAULT_SCOPES

    # -- routes ------------------------------------------------------------------------

    def handle(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        headers: Any,
        body: bytes,
    ) -> _Answer:
        if method == "POST" and path == "/oauth/token":
            return self._token(headers, body)
        if method == "POST" and path == "/graphql":
            return self._graphql(headers, body)
        if method == "POST" and path == "/_sink":
            return self._sink(body)
        if method == "GET" and path == "/_sink":
            return _Answer(200, self.sink_events)
        if path == "/_control/fault" and method == "POST":
            mode = (query.get("mode") or [""])[0]
            try:
                self.set_fault(mode)
            except ValueError as e:
                return _Answer(400, {"error": str(e)})
            return _Answer(200, {"fault": self.fault})
        if path == "/_control/reset" and method == "POST":
            self.reset()
            return _Answer(200, {"reset": True})
        if path == "/_control/state" and method == "GET":
            return _Answer(
                200,
                {
                    "fault": self.fault,
                    "faults": FAULTS,
                    "page_size": self.page_size,
                    "requests": self.requests,
                    "sink_events": len(self.sink_events),
                },
            )
        return _Answer(404, {"error": "not_found"})

    def _token(self, headers: Any, body: bytes) -> _Answer:
        content_type = (headers.get("Content-Type") or "").split(";")[0].strip()
        if content_type != "application/x-www-form-urlencoded":
            return _Answer(
                400,
                {"error": "invalid_request", "error_description": "form body required"},
            )
        form = {k: v[0] for k, v in parse_qs(body.decode("utf-8")).items()}
        if (
            form.get("grant_type") != "client_credentials"
            or form.get("audience") != AUDIENCE
        ):
            return _Answer(
                400,
                {
                    "error": "invalid_request",
                    "error_description": "grant_type=client_credentials and "
                    "audience=wiz-api are required",
                },
            )
        if (
            self.fault == "bad-credentials"
            or not secrets.compare_digest(form.get("client_id", ""), self.client_id)
            or not secrets.compare_digest(
                form.get("client_secret", ""),
                self.client_secret,
            )
        ):
            return _Answer(
                401,
                {"error": "access_denied", "error_description": "Unauthorized"},
            )
        token = "fake-wiz-token-" + secrets.token_urlsafe(24)
        with self._lock:
            self._tokens[token] = time.monotonic() + self.token_lifetime
        return _Answer(
            200,
            {
                "access_token": token,
                "expires_in": self.token_lifetime,
                "token_type": "Bearer",
            },
        )

    def _sink(self, body: bytes) -> _Answer:
        events = json.loads(body or b"[]")
        with self._lock:
            self.sink_events.extend(events if isinstance(events, list) else [events])
        return _Answer(
            200,
            {"accepted": len(events) if isinstance(events, list) else 1},
        )

    def _authenticated(self, headers: Any) -> bool:
        scheme, _, token = (headers.get("Authorization") or "").partition(" ")
        with self._lock:
            expires = self._tokens.get(token)
        return scheme == "Bearer" and expires is not None and time.monotonic() < expires

    def _graphql(self, headers: Any, body: bytes) -> _Answer:
        if not self._authenticated(headers):
            return _Answer(
                401,
                {"errors": [_error("unauthenticated", "UNAUTHENTICATED")]},
            )
        if self.fault == "forbidden-ip":
            return _Answer(
                403,
                {
                    "errors": [
                        _error(
                            "access from this IP address is not allowed",
                            "FORBIDDEN_IP",
                        ),
                    ],
                },
            )
        if self.fault in ("rate-limit-once", "rate-limit-in-200"):
            with self._lock:
                spent, self._fault_spent = self._fault_spent, True
            if not spent:
                limited = {
                    "errors": [_error("rate limit exceeded", "RATE_LIMIT_EXCEEDED")],
                }
                if self.fault == "rate-limit-once":
                    return _Answer(429, limited, {"Retry-After": self.retry_after})
                return _Answer(200, {"data": None, **limited})

        try:
            request = json.loads(body)
            source = request["query"]
            variables = request.get("variables") or {}
            if not isinstance(source, str) or not isinstance(variables, dict):
                raise TypeError
        except (ValueError, KeyError, TypeError):
            return _Answer(
                400,
                {
                    "errors": [
                        _error("a JSON body with a query is required", "BAD_REQUEST"),
                    ],
                },
            )
        try:
            document = parse(source)
        except GraphQLSyntaxError as e:
            return _Answer(400, {"errors": [_error(e.message, "GRAPHQL_PARSE_FAILED")]})
        invalid = validate(self.schema, document)
        if invalid:
            return _Answer(
                400,
                {
                    "errors": [
                        _error(e.message, "GRAPHQL_VALIDATION_FAILED") for e in invalid
                    ],
                },
            )

        root_value: dict[str, Callable[..., Any]] = {
            "cloudResourcesV2": self._cloud_resources,
            "hostedTechnologies": self._hosted_technologies,
        }
        result = execute_sync(
            self.schema,
            document,
            root_value=root_value,
            variable_values=variables,
            operation_name=request.get("operationName"),
        )
        errors = [_formatted(e) for e in result.errors or []]
        if result.errors and all(e.path is None for e in result.errors):
            # Raised before any field ran: the variables did not coerce.
            for error in errors:
                error.setdefault("extensions", {}).setdefault("code", "BAD_USER_INPUT")
            return _Answer(400, {"errors": errors})
        answer: dict[str, Any] = {"data": result.data}
        if errors:
            answer["errors"] = errors
        return _Answer(200, answer)

    # -- resolvers ---------------------------------------------------------------------

    def _require_scope(self, root: str) -> None:
        wanted = REQUIRED_SCOPES[root]
        if self.scopes.isdisjoint(wanted):
            raise GraphQLError(
                "access denied, at least one of the following is required: "
                f"[{' '.join(wanted)}]",
                extensions={"code": "UNAUTHORIZED"},
            )

    def _entity_types(self, names: Any, where: str) -> list[str]:
        unknown = [n for n in names or [] if n not in self.entity_types]
        if unknown:
            raise GraphQLError(
                f"{where}: unknown entity type(s) {', '.join(map(str, unknown))}",
                extensions={"code": "BAD_USER_INPUT"},
            )
        return list(names or [])

    def _cloud_resources(
        self,
        info: Any,
        filterBy: Optional[dict[str, Any]] = None,
        first: Optional[int] = None,
        after: Optional[str] = None,
        orderBy: Any = None,
    ) -> dict[str, Any]:
        root = "cloudResourcesV2"
        self._note(root, filterBy, first, after)
        self._require_scope(root)
        filters = dict(filterBy or {})
        type_filter = filters.pop("type", None) or {}
        _not_implemented(root, filters, orderBy, type_filter, {"equals", "notEquals"})
        equals = self._entity_types(type_filter.get("equals"), "type.equals")
        not_equals = self._entity_types(type_filter.get("notEquals"), "type.notEquals")
        nodes = [
            n
            for n in self.tenant[root]
            if (not equals or n["type"] in equals) and n["type"] not in not_equals
        ]
        return self._page(root, nodes, first, after, self.fault == "repeated-cursor")

    def _hosted_technologies(
        self,
        info: Any,
        filterBy: Optional[dict[str, Any]] = None,
        first: Optional[int] = None,
        after: Optional[str] = None,
        orderBy: Any = None,
    ) -> dict[str, Any]:
        root = "hostedTechnologies"
        self._note(root, filterBy, first, after)
        self._require_scope(root)
        filters = dict(filterBy or {})
        technology_filter = dict(filters.pop("technologyV2", None) or {})
        category = dict(technology_filter.pop("category", None) or {})
        resource_filter = dict(filters.pop("resource", None) or {})
        resource_type = dict(resource_filter.pop("type", None) or {})
        _not_implemented(
            root,
            {**filters, **technology_filter, **resource_filter},
            orderBy,
            {**category, **resource_type},
            {"stackLayer", "equals"},
        )
        layers = category.get("stackLayer") or []
        types = self._entity_types(resource_type.get("equals"), "resource.type.equals")
        nodes = [
            n
            for n in self.tenant[root]
            if (not layers or n["technology"]["stackLayer"] in layers)
            and (not types or n["resource"]["type"] in types)
        ]
        return self._page(root, nodes, first, after, repeat_cursor=False)

    def _note(self, root: str, filter_by: Any, first: Any, after: Any) -> None:
        with self._lock:
            self.variables.append(
                (root, {"filterBy": filter_by, "first": first, "after": after}),
            )

    def _page(
        self,
        root: str,
        nodes: list[dict[str, Any]],
        first: Optional[int],
        after: Optional[str],
        repeat_cursor: bool,
    ) -> dict[str, Any]:
        if first is not None and first < 0:
            raise GraphQLError(
                "first must not be negative",
                extensions={"code": "BAD_USER_INPUT"},
            )
        size = min(first if first is not None else self.page_size, self.page_size)
        start = _offset(root, after)
        end = start + size
        cursor_at = size if repeat_cursor else end
        return {
            "nodes": nodes[start:end],
            "pageInfo": {
                "hasNextPage": repeat_cursor or end < len(nodes),
                "endCursor": _cursor(root, cursor_at) if nodes[start:end] else None,
            },
        }


def _not_implemented(
    root: str,
    leftover: dict[str, Any],
    order_by: Any,
    leaves: dict[str, Any],
    supported_leaves: set[str],
) -> None:
    unsupported = sorted(leftover) + sorted(set(leaves) - supported_leaves)
    if order_by is not None:
        unsupported.append("orderBy")
    if unsupported:
        raise GraphQLError(
            f"the fake Wiz does not implement {root} filter(s) {', '.join(unsupported)}; "
            f"add them to tests/fakes/wiz/server.py",
            extensions={"code": "FAKE_NOT_IMPLEMENTED"},
        )


def _cursor(root: str, offset: int) -> str:
    return base64.urlsafe_b64encode(f"{root}:{offset}".encode()).decode()


def _offset(root: str, after: Optional[str]) -> int:
    if after is None:
        return 0
    try:
        cursor_root, _, offset = base64.urlsafe_b64decode(after).decode().partition(":")
        if cursor_root == root and int(offset) >= 0:
            return int(offset)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        pass
    raise GraphQLError("invalid cursor", extensions={"code": "BAD_USER_INPUT"})


def _formatted(error: GraphQLError) -> dict[str, Any]:
    return dict(error.formatted)


def _handler_for(fake: FakeWiz) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _serve(self, method: str) -> None:
            url = urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            answer = fake.handle(
                method,
                url.path,
                parse_qs(url.query),
                self.headers,
                body,
            )
            root = None
            if url.path == "/graphql" and body:
                root = next(
                    (
                        r
                        for r in REQUIRED_SCOPES
                        if r in body.decode("utf-8", "replace")
                    ),
                    None,
                )
            with fake._lock:
                fake.requests.append((url.path, root, answer.status))
            payload = json.dumps(answer.body).encode()
            self.send_response(answer.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for name, value in answer.headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            self._serve("GET")

        def do_POST(self) -> None:
            self._serve("POST")

        def log_message(self, format: str, *args: Any) -> None:
            log.info("%s %s", self.address_string(), format % args)

    return Handler
