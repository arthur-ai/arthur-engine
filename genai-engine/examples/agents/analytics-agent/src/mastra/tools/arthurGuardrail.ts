import { AISpanType, TracingContext } from "@mastra/core/ai-tracing";
import { getArthurApiClient } from "@/mastra/lib/arthur-api-client/client";

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

/**
 * Validates an LLM response against Arthur Engine guardrails.
 *
 * Creates a child span named "Guardrail" under the current tracing context,
 * which will appear as an OpenInference GUARDRAIL span in Arthur's trace view.
 *
 * Flow:
 *   1. POST /api/v2/tasks/{task_id}/validate_prompt  → get inference_id
 *   2. POST /api/v2/tasks/{task_id}/validate_response/{inference_id}
 *      with `response` + `context` → Arthur runs hallucination rule
 */
export async function checkArthurGuardrails(
  prompt: string,
  response: string,
  context: string,
  tracingContext?: TracingContext,
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

    // Step 1 — register the prompt, get an inference_id
    const promptResult =
      await api.api.validatePromptEndpointApiV2TasksTaskIdValidatePromptPost(
        taskId,
        { prompt }
      );

    const inferenceId = promptResult.data.inference_id;
    if (!inferenceId) {
      throw new Error("Arthur validate_prompt did not return an inference_id");
    }

    // Step 2 — validate the response with the ground-truth context so the
    // hallucination rule can compare each claim against the actual data
    const responseResult =
      await api.api.validateResponseEndpointApiV2TasksTaskIdValidateResponseInferenceIdPost(
        inferenceId,
        taskId,
        { response, context }
      );

    const ruleResults: GuardrailRuleResult[] = (
      responseResult.data.rule_results ?? []
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
      const hallucinationFail = failedRules.find(
        (r) =>
          r.ruleName.toLowerCase().includes("hallucination") && r.claims?.length
      );
      if (hallucinationFail?.claims) {
        const badClaims = hallucinationFail.claims
          .filter((c) => !c.valid)
          .map((c) => `"${c.claim}": ${c.reason}`)
          .join("; ");
        blockedReason = `Hallucination detected — ${badClaims}`;
      } else {
        blockedReason = `Guardrail failed: ${failedRules.map((r) => r.ruleName).join(", ")}`;
      }
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
