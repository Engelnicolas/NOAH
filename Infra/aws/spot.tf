# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH — Infra/aws — instances, Spot market options, data volumes, power state.
#
# DECISION G16 — the Spot options are declared INLINE on the instance resource,
# never in a launch template.
#
# V11 settled this on 15/08/2026 and corrected the motive this file used to
# carry. The defect was real for inline options up to provider 5.85.x and is
# fixed in 5.86.0; what protects against it is the version floor in main.tf,
# NOT where the options are declared — cancellation at destroy is guarded by
# the COMPUTED attribute `instance_lifecycle`, read back from DescribeInstances,
# which a referenced launch template does not prevent from being set.
#
# G16 therefore stands on three other arguments:
#   1. visibility in the plan — inline options show up in `tofu plan`; buried
#      in a template they are an opaque reference, and this is a decision whose
#      mistakes bill in silence;
#   2. independence from a successful read — inline options make the Spot
#      market exist in the configuration, i.e. in the stated intent, not only
#      in the observed state;
#   3. consistency with G18 — the data volume leaves the template; keeping only
#      the Spot options in it would leave half a template with no coherent
#      scope of its own.
#
# What remains proscribed: a launch template consumed by anything OTHER than an
# aws_instance — an autoscaling group, a one-off console launch — which leaves
# the provider no resource to destroy, hence no request to cancel.

# --- Compute node -----------------------------------------------------------

resource "aws_instance" "compute" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.compute_instance_type
  subnet_id     = aws_subnet.public.id
  key_name      = aws_key_pair.compute.key_name

  vpc_security_group_ids = [aws_security_group.compute.id]
  iam_instance_profile   = aws_iam_instance_profile.compute.name

  # G19 — without this the VPC DROPS packets whose source address is not the
  # instance's own, and the Garage nodes' bootstrap hangs with no usable error
  # message. This is the setting everyone forgets.
  source_dest_check = false

  # Path C of §16.5. The hop limit of 1 is DELIBERATELY the setting that breaks
  # container access to IMDS: host processes, cloud-init included, stay served;
  # pods no longer are. The v12 template carried 2, which opened IMDS to every
  # pod in the cluster.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  instance_market_options {
    market_type = "spot"

    spot_options {
      # G11 — `stop`, never `terminate`. On the compute node the pool is not at
      # stake, but a uniform behaviour keeps the fleet legible and keeps the
      # root volume (hence the K3s state) across an interruption.
      # `stop` REQUIRES spot_instance_type = "persistent".
      instance_interruption_behavior = "stop"
      spot_instance_type             = "persistent"
    }
  }

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name         = local.compute_name
    "noah:role"  = "compute-node"
    "noah:tier"  = "compute"
  }

  lifecycle {
    # The AMI moves as Canonical publishes; a new AMI id must not silently
    # replace a running node and take its root volume with it.
    ignore_changes = [ami]
  }
}

# --- Garage nodes -----------------------------------------------------------

resource "aws_instance" "garage" {
  count = var.node_count

  ami           = data.aws_ami.ubuntu.id
  instance_type = var.garage_instance_type
  subnet_id     = aws_subnet.garage.id
  key_name      = aws_key_pair.garage.key_name

  vpc_security_group_ids = [aws_security_group.garage.id]

  # NO INSTANCE PROFILE. Not a restricted one: none at all (§16.5). These
  # machines run Garage and nothing else; no AWS API call is legitimate from
  # them. The consequence is stronger than any hardening of path C — with no
  # credentials on the machine THERE IS NOTHING FOR IMDS TO LEAK. The path is
  # closed by construction, not by setting, and no configuration drift can
  # reopen it.
  # iam_instance_profile = (intentionally absent)

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  # T family at a low real load. `standard` rather than the `unlimited`
  # default: unlimited bills surplus credits in silence once the baseline is
  # exceeded for any length of time.
  credit_specification {
    cpu_credits = "standard"
  }

  instance_market_options {
    market_type = "spot"

    spot_options {
      # G11 — a Garage node in `terminate` is a contradiction in terms: the ZFS
      # pool IS the subject of trials V1 to V3, and a Spot interruption would
      # destroy it at random intervals. `stop` keeps the volumes intact and the
      # instance restarts, with the same instance id, when capacity returns.
      instance_interruption_behavior = "stop"
      spot_instance_type             = "persistent"
    }
  }

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name          = local.garage_names[count.index]
    "noah:role"   = "garage-node"
    "noah:tier"   = "storage"
    "garage:zone" = local.garage_zones[count.index]
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

# --- Data volumes — G18 -----------------------------------------------------
#
# The Garage data volume is a STANDALONE resource, attached to the instance,
# not a disk of the template. DeleteOnTermination = false already protects the
# ZFS pool; full decoupling does better — the pool's lifecycle becomes
# independent of the instance's. A replaced instance (type change, manual
# destruction, a taint that forced it) finds its volume again instead of
# receiving a fresh one. That is what makes the snapshot history survive
# operational handling, and not merely Spot interruptions.

resource "aws_ebs_volume" "garage_data" {
  count = var.node_count

  availability_zone = var.availability_zone
  size              = var.garage_data_size
  type              = "gp3"
  encrypted         = true

  tags = {
    Name          = "${local.garage_names[count.index]}-data"
    "noah:role"   = "garage-node"
    "noah:tier"   = "storage"
    "garage:zone" = local.garage_zones[count.index]
  }
}

resource "aws_volume_attachment" "garage_data" {
  count = var.node_count

  # Short device name as seen by the API. It is NOT what the garage-zfs role
  # uses — see the data_device field of infra-inventory.json in outputs.tf: on
  # Nitro instances the NVMe enumeration order is not guaranteed, and a short
  # name would eventually point at the root disk.
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.garage_data[count.index].id
  instance_id = aws_instance.garage[count.index].id

  # The volume survives the instance. Detaching by force at destroy time would
  # risk the pool; letting the volume outlive an orphaned attachment is the
  # lesser evil, and G18 is precisely about that ordering.
  skip_destroy = true
}

# --- Power state — the daily cost lever (G12) -------------------------------
#
# Stopping the instances IS NOT ENOUGH: most of the monthly cost runs with the
# machines off — EBS volumes and the public IPv4 address are billed at rest.
# This resource is what replaces stopping them by hand, and it is
# infrastructure as code, hence reproducible.
#
# If AWS has stopped an instance and the configuration asks for `running`, the
# next apply attempts a start that may fail for want of capacity. That is the
# expected behaviour and it is informative: it signals a shortage on the chosen
# instance type, not a platform failure.

resource "aws_ec2_instance_state" "compute" {
  instance_id = aws_instance.compute.id
  state       = var.power_state
}

resource "aws_ec2_instance_state" "garage" {
  count = var.node_count

  instance_id = aws_instance.garage[count.index].id
  state       = var.power_state
}
