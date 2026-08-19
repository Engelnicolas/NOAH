# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH — Infra/aws — input variables.
#
# The same four variables are exposed by every target (Garage.md §16.6):
# node_count, power_state, garage_data_size, operator_cidr. That identity of
# contract is what makes portability a verifiable fact rather than an
# intention, so do not add a target-specific variable to that set.

variable "state_passphrase" {
  description = <<-EOT
    Passphrase used to encrypt the OpenTofu state (decision G14). Comes from
    secret domain 3 — Secrets/garage-admin.enc.yaml, key `tofu_state_passphrase`
    — and is normally supplied by `noah garage infra`, which reads it there and
    exports it as TF_VAR_state_passphrase.

    DELIBERATELY WITHOUT A DEFAULT. Encryption is declared in the configuration
    rather than left to the TF_ENCRYPTION environment variable precisely so
    that a missing passphrase fails the run instead of silently writing the
    whole topology to disk in the clear (§16.5). Explicit, never implicit —
    the same rule as TLS in §5.2.
  EOT
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.state_passphrase) >= 16
    error_message = "The pbkdf2 key provider imposes a 16-character minimum on the state passphrase."
  }
}

variable "node_count" {
  description = <<-EOT
    Number of Garage nodes: 2 for the development topology, 3 for production
    (G7). Refused outside {2, 3} — an echo of G8 one layer earlier: §4.1
    already refuses a bad count, but only once the machines exist. Refusing
    here makes the mistake fall before anything has been paid for (§16.7).
  EOT
  type        = number
  default     = 2

  validation {
    condition     = contains([2, 3], var.node_count)
    error_message = "node_count must be 2 (development) or 3 (production). One node cannot demonstrate CRDT resurrection (V2); more than three is outside the target."
  }
}

variable "power_state" {
  description = <<-EOT
    running | stopped. The daily cost lever (G12): `tofu apply -var
    power_state=stopped` shuts the three machines down without destroying
    anything, `running` brings them back. Storage and addressing keep billing
    either way — stopping is not destroying, and it is not free.
  EOT
  type        = string
  default     = "running"

  validation {
    condition     = contains(["running", "stopped"], var.power_state)
    error_message = "power_state must be \"running\" or \"stopped\"."
  }
}

variable "garage_data_size" {
  description = <<-EOT
    Size in GiB of the dedicated data volume of each Garage node. 20 GiB is
    enough for development; the ZFS mirror of appendix A.2 is NOT required
    there (§5.1) — provided the gap is never carried into production, where it
    would destroy the point of the mirror.
  EOT
  type        = number
  default     = 20
}

variable "operator_cidr" {
  description = <<-EOT
    Prefix from which the operator workstation reaches the platform over SSH.
    0.0.0.0/0 is REFUSED (§16.7): since G19 the compute node is the only
    exposed machine AND the jump host to the storage tier, so opening SSH to
    the world would undo §3 more surely than every path in §16.5 combined.
  EOT
  type        = string

  validation {
    condition     = !contains(["0.0.0.0/0", "::/0"], var.operator_cidr)
    error_message = "operator_cidr must not be 0.0.0.0/0 or ::/0: SSH open to the world defeats the whole isolation argument of §3."
  }
}

# --- Target-specific below this line -----------------------------------------

variable "region" {
  description = "AWS region. eu-west-3 (Paris) — G17: a project whose value proposition is data-hosting sovereignty does not develop elsewhere, not even in development."
  type        = string
  default     = "eu-west-3"
}

variable "availability_zone" {
  description = <<-EOT
    ONE availability zone, and this is not a shortcut. An EBS volume is bound
    to its zone, and a stopped Spot instance restarts in its own. Spreading the
    machines over two zones — a perfectly sound resilience reflex elsewhere —
    would break G11 IN SILENCE: on capacity return the instance would not find
    its volume. Not to be confused with the Garage zones site-a / site-b, which
    are internal placement labels with no relation to this.
  EOT
  type        = string
  default     = "eu-west-3a"
}

variable "compute_instance_type" {
  description = "Compute node: 8 vCPU / 32 GiB per appendix A.1, fixed performance. A burstable T family would be a trap here — `unlimited` is its default and bills surplus credits silently."
  type        = string
  default     = "m6a.2xlarge"
}

variable "garage_instance_type" {
  description = "Garage nodes: 2 vCPU / 4 GiB per §1.1. T family is fine at this load, with CpuCredits forced to `standard` (see spot.tf)."
  type        = string
  default     = "t3a.medium"
}

variable "compute_ssh_public_key" {
  description = "PUBLIC half of the cluster SSH key. OpenTofu publishes public keys; the private halves never traverse the state (§16.7, point 4)."
  type        = string
}

variable "garage_ssh_public_key" {
  description = <<-EOT
    PUBLIC half of the Garage administration SSH key — a DIFFERENT key pair
    from the cluster's, which is the code form of condition 3 of §10.2. Its
    private half lives in secret domain 3 and is never copied to the bastion:
    ProxyJump carries the connection, it does not hold the key (G20).
  EOT
  type        = string
}

variable "vpc_cidr" {
  description = "VPC prefix."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Public subnet — compute node only."
  type        = string
  default     = "10.0.1.0/24"
}

variable "garage_subnet_cidr" {
  description = "Private subnet carrying the Garage nodes. Emitted as `garage_cidr` in infra-inventory.json: the cluster egress policies are founded on it (cilium_sso.md N7), and a prefix entered by hand in two places is a prefix that drifts."
  type        = string
  default     = "10.0.2.0/24"
}

variable "root_volume_size" {
  description = "Root volume size in GiB, all instances."
  type        = number
  default     = 40
}

variable "name_prefix" {
  description = "Prefix for the Name tags."
  type        = string
  default     = "noah"
}
