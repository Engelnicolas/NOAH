#!/usr/bin/env python3
"""
Export environment variables from encrypted SOPS configuration for Ansible
"""

import sys
import os
from pathlib import Path

# Get the current working directory (should be NOAH root)
noah_root = Path.cwd()
sys.path.insert(0, str(noah_root))

from Scripts.security.secure_env_loader import SecureEnvLoader

def main():
    """Load encrypted config and export environment variables"""
    try:
        # Load encrypted configuration
        loader = SecureEnvLoader()
        config_path = noah_root / 'Config' / 'config.enc.yaml'
        loader.load_secure_env(config_path)
        
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
