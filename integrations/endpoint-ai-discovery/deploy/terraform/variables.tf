variable "arthur_engine_ref" {
  description = "The arthur-engine tag or commit in this module's source, after ?ref=. Never a branch: VMs download the collector, the reporter and the units at this ref whenever the policy is enforced, so a ref that moves breaks them. The plan fails unless each file there matches this module's copy."
  type        = string
  default     = null
}

variable "file_base_url" {
  description = "Serve the four files from a mirror instead of raw.githubusercontent.com: a URL under which they sit at their paths in this tree, such as https://mirror.example.com/endpoint-ai-discovery for .../dist/collect-linux.sh. Overrides arthur_engine_ref."
  type        = string
  default     = null
}

variable "projects" {
  description = "Project IDs of the fleet. Each gets the OS Config API and the metadata keys in project_metadata, and without an orchestrator an OS policy assignment in every zone."
  type        = list(string)

  validation {
    condition     = alltrue([for p in var.projects : can(regex("^(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]$", p))])
    error_message = "projects takes project IDs, such as my-project-123, not names or numbers."
  }

  validation {
    condition     = length(distinct(var.projects)) == length(var.projects)
    error_message = "projects names a project twice."
  }
}

variable "zones" {
  description = "Zones the fleet runs in. An OS policy assignment applies only to VMs in its own zone."
  type        = list(string)

  validation {
    condition     = length(var.zones) > 0
    error_message = "zones is empty, so no VM would be in scope."
  }

  validation {
    condition     = length(distinct(var.zones)) == length(var.zones)
    error_message = "zones names a zone twice."
  }
}

variable "name" {
  description = "Name of each OS policy assignment, and the orchestrator's ID."
  type        = string
  default     = "arthur-ai-discovery"
}

variable "label" {
  description = "A pilot: target only the VMs carrying this label, instead of every VM in the zones. Leave unset for the fleet. There is no exclusion label on purpose: a label a VM's owner can set would be an opt-out from discovery."
  type = object({
    key   = string
    value = string
  })
  default = null

  # The key rule Arthur's source holds its include_labels to: a key it refuses matches no VM.
  validation {
    condition     = var.label == null || can(regex("^[a-z][a-z0-9_-]{0,62}$", try(var.label.key, "")))
    error_message = "label.key starts with a lowercase letter and holds lowercase letters, digits, '_' and '-'."
  }

  # Compute Engine's value rule. A value it could not hold matches no VM, and a comma would split
  # the source's include_labels.
  validation {
    condition     = var.label == null || can(regex("^[\\p{Ll}\\p{Lo}\\p{N}_-]{0,63}$", try(var.label.value, "")))
    error_message = "label.value holds up to 63 lowercase letters, digits, '_' and '-'."
  }
}

variable "project_metadata" {
  description = "The metadata keys this module sets to TRUE in each project: enable-osconfig and enable-guest-attributes, without both of which nothing on a VM reports. Creating a key a project already holds fails the apply, so leave out one every project already sets TRUE. [] leaves project metadata alone, for keys set per VM."
  type        = set(string)
  default     = ["enable-osconfig", "enable-guest-attributes"]

  validation {
    condition     = length(setsubtract(var.project_metadata, ["enable-osconfig", "enable-guest-attributes"])) == 0
    error_message = "project_metadata takes enable-osconfig and enable-guest-attributes only."
  }
}

variable "enable_apis" {
  description = "Enable osconfig.googleapis.com in each project. It stays enabled when this module is destroyed."
  type        = bool
  default     = true
}

variable "reader" {
  description = "IAM member for the credential of Arthur's gcp_compute_engine discovery source, such as serviceAccount:arthur-discovery@my-project.iam.gserviceaccount.com. Granted reader_role in each project. A source scoped to an organization or a folder is granted there instead, outside this module."
  type        = string
  default     = null
}

variable "reader_role" {
  description = "The role granted to reader. roles/compute.viewer holds the three permissions the source uses."
  type        = string
  default     = "roles/compute.viewer"
}

variable "verify_file_urls" {
  description = "Download each file at plan time and fail unless it matches this module's copy. Turn off only where the machine running Terraform cannot reach the URLs the VMs use."
  type        = bool
  default     = true
}

variable "orchestrator" {
  description = "Roll out with one VM Manager policy orchestrator at a folder or an organization, instead of an assignment per project and zone. Set folder or organization, by number."
  type = object({
    folder          = optional(string)
    organization    = optional(string)
    include_folders = optional(list(string), [])
    action          = optional(string, "UPSERT")
  })
  default = null

  validation {
    condition     = var.orchestrator == null || ((try(var.orchestrator.folder, null) == null) != (try(var.orchestrator.organization, null) == null))
    error_message = "orchestrator takes exactly one of folder and organization."
  }

  validation {
    condition     = var.orchestrator == null || contains(["UPSERT", "DELETE"], try(var.orchestrator.action, ""))
    error_message = "orchestrator.action is UPSERT or DELETE."
  }

  # Every value that is set, the empty string included: "" would reach the API as a parent.
  validation {
    condition = var.orchestrator == null || alltrue([
      for n in concat(
        [for v in [try(var.orchestrator.folder, null), try(var.orchestrator.organization, null)] : v if v != null],
        try(var.orchestrator.include_folders, []),
      ) : can(regex("^[0-9]+$", n))
    ])
    error_message = "orchestrator takes folder and organization numbers, without a folders/ or organizations/ prefix."
  }
}
