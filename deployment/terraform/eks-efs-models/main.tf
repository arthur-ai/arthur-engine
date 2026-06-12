locals {
  # Arthur naming convention: ${namespace}-genai-engine${suffix}-<type>
  prefix = "${var.arthur_resource_namespace}-genai-engine${var.arthur_resource_name_suffix}"

  # Standard Arthur tagging. "Purpose" matches the value used on the S3 models
  # bucket in arthur-genai-engine-model-upload.yml.
  tags = merge(
    { Purpose = "Arthur GenAI Engine Model Storage" },
    var.tags,
  )

  create_efs      = var.existing_efs_file_system_id == ""
  create_efs_sg   = length(var.byo_efs_security_group_ids) == 0
  create_csi_role = var.byo_efs_csi_role_arn == ""

  # Auto Mode nodes attach to the EKS-created cluster security group.
  node_security_group_id = data.aws_eks_cluster.this.vpc_config[0].cluster_security_group_id

  efs_id           = local.create_efs ? aws_efs_file_system.models[0].id : var.existing_efs_file_system_id
  efs_sg_ids       = local.create_efs_sg ? [aws_security_group.efs[0].id] : var.byo_efs_security_group_ids
  efs_csi_role_arn = local.create_csi_role ? aws_iam_role.efs_csi[0].arn : var.byo_efs_csi_role_arn
}

# ---------------------------------------------------------------------------
# EFS filesystem (encrypted at rest; elastic throughput by default).
# DeletionPolicy: Retain equivalent — prevent_destroy guards the several GB of
# uploaded models. To intentionally tear down the filesystem, remove the
# lifecycle block (or manage the FS out-of-band via existing_efs_file_system_id).
# ---------------------------------------------------------------------------

resource "aws_efs_file_system" "models" {
  count = local.create_efs ? 1 : 0

  encrypted        = true
  performance_mode = var.performance_mode
  throughput_mode  = var.throughput_mode

  tags = merge(local.tags, { Name = "${local.prefix}-models-efs" })

  lifecycle {
    prevent_destroy = true
  }
}

# ---------------------------------------------------------------------------
# Mount-target security group — allows inbound NFS (2049) from the Auto Mode
# cluster security group only.
# ---------------------------------------------------------------------------

resource "aws_security_group" "efs" {
  count = local.create_efs_sg ? 1 : 0

  name        = "${local.prefix}-efs"
  description = "NFS access to the Arthur models EFS from the EKS Auto Mode nodes"
  vpc_id      = var.vpc_id

  tags = merge(local.tags, { Name = "${local.prefix}-efs" })
}

resource "aws_vpc_security_group_ingress_rule" "nfs" {
  count = local.create_efs_sg ? 1 : 0

  security_group_id            = aws_security_group.efs[0].id
  description                  = "NFS from EKS Auto Mode nodes"
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  referenced_security_group_id = local.node_security_group_id

  tags = merge(local.tags, { Name = "${local.prefix}-efs-nfs" })
}

resource "aws_vpc_security_group_egress_rule" "all" {
  count = local.create_efs_sg ? 1 : 0

  security_group_id = aws_security_group.efs[0].id
  description       = "Allow all egress"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"

  tags = merge(local.tags, { Name = "${local.prefix}-efs-egress" })
}

# One mount target per subnet so every node AZ can reach the filesystem.
resource "aws_efs_mount_target" "this" {
  for_each = toset(var.subnet_ids)

  file_system_id  = local.efs_id
  subnet_id       = each.value
  security_groups = local.efs_sg_ids
}

# ---------------------------------------------------------------------------
# Access point — enforces the POSIX identity the upload job and genai-engine
# pods run as, and roots reads/writes at var.root_directory.
# ---------------------------------------------------------------------------

resource "aws_efs_access_point" "models" {
  file_system_id = local.efs_id

  posix_user {
    uid = var.access_point_uid
    gid = var.access_point_gid
  }

  root_directory {
    path = var.root_directory
    creation_info {
      owner_uid   = var.access_point_uid
      owner_gid   = var.access_point_gid
      permissions = var.directory_perms
    }
  }

  tags = merge(local.tags, { Name = "${local.prefix}-models-ap" })

  depends_on = [aws_efs_mount_target.this]
}

# ---------------------------------------------------------------------------
# IAM for the EFS CSI driver, wired via EKS Pod Identity (recommended for
# Auto Mode — no OIDC provider to manage).
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "efs_csi_trust" {
  count = local.create_csi_role ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole", "sts:TagSession"]

    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "efs_csi" {
  count = local.create_csi_role ? 1 : 0

  name               = "${local.prefix}-efs-csi-role"
  assume_role_policy = data.aws_iam_policy_document.efs_csi_trust[0].json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "efs_csi" {
  count = local.create_csi_role ? 1 : 0

  role       = aws_iam_role.efs_csi[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"
}

resource "aws_eks_pod_identity_association" "efs_csi" {
  count = local.create_csi_role ? 1 : 0

  cluster_name    = var.cluster_name
  namespace       = "kube-system"
  service_account = "efs-csi-controller-sa"
  role_arn        = aws_iam_role.efs_csi[0].arn

  tags = local.tags
}

# ---------------------------------------------------------------------------
# EFS CSI driver add-on. Auto Mode ships EBS storage but NOT the EFS driver,
# so it must be installed explicitly.
# ---------------------------------------------------------------------------

resource "aws_eks_addon" "efs_csi" {
  cluster_name  = var.cluster_name
  addon_name    = "aws-efs-csi-driver"
  addon_version = var.efs_csi_addon_version

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = local.tags

  depends_on = [aws_eks_pod_identity_association.efs_csi]
}

# ---------------------------------------------------------------------------
# Kubernetes storage objects (static provisioning).
# The StorageClass is a binding-only placeholder — it is NOT marked default so
# it never competes with the Auto Mode EBS default StorageClass.
# ---------------------------------------------------------------------------

resource "kubernetes_storage_class_v1" "efs" {
  metadata {
    name = var.storage_class_name
  }

  storage_provisioner = "efs.csi.aws.com"
  reclaim_policy      = "Retain"
  volume_binding_mode = "Immediate"
}

resource "kubernetes_persistent_volume_v1" "models" {
  metadata {
    name   = "${local.prefix}-models"
    labels = { app = "arthur-models" }
  }

  spec {
    capacity = {
      storage = var.storage_size
    }
    access_modes                     = ["ReadWriteMany"]
    persistent_volume_reclaim_policy = "Retain"
    storage_class_name               = var.storage_class_name
    mount_options                    = ["tls"]

    persistent_volume_source {
      csi {
        driver        = "efs.csi.aws.com"
        volume_handle = "${local.efs_id}::${aws_efs_access_point.models.id}"
      }
    }
  }

  depends_on = [aws_eks_addon.efs_csi]
}

resource "kubernetes_persistent_volume_claim_v1" "models" {
  metadata {
    name      = var.pvc_name
    namespace = var.namespace
    labels    = { app = "arthur-models" }
  }

  spec {
    access_modes       = ["ReadWriteMany"]
    storage_class_name = var.storage_class_name
    volume_name        = kubernetes_persistent_volume_v1.models.metadata[0].name

    resources {
      requests = {
        storage = var.storage_size
      }
    }
  }

  wait_until_bound = true
}
