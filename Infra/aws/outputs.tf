# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH — Infra/aws — the output contract of §16.3.
#
# Every target produces the SAME infra-inventory.json, whatever the provider.
# `noah garage deploy --from-infra <path>` reads it and feeds _build_inventory()
# — it does not bypass it. Nothing downstream of §4 knows which infrastructure
# provider is in play, and that is what makes the `baremetal/` target realisable
# with a hand-written file and no code at all.

locals {
  infra_inventory = {
    provider = "aws"

    compute_node = {
      name       = local.compute_name
      public_ip  = aws_eip.compute.public_ip
      private_ip = aws_instance.compute.private_ip
    }

    # The machine through which the Garage nodes are reached. Since G19 they
    # sit in a private subnet with no public address; `bastion` names the hop.
    # A target that gave every machine a public address would fill public_ip
    # and set bastion to null WITHOUT changing the contract.
    bastion = local.compute_name

    # The field that was missing, and it has no consumer in Garage.md. It is
    # produced here because the IaC layer creates the subnet and is therefore
    # the only layer that knows the exact prefix. Its consumer is the cluster
    # network baseline: cilium_sso.md §6.6 founds every Garage egress rule on
    # `toCIDR: ${garage_cidr}` (decision N7). Entering it twice would make the
    # two diverge — and a prefix entered wider than the real subnet widens the
    # cluster's S3 egress rules WITHOUT ANY TEST SEEING IT.
    #
    # A prefix is not a secret: knowing it grants no access.
    garage_cidr = aws_subnet.garage.cidr_block

    garage_nodes = [
      for i in range(var.node_count) : {
        name = local.garage_names[i]

        # null, not absent. ONE null field is admitted in this file, never a
        # missing one: a missing field reads as an oversight of the generator,
        # a null one as a topology decision.
        public_ip  = null
        private_ip = aws_instance.garage[i].private_ip
        zone       = local.garage_zones[i]
        capacity   = "${var.garage_data_size}G"

        # NEVER A SHORT DEVICE NAME. /dev/nvme1n1 would be the natural value on
        # AWS — and it is wrong. On Nitro instances, m6a and t3a included, the
        # NVMe enumeration order is NOT guaranteed: depending on attachment
        # order the data volume shows up as nvme1n1 or nvme2n1, and garage-zfs
        # would then create the pool ON THE ROOT DISK — a silent data loss at
        # the first attachment that changes order.
        #
        # The deterministic by-id path is derived from the EBS volume id with
        # its dash removed, which is exactly the serial Nitro exposes. On a
        # virtio host, /dev/disk/by-id/virtio-<serial> plays the same role;
        # /dev/vdb has the same defect as /dev/nvme1n1 and is proscribed for
        # the same reason.
        data_device = "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_${replace(aws_ebs_volume.garage_data[i].id, "-", "")}"
      }
    ]
  }
}

output "infra_inventory" {
  description = "The §16.3 contract, also written to infra-inventory.json by main.tf."
  value       = local.infra_inventory
}

output "infra_inventory_path" {
  description = "Path to hand to `noah garage deploy --from-infra`."
  value       = local_file.infra_inventory.filename
}

output "compute_public_ip" {
  description = "The platform's single public IPv4 address (G19)."
  value       = aws_eip.compute.public_ip
}

output "garage_replication_factor" {
  description = "Derived from the node count, never entered separately (G8). Shown here so the plan states the topology it is about to pay for."
  value       = var.node_count
}
