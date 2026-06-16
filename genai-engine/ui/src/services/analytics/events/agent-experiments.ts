export interface AgentExperimentEvents {
  "agent_experiment/intent_create": { template_id: string | undefined };
  "agent_experiment/created": { experiment_id: string };
  "agent_experiment/deleted": { experiment_id: string };
  "agent_experiment/copied": { experiment_id: string | undefined };
}
