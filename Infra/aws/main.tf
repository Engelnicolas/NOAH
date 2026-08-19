# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH — Infra/aws — machines and network for the development platform.
#
# WHAT THIS LAYER DOES, AND WHERE IT STOPS (Garage.md §16.1)
#
#   machine lifecycle  → here: instances, disks, network, security groups,
#                        public SSH keys, power state
#   machine content    → Ansible/roles/garage-*: ZFS, the Garage binary,
#                        garage.toml, cluster formation, the TLS proxy
#
# No remote-exec, no local-exec calling ansible-playbook. OpenTofu NEVER
# connects over SSH to the machines it creates. The handover is a file
# (infra-inventory.json, §16.3), not a call — which is what makes the
# `baremetal/` target achievable without a single line of code, and what stops
# a fourth secret domain appearing.
#
# This is not a style preference. A remote-exec that installs Garage ties the
# OpenTofu state to the application state: one partial destroy, one instance
# recreated after a Spot interruption, and the state claims a configured Garage
# where there is a bare Ubuntu. §16.4 makes that situation NORMAL, not
# exceptional — it is how a Spot fleet behaves.

terraform {
  required_version = ">= 1.10.0" # OCI provider mirror for offline use, C4

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # V11 FLOOR — NOT A COMFORT SETTING (§16.2, §12.1).
      #
      # Up to and including 5.85.x, destroying a `persistent` Spot instance
      # reported success WITHOUT cancelling the request, which then relaunched
      # an instance outside the state that billed until somebody noticed.
      # Fixed in 5.86.0 (PR #41206). Below this floor G12 inverts: `tofu
      # destroy`, presented as the end-of-campaign saving lever, becomes a
      # silent billing leak. The constraint is budgetary before it is
      # technical, and a committed .terraform.lock.hcl pins it for good.
      version = ">= 5.86.0"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.4.0"
    }
  }

  # G14 — state encrypted by a pbkdf2 passphrase from secret domain 3, not by
  # KMS. Two reasons: the European target cannot depend on KMS, and a state
  # encrypted with a key the AWS account itself holds is no protection against
  # path B of §16.5.
  #
  # Declared HERE rather than left to the TF_ENCRYPTION environment variable:
  # if that variable is unset, OpenTofu writes the state in the clear without
  # saying a word. var.state_passphrase has no default, so its absence fails
  # the run instead. (Variables in this block need the early-evaluation support
  # of OpenTofu 1.8+, which the required_version above covers.)
  encryption {
    key_provider "pbkdf2" "state" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "state" {
      keys = key_provider.pbkdf2.state
    }

    state {
      method   = method.aes_gcm.state
      enforced = true
    }

    plan {
      method   = method.aes_gcm.state
      enforced = true
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      "noah:managed-by" = "opentofu"
      "noah:platform"   = var.name_prefix
    }
  }
}

locals {
  # site-a, site-b for two nodes; site-a, site-a, site-b for three (§4.1).
  # One zone per node in development exercises the zone-aware placement code
  # path that will carry geo-distribution in production; two co-located nodes
  # would not.
  garage_zones = var.node_count == 3 ? ["site-a", "site-a", "site-b"] : ["site-a", "site-b"]

  garage_names = [for i in range(var.node_count) : "garage-${substr("abc", i, 1)}"]
  compute_name = "${var.name_prefix}-compute-dev"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name = "name"
    # GA kernel, deliberately NOT HWE: a kernel upgrade running ahead of
    # OpenZFS support makes the pool unreachable at the next reboot (§5.1,
    # §18). The AMI only sets the starting point; the pin itself is held by
    # the garage-zfs role.
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- Network ----------------------------------------------------------------

resource "aws_vpc" "noah" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${var.name_prefix}-vpc" }
}

resource "aws_internet_gateway" "noah" {
  vpc_id = aws_vpc.noah.id
  tags   = { Name = "${var.name_prefix}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.noah.id
  cidr_block        = var.public_subnet_cidr
  availability_zone = var.availability_zone

  # No auto-assigned public address: the compute node carries an Elastic IP
  # instead. An auto-assigned address CHANGES at every stop/start cycle — and
  # G12 makes power_state the daily lever, so those cycles are frequent. A
  # moving address would rewrite infra-inventory.json, the Ansible inventory
  # and the operator's SSH config every time, and would make the jump-host
  # entry point to the now-private Garage nodes unstable. Since every public
  # IPv4 address is billed whether attached or not, the Elastic IP costs
  # nothing more and buys stability (G19).
  map_public_ip_on_launch = false

  tags = { Name = "${var.name_prefix}-public" }
}

resource "aws_subnet" "garage" {
  vpc_id            = aws_vpc.noah.id
  cidr_block        = var.garage_subnet_cidr
  availability_zone = var.availability_zone

  tags = { Name = "${var.name_prefix}-garage" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.noah.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.noah.id
  }

  tags = { Name = "${var.name_prefix}-rt-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# G19 — the Garage nodes' only way out is the compute node's interface. One
# Elastic IP for the whole platform instead of three billed addresses.
#
# TWO COSTS, STATED PLAINLY: the compute node becomes a single point of failure
# for egress, and it lands on the network path of the storage tier — an
# accepted exception to §16.5, bounded by G20. Tolerable here because the
# Garage nodes only need egress at bootstrap and for updates, never to serve
# S3 (that traffic stays inside the VPC, between private addresses, and takes
# no default route). It would NOT be tolerable in production, and the target of
# §16.6 must not inherit the pattern.
resource "aws_route_table" "garage" {
  vpc_id = aws_vpc.noah.id

  route {
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_instance.compute.primary_network_interface_id
  }

  tags = { Name = "${var.name_prefix}-rt-garage" }
}

resource "aws_route_table_association" "garage" {
  subnet_id      = aws_subnet.garage.id
  route_table_id = aws_route_table.garage.id
}

resource "aws_eip" "compute" {
  domain   = "vpc"
  instance = aws_instance.compute.id

  tags = { Name = "${var.name_prefix}-eip-compute" }

  depends_on = [aws_internet_gateway.noah]
}

# --- SSH key pairs — two distinct pairs, which is the point ------------------

resource "aws_key_pair" "compute" {
  key_name   = "${var.name_prefix}-compute"
  public_key = var.compute_ssh_public_key
}

resource "aws_key_pair" "garage" {
  # A shared key would hand the storage tier to whoever gets root on the
  # compute node. `noah garage deploy` refuses one (T2); publishing a second
  # pair here is the same rule expressed in infrastructure.
  key_name   = "${var.name_prefix}-garage"
  public_key = var.garage_ssh_public_key
}

# --- The handover file (§16.3) ----------------------------------------------
#
# The ONLY coupling allowed between this layer and everything downstream.
# It contains no secret: no private key, no rpc_secret, no S3 credential, no
# cloud provider token. Only public infrastructure facts. That is what lets it
# sit on disk in the clear, and it is why the contract is a file rather than a
# call — a call would sooner or later have carried a secret.
resource "local_file" "infra_inventory" {
  filename        = "${path.module}/infra-inventory.json"
  file_permission = "0644"
  content         = jsonencode(local.infra_inventory)
}
