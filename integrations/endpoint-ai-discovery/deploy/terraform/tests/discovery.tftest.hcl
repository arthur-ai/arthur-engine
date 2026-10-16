# `terraform test` from deploy/terraform. Mocked providers: no credentials, no network, nothing
# created. What is asserted is what this module decides -- which resources, in which scope, and
# that the policy every one of them renders is the file's, pinned to the bytes beside it. Whether
# VM Manager then applies that policy is the runbook's acceptance check, on a real VM.

mock_provider "google" {}
mock_provider "http" {}

variables {
  arthur_engine_ref = "2.1.999"
  projects          = ["fleet-one", "fleet-two"]
  zones             = ["us-central1-a", "europe-west1-b"]
  verify_file_urls  = false

  # THE POLICY FILE AS EVERY RENDERING MUST CARRY IT: each file at its URL at the ref above, with
  # the sha256 of the copy beside the module. Each rendering is mapped back to the file's shape and
  # compared with this whole, so no field can drift without a run failing. An assignment cannot
  # set file modes, so it is compared with the same policy less them.
  pinned_policy = merge(yamldecode(file("../arthur-ai-discovery.os-policy.yaml")), {
    osPolicies = [for p in yamldecode(file("../arthur-ai-discovery.os-policy.yaml")).osPolicies : merge(p, {
      resourceGroups = [for g in p.resourceGroups : merge(g, {
        resources = [for r in g.resources : merge(r, { for f in try([r.file], []) : "file" => merge(f, { file = { remote = {
          uri            = replace(f.file.remote.uri, "arthur-engine/COMMIT", "arthur-engine/2.1.999")
          sha256Checksum = filesha256("../../${trimprefix(f.file.remote.uri, "https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/")}")
        } } }) })]
      })]
    })]
  })
  pinned_policy_without_modes = merge(yamldecode(file("../arthur-ai-discovery.os-policy.yaml")), {
    osPolicies = [for p in yamldecode(file("../arthur-ai-discovery.os-policy.yaml")).osPolicies : merge(p, {
      resourceGroups = [for g in p.resourceGroups : merge(g, {
        resources = [for r in g.resources : merge(r, { for f in try([r.file], []) : "file" => merge({ for k, v in f : k => v if k != "permissions" }, { file = { remote = {
          uri            = replace(f.file.remote.uri, "arthur-engine/COMMIT", "arthur-engine/2.1.999")
          sha256Checksum = filesha256("../../${trimprefix(f.file.remote.uri, "https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/")}")
        } } }) })]
      })]
    })]
  })
}

