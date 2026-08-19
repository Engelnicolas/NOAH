# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH — Infra/aws — security groups and IAM.
#
# §16.5 IS THE MOST IMPORTANT PART OF THIS TARGET, and it has no equivalent in
# the physical version of the architecture. §3 reasons about an attacker who
# gets root on the compute node and tries to reach the Garage nodes; on
# physical machines the only way in is the network, and a distinct SSH key (T2)
# closes it. On AWS the hypervisor adds three ways that bypass SSH entirely —
# ssm:SendCommand, ec2:CreateSnapshot, and IMDS theft from a pod — plus a
# fourth that G19 introduces knowingly (the compute node routes the Garage
# nodes' egress).
#
# Path A would undo D6 in silence: if the compute node's profile, or one just
# as broad, reaches the Garage nodes, then cluster-admin on the cluster gives
# root on the storage tier — exactly what §3 forbids, by a path none of its
# tests look at. Condition 3 of §10.2 is NOT held by the SSH key alone as soon
# as one is on a cloud.

# --- Security groups --------------------------------------------------------

resource "aws_security_group" "compute" {
  name        = "${var.name_prefix}-compute"
  description = "NOAH compute node: cluster ingress, operator SSH, NAT for the Garage subnet"
  vpc_id      = aws_vpc.noah.id

  tags = { Name = "${var.name_prefix}-sg-compute" }
}

resource "aws_vpc_security_group_ingress_rule" "compute_ssh" {
  security_group_id = aws_security_group.compute.id
  description       = "Operator SSH — and the ProxyJump entry point to the Garage nodes"
  cidr_ipv4         = var.operator_cidr
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "compute_kubeapi" {
  security_group_id = aws_security_group.compute.id
  description       = "Kubernetes API, operator only"
  cidr_ipv4         = var.operator_cidr
  from_port         = 6443
  to_port           = 6443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "compute_http" {
  security_group_id = aws_security_group.compute.id
  description       = "ingress-nginx, HTTP (ACME http-01 and redirect)"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "compute_https" {
  security_group_id = aws_security_group.compute.id
  description       = "ingress-nginx, HTTPS"
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "compute_all" {
  security_group_id = aws_security_group.compute.id
  description       = "Egress, including the translated return traffic of the Garage nodes"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# G20 — ROUTING IS NOT REACHING, and it has to be written in code rather than
# in intent. The compute node's position as a router earns it NO extra inbound
# rule here: the Garage nodes' group keeps accepting only S3, RPC and SSH from
# the sources foreseen. Translated return traffic comes back as an ESTABLISHED
# connection — tracked on the compute node — never as an inbound opening, which
# is why no related/established rule is added below.
resource "aws_security_group" "garage" {
  name        = "${var.name_prefix}-garage"
  description = "NOAH Garage nodes: S3 from the cluster, RPC between nodes, SSH via the jump host"
  vpc_id      = aws_vpc.noah.id

  tags = { Name = "${var.name_prefix}-sg-garage" }
}

resource "aws_vpc_security_group_ingress_rule" "garage_ssh" {
  security_group_id = aws_security_group.garage.id
  description       = "Administration SSH, relayed by ProxyJump through the compute node. The connection is carried, the key is not: it stays in secret domain 3 (G20)."
  referenced_security_group_id = aws_security_group.compute.id
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "garage_s3_tls" {
  security_group_id = aws_security_group.garage.id
  description       = "S3 API behind the TLS proxy — flows G1..G4 of cilium_sso.md §7.2"
  referenced_security_group_id = aws_security_group.compute.id
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "garage_s3_plain" {
  security_group_id = aws_security_group.garage.id
  description       = "S3 API in the clear — only reached when garage_tls_enabled is explicitly false (§5.2)"
  referenced_security_group_id = aws_security_group.compute.id
  from_port         = 3900
  to_port           = 3900
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "garage_rpc" {
  security_group_id = aws_security_group.garage.id
  description       = "Garage RPC, BETWEEN GARAGE NODES ONLY. The cluster has no business here (flow G5) — self-reference, not the compute group."
  referenced_security_group_id = aws_security_group.garage.id
  from_port         = 3901
  to_port           = 3901
  ip_protocol       = "tcp"
}

# Port 3903 — the Garage administration API — appears in NO ingress rule. It
# binds to the loopback on each node and is reached over SSH by
# garage_provision.py. Naming it here to state that its absence is deliberate:
# flow G5 of cilium_sso.md §7.2 forbids 22, 3901 and the admin API from the
# cluster, and an absent rule IS the measure.

resource "aws_vpc_security_group_egress_rule" "garage_all" {
  security_group_id = aws_security_group.garage.id
  description       = "Egress via the compute node — APT mirrors and the Garage binary at bootstrap"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# --- IAM — the compute node's role ------------------------------------------
#
# THE DENY IS UNCONDITIONAL, NOT TAG-SCOPED, and that is a deliberate departure
# from the table in §16.5, which states the parries as conditions on
# `noah:role`. That formulation is precise; this one is ROBUST. Two reasons:
# the compute node has no legitimate use for ANY of these actions, so the
# condition buys no flexibility; and an explicit Deny beats every Allow,
# INCLUDING one attached later by mistake. The guarantee becomes durable
# instead of point-in-time — which is what one expects of a control meant to
# hold for five years without supervision.

resource "aws_iam_role" "compute" {
  name = "${var.name_prefix}-compute-node"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { "noah:role" = "compute-node" }
}

resource "aws_iam_role_policy" "compute_deny_storage_reach" {
  name = "${var.name_prefix}-deny-storage-reach"
  role = aws_iam_role.compute.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # Path A — command execution as root on the Garage nodes with no SSH
        # key whatsoever.
        Sid    = "DenyRemoteCommandExecution"
        Effect = "Deny"
        Action = [
          "ssm:SendCommand",
          "ssm:StartSession",
          "ssm:ResumeSession",
          "ssm:CreateAssociation",
          "ssm:CreateAssociationBatch",
          "ssm:UpdateAssociation",
          "ssm:StartAutomationExecution",
        ]
        Resource = "*"
      },
      {
        # Path B — a full copy of the Garage data without ever touching a
        # machine. The criterion is not "is this a Garage secret", it is "does
        # this give access to the Garage data".
        Sid    = "DenyVolumeAndSnapshotReach"
        Effect = "Deny"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:CreateSnapshots",
          "ec2:CopySnapshot",
          "ec2:CreateVolume",
          "ec2:AttachVolume",
          "ec2:DetachVolume",
          "ec2:ModifyVolume",
          "ec2:CreateImage",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
        ]
        Resource = "*"
      },
      {
        Sid    = "DenyInstanceLifecycle"
        Effect = "Deny"
        Action = [
          "ec2:RunInstances",
          "ec2:TerminateInstances",
          "ec2:StopInstances",
          "ec2:StartInstances",
          "ec2:RebootInstances",
          "ec2:ModifyInstanceAttribute",
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "compute" {
  name = "${var.name_prefix}-compute-node"
  role = aws_iam_role.compute.name
}

# No role, no policy and no instance profile is declared for the Garage nodes.
# See the comment on aws_instance.garage in spot.tf: an instance profile
# granted to them "for SSM convenience" would put stealable credentials back on
# the storage tier, and IMDS would be the way to steal them.
