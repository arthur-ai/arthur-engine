export interface AgentNotebookEvents {
  "agent_notebook/intent_create": undefined;
  "agent_notebook/intent_cancel": undefined;
  "agent_notebook/created": { notebook_id: string };
  "agent_notebook/experiment_run": { notebook_id: string; experiment_id: string };
  "agent_notebook/load_experiment_config": { experiment_id: string };
  "agent_notebook/save": { notebook_id: string };
  "agent_notebook/history_view": { notebook_id: string };
  "agent_notebook/deleted": { notebook_id: string };
}