run "an_assignment_per_project_and_zone" {
  command = plan

  assert {
    condition = toset(keys(google_os_config_os_policy_assignment.discovery)) == toset([
      "fleet-one/us-central1-a", "fleet-one/europe-west1-b",
      "fleet-two/us-central1-a", "fleet-two/europe-west1-b",
    ])
    error_message = "Expected one assignment per project and zone."
  }
  assert {
    condition     = google_os_config_os_policy_assignment.discovery["fleet-two/europe-west1-b"].project == "fleet-two" && google_os_config_os_policy_assignment.discovery["fleet-two/europe-west1-b"].location == "europe-west1-b"
    error_message = "An assignment is not in the project and zone its key names."
  }
  # The whole policy, as each assignment renders it. VM Manager applies a group's resources in
  # sequence, so the order is part of the comparison.
  assert {
    condition = alltrue([for a in google_os_config_os_policy_assignment.discovery : jsonencode({
      osPolicies = [for p in a.os_policies : {
        id   = p.id
        mode = p.mode
        resourceGroups = [for g in p.resource_groups : {
          inventoryFilters = [for f in g.inventory_filters : { osShortName = f.os_short_name }]
          resources = [for r in g.resources : merge(
            { id = r.id },
            { for x in r.repository : "repository" => { apt = { archiveType = x.apt[0].archive_type, uri = x.apt[0].uri, distribution = x.apt[0].distribution, components = x.apt[0].components, gpgKey = x.apt[0].gpg_key } } },
            { for x in r.pkg : "pkg" => { desiredState = x.desired_state, apt = { name = x.apt[0].name } } },
            { for x in r.exec : "exec" => {
              validate = { interpreter = x.validate[0].interpreter, script = x.validate[0].script }
              enforce  = { interpreter = x.enforce[0].interpreter, script = x.enforce[0].script }
            } },
            { for x in r.file : "file" => { path = x.path, state = x.state, file = { remote = { uri = x.file[0].remote[0].uri, sha256Checksum = x.file[0].remote[0].sha256_checksum } } } },
          )]
        }]
      }]
      instanceFilter = { inclusionLabels = [for l in a.instance_filter[0].inclusion_labels : { labels = l.labels }] }
      rollout        = { disruptionBudget = { percent = a.rollout[0].disruption_budget[0].percent }, minWaitDuration = a.rollout[0].min_wait_duration }
    }) == jsonencode(var.pinned_policy_without_modes)])
    error_message = "An assignment does not render the policy file, pinned to this tree at the ref."
  }
  assert {
    condition     = google_os_config_os_policy_assignment.discovery["fleet-one/us-central1-a"].skip_await_rollout
    error_message = "A fleet rollout outlasts the provider's timeout; the assignment must not wait for it."
  }
  assert {
    condition     = length(google_os_config_v2_policy_orchestrator_for_folder.discovery) + length(google_os_config_v2_policy_orchestrator_for_organization.discovery) == 0
    error_message = "No orchestrator without var.orchestrator."
  }
  assert {
    condition = toset([for m in google_compute_project_metadata_item.discovery : "${m.project} ${m.key}=${m.value}"]) == toset([
      "fleet-one enable-guest-attributes=TRUE", "fleet-one enable-osconfig=TRUE",
      "fleet-two enable-guest-attributes=TRUE", "fleet-two enable-osconfig=TRUE",
    ])
    error_message = "Expected enable-osconfig and enable-guest-attributes TRUE in both projects."
  }
  assert {
    condition     = toset(keys(google_project_service.osconfig)) == toset(["fleet-one", "fleet-two"]) && !google_project_service.osconfig["fleet-one"].disable_on_destroy
    error_message = "Expected the OS Config API in both projects, left enabled on destroy."
  }
  assert {
    condition     = length(google_project_iam_member.reader) == 0
    error_message = "No grant without var.reader."
  }
  assert {
    condition     = output.arthur_source == { project_ids = "fleet-one,fleet-two", include_labels = "arthur-ai-discovery=enabled" }
    error_message = "arthur_source does not name the projects and the label."
  }
}

run "each_file_is_pinned_to_the_copy_beside_the_module" {
  command = plan

  assert {
    condition = output.pinned_files == {
      collector = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/dist/collect-linux.sh", sha256 = filesha256("../../dist/collect-linux.sh") }
      reporter  = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/deploy/report-guest-attributes.sh", sha256 = filesha256("../report-guest-attributes.sh") }
      service   = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/deploy/arthur-ai-discovery.service", sha256 = filesha256("../arthur-ai-discovery.service") }
      timer     = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/deploy/arthur-ai-discovery.timer", sha256 = filesha256("../arthur-ai-discovery.timer") }
    }
    error_message = "A file is not pinned to its URL at the ref and the sha256 of this tree's copy."
  }
}

run "a_mirror_serves_the_files" {
  command = plan

  variables {
    file_base_url = "https://mirror.example.com/endpoint-ai-discovery/"
  }

  assert {
    condition = [
      for r in google_os_config_os_policy_assignment.discovery["fleet-one/us-central1-a"].os_policies[0].resource_groups[0].resources :
      r.file[0].file[0].remote[0].uri if length(r.file) > 0
      ] == [
      "https://mirror.example.com/endpoint-ai-discovery/dist/collect-linux.sh",
      "https://mirror.example.com/endpoint-ai-discovery/deploy/report-guest-attributes.sh",
      "https://mirror.example.com/endpoint-ai-discovery/deploy/arthur-ai-discovery.service",
      "https://mirror.example.com/endpoint-ai-discovery/deploy/arthur-ai-discovery.timer",
    ]
    error_message = "file_base_url does not replace the GitHub URL, path for path, in what the VMs download."
  }
}

