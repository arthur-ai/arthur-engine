import { v4 as uuidv4 } from "uuid";

import type { EvaluatedTrace } from "./types";

import { useTraces } from "@/hooks/traces/useTraces";
import { TraceMetadataResponse } from "@/lib/api-client/api-client";

const generateMockTraces = (traces: TraceMetadataResponse[]): EvaluatedTrace[] => {
  const now = Date.now();
  const results: EvaluatedTrace["result"][] = ["pass", "pass", "pass", "pass", "pass", "pass", "fail", "fail", "pass", "error"];
  const reasons = {
    pass: [
      "Response accurately reflects source context",
      "No hallucination detected",
      "All claims supported by provided context",
      "Response is factually consistent",
    ],
    fail: [
      "Response contains unsupported claims",
      "Detected factual inconsistency with context",
      "Model generated information not in source",
      "Hallucination detected in response",
    ],
    error: ["Evaluation timeout exceeded", "Failed to parse model response", null],
  };

  return traces.map((trace, i) => {
    const result = results[i % results.length];
    const reasonOptions = reasons[result];
    const reason = reasonOptions[Math.floor(Math.random() * reasonOptions.length)];

    return {
      id: uuidv4(),
      traceId: trace.trace_id,
      evaluatedAt: new Date(now - i * 45000 - Math.random() * 30000).toISOString(),
      result,
      score: result === "error" ? null : result === "pass" ? 0.7 + Math.random() * 0.3 : Math.random() * 0.5,
      reason,
      latencyMs: trace.duration_ms,
      inputTokens: trace.prompt_token_count ?? 0,
      outputTokens: trace.completion_token_count ?? 0,
    };
  });
};

const date = new Date();

export const useMockTraces = (taskId: string) => {
  const { data: traces } = useTraces({ taskId, page: 0, pageSize: 100, filters: [], timeRange: "3 months" });

  const mockTraces = generateMockTraces(traces?.traces ?? []);

  return {
    id: "mock-eval-id",
    name: "Production Hallucination Monitor",
    status: "active",
    createdAt: new Date(date.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: date.toISOString(),
    config: {
      evaluator: {
        name: "Hallucination Detector",
        version: 3,
      },
      transform: {
        datasetId: "ds-001",
        name: "Production Traces Transform",
      },
      variables: {
        user_query: "span.input",
        model_response: "span.output",
        context: "span.attributes.context",
      },
      filter: {
        spanTypes: ["llm", "chat"],
        metadata: {
          environment: "production",
        },
      },
    },
    stats: {
      totalEvaluated: 1247,
      passCount: 1089,
      failCount: 143,
      errorCount: 15,
      passRate: 87.3,
      avgScore: 0.84,
      evaluatedToday: 47,
      avgLatencyMs: 245,
    },
    evaluatedTraces: mockTraces,
  } as const;
};
