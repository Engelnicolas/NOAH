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

import os
import subprocess
import tempfile
from pathlib import Path

import click
import yaml

from Scripts.cluster_destroy.kubectl_utils import cleanup_kubectl_cache


def _run_destroy_playbook(config, extra_vars: dict) -> int:
    """Run Ansible/cluster-destroy.yml with *extra_vars*.

    Inlined here rather than routed through a shared runner: the bootstrap
    path does the same (Scripts/cluster_create/bootstrap_utils.py), and one
    execution pattern is enough for the whole project.

    Variables travel in a temporary YAML file passed as `--extra-vars @file`,
    never as `k=v` — `security_config` is a dict, and the k=v form would
    flatten it into a string the playbook cannot read back.
    """
    ansible_dir = Path(config.get('ANSIBLE_PLAYBOOK_DIR', './Ansible')).resolve()

    with tempfile.TemporaryDirectory(prefix="noah-destroy-") as tmpdir:
        vars_path = Path(tmpdir) / "extra-vars.yml"
        vars_path.write_text(yaml.safe_dump(extra_vars, sort_keys=False))
        os.chmod(vars_path, 0o600)

        # Checked before any subprocess.run, so tests never reach Ansible.
        if os.environ.get('NOAH_SKIP_ANSIBLE', 'false').lower() in ('1', 'true', 'yes'):
            click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ansible-playbook.")
            return 0

        cmd = [
            'ansible-playbook',
            '-i', 'inventory/hosts.yml',   # cluster-destroy.yml runs on localhost
            'cluster-destroy.yml',
            '--extra-vars', f'@{vars_path}',
        ]
        env = os.environ.copy()
        env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        env['SOPS_AGE_KEY_FILE'] = str(config.get('AGE_KEY_FILE', './Age/keys.txt'))
        return subprocess.run(cmd, cwd=ansible_dir, env=env).returncode


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
    _run_destroy_playbook(ctx.obj['config'], {
        'cluster_name': name,
        'cleanup_secrets': not keep_secrets,
        'cleanup_certificates': not keep_secrets,
        'security_config': security_config,
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
