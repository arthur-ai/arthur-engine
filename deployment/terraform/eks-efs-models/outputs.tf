output "efs_file_system_id" {
  value       = local.efs_id
  description = "ID of the EFS filesystem backing the models PVC."
}

output "efs_access_point_id" {
  value       = aws_efs_access_point.models.id
  description = "ID of the EFS access point the PV mounts."
}

output "efs_mount_target_ids" {
  value       = [for mt in aws_efs_mount_target.this : mt.id]
  description = "IDs of the EFS mount targets (one per subnet)."
}

output "efs_security_group_id" {
  value       = local.create_efs_sg ? aws_security_group.efs[0].id : null
  description = "Security group created for the EFS mount targets (null if BYO)."
}

output "node_security_group_id" {
  value       = local.node_security_group_id
  description = "Resolved EKS Auto Mode cluster security group allowed inbound NFS (for debugging)."
}

output "efs_csi_addon_arn" {
  value       = aws_eks_addon.efs_csi.arn
  description = "ARN of the aws-efs-csi-driver EKS add-on."
}

output "efs_csi_role_arn" {
  value       = local.efs_csi_role_arn
  description = "IAM role ARN used by the EFS CSI driver."
}

output "storage_class_name" {
  value       = kubernetes_storage_class_v1.efs.metadata[0].name
  description = "Name of the EFS StorageClass."
}

output "pvc_name" {
  value       = kubernetes_persistent_volume_claim_v1.models.metadata[0].name
  description = "Name of the models PVC."
}

output "pvc_namespace" {
  value       = kubernetes_persistent_volume_claim_v1.models.metadata[0].namespace
  description = "Namespace of the models PVC."
}

# Copy-paste hint for wiring the volume into the genai-engine deployment.
output "model_upload_hint" {
  description = "How to point genai-engine at this PVC via the Helm chart's modelPVC values."
  value       = <<-EOT
    Enable the model PVC in the genai-engine Helm chart (off by default):

      --set modelPVC.enabled=true \
      --set modelPVC.claimName=${var.pvc_name} \
      --set modelPVC.mountPath=/home/nonroot/models-output

    The chart then mounts the claim read-only and sets MODEL_STORAGE_PATH + HF_HUB_OFFLINE=1.
    No pod securityContext change is needed: the EFS access point's posix_user enforces
    uid/gid ${var.access_point_uid} for all reads, regardless of the pod's runAsUser.
  EOT
}
