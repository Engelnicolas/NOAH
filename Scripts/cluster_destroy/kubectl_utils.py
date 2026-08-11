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
NOAH CLI - kubectl Utilities

This module contains kubectl-related utility functions for the NOAH CLI.
Helps manage kubectl configuration, cache, and environment cleanup.
"""

import os
import shutil
from pathlib import Path

import click


def cleanup_kubectl_cache():
    """
    Clean up kubectl client cache and configuration to prevent memcache errors.
    
    This function removes:
    - ~/.kube/config file
    - ~/.kube/cache directory  
    - KUBECONFIG environment variable (if pointing to K3s config)
    
    This prevents kubectl memcache errors after cluster destruction by ensuring
    the client doesn't try to connect to non-existent clusters.
    
    Returns:
        bool: True if cleanup was successful, False if errors occurred
    """
    try:
        kube_dir = Path.home() / '.kube'

        # Remove kubectl config file
        config_file = kube_dir / 'config'
        if config_file.exists():
            config_file.unlink()
            click.echo("[VERBOSE] Removed kubectl config file")
        
        # Remove kubectl cache directory
        cache_dir = kube_dir / 'cache'
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            click.echo("[VERBOSE] Removed kubectl cache directory")
        
        # Clear KUBECONFIG environment variable if it points to removed K3s config
        kubeconfig = os.environ.get('KUBECONFIG')
        if kubeconfig == '/etc/rancher/k3s/k3s.yaml':
            if 'KUBECONFIG' in os.environ:
                del os.environ['KUBECONFIG']
            click.echo("[VERBOSE] Cleared KUBECONFIG environment variable")
        
        click.echo("[VERBOSE] kubectl cache cleanup completed - memcache errors should be resolved")
        return True
        
    except Exception as e:
        click.echo(f"[WARNING] kubectl cache cleanup failed: {e}")
        return False
