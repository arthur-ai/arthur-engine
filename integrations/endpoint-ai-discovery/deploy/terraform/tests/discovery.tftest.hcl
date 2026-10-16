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
  assert {
    condition     = length(google_os_config_v2_policy_orchestrator_for_folder.discovery) + length(google_os_config_v2_policy_orchestrator_for_organization.discovery) == 0
    error_message = "No orchestrator without var.orchestrator."
  }
  # Every resource of the file, in its order: VM Manager applies a group's resources in sequence.
  assert {
    condition = [for r in google_os_config_os_policy_assignment.discovery["fleet-one/us-central1-a"].os_policies[0].resource_groups[0].resources : r.id] == [
      for r in yamldecode(file("../arthur-ai-discovery.os-policy.yaml")).osPolicies[0].resourceGroups[0].resources : r.id
    ]
    error_message = "The assignment does not carry the policy's resources in the policy's order."
  }
  assert {
    condition     = google_os_config_os_policy_assignment.discovery["fleet-one/us-central1-a"].instance_filter[0].inclusion_labels[0].labels == tomap({ arthur-ai-discovery = "enabled" })
    error_message = "The assignment does not target the policy's label."
  }
  assert {
    condition     = google_os_config_os_policy_assignment.discovery["fleet-one/us-central1-a"].skip_await_rollout
    error_message = "A fleet rollout outlasts the provider's timeout; the assignment must not wait for it."
  }
  assert {
    condition     = length(google_compute_project_metadata_item.discovery) == 4 && alltrue([for m in google_compute_project_metadata_item.discovery : m.value == "TRUE"])
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
    condition     = output.pinned_files.collector.uri == "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/dist/collect-linux.sh"
    error_message = "The collector's URL is not this tree at arthur_engine_ref."
  }
  assert {
    condition = output.pinned_files == {
      collector = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/dist/collect-linux.sh", sha256 = filesha256("../../dist/collect-linux.sh") }
      reporter  = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/deploy/report-guest-attributes.sh", sha256 = filesha256("../report-guest-attributes.sh") }
      service   = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/deploy/arthur-ai-discovery.service", sha256 = filesha256("../arthur-ai-discovery.service") }
      timer     = { uri = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/2.1.999/integrations/endpoint-ai-discovery/deploy/arthur-ai-discovery.timer", sha256 = filesha256("../arthur-ai-discovery.timer") }
    }
    error_message = "A file is not pinned to its URL at the ref and the sha256 of this tree's copy."
  }
  # What a VM receives is the rendered resource, not the output: read the pin back off it.
  assert {
    condition = [
      for r in google_os_config_os_policy_assignment.discovery["fleet-two/us-central1-a"].os_policies[0].resource_groups[0].resources :
      r.file[0].file[0].remote[0].sha256_checksum if length(r.file) > 0
      ] == [
      filesha256("../../dist/collect-linux.sh"), filesha256("../report-guest-attributes.sh"),
      filesha256("../arthur-ai-discovery.service"), filesha256("../arthur-ai-discovery.timer"),
    ]
    error_message = "The assignment does not carry each file's sha256."
  }
}

run "a_mirror_serves_the_files" {
  command = plan

  variables {
    file_base_url = "https://mirror.example.com/endpoint-ai-discovery/"
  }

  assert {
    condition     = output.pinned_files.timer.uri == "https://mirror.example.com/endpoint-ai-discovery/deploy/arthur-ai-discovery.timer"
    error_message = "file_base_url does not replace the GitHub URL, path for path."
  }
}

run "a_label_and_a_reader" {
  command = plan

  variables {
    label  = { key = "ai-inventory", value = "on" }
    reader = "serviceAccount:arthur@reader-project.iam.gserviceaccount.com"
  }

  assert {
    condition     = google_os_config_os_policy_assignment.discovery["fleet-one/us-central1-a"].instance_filter[0].inclusion_labels[0].labels == tomap({ ai-inventory = "on" })
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

run "metadata_and_apis_left_alone" {
  command = plan

  variables {
    project_metadata = false
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
  # The orchestrator can set what an assignment cannot.
  assert {
    condition = {
      for r in google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestrated_resource[0].os_policy_assignment_v1_payload[0].os_policies[0].resource_groups[0].resources :
      r.id => r.file[0].permissions if length(r.file) > 0
    } == { collector = "755", reporter = "755", service = "644", timer = "644" }
    error_message = "The orchestrator does not carry the policy's file permissions."
  }
  assert {
    condition = [
      for r in google_os_config_v2_policy_orchestrator_for_folder.discovery[0].orchestrated_resource[0].os_policy_assignment_v1_payload[0].os_policies[0].resource_groups[0].resources : r.id
      ] == [
      for r in yamldecode(file("../arthur-ai-discovery.os-policy.yaml")).osPolicies[0].resourceGroups[0].resources : r.id
    ]
    error_message = "The orchestrator does not carry the policy's resources in the policy's order."
  }
  assert {
    condition     = length(google_compute_project_metadata_item.discovery) == 4
    error_message = "The projects still need their metadata under an orchestrator."
  }
}

run "an_organization_orchestrator_deleting" {
  command = plan

  variables {
    orchestrator = { organization = "987654321", action = "DELETE" }
  }

  assert {
    condition     = length(google_os_config_v2_policy_orchestrator_for_folder.discovery) == 0 && google_os_config_v2_policy_orchestrator_for_organization.discovery[0].organization_id == "987654321"
    error_message = "Expected the orchestrator at the organization."
  }
  assert {
    condition     = google_os_config_v2_policy_orchestrator_for_organization.discovery[0].action == "DELETE" && length(google_os_config_v2_policy_orchestrator_for_organization.discovery[0].orchestrated_resource[0].os_policy_assignment_v1_payload) == 0
    error_message = "DELETE takes the orchestrated resource's name and no payload."
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

run "project_ids_not_numbers" {
  command = plan

  variables {
    projects = ["123456789012"]
  }

  expect_failures = [var.projects]
}
