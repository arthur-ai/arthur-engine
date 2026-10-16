output "arthur_source" {
  description = "Fields for Arthur's gcp_compute_engine discovery source. project_ids lists var.projects only: add any project an orchestrator reaches through include_folders."
  value = {
    project_ids    = join(",", var.projects)
    include_labels = join(",", [for k, v in local.labels : "${k}=${v}"])
  }
}

output "os_policy_assignments" {
  description = "The OS policy assignments, one per project and zone, when no orchestrator is set."
  value       = [for a in google_os_config_os_policy_assignment.discovery : a.id]
}

output "policy_orchestrator" {
  description = "The policy orchestrator, when one is set."
  value = one(concat(
    google_os_config_v2_policy_orchestrator_for_folder.discovery[*].id,
    google_os_config_v2_policy_orchestrator_for_organization.discovery[*].id,
  ))
}

output "pinned_files" {
  description = "Each file the VMs download: its URL and the sha256 the OS policy holds it to."
  value       = { for id, p in local.pins : id => { uri = p.uri, sha256 = p.sha256 } }
}
