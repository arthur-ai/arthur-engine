export type AgentExperimentEndpoint = {
  id: string;
  name: string;
  url: string;
  headers: Record<string, string>;
  body: string;
  variables: string[];
};

export type AgentExperiment = {
  id: string;
  name: string;
  dataset_id: string;
  endpoint_id: string;
  /** Mapping between request body variables and dataset columns */
  variable_mapping: Record<string, string>;
  runtime_variable_mapping: Record<string, string>;
};
