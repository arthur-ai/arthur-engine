import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";

import { flattenSpans, getNestedValue, getSpanOutput, getSpanType } from "./spans";

import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { RuleResultEnum } from "@/lib/api-client/api-client";

/**
 * Guardrail-invocation parsing for the trace viewer.
 *
 * Guardrail outcomes ride inside OpenInference `GUARDRAIL` spans as JSON under
 * `raw_data.attributes.output.value`. Two payload dialects exist and are both
 * handled here:
 *  - snake_case (stateful `/validate`): `{ blocked, blocked_reason, rule_results: [ExternalRuleResult] }`
 *  - camelCase (instrumented apps):     `{ blocked, blockedReason, ruleResults: [{ ruleName, result, ... }] }`
 */

export type GuardrailStatus = "passed" | "failed" | "degraded";

export type GuardrailRuleResult = {
  name: string;
  result: RuleResultEnum;
};

export type GuardrailInvocation = {
  spanId: string;
  /** Span name, e.g. "prompt-shield" (instrumented) or "guardrail.validate_prompt" (stateful). */
  name: string;
  /** Name of the span this guardrail ran under, e.g. "agent.invoke nda-summarizer". */
  parentSpanName?: string;
  ruleCount: number;
  status: GuardrailStatus;
  blocked: boolean;
  blockedReason?: string;
  ruleResults: GuardrailRuleResult[];
};

export type GuardrailSummary = {
  total: number;
  passed: number;
  failed: number;
  degraded: number;
};

/** Rule outcomes that mean a rule could not be fully evaluated (no hard failure). */
const DEGRADED_RESULTS: ReadonlySet<RuleResultEnum> = new Set<RuleResultEnum>([
  "Skipped",
  "Unavailable",
  "Partially Unavailable",
  "Model Not Available",
]);

const RULE_RESULT_VALUES: ReadonlySet<string> = new Set<RuleResultEnum>([
  "Pass",
  "Fail",
  "Skipped",
  "Unavailable",
  "Partially Unavailable",
  "Model Not Available",
]);

type RawRule = {
  name?: unknown;
  ruleName?: unknown;
  result?: unknown;
};

type RawGuardrailPayload = {
  blocked?: unknown;
  blocked_reason?: unknown;
  blockedReason?: unknown;
  rule_results?: unknown;
  ruleResults?: unknown;
};

const tryParseJson = (value: string): unknown => {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
};

const coerceRuleResult = (value: unknown): RuleResultEnum | null =>
  typeof value === "string" && RULE_RESULT_VALUES.has(value) ? (value as RuleResultEnum) : null;

/**
 * Reads the guardrail payload from a span. Prefers the shared `getSpanOutput`
 * extractor (returns the `output.value` string); falls back to reading the
 * nested attribute directly, which may already be a parsed object.
 */
const readGuardrailPayload = (span: NestedSpanWithMetricsResponse): RawGuardrailPayload | null => {
  const output = getSpanOutput(span);
  let raw: unknown = typeof output === "string" ? tryParseJson(output) : output;

  if (raw == null) {
    const fallback = getNestedValue<unknown>(span.raw_data, "attributes.output.value");
    raw = typeof fallback === "string" ? tryParseJson(fallback) : (fallback ?? null);
  }

  return raw != null && typeof raw === "object" ? (raw as RawGuardrailPayload) : null;
};

const normalizeRuleResults = (payload: RawGuardrailPayload): GuardrailRuleResult[] => {
  const rawRules = payload.rule_results ?? payload.ruleResults;
  if (!Array.isArray(rawRules)) return [];

  const rules: GuardrailRuleResult[] = [];
  for (const entry of rawRules) {
    if (!entry || typeof entry !== "object") continue;
    const rule = entry as RawRule;
    const result = coerceRuleResult(rule.result);
    if (!result) continue;
    const name = typeof rule.name === "string" ? rule.name : typeof rule.ruleName === "string" ? rule.ruleName : "Rule";
    rules.push({ name, result });
  }
  return rules;
};

/**
 * 3-state rollup: a hard `Fail` (or an explicit block) is `failed`; otherwise a
 * rule that could not be evaluated is `degraded`; otherwise `passed`.
 */
export const deriveGuardrailStatus = (ruleResults: GuardrailRuleResult[], blocked: boolean): GuardrailStatus => {
  if (blocked || ruleResults.some((r) => r.result === "Fail")) return "failed";
  if (ruleResults.some((r) => DEGRADED_RESULTS.has(r.result))) return "degraded";
  return "passed";
};

/**
 * Parses a single span into a guardrail invocation. Returns `null` when the
 * span is not a `GUARDRAIL` span or carries no parseable guardrail payload.
 * `parentSpanName` is resolved by {@link extractGuardrailInvocations}.
 */
export const parseGuardrailSpan = (span: NestedSpanWithMetricsResponse): Omit<GuardrailInvocation, "parentSpanName"> | null => {
  if (getSpanType(span) !== OpenInferenceSpanKind.GUARDRAIL) return null;

  const payload = readGuardrailPayload(span);
  if (!payload) return null;

  const ruleResults = normalizeRuleResults(payload);
  const blocked = payload.blocked === true;
  const blockedReason =
    typeof payload.blocked_reason === "string"
      ? payload.blocked_reason
      : typeof payload.blockedReason === "string"
        ? payload.blockedReason
        : undefined;

  return {
    spanId: span.span_id,
    name: span.span_name ?? "guardrail",
    ruleCount: ruleResults.length,
    status: deriveGuardrailStatus(ruleResults, blocked),
    blocked,
    blockedReason,
    ruleResults,
  };
};

/**
 * Walks the trace's span tree and returns one entry per guardrail invocation,
 * each annotated with the name of the span it ran under.
 */
export const extractGuardrailInvocations = (rootSpans: NestedSpanWithMetricsResponse[]): GuardrailInvocation[] => {
  const flat = flattenSpans(rootSpans);

  const nameBySpanId = new Map<string, string>();
  for (const span of flat) {
    if (span.span_name) nameBySpanId.set(span.span_id, span.span_name);
  }

  const invocations: GuardrailInvocation[] = [];
  for (const span of flat) {
    const parsed = parseGuardrailSpan(span);
    if (!parsed) continue;
    const parentSpanName = span.parent_span_id ? nameBySpanId.get(span.parent_span_id) : undefined;
    invocations.push({ ...parsed, parentSpanName });
  }
  return invocations;
};

export const summarizeGuardrails = (invocations: GuardrailInvocation[]): GuardrailSummary =>
  invocations.reduce<GuardrailSummary>(
    (acc, inv) => {
      acc.total += 1;
      acc[inv.status] += 1;
      return acc;
    },
    { total: 0, passed: 0, failed: 0, degraded: 0 }
  );
