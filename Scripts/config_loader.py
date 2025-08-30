"""Configuration loader module - Updated for NOAH SecureEnvLoader integration"""

import os
from pathlib import Path
from typing import Any, Optional

class ConfigLoader:
    """
    Simplified ConfigLoader that works with NOAH's SecureEnvLoader system.
    Since SecureEnvLoader already loads encrypted config into os.environ,
    this class now just provides a convenient interface to environment variables.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize ConfigLoader. 
        Note: env_file parameter is kept for backward compatibility but ignored.
        Configuration is now loaded by SecureEnvLoader in noah.py.
        """
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from environment variables (already set by SecureEnvLoader)"""
        # Load all environment variables starting with NOAH_ or specific prefixes
        prefixes = ['NOAH_', 'KUBERNETES_', 'AUTHENTIK_', 
                   'CILIUM_', 'TLS_', 'AGE_', 'SOPS_', 'ANSIBLE_', 'HELM_']
        
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in prefixes):
                self.config[key] = value
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value from environment or cached config"""
        return self.config.get(key, os.environ.get(key, default))
    
    def set(self, key: str, value: Any):
        """Set configuration value in both cache and environment"""
        self.config[key] = value
        os.environ[key] = str(value)
    
    def get_namespace(self, service: str) -> str:
        """Get namespace for a service"""
        namespace_map = {
            'authentik': self.get('KUBERNETES_NAMESPACE_IDENTITY', 'identity'),
            'cilium': self.get('KUBERNETES_NAMESPACE_NETWORK', 'kube-system'),
            'samba4': self.get('KUBERNETES_NAMESPACE_IDENTITY', 'identity')
        }
        return namespace_map.get(service, 'default')
    
    def get_domain(self) -> str:
        """Get the configured domain"""
        return self.get('NOAH_DOMAIN', 'noah-infra.com')
    
    def get_cluster_name(self) -> str:
        """Get the configured cluster name"""
        return self.get('KUBERNETES_CLUSTER_NAME', 'noah-cluster')
