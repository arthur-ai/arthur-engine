export const DATA_TOUR = {
  CHATBOT_FAB: "chatbot-fab",
  CHATBOT_PANEL: "chatbot-panel",
  NAV_TRACES: "nav-traces",
  TRACES_TABLE: "traces-table",
  TRACE_DRAWER: "trace-drawer",
  NAV_DATASETS: "nav-datasets",
  DATASETS_TABLE: "datasets-table",
  NAV_PROMPTS: "nav-prompts",
  PROMPTS_TABLE: "prompts-table",
  CREATE_EXPERIMENT_BUTTON: "create-experiment-button",
} as const;

export type DataTourKey = keyof typeof DATA_TOUR;
export type DataTourValue = (typeof DATA_TOUR)[DataTourKey];

export const tourSelector = (key: DataTourKey): string => `[data-tour="${DATA_TOUR[key]}"]`;
