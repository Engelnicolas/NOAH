#!/usr/bin/env python3
"""
Export environment variables from encrypted SOPS configuration for Ansible
"""

import sys
import os
sys.path.insert(0, '/root/NOAH')

from Scripts.secure_env_loader import SecureEnvLoader
from pathlib import Path

def main():
    """Load encrypted config and export environment variables"""
    try:
        # Load encrypted configuration
        loader = SecureEnvLoader()
        loader.load_secure_env(Path('/root/NOAH/Config/config.enc.yaml'))
        
        # Output environment variables in shell format
        important_vars = [
            'NOAH_ROOT_DIR', 'NOAH_SCRIPTS_DIR', 'NOAH_CERTIFICATES_DIR',
            'ANSIBLE_PLAYBOOK_DIR', 'HELM_CHART_DIR',
            'KUBERNETES_CLUSTER_NAME', 'KUBERNETES_NAMESPACE_IDENTITY',
            'AUTHENTIK_SECRET_KEY', 'AUTHENTIK_BOOTSTRAP_PASSWORD',
            'TLS_COUNTRY', 'TLS_STATE', 'TLS_LOCALITY', 'TLS_ORGANIZATION'
        ]
        
        for var in important_vars:
            value = os.getenv(var)
            if value:
                print(f"{var}={value}")
            
    except Exception as e:
        print(f"ERROR: Failed to load encrypted configuration: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
