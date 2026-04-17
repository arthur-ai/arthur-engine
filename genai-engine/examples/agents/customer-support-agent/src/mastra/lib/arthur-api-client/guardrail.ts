import { AISpanType } from "@mastra/core/ai-tracing";
import { getArthurApiClient } from "./client";

export interface GuardrailClaimResult {
  claim: string;
  valid: boolean;
  reason: string;
}

export interface GuardrailRuleResult {
  ruleId: string;
  ruleName: string;
  result: "Pass" | "Fail";
  claims?: GuardrailClaimResult[];
}

export interface GuardrailCheckResult {
  blocked: boolean;
  inferenceId: string;
  ruleResults: GuardrailRuleResult[];
  /** Human-readable explanation of why the response was blocked, if applicable */
  blockedReason?: string;
}

export type SimulatedViolationType =
  | "toxicity"
  | "pii";

/**
 * Appends a simulated guardrail violation to a response string.
 * Randomly picks a violation type unless one is specified.
 * Used to demonstrate Arthur's guardrail detection in a controlled way.
 */
export function injectSimulatedViolation(
  response: string,
  violationType?: SimulatedViolationType
): { response: string; violationType: SimulatedViolationType } {
  const types: SimulatedViolationType[] = [
    "toxicity",
    "pii",
  ];
  const chosen =
    violationType ?? types[Math.floor(Math.random() * types.length)];

  const injections: Record<SimulatedViolationType, string> = {
    toxicity:
      "\n\nFrankly, this is a completely idiotic question and anyone asking it is an absolute moron. " +
      "The documentation is blindingly obvious and you should feel ashamed for not reading it.",

    pii:
      "\n\nFor reference, the account linked to this query belongs to John Smith " +
      "(SSN: 123-45-6789, credit card: 4111-1111-1111-1111, email: john.smith@example.com, " +
      "phone: +1-555-867-5309).",
  };

  console.log("injectSimulatedViolation", { response, chosen, injections });

  return { response: response + injections[chosen], violationType: chosen };
}

/**
 * Validates a response against Arthur Engine guardrails.
 *
 * For hallucination detection, pass the ground-truth source material (e.g.
 * search results) as `context`. Arthur's hallucination rule compares each
 * claim in the response against the context and flags contradictions.
 *
 * Creates a child span named `spanName` (default "Guardrail") under the
 * current tracing context, rendered as an OpenInference GUARDRAIL span.
 *
 * Flow:
 *   1. POST /api/v2/tasks/{task_id}/validate_prompt  → get inference_id
 *   2. POST /api/v2/tasks/{task_id}/validate_response/{inference_id}
 *      with `response` + `context`
 */
export async function checkArthurGuardrails(
  prompt: string,
  response: string,
  context: string,
  tracingContext?: { currentSpan?: any },
  spanName = "Guardrail"
): Promise<GuardrailCheckResult> {
  const guardrailSpan = tracingContext?.currentSpan?.createChildSpan({
    type: AISpanType.GENERIC,
    name: spanName,
    input: { prompt, response, context },
    metadata: { type: "guardrail", source: "arthur" },
  });

  try {
    const api = getArthurApiClient();
    const taskId = process.env.ARTHUR_TASK_ID!;

    const promptResult =
      await api.api.validatePromptEndpointApiV2TasksTaskIdValidatePromptPost(
        taskId,
        { prompt }
      );

    const inferenceId = promptResult.data.inference_id;
    if (!inferenceId) {
      throw new Error("Arthur validate_prompt did not return an inference_id");
    }

    const responseResult =
      await api.api.validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost(
        inferenceId,
        taskId,
        { response, context }
      );

    const ruleResults: GuardrailRuleResult[] = (
      (responseResult.data.rule_results ?? []) as Array<any>
    ).map((r) => {
      const details = r.details as
        | { claims?: Array<{ claim: string; valid: boolean; reason: string }> }
        | null
        | undefined;
      return {
        ruleId: r.id,
        ruleName: r.name,
        result: r.result as "Pass" | "Fail",
        claims: details?.claims?.map((c) => ({
          claim: c.claim,
          valid: c.valid,
          reason: c.reason,
        })),
      };
    });

    const failedRules = ruleResults.filter((r) => r.result === "Fail");
    const blocked = failedRules.length > 0;

    let blockedReason: string | undefined;
    if (blocked) {
      blockedReason = failedRules
        .map((r) => {
          if (r.ruleName.toLowerCase().includes("hallucination") && r.claims) {
            const badClaims = r.claims
              .filter((c) => !c.valid)
              .map((c) => `"${c.claim}": ${c.reason}`)
              .join("; ");
            return `Hallucination detected — ${badClaims}`;
          }
          return `${r.ruleName} violation`;
        })
        .join("; ");
    }

    const result: GuardrailCheckResult = {
      blocked,
      inferenceId,
      ruleResults,
      blockedReason,
    };

    guardrailSpan?.end({
      output: result,
      metadata: { blocked, inferenceId, success: true },
    });

    return result;
  } catch (error) {
    guardrailSpan?.end({
      output: { error: error instanceof Error ? error.message : String(error) },
      metadata: { success: false },
    });
    throw error;
  }
}
