export interface EvaluatedTrace {
  id: string;
  traceId: string;
  evaluatedAt: string;
  result: "pass" | "fail" | "error";
  score: number | null;
  reason: string | null;
  latencyMs: number;
  inputTokens: number;
  outputTokens: number;
}

export interface LiveEvalConfig {
  evaluator: {
    name: string;
    version: number;
  };
  transform: {
    datasetId: string;
    name: string;
  };
  variables: Record<string, string>;
  filter: {
    spanTypes?: string[];
    metadata?: Record<string, string>;
  };
}

export interface LiveEvalDetail {
  id: string;
  name: string;
  status: "active" | "inactive";
  createdAt: string;
  updatedAt: string;
  config: LiveEvalConfig;
  stats: {
    totalEvaluated: number;
    passCount: number;
    failCount: number;
    errorCount: number;
    passRate: number;
    avgScore: number | null;
    evaluatedToday: number;
    avgLatencyMs: number;
  };
  evaluatedTraces: EvaluatedTrace[];
}
