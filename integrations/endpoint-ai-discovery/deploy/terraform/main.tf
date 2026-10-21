# Arthur endpoint AI discovery on Compute Engine: VM Manager installs osquery and a systemd
# timer on every Debian and Ubuntu VM in the fleet, and the collector it runs publishes an AI
# inventory to the VM's guest attributes, where Arthur's gcp_compute_engine discovery source
# reads it. The runbook is docs/mdm/gce.md in this tree.
#
# THE POLICY IS deploy/arthur-ai-discovery.os-policy.yaml, read here rather than restated: the
# gcloud path renders the same file. Each file it names is pinned to the copy in this module's
# own package, which is this tree at arthur_engine_ref.

locals {
  policy    = yamldecode(file("${path.module}/../arthur-ai-discovery.os-policy.yaml"))
  os_policy = local.policy.osPolicies[0]
  group     = local.os_policy.resourceGroups[0]

  description = "Arthur endpoint AI discovery: osquery and a collector timer reporting to guest attributes"

  # Null is the fleet: the policy targets every VM, and only a pilot narrows it to a label.
  labels = var.label == null ? null : tomap({ (var.label.key) = var.label.value })

  # The policy names each file by its URL in this tree at COMMIT, so the path after the prefix
  # is the path beside this module.
  github_prefix = "https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/"
  base_url = (
    var.file_base_url != null ? trimsuffix(var.file_base_url, "/") :
    var.arthur_engine_ref != null ? "https://raw.githubusercontent.com/arthur-ai/arthur-engine/${var.arthur_engine_ref}/integrations/endpoint-ai-discovery" :
    null
  )
  file_resources = [for r in local.group.resources : r if can(r.file.file.remote.uri)]
  unpinnable     = [for r in local.file_resources : r.id if !startswith(r.file.file.remote.uri, local.github_prefix)]
  pins = {
    for r in local.file_resources : r.id => {
      src    = trimprefix(r.file.file.remote.uri, local.github_prefix)
      uri    = local.base_url == null ? null : "${local.base_url}/${trimprefix(r.file.file.remote.uri, local.github_prefix)}"
      sha256 = filesha256("${path.module}/../../${trimprefix(r.file.file.remote.uri, local.github_prefix)}")
    } if startswith(r.file.file.remote.uri, local.github_prefix)
  }

  # THE POLICY AS THIS MODULE RENDERS IT, rebuilt key by key and compared whole with the file. A
  # key the resources below do not carry -- a yum repository, a second resource group, a fixed
  # disruption budget -- fails the plan instead of going missing from every VM. The resources
  # render from this rather than from the file, and every value here is read with try(), so the
  # comparison is the one place a changed policy fails, and it fails with its own message.
  carried = {
    osPolicies = [{
      id   = try(local.os_policy.id, null)
      mode = try(local.os_policy.mode, null)
      resourceGroups = [{
        inventoryFilters = [for f in try(local.group.inventoryFilters, []) : { osShortName = try(f.osShortName, null) }]
        resources = [for r in local.group.resources : merge(
          { id = r.id },
          { for k in ["repository"] : k => { apt = {
            archiveType  = try(r.repository.apt.archiveType, null)
            uri          = try(r.repository.apt.uri, null)
            distribution = try(r.repository.apt.distribution, null)
            components   = try(r.repository.apt.components, null)
            gpgKey       = try(r.repository.apt.gpgKey, null)
          } } if can(r.repository) },
          { for k in ["pkg"] : k => {
            desiredState = try(r.pkg.desiredState, null)
            apt          = { name = try(r.pkg.apt.name, null) }
          } if can(r.pkg) },
          { for k in ["exec"] : k => {
            validate = { interpreter = try(r.exec.validate.interpreter, null), script = try(r.exec.validate.script, null) }
            enforce  = { interpreter = try(r.exec.enforce.interpreter, null), script = try(r.exec.enforce.script, null) }
          } if can(r.exec) },
          { for k in ["file"] : k => {
            path        = try(r.file.path, null)
            state       = try(r.file.state, null)
            permissions = try(r.file.permissions, null)
            file = { remote = {
              uri            = try(r.file.file.remote.uri, null)
              sha256Checksum = try(r.file.file.remote.sha256Checksum, null)
            } }
          } if can(r.file) },
        )]
      }]
    }]
    instanceFilter = { all = try(local.policy.instanceFilter.all, null) }
    rollout = {
      disruptionBudget = { percent = try(local.policy.rollout.disruptionBudget.percent, null) }
      minWaitDuration  = try(local.policy.rollout.minWaitDuration, null)
    }
  }
  rendered       = local.carried.osPolicies[0]
  rendered_group = local.rendered.resourceGroups[0]
  rollout        = local.carried.rollout
}

