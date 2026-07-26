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

"""Configuration loader module - Enhanced for dynamic domain management in Helm charts"""

import os
import yaml
from pathlib import Path
from typing import Any, Optional, Dict

class ConfigLoader:
    """
    Enhanced ConfigLoader with dynamic domain management for Helm charts.
    Provides hierarchical configuration with service-specific domain resolution.
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize ConfigLoader with enhanced domain management.
        Note: env_file parameter is kept for backward compatibility but ignored.
        Configuration is now loaded by SecureEnvLoader in noah.py.
        """
        self.config = {}
        self.service_configs = {}
        self.load_config()
        self._init_service_configurations()
    
    def load_config(self):
        """Load configuration from environment variables (already set by SecureEnvLoader)"""
        # Load all environment variables starting with NOAH_ or specific prefixes
        prefixes = ['NOAH_', 'KUBERNETES_', 'AUTHENTIK_', 
                   'CILIUM_', 'TLS_', 'AGE_', 'SOPS_', 'ANSIBLE_', 'HELM_']
        
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in prefixes):
                self.config[key] = value
    
    def _init_service_configurations(self):
        """Initialize service-specific configurations with domain management"""
        self.service_configs = {
            'authentik': {
                'default_subdomain': 'auth',
                'namespace': self.get('KUBERNETES_NAMESPACE_IDENTITY', 'authentik'),
                'port': 80,
                'https_port': 443,
                'path': '/',
                'path_type': 'Prefix',
                'tls_enabled': True,
                'ingress_enabled': True
            },
            'cilium': {
                'default_subdomain': 'hubble',
                'namespace': self.get('KUBERNETES_NAMESPACE_NETWORK', 'kube-system'),
                'port': 80,
                'https_port': 443,
                'path': '/',
                'path_type': 'Prefix',
                'tls_enabled': True,
                'ingress_enabled': True,
                'hubble': {
                    'subdomain': 'hubble',
                    'enabled': True
                }
            },
            'nextcloud': {
                'default_subdomain': 'nextcloud',
                'namespace': 'nextcloud',
                'port': 80,
                'https_port': 443,
                'path': '/',
                'path_type': 'Prefix',
                'tls_enabled': True,
                'ingress_enabled': True
            },
            'headlamp': {
                'default_subdomain': 'headlamp',
                'namespace': 'headlamp',
                'port': 80,
                'https_port': 443,
                'path': '/',
                'path_type': 'Prefix',
                'tls_enabled': True,
                'ingress_enabled': True
            },
            'nginx-ingress': {
                'default_subdomain': '',
                'namespace': 'ingress-nginx',
                'port': 80,
                'https_port': 443,
                'tls_enabled': False,
                'ingress_enabled': False  # nginx-ingress IS the controller, not a backend service
            }
        }
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value from environment or cached config"""
        return self.config.get(key, os.environ.get(key, default))
    
    def set(self, key: str, value: Any):
        """Set configuration value in both cache and environment"""
        self.config[key] = value
        os.environ[key] = str(value)
    
    def get_namespace(self, service: str) -> str:
        """Get namespace for a service"""
        if service in self.service_configs:
            return self.service_configs[service]['namespace']
        
        # Fallback to legacy mapping
        namespace_map = {
            'authentik': self.get('KUBERNETES_NAMESPACE_IDENTITY', 'authentik'),
            'cilium': self.get('KUBERNETES_NAMESPACE_NETWORK', 'kube-system')
        }
        return namespace_map.get(service, 'default')
    
    def get_global_domain(self) -> str:
        """Get the global configured domain"""
        return self.get('NOAH_DOMAIN', '')
    
    def get_cluster_name(self, domain: str = None) -> str:
        """Get the configured cluster name.

        Priority: KUBERNETES_CLUSTER_NAME env var → derived from domain → 'noah-cluster'.
        Deriving from domain ensures each deployment on a distinct domain gets a unique
        txtOwnerId for external-dns, preventing record ownership collisions.
        """
        explicit = self.get('KUBERNETES_CLUSTER_NAME', '')
        if explicit:
            return explicit
        if domain:
            return 'noah-' + domain.replace('.', '-')
        fallback_domain = self.get_domain()
        if fallback_domain:
            return 'noah-' + fallback_domain.replace('.', '-')
        return 'noah-cluster'
    
    def get_environment(self) -> str:
        """Get the deployment environment"""
        return self.get('NOAH_ENVIRONMENT', 'production')
    
    # Enhanced domain management methods
    
    def get_service_domain(self, service: str) -> str:
        """
        Get the domain for a specific service with hierarchy resolution.
        Priority: service-specific > global domain
        """
        # Check for service-specific domain override
        service_domain_key = f'NOAH_{service.upper()}_DOMAIN'
        service_domain = self.get(service_domain_key)
        
        if service_domain:
            return service_domain
        
        # Fallback to global domain
        return self.get_global_domain()
    
    def get_service_subdomain(self, service: str, component: Optional[str] = None) -> str:
        """
        Get the subdomain for a service or service component.
        """
        # Check for service-specific subdomain override
        if component:
            subdomain_key = f'NOAH_{service.upper()}_{component.upper()}_SUBDOMAIN'
        else:
            subdomain_key = f'NOAH_{service.upper()}_SUBDOMAIN'
        
        subdomain = self.get(subdomain_key)
        if subdomain:
            return subdomain
        
        # Get default from service configuration
        if service in self.service_configs:
            if component and component in self.service_configs[service]:
                return self.service_configs[service][component].get('subdomain', component)
            return self.service_configs[service]['default_subdomain']
        
        # Ultimate fallback
        return service
    
    def get_service_fqdn(self, service: str, component: Optional[str] = None) -> str:
        """
        Get fully qualified domain name for a service.
        Format: {subdomain}.{domain}
        """
        subdomain = self.get_service_subdomain(service, component)
        domain = self.get_service_domain(service)
        return f"{subdomain}.{domain}"
    
    def get_service_ingress_config(self, service: str) -> Dict[str, Any]:
        """
        Generate ingress configuration for a service.
        """
        if service not in self.service_configs:
            raise ValueError(f"Unknown service: {service}")
        
        service_config = self.service_configs[service]
        
        if not service_config.get('ingress_enabled', False):
            return {'enabled': False}
        
        fqdn = self.get_service_fqdn(service)
        tls_secret_name = f"{service}-tls"
        
        return {
            'enabled': True,
            'className': self.get('NOAH_INGRESS_CLASS', 'cilium'),
            'annotations': {
                'cert-manager.io/cluster-issuer': 'letsencrypt-prod',
                'nginx.ingress.kubernetes.io/ssl-redirect': 'true' if service_config.get('tls_enabled') else 'false'
            },
            'hosts': [{
                'host': fqdn,
                'paths': [{
                    'path': service_config.get('path', '/'),
                    'pathType': service_config.get('path_type', 'Prefix')
                }]
            }],
            'tls': [{
                'secretName': tls_secret_name,
                'hosts': [fqdn]
            }] if service_config.get('tls_enabled', True) else []
        }
    
    def get_service_config(self, service: str) -> Dict[str, Any]:
        """
        Get complete service configuration including domain, networking, and security.
        """
        if service not in self.service_configs:
            raise ValueError(f"Unknown service: {service}")
        
        base_config = self.service_configs[service].copy()
        
        # Add dynamic values
        base_config.update({
            'domain': self.get_service_domain(service),
            'subdomain': self.get_service_subdomain(service),
            'fqdn': self.get_service_fqdn(service),
            'ingress': self.get_service_ingress_config(service),
            'namespace': self.get_namespace(service)
        })
        
        return base_config
    
    def generate_helm_values(self, service: str, custom_values: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate complete Helm values for a service with domain management.
        """
        service_config = self.get_service_config(service)
        
        # Base Helm values structure
        helm_values = {
            'global': {
                'domain': self.get_global_domain(),
                'cluster_name': self.get_cluster_name(),
                'environment': self.get_environment(),
                'namespace': service_config['namespace'],
                'noah': {
                    'version': self.get('NOAH_VERSION', '0.2.1'),
                    'managed': True
                }
            },
            'service': {
                'name': service,
                'domain': service_config['domain'],
                'subdomain': service_config['subdomain'],
                'fqdn': service_config['fqdn'],
                'port': service_config.get('port', 80),
                'httpsPort': service_config.get('https_port', 443)
            },
            'ingress': service_config['ingress'],
            'tls': {
                'enabled': service_config.get('tls_enabled', True),
                'secretName': f"{service}-tls"
            }
        }
        
        # Service-specific customizations
        if service == 'authentik':
            helm_values.update(self._get_authentik_helm_values())
        elif service == 'cilium':
            helm_values.update(self._get_cilium_helm_values())
        
        # Apply custom values if provided
        if custom_values:
            helm_values = self._deep_merge(helm_values, custom_values)
        
        return helm_values
    
    def _get_authentik_helm_values(self) -> Dict[str, Any]:
        """Generate Authentik-specific Helm values"""
        return {
            'authentik': {
                'secret_key': {
                    'secretName': 'authentik-secret',
                    'secretKey': 'secret-key'
                },
                'postgresql': {
                    'enabled': True,
                    'auth': {
                        'existingSecret': 'authentik-postgresql'
                    }
                },
                'redis': {
                    'enabled': True,
                    'auth': {
                        'existingSecret': 'authentik-redis'
                    }
                }
            }
        }
    
    def _get_cilium_helm_values(self) -> Dict[str, Any]:
        """Generate Cilium-specific Helm values"""
        hubble_fqdn = self.get_service_fqdn('cilium', 'hubble')
        
        return {
            'cilium': {
                'kubeProxyReplacement': True,
                'hubble': {
                    'enabled': True,
                    'relay': {
                        'enabled': True
                    },
                    'ui': {
                        'enabled': True,
                        'ingress': {
                            'enabled': True,
                            'hosts': [hubble_fqdn],
                            'tls': [{
                                'secretName': 'hubble-ui-tls',
                                'hosts': [hubble_fqdn]
                            }]
                        }
                    }
                }
            }
        }
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def export_helm_values_file(self, service: str, output_path: Path, custom_values: Optional[Dict] = None):
        """
        Export Helm values to a YAML file for a specific service.
        """
        values = self.generate_helm_values(service, custom_values)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(values, f, default_flow_style=False, indent=2)
        
        print(f"✅ Exported Helm values for {service} to {output_path}")
    
    # DNS provider configuration methods

    # Legacy compatibility methods
    def get_domain(self) -> str:
        """Legacy method - use get_global_domain() instead"""
        return self.get_global_domain()
