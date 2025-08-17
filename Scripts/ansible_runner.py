"""Ansible playbook execution module"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional

class AnsibleRunner:
    def __init__(self, config_loader):
        self.config = config_loader
        self.playbook_dir = Path(self.config.get('ANSIBLE_PLAYBOOK_DIR', './Ansible'))
        self.inventory = self.config.get('ANSIBLE_INVENTORY', './Ansible/inventory')
    
    def run_playbook(self, playbook_name: str, extra_vars: Optional[Dict] = None):
        """Execute an Ansible playbook"""
        playbook_path = self.playbook_dir / playbook_name
        
        if not playbook_path.exists():
            raise Exception(f"Playbook not found: {playbook_path}")
        
        # Build ansible-playbook command
        cmd = [
            'ansible-playbook',
            str(playbook_path),
            '-i', self.inventory
        ]
        
        # Add extra variables
        if extra_vars:
            extra_vars_str = ' '.join([f'{k}={v}' for k, v in extra_vars.items()])
            cmd.extend(['--extra-vars', extra_vars_str])
        
        # Set environment variables
        env = os.environ.copy()
        env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        env['SOPS_AGE_KEY_FILE'] = str(self.config.get('AGE_KEY_FILE', './Age/keys.txt'))
        
        print(f"Running playbook: {playbook_name}")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Playbook {playbook_name} executed successfully")
            return True
        else:
            print(f"Playbook {playbook_name} failed: {result.stderr}")
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
