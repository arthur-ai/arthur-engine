export interface TaskEvents {
  // "Create their own task" activation milestone. Distinct from the demo
  // task, which is provisioned server-side during onboarding (`signup.task_id`)
  // and never fires this event.
  "task/created": { task_id: string; is_agentic: boolean; source: "create_task_form" };
}
