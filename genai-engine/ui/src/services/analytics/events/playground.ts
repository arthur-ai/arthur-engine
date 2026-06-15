export interface PlaygroundEvents {
  "Run All Prompts": { prompt_count: number; config_mode: boolean };
  "Prompt Saved": { prompt_name: string; version: number | undefined; message_count: number; has_tools: boolean };
  "Prompt Loaded": { prompt_name: string; version: number; source: "selector" };
  "Prompt Run": {
    model_provider: string;
    model_name: string;
    message_count: number;
    has_tools: boolean;
    is_streaming: boolean;
    config_mode: boolean;
  };
  "Prompt Preview": { model_provider: string; model_name: string; message_count: number };
  "Experiment Config Created": { dataset_id: string | undefined; eval_count: number; prompt_count: number; has_row_filter: boolean };
  "Experiment Run Started": { prompt_count: number; dataset_id: string | undefined; eval_count: number };
  "Model Params Changed": { model_provider: string | undefined; model_name: string | undefined; param_count: number };
  "Tool Added": { prompt_id: string; tool_count: number };
  "Tool Removed": { prompt_id: string; tool_name: string | undefined; tool_count: number };
  "Output Field Changed": { prompt_id: string; has_schema: boolean };
  "Variable Value Changed": { variable_name: string; has_value: boolean };
  "Notebook Loaded": { notebook_id: string | null; prompt_count: number; has_config: boolean };
  "Notebook Saved": { notebook_id: string; prompt_count: number; save_trigger: "auto" | "manual" };
  "Notebook Renamed": { notebook_id: string };
}
