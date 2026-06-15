export interface CrossLinkEvents {
  "playground/open_from_span": { task_id: string; span_id: string; trace_id: string; source: "span_drawer" };
  "continuous_evals/new_from_trace": { task_id: string; trace_id: string; source: "trace_actions" };
}
