# One OS policy assignment per project and zone: an assignment reaches only the VMs in its own
# zone. The orchestrator in orchestrator.tf renders the same policy; a change to one rendering
# belongs in both, and in local.carried.

resource "google_os_config_os_policy_assignment" "discovery" {
  for_each = var.orchestrator == null ? {
    for pz in setproduct(var.projects, var.zones) : "${pz[0]}/${pz[1]}" => { project = pz[0], zone = pz[1] }
  } : {}

  project     = each.value.project
  location    = each.value.zone
  name        = var.name
  description = local.description

  # A pin bump re-rolls every labelled VM at the policy's own pace, which on a fleet outlasts the
  # provider's timeout. VM Manager's compliance view shows the rollout instead.
  skip_await_rollout = true

  os_policies {
    id   = local.rendered.id
    mode = local.rendered.mode

    resource_groups {
      dynamic "inventory_filters" {
        for_each = local.rendered_group.inventoryFilters
        content {
          os_short_name = inventory_filters.value.osShortName
        }
      }

      dynamic "resources" {
        for_each = local.rendered_group.resources
        content {
          id = resources.value.id

          dynamic "repository" {
            for_each = can(resources.value.repository) ? [resources.value.repository.apt] : []
            content {
              apt {
                archive_type = repository.value.archiveType
                uri          = repository.value.uri
                distribution = repository.value.distribution
                components   = repository.value.components
                gpg_key      = repository.value.gpgKey
              }
            }
          }

          dynamic "pkg" {
            for_each = can(resources.value.pkg) ? [resources.value.pkg] : []
            content {
              desired_state = pkg.value.desiredState
              apt {
                name = pkg.value.apt.name
              }
            }
          }

          dynamic "exec" {
            for_each = can(resources.value.exec) ? [resources.value.exec] : []
            content {
              validate {
                interpreter = exec.value.validate.interpreter
                script      = exec.value.validate.script
              }
              enforce {
                interpreter = exec.value.enforce.interpreter
                script      = exec.value.enforce.script
              }
            }
          }

          # No permissions: the provider makes them output-only on an assignment, so every file
          # lands at the API default of 755. The scripts need that; systemd warns that the units
          # are executable and loads them.
          dynamic "file" {
            for_each = contains(keys(local.pins), resources.value.id) ? [resources.value.file] : []
            content {
              path  = file.value.path
              state = file.value.state
              file {
                remote {
                  uri             = local.pins[resources.value.id].uri
                  sha256_checksum = local.pins[resources.value.id].sha256
                }
              }
            }
          }
        }
      }
    }
  }

  instance_filter {
    inclusion_labels {
      labels = local.labels
    }
  }

  rollout {
    disruption_budget {
      percent = local.rollout.disruptionBudget.percent
    }
    min_wait_duration = local.rollout.minWaitDuration
  }

  depends_on = [
    terraform_data.policy,
    google_project_service.osconfig,
    google_compute_project_metadata_item.discovery,
  ]
}
