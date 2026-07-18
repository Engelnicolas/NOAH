#!/usr/bin/env python3
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

"""
NOAH - Cluster Destroy Utilities
Handles Kubernetes cluster destruction and cleanup operations
"""

import click
from Scripts.cluster_destroy.kubectl_utils import cleanup_kubectl_cache


def destroy_cluster(ctx, name, force, keep_secrets, get_security_config):
    """Destroy Kubernetes cluster and clean up resources"""
    if not force:
        click.confirm(f'Are you sure you want to destroy cluster {name}?', abort=True)
    click.echo("[VERBOSE] Starting cluster destruction process...")
    click.echo(f"[VERBOSE] Cluster name: {name}")
    click.echo(f"[VERBOSE] Force mode: {force}")
    click.echo(f"[VERBOSE] Keep secrets: {keep_secrets}")
    
    # Get current security configuration
    security_config = get_security_config()
    
    click.echo(f"Destroying cluster: {name}")
    click.echo("[VERBOSE] Running Ansible playbook: cluster-destroy.yml")
    
    # Clean up secrets and certificates unless specified otherwise
    ctx.obj['ansible'].run_playbook('cluster-destroy.yml', {
        'cluster_name': name,
        'cleanup_secrets': not keep_secrets,
        'cleanup_certificates': not keep_secrets,
        'security_config': security_config
    })
    
    if not keep_secrets:
        click.echo("[VERBOSE] Cleaning up local secrets and certificates...")
        ctx.obj['secrets'].cleanup_local_secrets()
    
    # Clean up kubectl client cache to prevent memcache errors
    click.echo("[VERBOSE] Cleaning up kubectl client cache...")
    cleanup_kubectl_cache()


def destroy_cluster_command(ctx, name, force, keep_secrets, get_security_config):
    """Click command wrapper for cluster destruction"""
    destroy_cluster(ctx, name, force, keep_secrets, get_security_config)