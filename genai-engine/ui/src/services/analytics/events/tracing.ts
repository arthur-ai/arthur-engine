type TraceLevel = "trace" | "span" | "session" | "user";
type TraceTimeRange = "5 minutes" | "30 minutes" | "1 day" | "1 week" | "1 month" | "3 months" | "1 year" | "all time";
type FilterOperator = "lt" | "lte" | "gt" | "gte" | "eq" | "in" | "not_in" | "contains" | "";

export interface TracingEvents {
  "tracing/level_changed": { task_id: string; from_level: TraceLevel; to_level: TraceLevel; time_range: TraceTimeRange };
  "tracing/time_range_changed": { task_id: string; level: TraceLevel; from_time_range: TraceTimeRange; to_time_range: TraceTimeRange };
  "tracing/drawer_opened": {
    task_id: string;
    level: TraceLevel;
    source: "table";
    trace_id?: string;
    span_id?: string;
    session_id?: string;
    user_id?: string;
  };
  "tracing/drawer_closed": { level: TraceLevel; id: string };
  "tracing/drawer_switch": { from_level: "span"; to_level: "trace"; span_id: string; trace_id: string; task_id: string };
  "tracing/filters_applied": { filter_count: number; filter_fields: string[]; filter_operators: FilterOperator[]; source: "filters_row" };
  "tracing/filters_cleared": { previous_filter_count: number; source: "filters_row" };
  "tracing/filters_from_url_loaded": { filter_count: number; source: "url" };
  "tracing/content_modal_opened": {
    level: "span" | "trace";
    trace_id: string | null | undefined;
    span_id: string | null | undefined;
    title: string;
    content_length: number;
  };
  "tracing/content_copied": {
    level: "span" | "trace";
    trace_id: string | null | undefined;
    span_id: string | null | undefined;
    title: string;
    content_length: number;
  };
  "tracing/id_copied": { level: TraceLevel; id_type: "trace" | "span" | "session" | "user"; id_value: string; source: "table" };
  "tracing/refresh_metrics_clicked": { level: "span" | "trace"; trace_id: string; task_id: string; span_id?: string };
  "tracing/refresh_metrics_result": {
    level: "span" | "trace";
    trace_id: string;
    task_id: string;
    success: boolean;
    span_id?: string;
    error_message?: string;
  };
}
