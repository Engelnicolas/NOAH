"""Configuration loader module"""

import os
from pathlib import Path
from typing import Any, Optional
from dotenv import load_dotenv

class ConfigLoader:
    def __init__(self, env_file: str = '.env'):
        self.env_file = Path(env_file)
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment file"""
        if self.env_file.exists():
            load_dotenv(self.env_file)
        
        # Load all environment variables starting with NOAH_ or specific prefixes
        prefixes = ['NOAH_', 'KUBERNETES_', 'AUTHENTIK_', 
                   'CILIUM_', 'TLS_', 'AGE_', 'SOPS_', 'ANSIBLE_', 'HELM_']
        
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in prefixes):
                self.config[key] = value
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, os.environ.get(key, default))
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        os.environ[key] = str(value)
    
    def get_namespace(self, service: str) -> str:
        """Get namespace for a service"""
        namespace_map = {
            'authentik': self.get('KUBERNETES_NAMESPACE_IDENTITY', 'identity'),
            'cilium': self.get('KUBERNETES_NAMESPACE_NETWORK', 'kube-system')
        }
        return namespace_map.get(service, 'default')