run "a_label_and_a_reader" {
  command = plan

  variables {
    label  = { key = "ai-inventory", value = "on" }
    reader = "serviceAccount:arthur@reader-project.iam.gserviceaccount.com"
  }

  assert {
    condition     = alltrue([for a in google_os_config_os_policy_assignment.discovery : a.instance_filter[0].inclusion_labels[0].labels == tomap({ ai-inventory = "on" })])
    error_message = "label does not replace the policy's label."
  }
  assert {
    condition     = output.arthur_source.include_labels == "ai-inventory=on"
    error_message = "arthur_source does not carry the label the assignments target."
  }
  assert {
    condition     = toset([for m in google_project_iam_member.reader : "${m.project} ${m.role} ${m.member}"]) == toset(["fleet-one roles/compute.viewer serviceAccount:arthur@reader-project.iam.gserviceaccount.com", "fleet-two roles/compute.viewer serviceAccount:arthur@reader-project.iam.gserviceaccount.com"])
    error_message = "reader is not granted roles/compute.viewer in each project."
  }
}

# A project that already holds enable-osconfig, as Google's VM Manager setup leaves it.
run "a_metadata_key_left_out" {
  command = plan

  variables {
    project_metadata = ["enable-guest-attributes"]
  }

  assert {
    condition     = toset(keys(google_compute_project_metadata_item.discovery)) == toset(["fleet-one/enable-guest-attributes", "fleet-two/enable-guest-attributes"])
    error_message = "project_metadata does not limit the keys this module creates."
  }
}

run "metadata_and_apis_left_alone" {
  command = plan

  variables {
    project_metadata = []
    enable_apis      = false
  }

  assert {
    condition     = length(google_compute_project_metadata_item.discovery) == 0 && length(google_project_service.osconfig) == 0
    error_message = "project_metadata and enable_apis do not turn their resources off."
  }
}

run "a_folder_orchestrator" {
  command = plan

  variables {
    orchestrator = { folder = "123456789012", include_folders = ["555"] }
  }

  override_data {
    target = data.google_project.fleet["fleet-one"]
    values = { number = "1111" }
  }
  override_data {
    target = data.google_project.fleet["fleet-two"]
    values = { number = "2222" }
  }

  assert {
    condition     = length(google_os_config_os_policy_assignment.discovery) == 0 && length(google_os_config_v2_policy_orchestrator_for_organization.discovery) == 0
    error_message = "An orchestrator replaces the assignments."
  }
  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_folder.discovery[0].folder_id == "123456789012" && google_os_config_v2_policy_orchestrator_for_folder.discovery[0].action == "UPSERT" && google_os_config_v2_policy_orchestrator_for_folder.discovery[0].state == "ACTIVE"
    error_message = "Expected an active UPSERT orchestrator at the folder."
  }
  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestrated_resource[0].id == "arthur-ai-discovery"
    error_message = "The orchestrated resource must be named: DELETE finds the assignments by it."
  }
  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestration_scope[0].selectors[0].resource_hierarchy_selector[0].included_projects == tolist(["projects/1111", "projects/2222"])
    error_message = "The scope does not name the projects by number."
  }
  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestration_scope[0].selectors[0].resource_hierarchy_selector[0].included_folders == tolist(["folders/555"])
    error_message = "The scope does not name include_folders."
  }
  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestration_scope[0].selectors[1].location_selector[0].included_locations == tolist(["us-central1-a", "europe-west1-b"])
    error_message = "The zones are not their own selector."
  }
  # The whole policy, file modes included: the orchestrator can set what an assignment cannot.
  assert {
    condition = jsonencode({
      for a in google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestrated_resource[0].os_policy_assignment_v1_payload : "doc" => {
        osPolicies = [for p in a.os_policies : {
          id   = p.id
          mode = p.mode
          resourceGroups = [for g in p.resource_groups : {
            inventoryFilters = [for f in g.inventory_filters : { osShortName = f.os_short_name }]
            resources = [for r in g.resources : merge(
              { id = r.id },
              { for x in r.repository : "repository" => { apt = { archiveType = x.apt[0].archive_type, uri = x.apt[0].uri, distribution = x.apt[0].distribution, components = x.apt[0].components, gpgKey = x.apt[0].gpg_key } } },
              { for x in r.pkg : "pkg" => { desiredState = x.desired_state, apt = { name = x.apt[0].name } } },
              { for x in r.exec : "exec" => {
                validate = { interpreter = x.validate[0].interpreter, script = x.validate[0].script }
                enforce  = { interpreter = x.enforce[0].interpreter, script = x.enforce[0].script }
              } },
              { for x in r.file : "file" => { path = x.path, state = x.state, permissions = x.permissions, file = { remote = { uri = x.file[0].remote[0].uri, sha256Checksum = x.file[0].remote[0].sha256_checksum } } } },
            )]
          }]
        }]
        instanceFilter = { inclusionLabels = [for l in a.instance_filter[0].inclusion_labels : { labels = l.labels }] }
        rollout        = { disruptionBudget = { percent = a.rollout[0].disruption_budget[0].percent }, minWaitDuration = a.rollout[0].min_wait_duration }
      }
    }) == jsonencode({ doc = var.pinned_policy })
    error_message = "The folder orchestrator does not render the policy file, pinned to this tree at the ref."
  }
  assert {
    condition     = length(google_compute_project_metadata_item.discovery) == 4
    error_message = "The projects still need their metadata under an orchestrator."
  }
}