resource "terraform_data" "policy" {
  lifecycle {
    precondition {
      condition     = jsonencode(local.carried) == jsonencode(local.policy)
      error_message = "deploy/arthur-ai-discovery.os-policy.yaml differs from the policy this module renders, so the VMs would not get the file as written. A key was added, removed or reshaped: change local.carried and the renderings in assignments.tf and orchestrator.tf with it."
    }
    precondition {
      condition     = length(local.unpinnable) == 0
      error_message = "The policy's file(s) ${join(", ", local.unpinnable)} are not at a URL under ${local.github_prefix}, so this module cannot pin them to its own copy."
    }
    precondition {
      condition     = local.base_url != null
      error_message = "Set arthur_engine_ref to the ?ref= in this module's source, or file_base_url to a mirror of the files."
    }
    precondition {
      condition     = length(var.projects) > 0 || length(try(var.orchestrator.include_folders, [])) > 0
      error_message = "projects is empty, so no VM would be in scope. An orchestrator can take include_folders instead."
    }
  }
}

# Download each file the VMs will, and compare it with this module's copy. A ref that does not
# match the module's source fails here, rather than on every VM as a checksum mismatch.
data "http" "file" {
  for_each = var.verify_file_urls && local.base_url != null ? local.pins : {}
  url      = each.value.uri

  lifecycle {
    postcondition {
      condition     = self.status_code == 200 && sha256(self.response_body) == each.value.sha256
      error_message = "${each.value.uri} answers HTTP ${self.status_code} with bytes that are not this module's ${each.value.src}, so every VM would refuse it. Either the URL serves another version -- arthur_engine_ref must be the ?ref= in this module's source, and file_base_url a mirror of that ref -- or this module's copy is not the committed file."
    }
  }
}

resource "google_project_service" "osconfig" {
  for_each = var.enable_apis ? toset(var.projects) : toset([])
  project  = each.key
  service  = "osconfig.googleapis.com"

  # Other OS policies and patch jobs may use it.
  disable_on_destroy = false
}

# Project-wide, as the default for each VM that does not set its own; a VM's own value wins, key
# by key. The agent acts on policies only with enable-osconfig, so a VM's own FALSE there gets
# nothing installed. Without enable-guest-attributes the policy installs and the timer runs, but
# the reporter's writes are refused with 403. The policy cannot set either key: it runs inside
# the VM. Arthur's source counts a VM with either off, by name, so turning one off is visible.
#
# CREATING A KEY THE PROJECT ALREADY HOLDS FAILS THE APPLY, `key ... already present`, and
# Google's VM Manager setup puts enable-osconfig in project metadata. Leave such a key out of
# project_metadata, or import it; destroying this module deletes every key it manages, imported
# ones included.
resource "google_compute_project_metadata_item" "discovery" {
  for_each = {
    for pk in setproduct(var.projects, sort(var.project_metadata)) : "${pk[0]}/${pk[1]}" => { project = pk[0], key = pk[1] }
  }
  project = each.value.project
  key     = each.value.key
  value   = "TRUE"
}

resource "google_project_iam_member" "reader" {
  for_each = var.reader == null ? toset([]) : toset(var.projects)
  project  = each.key
  role     = var.reader_role
  member   = var.reader
}
