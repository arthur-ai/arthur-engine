# One VM Manager policy orchestrator at a folder or an organization, in place of the assignments:
# it creates and updates the same OS policy assignment in every project and zone in its scope.
# The folder and organization resources render one policy, the one assignments.tf renders, and
# a change to one rendering belongs in all three, and in local.carried.
#
# DESTROYING AN ORCHESTRATOR LEAVES ITS ASSIGNMENTS ENFORCING. To remove them, apply with
# orchestrator.action = "DELETE", wait for the orchestrator to finish, then remove this module.
#
# Its one-time setup is not here: the folder's or organization's service agents and their roles,
# a quota project in the provider, and a VPC Service Controls ingress rule where a perimeter
# applies. docs/mdm/gce.md has the commands.

data "google_project" "fleet" {
  for_each   = var.orchestrator == null ? toset([]) : toset(var.projects)
  project_id = each.key
}

locals {
  orchestrator_folder       = try(var.orchestrator.folder, null)
  orchestrator_organization = try(var.orchestrator.organization, null)
  orchestrator_upsert       = try(var.orchestrator.action, null) == "UPSERT"

  # Selectors take numbers. Projects and zones are separate selectors: the API refuses both in one.
  scope_projects = [for p in var.projects : "projects/${data.google_project.fleet[p].number}" if var.orchestrator != null]
  scope_folders  = [for f in try(var.orchestrator.include_folders, []) : "folders/${f}"]
}

resource "google_os_config_v2_policy_orchestrator_for_folder" "discovery" {
  count = local.orchestrator_folder == null ? 0 : 1

  folder_id              = local.orchestrator_folder
  policy_orchestrator_id = var.name
  description            = local.description
  action                 = var.orchestrator.action
  state                  = "ACTIVE"

  orchestrated_resource {
    # Named, because DELETE finds the assignments by it.
    id = var.name

    dynamic "os_policy_assignment_v1_payload" {
      for_each = local.orchestrator_upsert ? [1] : []
      content {
        description = local.description

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

                # The orchestrator's payload takes permissions, which an assignment's does not.
                dynamic "file" {
                  for_each = contains(keys(local.pins), resources.value.id) ? [resources.value.file] : []
                  content {
                    path        = file.value.path
                    state       = file.value.state
                    permissions = file.value.permissions
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
      }
    }
  }

  orchestration_scope {
    selectors {
      resource_hierarchy_selector {
        included_projects = length(local.scope_projects) > 0 ? local.scope_projects : null
        included_folders  = length(local.scope_folders) > 0 ? local.scope_folders : null
      }
    }
    selectors {
      location_selector {
        included_locations = var.zones
      }
    }
  }

  depends_on = [
    terraform_data.policy,
    google_project_service.osconfig,
    google_compute_project_metadata_item.discovery,
  ]
}

resource "google_os_config_v2_policy_orchestrator_for_organization" "discovery" {
  count = local.orchestrator_organization == null ? 0 : 1

  organization_id        = local.orchestrator_organization
  policy_orchestrator_id = var.name
  description            = local.description
  action                 = var.orchestrator.action
  state                  = "ACTIVE"

  orchestrated_resource {
    # Named, because DELETE finds the assignments by it.
    id = var.name

    dynamic "os_policy_assignment_v1_payload" {
      for_each = local.orchestrator_upsert ? [1] : []
      content {
        description = local.description

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

                # The orchestrator's payload takes permissions, which an assignment's does not.
                dynamic "file" {
                  for_each = contains(keys(local.pins), resources.value.id) ? [resources.value.file] : []
                  content {
                    path        = file.value.path
                    state       = file.value.state
                    permissions = file.value.permissions
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
      }
    }
  }

  orchestration_scope {
    selectors {
      resource_hierarchy_selector {
        included_projects = length(local.scope_projects) > 0 ? local.scope_projects : null
        included_folders  = length(local.scope_folders) > 0 ? local.scope_folders : null
      }
    }
    selectors {
      location_selector {
        included_locations = var.zones
      }
    }
  }

  depends_on = [
    terraform_data.policy,
    google_project_service.osconfig,
    google_compute_project_metadata_item.discovery,
  ]
}