run "an_organization_orchestrator" {
  command = plan

  variables {
    orchestrator = { organization = "987654321" }
  }

  assert {
    condition     = length(google_os_config_v2_policy_orchestrator_for_folder.discovery) == 0 && google_os_config_v2_policy_orchestrator_for_organization.discovery[0].organization_id == "987654321" && google_os_config_v2_policy_orchestrator_for_organization.discovery[0].action == "UPSERT"
    error_message = "Expected an UPSERT orchestrator at the organization."
  }
  assert {
    condition = jsonencode({
      for a in google_os_config_v2_policy_orchestrator_for_organization.discovery[0].orchestrated_resource[0].os_policy_assignment_v1_payload : "doc" => {
        osPolicies = [for p in a.os_policies : {
          id   = p.id
          mode = p.mode
          resourceGroups = [for g in p.resource_groups : {
            inventoryFilters = [for f in g.inventory_filters : { osShortName = f.os_short_name }]
            resources = [for r in g.resources : merge(
              { id = r.id },
              { for x in r.repository : "repository" => { apt = { archiveType = x.apt[0].archive_type, uri = x.apt[0].uri, distribution = x.apt[0].distribution, components = x.apt[0].components, gpgKey = x.apt[0].gpg_key } } },
              { for x in r.pkg : "pkg" => { desiredState = x.desired_state, apt = { name = x.apt[0].name } } },
              { for x in r.exec : "exec" => {
                validate = { interpreter = x.validate[0].interpreter, script = x.validate[0].script }
                enforce  = { interpreter = x.enforce[0].interpreter, script = x.enforce[0].script }
              } },
              { for x in r.file : "file" => { path = x.path, state = x.state, permissions = x.permissions, file = { remote = { uri = x.file[0].remote[0].uri, sha256Checksum = x.file[0].remote[0].sha256_checksum } } } },
            )]
          }]
        }]
        instanceFilter = { inclusionLabels = [for l in a.instance_filter[0].inclusion_labels : { labels = l.labels }] }
        rollout        = { disruptionBudget = { percent = a.rollout[0].disruption_budget[0].percent }, minWaitDuration = a.rollout[0].min_wait_duration }
      }
    }) == jsonencode({ doc = var.pinned_policy })
    error_message = "The organization orchestrator does not render the policy file, pinned to this tree at the ref."
  }
}

