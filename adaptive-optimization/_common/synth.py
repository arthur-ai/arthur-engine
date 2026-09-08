"""Build synthetic spans directly in the engine's normalized `arthur_span_v1` shape.

The example_sessions generator round-trips through the engine's real
SpanNormalizationService; these POCs emit the normalized form directly so they
stay stdlib-only and runnable anywhere. The shape is the same either way —
nested OpenInference attributes, one flat span list per trace.
"""

import json
import random
from datetime import datetime, timedelta, timezone

SPAN_VERSION = "arthur_span_v1"


class IdGen:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def hex(self, nbytes: int) -> str:
        return "".join(self.rng.choice("0123456789abcdef") for _ in range(nbytes * 2))

    def trace(self) -> str:
        return self.hex(16)

    def span(self) -> str:
        return self.hex(8)


def _nest(flat: dict) -> dict:
    """Unflatten dotted attribute keys into the nested form, lists for digits."""
    root: dict = {}
    for key, value in flat.items():
        parts = key.split(".")
        cur = root
        for i, part in enumerate(parts[:-1]):
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value

    def listify(node):
        if isinstance(node, dict):
            keys = list(node.keys())
            if keys and all(k.isdigit() for k in keys):
                return [listify(node[k]) for k in sorted(keys, key=int)]
            return {k: listify(v) for k, v in node.items()}
        return node

    return listify(root)


def make_span(*, trace_id, span_id, parent_span_id=None, name, kind, start,
              duration_ms, flat_attrs, session_id=None, user_id=None,
              status="STATUS_CODE_OK", error=None) -> dict:
    flat = {"openinference.span.kind": kind}
    flat.update(flat_attrs)
    if session_id:
        flat["session.id"] = session_id
    if user_id:
        flat["user.id"] = user_id

    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": name,
        "kind": "SPAN_KIND_INTERNAL",
        "startTimeUnixNano": str(int(start.timestamp() * 1e9)),
        "endTimeUnixNano": str(int((start + timedelta(milliseconds=duration_ms)).timestamp() * 1e9)),
        "attributes": _nest(flat),
        "status": {"code": status},
        "arthur_span_version": SPAN_VERSION,
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id
    if error:
        span["status"]["message"] = error
    return span


def llm_attrs(*, model, system, user, output, prompt_tokens, completion_tokens,
              temperature=None, node_id=None, tool_calls=None, extra=None) -> dict:
    """Flat OpenInference attributes for an LLM span."""
    flat = {
        "llm.model_name": model,
        "llm.provider": "openai" if model.startswith("gpt") else "anthropic",
        "llm.token_count.prompt": prompt_tokens,
        "llm.token_count.completion": completion_tokens,
        "llm.token_count.total": prompt_tokens + completion_tokens,
        "llm.invocation_parameters.model": model,
        "llm.input_messages.0.message.role": "system",
        "llm.input_messages.0.message.content": system,
        "llm.input_messages.1.message.role": "user",
        "llm.input_messages.1.message.content": user,
        "input.mime_type": "application/json",
        "input.value": json.dumps({"messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}),
    }
    # Only present when the caller actually passed one — absence is meaningful.
    if temperature is not None:
        flat["llm.invocation_parameters.temperature"] = temperature
    if node_id:
        flat["graph.node.id"] = node_id
    flat["llm.output_messages.0.message.role"] = "assistant"
    if tool_calls:
        for j, tc in enumerate(tool_calls):
            p = f"llm.output_messages.0.message.tool_calls.{j}.tool_call"
            flat[f"{p}.id"] = tc["id"]
            flat[f"{p}.function.name"] = tc["name"]
            flat[f"{p}.function.arguments"] = json.dumps(tc["args"])
    else:
        flat["llm.output_messages.0.message.content"] = output
        flat["output.value"] = output
    if extra:
        flat.update(extra)
    return flat


def tool_attrs(*, name, args, result, description=None) -> dict:
    flat = {
        "tool.name": name,
        "input.mime_type": "application/json",
        "input.value": json.dumps(args),
        "output.mime_type": "application/json",
        "output.value": json.dumps(result),
    }
    if description:
        flat["tool.description"] = description
    return flat


def root_attrs(*, question, answer, agent=None, metadata=None) -> dict:
    flat = {"input.value": question, "output.value": answer}
    if agent:
        flat["agent.name"] = agent
        flat["graph.node.id"] = agent
    if metadata:
        flat["metadata"] = metadata
    return flat


def write_corpus(path: str, traces: list[dict], meta: dict | None = None) -> None:
    with open(path, "w") as fh:
        json.dump(traces, fh, indent=1)
        fh.write("\n")
    if meta is not None:
        with open(path.replace(".json", ".meta.json"), "w") as fh:
            json.dump(meta, fh, indent=2)
            fh.write("\n")
