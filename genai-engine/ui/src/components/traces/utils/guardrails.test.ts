import { describe, expect, it } from "vitest";

import { type GuardrailInvocation, deriveGuardrailStatus, extractGuardrailInvocations, parseGuardrailSpan, summarizeGuardrails } from "./guardrails";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

const makeSpan = (overrides: Partial<NestedSpanWithMetricsResponse>): NestedSpanWithMetricsResponse => ({
  id: "id",
  span_id: "span",
  trace_id: "trace",
  start_time: "2026-06-05T00:00:00Z",
  end_time: "2026-06-05T00:00:01Z",
  created_at: "2026-06-05T00:00:00Z",
  updated_at: "2026-06-05T00:00:00Z",
  status_code: "Ok",
  raw_data: {},
  ...overrides,
});

/**
 * Builds the unflattened OpenInference attributes a span carries after
 * ingestion: span kind at `openinference.span.kind`, output JSON at
 * `output.value`.
 */
const rawData = (kind: string, outputValue?: unknown) => ({
  attributes: {
    openinference: { span: { kind } },
    ...(outputValue === undefined ? {} : { output: { value: outputValue } }),
  },
});

/** A GUARDRAIL span carrying `payload` at output.value (stringified by default). */
const guardrailSpan = (payload: unknown, overrides: Partial<NestedSpanWithMetricsResponse> = {}, asString = true): NestedSpanWithMetricsResponse =>
  makeSpan({
    span_name: "prompt-shield",
    raw_data: rawData("GUARDRAIL", asString ? JSON.stringify(payload) : payload),
    ...overrides,
  });

describe("parseGuardrailSpan", () => {
  it("parses the snake_case (stateful validate) dialect", () => {
    const span = guardrailSpan({
      blocked: false,
      blocked_reason: null,
      inference_id: "inf-1",
      rule_results: [
        { id: "r1", name: "PII", result: "Pass" },
        { id: "r2", name: "Toxicity", result: "Pass" },
      ],
    });

    const result = parseGuardrailSpan(span);

    expect(result).not.toBeNull();
    expect(result?.name).toBe("prompt-shield");
    expect(result?.ruleCount).toBe(2);
    expect(result?.status).toBe("passed");
    expect(result?.ruleResults).toEqual([
      { name: "PII", result: "Pass" },
      { name: "Toxicity", result: "Pass" },
    ]);
  });

  it("parses the camelCase (instrumented app) dialect", () => {
    const span = guardrailSpan(
      {
        blocked: true,
        blockedReason: "Prompt injection detected",
        ruleResults: [
          { ruleId: "r1", ruleName: "prompt-injection", result: "Fail" },
          { ruleId: "r2", ruleName: "pii", result: "Pass" },
        ],
      },
      { span_name: "response-quality" }
    );

    const result = parseGuardrailSpan(span);

    expect(result?.name).toBe("response-quality");
    expect(result?.ruleCount).toBe(2);
    expect(result?.status).toBe("failed");
    expect(result?.blocked).toBe(true);
    expect(result?.blockedReason).toBe("Prompt injection detected");
    expect(result?.ruleResults[0]).toEqual({ name: "prompt-injection", result: "Fail" });
  });

  it("reports degraded when a rule could not be evaluated and none failed", () => {
    const span = guardrailSpan({
      blocked: false,
      rule_results: [
        { name: "PII", result: "Pass" },
        { name: "Toxicity", result: "Unavailable" },
      ],
    });

    expect(parseGuardrailSpan(span)?.status).toBe("degraded");
  });

  it("accepts an already-parsed (non-stringified) payload object", () => {
    const span = guardrailSpan({ blocked: false, rule_results: [{ name: "PII", result: "Pass" }] }, {}, false);

    expect(parseGuardrailSpan(span)?.status).toBe("passed");
  });

  it("returns null for non-guardrail spans", () => {
    const span = makeSpan({ raw_data: rawData("LLM", "{}") });

    expect(parseGuardrailSpan(span)).toBeNull();
  });

  it("returns null when the payload is not valid JSON", () => {
    const span = makeSpan({ raw_data: rawData("GUARDRAIL", "not-json") });

    expect(parseGuardrailSpan(span)).toBeNull();
  });
});

describe("deriveGuardrailStatus", () => {
  it("is failed when blocked, even with no failing rule", () => {
    expect(deriveGuardrailStatus([{ name: "PII", result: "Pass" }], true)).toBe("failed");
  });

  it("is failed on any Fail result", () => {
    expect(deriveGuardrailStatus([{ name: "PII", result: "Fail" }], false)).toBe("failed");
  });

  it("is degraded on Skipped/Unavailable with no failure", () => {
    expect(deriveGuardrailStatus([{ name: "PII", result: "Skipped" }], false)).toBe("degraded");
    expect(deriveGuardrailStatus([{ name: "PII", result: "Model Not Available" }], false)).toBe("degraded");
  });

  it("is passed when every rule passes", () => {
    expect(deriveGuardrailStatus([{ name: "PII", result: "Pass" }], false)).toBe("passed");
  });
});

describe("extractGuardrailInvocations", () => {
  it("collects guardrail spans and resolves the parent span name", () => {
    const child = guardrailSpan({ blocked: false, rule_results: [{ name: "PII", result: "Pass" }] }, { span_id: "g1", parent_span_id: "a1" });
    const agent = makeSpan({
      span_id: "a1",
      span_name: "agent.invoke nda-summarizer",
      raw_data: rawData("AGENT"),
      children: [child],
    });

    const result = extractGuardrailInvocations([agent]);

    expect(result).toHaveLength(1);
    expect(result[0].spanId).toBe("g1");
    expect(result[0].parentSpanName).toBe("agent.invoke nda-summarizer");
  });

  it("ignores non-guardrail and unparseable spans", () => {
    const llm = makeSpan({ span_id: "l1", raw_data: rawData("LLM", "{}") });
    const bad = makeSpan({ span_id: "b1", raw_data: rawData("GUARDRAIL") });

    expect(extractGuardrailInvocations([llm, bad])).toEqual([]);
  });
});

describe("summarizeGuardrails", () => {
  it("counts invocations by status", () => {
    const invocations = [{ status: "passed" }, { status: "failed" }, { status: "degraded" }, { status: "passed" }] as GuardrailInvocation[];

    expect(summarizeGuardrails(invocations)).toEqual({ total: 4, passed: 2, failed: 1, degraded: 1 });
  });
});
