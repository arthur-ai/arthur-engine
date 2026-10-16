variable "arthur_engine_ref" {
  description = "The arthur-engine tag or commit in this module's source, after ?ref=. VMs download the collector, the reporter and the units at this ref, and the plan fails unless each matches this module's copy."
  type        = string
  default     = null
}

variable "file_base_url" {
  description = "Serve the four files from a mirror instead of raw.githubusercontent.com: a URL under which they sit at their paths in this tree, such as https://mirror.example.com/endpoint-ai-discovery for .../dist/collect-linux.sh. Overrides arthur_engine_ref."
  type        = string
  default     = null
}

variable "projects" {
  description = "Project IDs of the fleet. Each gets the OS Config API and the two metadata keys, and without an orchestrator an OS policy assignment in every zone."
  type        = list(string)

  validation {
    condition     = alltrue([for p in var.projects : can(regex("^(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]$", p))])
    error_message = "projects takes project IDs, such as my-project-123, not names or numbers."
  }
}

variable "zones" {
  description = "Zones the fleet runs in. An OS policy assignment applies only to VMs in its own zone."
  type        = list(string)

  validation {
    condition     = length(var.zones) > 0
    error_message = "zones is empty, so no VM would be in scope."
  }
}

variable "name" {
  description = "Name of each OS policy assignment, and the orchestrator's ID."
  type        = string
  default     = "arthur-ai-discovery"
}

variable "label" {
  description = "The VM label that switches discovery on. Defaults to the policy's own, arthur-ai-discovery=enabled."
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
}

variable "project_metadata" {
  description = "Set enable-osconfig and enable-guest-attributes to TRUE in each project's metadata. Without both, nothing on a VM reports; set them per VM instead if this is false."
  type        = bool
  default     = true
}

variable "enable_apis" {
  description = "Enable osconfig.googleapis.com in each project. It stays enabled when this module is destroyed."
  type        = bool
  default     = true
}

variable "reader" {
  description = "IAM member for the credential of Arthur's gcp_compute_engine discovery source, such as serviceAccount:arthur-discovery@my-project.iam.gserviceaccount.com. Granted reader_role in each project."
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

  validation {
    condition = var.orchestrator == null || alltrue([
      for n in concat(compact([try(var.orchestrator.folder, null), try(var.orchestrator.organization, null)]), try(var.orchestrator.include_folders, [])) :
      can(regex("^[0-9]+$", n))
    ])
    error_message = "orchestrator takes folder and organization numbers, without a folders/ or organizations/ prefix."
  }
}
