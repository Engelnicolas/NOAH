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

"""Ansible playbook execution module"""

import os
import subprocess
from pathlib import Path


class AnsibleRunner:
    def __init__(self, config_loader):
        self.config = config_loader
        self.playbook_dir = Path(self.config.get('ANSIBLE_PLAYBOOK_DIR', './Ansible')).resolve()
        self.ansible_dir = Path('./Ansible').resolve()
    
    def run_playbook(self, playbook_name: str, extra_vars: dict | None = None):
        """Execute an Ansible playbook"""
        playbook_path = self.playbook_dir / playbook_name
        
        if not playbook_path.exists():
            raise Exception(f"Playbook not found: {playbook_path}")

        # Test shortcut: allow skipping real Ansible execution in unit/integration tests
        if os.environ.get('NOAH_SKIP_ANSIBLE', 'false').lower() in ('1','true','yes'):
            print(f"[TEST-SHORTCUT] Skipping execution of {playbook_name} due to NOAH_SKIP_ANSIBLE env var.")
            print(f"[TEST-SHORTCUT] Extra vars: {extra_vars}")
            return True
        
        # Build ansible-playbook command - use config file in Ansible directory
        # Use relative path from Ansible directory
        cmd = [
            'ansible-playbook',
            '-i', 'inventory/hosts.yml',  # Explicitly specify inventory
            playbook_name  # Just the filename since we'll run from Ansible dir
        ]
        
        # Set working directory to Ansible folder to use ansible.cfg
        cwd = self.ansible_dir
        
        # Add extra variables
        if extra_vars:
            extra_vars_str = ' '.join([f'{k}={v}' for k, v in extra_vars.items()])
            cmd.extend(['--extra-vars', extra_vars_str])
        
        # Set environment variables
        env = os.environ.copy()
        env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        env['SOPS_AGE_KEY_FILE'] = str(self.config.get('AGE_KEY_FILE', './Age/keys.txt'))
        
        print(f"Running playbook: {playbook_name}")
        result = subprocess.run(cmd, env=env, text=True, cwd=cwd)
        
        if result.returncode == 0:
            print(f"Playbook {playbook_name} executed successfully")
            return True
        else:
            print(f"Playbook {playbook_name} failed with exit code: {result.returncode}")
            return False
    
    def check_prerequisites(self) -> bool:
        """Check if Ansible and required modules are installed"""
        required_commands = ['ansible', 'ansible-playbook']
        
        for cmd in required_commands:
            result = subprocess.run(['which', cmd], capture_output=True)
            if result.returncode != 0:
                print(f"Error: {cmd} not found. Please install Ansible.")
                return False
        
        # Check for required Ansible collections
        result = subprocess.run(
            ['ansible-galaxy', 'collection', 'list'],
            capture_output=True,
            text=True
        )
        
        required_collections = [
            'kubernetes.core',
            'community.general',
            'community.sops'
        ]
        
        for collection in required_collections:
            if collection not in result.stdout:
                print(f"Installing required collection: {collection}")
                subprocess.run(['ansible-galaxy', 'collection', 'install', collection])
        
        return True
