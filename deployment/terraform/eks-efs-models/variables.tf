# ---------------------------------------------------------------------------
# Naming & tagging — mirrors the ArthurResourceNamespace / ArthurResourceNameSuffix
# convention used across deployment/cloudformation/. Resources are named
# "${arthur_resource_namespace}-genai-engine${arthur_resource_name_suffix}-<type>".
# ---------------------------------------------------------------------------

variable "arthur_resource_namespace" {
  type        = string
  default     = "arthur"
  description = "A unique namespace for this Arthur stack's resources (e.g. arthur1)."

  validation {
    condition     = length(var.arthur_resource_namespace) >= 1 && length(var.arthur_resource_namespace) <= 14
    error_message = "arthur_resource_namespace must be between 1 and 14 characters."
  }
}

variable "arthur_resource_name_suffix" {
  type        = string
  default     = ""
  description = "Name suffix for Arthur stack resources (e.g. -prod)."

  validation {
    condition     = length(var.arthur_resource_name_suffix) <= 5
    error_message = "arthur_resource_name_suffix must be at most 5 characters."
  }
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Additional tags applied to all AWS resources (merged over the standard Arthur tags)."
}

# ---------------------------------------------------------------------------
# Cluster & networking
# ---------------------------------------------------------------------------

variable "cluster_name" {
  type        = string
  description = "Name of the existing EKS Auto Mode cluster."
}

variable "region" {
  type        = string
  description = "AWS region of the cluster and EFS resources."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID of the cluster (used for the EFS mount-target security group)."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets to create EFS mount targets in. Use the private/service subnets where genai-engine and the upload job can schedule (analogous to GenaiEngineECSServiceSubnetIDs in CloudFormation)."

  validation {
    condition     = length(var.subnet_ids) > 0
    error_message = "At least one subnet ID is required for an EFS mount target."
  }
}

# ---------------------------------------------------------------------------
# Bring-your-own (BYO) overrides — mirrors ExistingModelsBucketName /
# PostgresBYOSecurityGroupIDs / GenaiEngineBYO*RoleIAMArn in CloudFormation.
# When set, the corresponding resource is NOT created and the provided value is used.
# ---------------------------------------------------------------------------

variable "existing_efs_file_system_id" {
  type        = string
  default     = ""
  description = "Reuse an existing EFS filesystem instead of creating one. Empty = create a new filesystem."
}

variable "byo_efs_security_group_ids" {
  type        = list(string)
  default     = []
  description = "Reuse existing security group(s) for the EFS mount targets. Empty = create one allowing NFS (2049) from the cluster security group."
}

variable "byo_efs_csi_role_arn" {
  type        = string
  default     = ""
  description = "Reuse an existing IAM role for the EFS CSI driver. Empty = create a role + Pod Identity association."
}

# ---------------------------------------------------------------------------
# EFS filesystem tuning
# ---------------------------------------------------------------------------

variable "throughput_mode" {
  type        = string
  default     = "elastic"
  description = "EFS throughput mode. Elastic is recommended — model loading is many small-file reads and a low-baseline Bursting filesystem can throttle at startup."

  validation {
    condition     = contains(["elastic", "bursting", "provisioned"], var.throughput_mode)
    error_message = "throughput_mode must be one of: elastic, bursting, provisioned."
  }
}

variable "performance_mode" {
  type        = string
  default     = "generalPurpose"
  description = "EFS performance mode."

  validation {
    condition     = contains(["generalPurpose", "maxIO"], var.performance_mode)
    error_message = "performance_mode must be one of: generalPurpose, maxIO."
  }
}

# ---------------------------------------------------------------------------
# Access point / POSIX identity — must match the upload job's runAsUser
# (deployment/model-upload/k8s/04-job.yaml: 1000760000) and the genai-engine pod.
# ---------------------------------------------------------------------------

variable "access_point_uid" {
  type        = number
  default     = 1000760000
  description = "POSIX uid the EFS access point enforces. Must match the upload job and genai-engine pod runAsUser."
}

variable "access_point_gid" {
  type        = number
  default     = 1000760000
  description = "POSIX gid the EFS access point enforces. Must match the upload job and genai-engine pod runAsGroup."
}

variable "root_directory" {
  type        = string
  default     = "/models"
  description = "Root directory on the EFS filesystem exposed by the access point."
}

variable "directory_perms" {
  type        = string
  default     = "700"
  description = "Permissions for the access point root directory."
}

# ---------------------------------------------------------------------------
# Kubernetes storage objects
# ---------------------------------------------------------------------------

variable "namespace" {
  type        = string
  default     = "default"
  description = "Namespace where the PVC is created. Must match the namespace of the upload job and genai-engine deployment."
}

variable "pvc_name" {
  type        = string
  default     = "arthur-models-pvc"
  description = "Name of the PVC. Keep the default so the existing upload job manifests (claimName: arthur-models-pvc) work unchanged."
}

variable "storage_class_name" {
  type        = string
  default     = "efs-models"
  description = "Name of the StorageClass. Must differ from the Auto Mode default EBS StorageClass and is NOT marked default."
}

variable "storage_size" {
  type        = string
  default     = "25Gi"
  description = "Nominal storage request for the PV/PVC. EFS is elastic, so this is a nominal value, not a hard cap."
}

# ---------------------------------------------------------------------------
# EKS add-on
# ---------------------------------------------------------------------------

variable "efs_csi_addon_version" {
  type        = string
  default     = null
  description = "Version of the aws-efs-csi-driver EKS add-on. Null resolves to the default version for the cluster's Kubernetes version."
}