run "an_organization_orchestrator_deleting" {
  command = plan

  variables {
    orchestrator = { organization = "987654321", action = "DELETE" }
  }

  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_organization.discovery[0].action == "DELETE" && length(google_os_config_v2_policy_orchestrator_for_organization.discovery[0].orchestrated_resource[0].os_policy_assignment_v1_payload) == 0
    error_message = "DELETE takes the orchestrated resource's name and no payload."
  }
}

# Folders alone: the orchestrator reaches projects this module was not given.
run "an_orchestrator_scoped_by_folders_alone" {
  command = plan

  variables {
    projects     = []
    orchestrator = { folder = "123456789012", include_folders = ["555"] }
  }

  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestration_scope[0].selectors[0].resource_hierarchy_selector[0].included_projects == null
    error_message = "No projects should mean no project selector, not an empty one."
  }
  assert {
    condition     = output.arthur_source.project_ids == null
    error_message = "arthur_source should name no projects rather than an empty list the source refuses."
  }
}

run "verified_files_match" {
  command = plan

  variables {
    verify_file_urls = true
  }

  override_data {
    target = data.http.file["collector"]
    values = { status_code = 200, response_body = file("../../dist/collect-linux.sh") }
  }
  override_data {
    target = data.http.file["reporter"]
    values = { status_code = 200, response_body = file("../report-guest-attributes.sh") }
  }
  override_data {
    target = data.http.file["service"]
    values = { status_code = 200, response_body = file("../arthur-ai-discovery.service") }
  }
  override_data {
    target = data.http.file["timer"]
    values = { status_code = 200, response_body = file("../arthur-ai-discovery.timer") }
  }

  assert {
    condition     = length(data.http.file) == 4
    error_message = "Expected every file downloaded and compared."
  }
}

# A ref that serves other bytes -- the module bumped and arthur_engine_ref not -- fails the plan.
run "a_ref_serving_other_bytes_fails_the_plan" {
  command = plan

  variables {
    verify_file_urls = true
  }

  override_data {
    target = data.http.file["collector"]
    values = { status_code = 200, response_body = "#!/bin/sh\n# another ref's collector\n" }
  }
  override_data {
    target = data.http.file["reporter"]
    values = { status_code = 200, response_body = file("../report-guest-attributes.sh") }
  }
  override_data {
    target = data.http.file["service"]
    values = { status_code = 200, response_body = file("../arthur-ai-discovery.service") }
  }
  override_data {
    target = data.http.file["timer"]
    values = { status_code = 200, response_body = file("../arthur-ai-discovery.timer") }
  }

  expect_failures = [data.http.file]
}

run "a_ref_or_a_mirror_is_required" {
  command = plan

  variables {
    arthur_engine_ref = null
  }

  expect_failures = [terraform_data.policy]
}

run "no_projects_and_no_folders" {
  command = plan

  variables {
    projects = []
  }

  expect_failures = [terraform_data.policy]
}

run "one_of_folder_and_organization" {
  command = plan

  variables {
    orchestrator = { folder = "1", organization = "2" }
  }

  expect_failures = [var.orchestrator]
}

run "folder_numbers_not_names" {
  command = plan

  variables {
    orchestrator = { folder = "folders/123" }
  }

  expect_failures = [var.orchestrator]
}

run "an_empty_folder_number" {
  command = plan

  variables {
    orchestrator = { folder = "" }
  }

  expect_failures = [var.orchestrator]
}

run "project_ids_not_numbers" {
  command = plan

  variables {
    projects = ["123456789012"]
  }

  expect_failures = [var.projects]
}

run "a_project_named_twice" {
  command = plan

  variables {
    projects = ["fleet-one", "fleet-one"]
  }

  expect_failures = [var.projects]
}

run "a_zone_named_twice" {
  command = plan

  variables {
    zones = ["us-central1-a", "us-central1-a"]
  }

  expect_failures = [var.zones]
}

run "a_label_value_no_vm_can_hold" {
  command = plan

  variables {
    label = { key = "ai-inventory", value = "On,off" }
  }

  expect_failures = [var.label]
}

run "a_metadata_key_this_module_does_not_set" {
  command = plan

  variables {
    project_metadata = ["enable-oslogin"]
  }

  expect_failures = [var.project_metadata]
}
