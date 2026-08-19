# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH - Network Operations & Automation Hub
# Copyright (C) 2026 Nicolas Engel <contact@nicolasengel.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Garage object storage — deployment, provisioning and admin secret domain.

Garage is the one component of the target that lives OUTSIDE the cluster and
out of reach of the compute node. That double externality is what gives the
ZFS-snapshot immutability strategy its value, so it is a property of the code
here, not merely of the deployment:

  * admin_store      — secret domain 3, encrypted to its own Age identity,
                       never handed to any node (§3.1)
  * garage_deploy    — inventory construction + Ansible/deploy-garage.yml
  * garage_provision — layout, buckets, S3 keys (generated here, imported
                       into Garage — never the other way round, §6.2)

See Specs/To-do/Garage.md.
"""
