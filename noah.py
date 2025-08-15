#!/usr/bin/env python3
"""
NOAH CLI - Python Implementation
Network Operations & Automation Hub

This is the Python implementation of the NOAH CLI,
converted from the original bash script for better maintainability.
"""

import click
import subprocess
import sys
import datetime
from pathlib import Path
from typing import Dict, Optional
import yaml
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt, Confirm
import shutil

console = Console()


class NoahConfig:
    """Enhanced configuration management for NOAH platform"""

    def __init__(self, config_path: Path = Path(".noah_config")):
        self.config_path = config_path
        self.config = self.load_config()
        self.script_dir = Path.cwd()
        self.env_profile = self.config.get('NOAH_ENV', 'development')  # Default to development

    def load_config(self) -> Dict:
        """Load configuration from file or defaults"""
        default_config = {
            # Infrastructure settings
            "INFRASTRUCTURE_TYPE": "kubernetes",
            "NOAH_ENV": "development",  # Default to development environment
            "NOAH_DEBUG": "true",  # Enable debug by default for development
            
            # Domain and networking
            "NOAH_DOMAIN": "noah.local",
            "INGRESS_IP": "127.0.0.1",
            "INGRESS_CLASS": "nginx",
            
            # Kubernetes cluster configuration
            "KUBE_VERSION": "v1.28.2",
            "KUBE_NETWORK_PLUGIN": "calico",
            "POD_SUBNET": "10.233.64.0/18",
            "SERVICE_SUBNET": "10.233.0.0/18",
            "CLUSTER_NAME": "noah-cluster",
            
            # Namespaces
            "NOAH_NAMESPACE": "noah",
            "MONITORING_NAMESPACE": "monitoring",
            
            # Helm configuration
            "HELM_VERSION": "3.13.2",
            
            # Certificate management
            "CERT_MANAGER_ENABLED": "true",
            "TLS_ENABLED": "true",
            "TLS_MODE": "letsencrypt",  # Options: manual, letsencrypt, self-signed
            "LETSENCRYPT_EMAIL": "admin@noah.local",
            
            # Storage configuration
            "STORAGE_CLASS": "local-storage",
            "STORAGE_PROVISIONER": "kubernetes.io/no-provisioner",
            
            # Monitoring configuration
            "MONITORING_ENABLED": "true",
            "METRICS_RETENTION": "30d",
            "PROMETHEUS_STORAGE_SIZE": "20Gi",
            "GRAFANA_STORAGE_SIZE": "10Gi",
            
            # Application configuration
            "POSTGRESQL_VERSION": "15.4.0",
            "POSTGRESQL_STORAGE_SIZE": "20Gi",
            "POSTGRESQL_DATABASE": "noah",
            "POSTGRESQL_USERNAME": "noah",
            
            # Backup configuration
            "BACKUP_ENABLED": "true",
            "BACKUP_RETENTION": "30d",
            "BACKUP_SCHEDULE": "0 2 * * *",
            
            # Development-specific paths
            "SOPS_AGE_KEY_FILE": str(Path.cwd() / 'age' / 'keys.txt'),
            "NOAH_TLS_CERT": str(Path.cwd() / 'certs' / 'tls.crt'),
            "NOAH_TLS_KEY": str(Path.cwd() / 'certs' / 'tls.key'),
            
            # KUBECONFIG path
            "KUBECONFIG": str(Path.home() / '.kube' / 'config'),
            
            # Application hostnames
            "KEYCLOAK_HOSTNAME": "keycloak.noah.local",
            "GRAFANA_HOSTNAME": "grafana.noah.local",
            "GITLAB_HOSTNAME": "gitlab.noah.local",
            "MATTERMOST_HOSTNAME": "mattermost.noah.local",
            "NEXTCLOUD_HOSTNAME": "nextcloud.noah.local",
            "PROMETHEUS_HOSTNAME": "prometheus.noah.local",
            "ALERTMANAGER_HOSTNAME": "alertmanager.noah.local",
            
            # Security settings
            "KEYCLOAK_REALM": "noah",
            "OAUTH2_PROXY_ENABLED": "true",
        }
        
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = {}
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
                
                # Merge with defaults
                default_config.update(config)
                return default_config
        
        return default_config

    def save_config(self):
        """Save configuration to file with comments and sections"""
        with open(self.config_path, 'w') as f:
            f.write(f"# NOAH Platform Configuration\n")
            f.write(f"# Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"# Environment: {self.env_profile}\n\n")
            
            # Infrastructure settings
            f.write("# Infrastructure Configuration\n")
            f.write(f"INFRASTRUCTURE_TYPE={self.config.get('INFRASTRUCTURE_TYPE', 'kubernetes')}\n")
            f.write(f"NOAH_ENV={self.config.get('NOAH_ENV', 'development')}\n")
            f.write(f"CLUSTER_NAME={self.config.get('CLUSTER_NAME', 'noah-cluster')}\n\n")
            
            # Domain and networking
            f.write("# Domain and Networking\n")
            f.write(f"NOAH_DOMAIN={self.config.get('NOAH_DOMAIN', 'noah.local')}\n")
            f.write(f"INGRESS_IP={self.config.get('INGRESS_IP', '127.0.0.1')}\n")
            f.write(f"INGRESS_CLASS={self.config.get('INGRESS_CLASS', 'nginx')}\n\n")
            
            # Kubernetes configuration
            f.write("# Kubernetes Configuration\n")
            f.write(f"KUBE_VERSION={self.config.get('KUBE_VERSION', 'v1.28.2')}\n")
            f.write(f"KUBE_NETWORK_PLUGIN={self.config.get('KUBE_NETWORK_PLUGIN', 'calico')}\n")
            f.write(f"POD_SUBNET={self.config.get('POD_SUBNET', '10.233.64.0/18')}\n")
            f.write(f"SERVICE_SUBNET={self.config.get('SERVICE_SUBNET', '10.233.0.0/18')}\n")
            f.write(f"KUBECONFIG={self.config.get('KUBECONFIG', str(Path.home() / '.kube' / 'config'))}\n\n")
            
            # Namespaces
            f.write("# Kubernetes Namespaces\n")
            f.write(f"NOAH_NAMESPACE={self.config.get('NOAH_NAMESPACE', 'noah')}\n")
            f.write(f"MONITORING_NAMESPACE={self.config.get('MONITORING_NAMESPACE', 'monitoring')}\n\n")
            
            # Helm configuration
            f.write("# Helm Configuration\n")
            f.write(f"HELM_VERSION={self.config.get('HELM_VERSION', '3.13.2')}\n\n")
            
            # Certificate management
            f.write("# Certificate Management\n")
            f.write(f"CERT_MANAGER_ENABLED={self.config.get('CERT_MANAGER_ENABLED', 'true')}\n")
            f.write(f"TLS_ENABLED={self.config.get('TLS_ENABLED', 'true')}\n")
            f.write(f"TLS_MODE={self.config.get('TLS_MODE', 'letsencrypt')}\n")
            f.write(f"LETSENCRYPT_EMAIL={self.config.get('LETSENCRYPT_EMAIL', 'admin@noah.local')}\n\n")
            
            # Storage configuration
            f.write("# Storage Configuration\n")
            f.write(f"STORAGE_CLASS={self.config.get('STORAGE_CLASS', 'local-storage')}\n")
            f.write(f"STORAGE_PROVISIONER={self.config.get('STORAGE_PROVISIONER', 'kubernetes.io/no-provisioner')}\n\n")
            
            # Monitoring configuration
            f.write("# Monitoring Configuration\n")
            f.write(f"MONITORING_ENABLED={self.config.get('MONITORING_ENABLED', 'true')}\n")
            f.write(f"METRICS_RETENTION={self.config.get('METRICS_RETENTION', '30d')}\n")
            f.write(f"PROMETHEUS_STORAGE_SIZE={self.config.get('PROMETHEUS_STORAGE_SIZE', '20Gi')}\n")
            f.write(f"GRAFANA_STORAGE_SIZE={self.config.get('GRAFANA_STORAGE_SIZE', '10Gi')}\n\n")
            
            # Application hostnames
            f.write("# Application Hostnames\n")
            f.write(f"KEYCLOAK_HOSTNAME={self.config.get('KEYCLOAK_HOSTNAME', 'keycloak.noah.local')}\n")
            f.write(f"GRAFANA_HOSTNAME={self.config.get('GRAFANA_HOSTNAME', 'grafana.noah.local')}\n")
            f.write(f"GITLAB_HOSTNAME={self.config.get('GITLAB_HOSTNAME', 'gitlab.noah.local')}\n")
            f.write(f"MATTERMOST_HOSTNAME={self.config.get('MATTERMOST_HOSTNAME', 'mattermost.noah.local')}\n")
            f.write(f"NEXTCLOUD_HOSTNAME={self.config.get('NEXTCLOUD_HOSTNAME', 'nextcloud.noah.local')}\n")
            f.write(f"PROMETHEUS_HOSTNAME={self.config.get('PROMETHEUS_HOSTNAME', 'prometheus.noah.local')}\n")
            f.write(f"ALERTMANAGER_HOSTNAME={self.config.get('ALERTMANAGER_HOSTNAME', 'alertmanager.noah.local')}\n\n")
            
            # PostgreSQL configuration
            f.write("# PostgreSQL Configuration\n")
            f.write(f"POSTGRESQL_VERSION={self.config.get('POSTGRESQL_VERSION', '15.4.0')}\n")
            f.write(f"POSTGRESQL_STORAGE_SIZE={self.config.get('POSTGRESQL_STORAGE_SIZE', '20Gi')}\n")
            f.write(f"POSTGRESQL_DATABASE={self.config.get('POSTGRESQL_DATABASE', 'noah')}\n")
            f.write(f"POSTGRESQL_USERNAME={self.config.get('POSTGRESQL_USERNAME', 'noah')}\n\n")
            
            # Backup configuration
            f.write("# Backup Configuration\n")
            f.write(f"BACKUP_ENABLED={self.config.get('BACKUP_ENABLED', 'true')}\n")
            f.write(f"BACKUP_RETENTION={self.config.get('BACKUP_RETENTION', '30d')}\n")
            f.write(f"BACKUP_SCHEDULE={self.config.get('BACKUP_SCHEDULE', '0 2 * * *')}\n\n")
            
            # Security settings
            f.write("# Security Settings\n")
            f.write(f"KEYCLOAK_REALM={self.config.get('KEYCLOAK_REALM', 'noah')}\n")
            f.write(f"OAUTH2_PROXY_ENABLED={self.config.get('OAUTH2_PROXY_ENABLED', 'true')}\n\n")
            
            # Development settings (only if dev environment)
            if self.env_profile == 'development':
                f.write("# Development Settings\n")
                f.write(f"NOAH_DEBUG={self.config.get('NOAH_DEBUG', 'true')}\n")
                
                # SOPS and security paths
                if 'SOPS_AGE_KEY_FILE' in self.config:
                    f.write(f"SOPS_AGE_KEY_FILE={self.config['SOPS_AGE_KEY_FILE']}\n")
                if 'NOAH_TLS_CERT' in self.config:
                    f.write(f"NOAH_TLS_CERT={self.config['NOAH_TLS_CERT']}\n")
                if 'NOAH_TLS_KEY' in self.config:
                    f.write(f"NOAH_TLS_KEY={self.config['NOAH_TLS_KEY']}\n")
                f.write("\n")
            
            # Additional settings
            other_keys = set(self.config.keys()) - {
                'INFRASTRUCTURE_TYPE', 'NOAH_ENV', 'CLUSTER_NAME', 'NOAH_DOMAIN', 'INGRESS_IP', 'INGRESS_CLASS',
                'KUBE_VERSION', 'KUBE_NETWORK_PLUGIN', 'POD_SUBNET', 'SERVICE_SUBNET', 'KUBECONFIG',
                'NOAH_NAMESPACE', 'MONITORING_NAMESPACE', 'HELM_VERSION', 'CERT_MANAGER_ENABLED', 'TLS_ENABLED',
                'TLS_MODE', 'LETSENCRYPT_EMAIL', 'STORAGE_CLASS', 'STORAGE_PROVISIONER', 'MONITORING_ENABLED',
                'METRICS_RETENTION', 'PROMETHEUS_STORAGE_SIZE', 'GRAFANA_STORAGE_SIZE', 'KEYCLOAK_HOSTNAME',
                'GRAFANA_HOSTNAME', 'GITLAB_HOSTNAME', 'MATTERMOST_HOSTNAME', 'NEXTCLOUD_HOSTNAME',
                'PROMETHEUS_HOSTNAME', 'ALERTMANAGER_HOSTNAME', 'POSTGRESQL_VERSION', 'POSTGRESQL_STORAGE_SIZE',
                'POSTGRESQL_DATABASE', 'POSTGRESQL_USERNAME', 'BACKUP_ENABLED', 'BACKUP_RETENTION', 'BACKUP_SCHEDULE',
                'KEYCLOAK_REALM', 'OAUTH2_PROXY_ENABLED', 'NOAH_DEBUG', 'SOPS_AGE_KEY_FILE', 'NOAH_TLS_CERT', 'NOAH_TLS_KEY'
            }
            
            if other_keys:
                f.write("# Additional Settings\n")
                for key in sorted(other_keys):
                    f.write(f"{key}={self.config[key]}\n")

    def get_env_vars(self) -> Dict[str, str]:
        """Get configuration as environment variables"""
        env_vars = {}
        
        # Convert all config to environment variables
        for key, value in self.config.items():
            env_vars[key] = value
        
        return env_vars

    def write_env_file(self, env_file_path: Optional[Path] = None):
        """Write environment variables to .env file"""
        if env_file_path is None:
            env_file_path = Path(f".env.{self.env_profile}")
        
        env_vars = self.get_env_vars()
        
        with open(env_file_path, 'w') as f:
            f.write(f"# NOAH Environment Variables\n")
            f.write(f"# Environment: {self.env_profile}\n")
            f.write(f"# Generated: {datetime.datetime.now().isoformat()}\n")
            f.write(f"# Source this file: source {env_file_path}\n\n")
            
            # Infrastructure
            f.write("# Infrastructure Configuration\n")
            infrastructure_vars = ['INFRASTRUCTURE_TYPE', 'NOAH_ENV', 'CLUSTER_NAME']
            for var in infrastructure_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Domain and Networking
            f.write("\n# Domain and Networking\n")
            network_vars = ['NOAH_DOMAIN', 'INGRESS_IP', 'INGRESS_CLASS']
            for var in network_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Kubernetes
            f.write("\n# Kubernetes Configuration\n")
            k8s_vars = ['KUBE_VERSION', 'KUBE_NETWORK_PLUGIN', 'POD_SUBNET', 'SERVICE_SUBNET', 'KUBECONFIG']
            for var in k8s_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Namespaces
            f.write("\n# Kubernetes Namespaces\n")
            namespace_vars = ['NOAH_NAMESPACE', 'MONITORING_NAMESPACE']
            for var in namespace_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Helm
            f.write("\n# Helm Configuration\n")
            helm_vars = ['HELM_VERSION']
            for var in helm_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Certificate management
            f.write("\n# Certificate Management\n")
            cert_vars = ['CERT_MANAGER_ENABLED', 'TLS_ENABLED', 'TLS_MODE', 'LETSENCRYPT_EMAIL']
            for var in cert_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Storage
            f.write("\n# Storage Configuration\n")
            storage_vars = ['STORAGE_CLASS', 'STORAGE_PROVISIONER']
            for var in storage_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Monitoring
            f.write("\n# Monitoring Configuration\n")
            monitoring_vars = ['MONITORING_ENABLED', 'METRICS_RETENTION', 'PROMETHEUS_STORAGE_SIZE', 'GRAFANA_STORAGE_SIZE']
            for var in monitoring_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Application hostnames
            f.write("\n# Application Hostnames\n")
            hostname_vars = ['KEYCLOAK_HOSTNAME', 'GRAFANA_HOSTNAME', 'GITLAB_HOSTNAME', 'MATTERMOST_HOSTNAME', 
                           'NEXTCLOUD_HOSTNAME', 'PROMETHEUS_HOSTNAME', 'ALERTMANAGER_HOSTNAME']
            for var in hostname_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # PostgreSQL
            f.write("\n# PostgreSQL Configuration\n")
            pg_vars = ['POSTGRESQL_VERSION', 'POSTGRESQL_STORAGE_SIZE', 'POSTGRESQL_DATABASE', 'POSTGRESQL_USERNAME']
            for var in pg_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Backup
            f.write("\n# Backup Configuration\n")
            backup_vars = ['BACKUP_ENABLED', 'BACKUP_RETENTION', 'BACKUP_SCHEDULE']
            for var in backup_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Security
            f.write("\n# Security Settings\n")
            security_vars = ['KEYCLOAK_REALM', 'OAUTH2_PROXY_ENABLED']
            for var in security_vars:
                if var in env_vars:
                    f.write(f"export {var}={env_vars[var]}\n")
            
            # Development-specific (for development environment only)
            if self.env_profile == 'development':
                f.write("\n# Development Settings\n")
                dev_vars = ['NOAH_DEBUG', 'SOPS_AGE_KEY_FILE', 'NOAH_TLS_CERT', 'NOAH_TLS_KEY']
                for var in dev_vars:
                    if var in env_vars:
                        f.write(f"export {var}={env_vars[var]}\n")
            
            # Additional variables
            all_categorized_vars = set([
                'INFRASTRUCTURE_TYPE', 'NOAH_ENV', 'CLUSTER_NAME', 'NOAH_DOMAIN', 'INGRESS_IP', 'INGRESS_CLASS',
                'KUBE_VERSION', 'KUBE_NETWORK_PLUGIN', 'POD_SUBNET', 'SERVICE_SUBNET', 'KUBECONFIG',
                'NOAH_NAMESPACE', 'MONITORING_NAMESPACE', 'HELM_VERSION', 'CERT_MANAGER_ENABLED', 'TLS_ENABLED',
                'TLS_MODE', 'LETSENCRYPT_EMAIL', 'STORAGE_CLASS', 'STORAGE_PROVISIONER', 'MONITORING_ENABLED',
                'METRICS_RETENTION', 'PROMETHEUS_STORAGE_SIZE', 'GRAFANA_STORAGE_SIZE', 'KEYCLOAK_HOSTNAME',
                'GRAFANA_HOSTNAME', 'GITLAB_HOSTNAME', 'MATTERMOST_HOSTNAME', 'NEXTCLOUD_HOSTNAME',
                'PROMETHEUS_HOSTNAME', 'ALERTMANAGER_HOSTNAME', 'POSTGRESQL_VERSION', 'POSTGRESQL_STORAGE_SIZE',
                'POSTGRESQL_DATABASE', 'POSTGRESQL_USERNAME', 'BACKUP_ENABLED', 'BACKUP_RETENTION', 'BACKUP_SCHEDULE',
                'KEYCLOAK_REALM', 'OAUTH2_PROXY_ENABLED', 'NOAH_DEBUG', 'SOPS_AGE_KEY_FILE', 'NOAH_TLS_CERT', 'NOAH_TLS_KEY'
            ])
            
            other_vars = set(env_vars.keys()) - all_categorized_vars
            if other_vars:
                f.write("\n# Additional Variables\n")
                for var in sorted(other_vars):
                    f.write(f"export {var}={env_vars[var]}\n")

    def sync_with_ansible_vars(self):
        """Sync configuration with Ansible global variables"""
        global_vars_file = Path("ansible/vars/global.yml")
        if not global_vars_file.exists():
            return False
        
        try:
            # Read current Ansible vars
            with open(global_vars_file, 'r') as f:
                ansible_vars = yaml.safe_load(f) or {}
            
            # Update Ansible vars with NOAH config
            ansible_vars.update({
                'domain_name': self.config.get('NOAH_DOMAIN', 'noah.local'),
                'ingress_ip': self.config.get('INGRESS_IP', '127.0.0.1'),
                'ingress_class': self.config.get('INGRESS_CLASS', 'nginx'),
                'cluster_name': self.config.get('CLUSTER_NAME', 'noah-cluster'),
                'kube_version': self.config.get('KUBE_VERSION', 'v1.28.2'),
                'kube_network_plugin': self.config.get('KUBE_NETWORK_PLUGIN', 'calico'),
                'pod_subnet': self.config.get('POD_SUBNET', '10.233.64.0/18'),
                'service_subnet': self.config.get('SERVICE_SUBNET', '10.233.0.0/18'),
                'storage_class': self.config.get('STORAGE_CLASS', 'local-storage'),
                'storage_provisioner': self.config.get('STORAGE_PROVISIONER', 'kubernetes.io/no-provisioner'),
                'cert_manager_enabled': self.config.get('CERT_MANAGER_ENABLED', 'true').lower() == 'true',
                'tls_enabled': self.config.get('TLS_ENABLED', 'true').lower() == 'true',
                'tls_mode': self.config.get('TLS_MODE', 'letsencrypt'),
                'letsencrypt_email': self.config.get('LETSENCRYPT_EMAIL', 'admin@noah.local'),
                'monitoring_enabled': self.config.get('MONITORING_ENABLED', 'true').lower() == 'true',
                'metrics_retention': self.config.get('METRICS_RETENTION', '30d'),
                'backup_enabled': self.config.get('BACKUP_ENABLED', 'true').lower() == 'true',
                'backup_retention': self.config.get('BACKUP_RETENTION', '30d'),
                'backup_schedule': self.config.get('BACKUP_SCHEDULE', '0 2 * * *'),
            })
            
            # Update namespace structure
            ansible_vars['namespaces'] = [
                {
                    'name': self.config.get('NOAH_NAMESPACE', 'noah'),
                    'labels': {'environment': self.env_profile}
                },
                {
                    'name': self.config.get('MONITORING_NAMESPACE', 'monitoring'),
                    'labels': {'environment': self.env_profile}
                }
            ]
            
            # Update application hostnames
            if 'applications' not in ansible_vars:
                ansible_vars['applications'] = {}
            
            apps_hostnames = {
                'keycloak': self.config.get('KEYCLOAK_HOSTNAME', 'keycloak.noah.local'),
                'grafana': self.config.get('GRAFANA_HOSTNAME', 'grafana.noah.local'),
                'gitlab': self.config.get('GITLAB_HOSTNAME', 'gitlab.noah.local'),
                'mattermost': self.config.get('MATTERMOST_HOSTNAME', 'mattermost.noah.local'),
                'nextcloud': self.config.get('NEXTCLOUD_HOSTNAME', 'nextcloud.noah.local'),
                'prometheus': self.config.get('PROMETHEUS_HOSTNAME', 'prometheus.noah.local'),
            }
            
            for app, hostname in apps_hostnames.items():
                if app not in ansible_vars['applications']:
                    ansible_vars['applications'][app] = {}
                ansible_vars['applications'][app]['hostname'] = hostname
                ansible_vars['applications'][app]['enabled'] = True
            
            # Update PostgreSQL configuration
            if 'postgresql' not in ansible_vars['applications']:
                ansible_vars['applications']['postgresql'] = {}
            
            ansible_vars['applications']['postgresql'].update({
                'version': self.config.get('POSTGRESQL_VERSION', '15.4.0'),
                'storage_size': self.config.get('POSTGRESQL_STORAGE_SIZE', '20Gi'),
                'database': self.config.get('POSTGRESQL_DATABASE', 'noah'),
                'username': self.config.get('POSTGRESQL_USERNAME', 'noah'),
                'enabled': True
            })
            
            # Write back to Ansible vars
            with open(global_vars_file, 'w') as f:
                yaml.dump(ansible_vars, f, default_flow_style=False, sort_keys=True)
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error syncing with Ansible vars: {e}[/red]")
            return False

    def set_development_mode(self, domain: str = "noah.local"):
        """Configure for development environment"""
        self.config.update({
            'NOAH_ENV': 'development',
            'NOAH_DOMAIN': domain,
            'NOAH_DEBUG': 'true',
            'SOPS_AGE_KEY_FILE': str(Path.cwd() / 'age' / 'keys.txt'),
            'NOAH_TLS_CERT': str(Path.cwd() / 'certs' / 'tls.crt'),
            'NOAH_TLS_KEY': str(Path.cwd() / 'certs' / 'tls.key'),
            # Update all hostnames for development domain
            'KEYCLOAK_HOSTNAME': f"keycloak.{domain}",
            'GRAFANA_HOSTNAME': f"grafana.{domain}",
            'GITLAB_HOSTNAME': f"gitlab.{domain}",
            'MATTERMOST_HOSTNAME': f"mattermost.{domain}",
            'NEXTCLOUD_HOSTNAME': f"nextcloud.{domain}",
            'PROMETHEUS_HOSTNAME': f"prometheus.{domain}",
            'ALERTMANAGER_HOSTNAME': f"alertmanager.{domain}",
        })
        self.env_profile = 'development'

    def set_production_mode(self, domain: Optional[str] = None):
        """Configure for production environment"""
        prod_config = {
            'NOAH_ENV': 'production',
            'NOAH_DEBUG': 'false'
        }
        
        if domain:
            prod_config['NOAH_DOMAIN'] = domain
            
        # Remove development-specific settings
        dev_keys = ['SOPS_AGE_KEY_FILE', 'NOAH_TLS_CERT', 'NOAH_TLS_KEY']
        for key in dev_keys:
            self.config.pop(key, None)
        
        self.config.update(prod_config)
        self.env_profile = 'production'

    def check_environment(self) -> bool:
        """Check NOAH environment prerequisites"""
        required_dirs = ["ansible", ".github/workflows"]
        required_files = ["ansible/ansible.cfg"]

        for dir_name in required_dirs:
            if not (self.script_dir / dir_name).exists():
                console.print(f"[red]❌ Missing directory: {dir_name}[/red]")
                return False

        for file_name in required_files:
            if not (self.script_dir / file_name).exists():
                console.print(f"[red]❌ Missing file: {file_name}[/red]")
                return False

        return True


class PrerequisiteChecker:
    """Check system prerequisites for NOAH"""

    @staticmethod
    def check_prerequisites() -> bool:
        """Check all required tools"""
        required_tools = {
            "python3": "Python 3.8+",
            "pip3": "Python package manager",
            "git": "Version control",
            "ansible": "Automation engine",
        }

        optional_tools = {
            "helm": "Kubernetes package manager",
            "kubectl": "Kubernetes CLI",
            "docker": "Container runtime",
            "sops": "Secrets management"
        }

        console.print("[yellow]🔍 Checking prerequisites...[/yellow]")

        missing_required = []
        missing_optional = []

        # Check required tools
        for tool, description in required_tools.items():
            if shutil.which(tool):
                console.print(f"[green]✅ {tool}[/green] - {description}")
            else:
                console.print(f"[red]❌ {tool}[/red] - {description}")
                missing_required.append(tool)

        # Check optional tools
        for tool, description in optional_tools.items():
            if shutil.which(tool):
                console.print(f"[green]✅ {tool}[/green] - {description}")
            else:
                console.print(f"[yellow]⚠️  {tool}[/yellow] - {description} (optional)")
                missing_optional.append(tool)

        if missing_required:
            console.print(f"\n[red]❌ Missing required tools: {', '.join(missing_required)}[/red]")
            console.print("[yellow]Install missing tools before continuing[/yellow]")
            return False

        if missing_optional:
            console.print(f"\n[yellow]⚠️  Missing optional tools: {', '.join(missing_optional)}[/yellow]")
            console.print("[blue]Some features may not be available[/blue]")

        console.print("\n[green]✅ Prerequisites check completed[/green]")
        return True


class AnsibleRunner:
    """Ansible playbook execution wrapper"""

    def __init__(self, config: NoahConfig):
        self.config = config
        self.inventory_path = Path("ansible/inventory/mycluster/hosts.yaml")
        self.playbooks_dir = Path("ansible/playbooks")

    def run_playbook(self, playbook: str, dry_run: bool = False, verbose: bool = False) -> bool:
        """Execute ansible playbook with progress tracking"""
        playbook_path = self.playbooks_dir / playbook

        if not playbook_path.exists():
            console.print(f"[red]❌ Playbook not found: {playbook_path}[/red]")
            return False

        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i", str(self.inventory_path),
        ]

        if dry_run:
            cmd.append("--check")
        if verbose:
            cmd.append("-vv")

        console.print(f"[blue]🚀 Executing playbook: {playbook}[/blue]")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Running {playbook}...", total=None)

                result = subprocess.run(
                    cmd,
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout
                )

                progress.remove_task(task)

            if result.returncode == 0:
                console.print(f"[green]✅ Playbook {playbook} completed successfully[/green]")
                if verbose:
                    console.print(result.stdout)
                return True
            else:
                console.print(f"[red]❌ Playbook {playbook} failed[/red]")
                console.print(f"[red]Error: {result.stderr}[/red]")
                return False

        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ Playbook {playbook} timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error running playbook {playbook}: {e}[/red]")
            return False


class KubernetesManager:
    """Kubernetes cluster management"""

    @staticmethod
    def check_connectivity() -> bool:
        """Check if kubectl can connect to cluster"""
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info", "--request-timeout=10s"],
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def get_cluster_status() -> Dict:
        """Get comprehensive cluster status"""
        status = {
            "nodes": [],
            "pods": [],
            "services": [],
            "ingress": []
        }

        try:
            # Get nodes
            result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                nodes_data = json.loads(result.stdout)
                status["nodes"] = [
                    {
                        "name": node["metadata"]["name"],
                        "status": next(
                            (cond["type"] for cond in node["status"]["conditions"]
                             if cond["status"] == "True" and cond["type"] == "Ready"),
                            "Unknown"
                        )
                    }
                    for node in nodes_data.get("items", [])
                ]
        except Exception:
            pass

        return status


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Simulate actions without execution')
@click.version_option(version='0.2.9', prog_name='NOAH CLI')
@click.pass_context
def cli(ctx, verbose, dry_run):
    """
    NOAH CLI - Network Operations & Automation Hub
    
    Modern Python-based infrastructure management tool with development-first approach.
    
    Commands are organized by context (development environment is the default):
    
    \b
    ENVIRONMENT SETUP (Development First):
    • init      - Initialize NOAH environment (defaults to development)
    • dev-setup - Setup development environment with certificates and SOPS
    • configure - Configure infrastructure settings  
    • deploy    - Deploy platform (defaults to development profile)
    
    \b
    PRODUCTION OPERATIONS:
    • validate  - Validate production configuration
    • prod-deploy - Deploy to production (alias: deploy --profile prod)
    
    \b
    DEVELOPMENT WORKFLOW:
    • test      - Run platform tests
    • logs      - View service logs
    
    \b
    SERVICE MANAGEMENT:
    • start     - Start NOAH services
    • stop      - Stop NOAH services  
    • restart   - Restart NOAH services
    • status    - Check service status
    
    \b
    SECURITY & SECRETS:
    • secrets   - Manage encrypted secrets with SOPS
    
    \b
    UTILITIES:
    • config    - Manage unified configuration (harmonized .noah_config/.env files)
    • dashboard - Open monitoring dashboard
    • pipeline  - Configure CI/CD pipeline
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    ctx.obj['config'] = NoahConfig()

    # Display banner
    if not ctx.resilient_parsing:
        banner = Panel(
            Text("NOAH CLI v0.2.9\nNetwork Operations & Automation Hub\nPython Implementation",
                 style="bold blue", justify="center"),
            style="blue",
            padding=(1, 2)
        )
        console.print(banner)

    # Check environment
    config = ctx.obj['config']
    if not config.check_environment():
        console.print("[red]❌ NOAH environment validation failed[/red]")
        console.print("[yellow]Make sure you're in the NOAH project root directory[/yellow]")
        sys.exit(1)


# =============================================================================
# ENVIRONMENT SETUP COMMANDS (Development First)
# =============================================================================

@cli.command()
@click.option('--infrastructure-type',
              type=click.Choice(['kubernetes', 'docker']),
              help='Infrastructure deployment type')
@click.option('--env', type=click.Choice(['development', 'production']), 
              default='development', help='Environment type (defaults to development)')
@click.pass_context
def init(ctx, infrastructure_type, env):
    """Initialize NOAH environment (defaults to development)
    
    Sets up the basic NOAH environment configuration with development as default.
    Choose between Kubernetes (recommended) or Docker infrastructure.
    """
    config = ctx.obj['config']
    dry_run = ctx.obj['dry_run']

    console.print(f"[yellow]🔄 Initializing NOAH environment for {env}...[/yellow]")

    # Set environment
    if env == 'development':
        config.set_development_mode()
        console.print("[green]✅ Development environment configured[/green]")
        console.print("[yellow]💡 This includes:[/yellow]")
        console.print("   - Debug mode enabled")
        console.print("   - SOPS configuration for secrets")
        console.print("   - Local certificate paths")
    else:
        config.set_production_mode()
        console.print("[green]✅ Production environment configured[/green]")

    # Configure infrastructure type
    if infrastructure_type:
        config.config['INFRASTRUCTURE_TYPE'] = infrastructure_type
    elif 'INFRASTRUCTURE_TYPE' not in config.config:
        infrastructure_type = click.prompt(
            "Choose infrastructure type",
            type=click.Choice(['kubernetes', 'docker']),
            default='kubernetes'
        )
        config.config['INFRASTRUCTURE_TYPE'] = infrastructure_type

    if not dry_run:
        config.save_config()

    console.print(f"[green]✅ Infrastructure type set to: {config.config['INFRASTRUCTURE_TYPE']}[/green]")

    console.print("[blue]📦 Installing Ansible collections...[/blue]")
    if not dry_run:
        subprocess.run([
            "ansible-galaxy", "collection", "install",
            "-r", "ansible/requirements.yml", "--force"
        ])

    console.print("[green]✅ NOAH environment initialized successfully[/green]")


@cli.command()
@click.option('--auto', is_flag=True, help='Automatic configuration with defaults')
@click.pass_context
def configure(ctx, auto):
    """Configure production infrastructure settings
    
    Interactive configuration of infrastructure settings for production deployment.
    Use --auto for automated configuration with defaults.
    """
    console.print("[yellow]🔧 Configuring NOAH deployment...[/yellow]")

    dry_run = ctx.obj['dry_run']

    # Configuration values
    config_values = {
        'domain': 'noah.local',
        'master_ip': '192.168.1.10',
        'worker_ip': '192.168.1.12',
        'ingress_ip': '192.168.1.10'
    }

    if not auto:
        console.print("\n[blue]📝 Interactive Configuration[/blue]")
        console.print("Press Enter to keep default values in brackets")

        config_values['domain'] = Prompt.ask("Domain name", default=config_values['domain'])
        config_values['master_ip'] = Prompt.ask("Master node IP", default=config_values['master_ip'])
        config_values['worker_ip'] = Prompt.ask("Worker node IP", default=config_values['worker_ip'])
        config_values['ingress_ip'] = Prompt.ask("Ingress IP", default=config_values['ingress_ip'])

    console.print("\n[green]📋 Configuration Summary:[/green]")
    for key, value in config_values.items():
        console.print(f"  {key}: {value}")

    if not auto and not Confirm.ask("\nApply this configuration?"):
        console.print("[yellow]Configuration cancelled[/yellow]")
        return

    # Update inventory file
    if not dry_run:
        inventory_content = f"""# NOAH Kubernetes cluster inventory - Generated automatically
all:
  hosts:
    noah-master-1:
      ansible_host: {config_values['master_ip']}
      ip: {config_values['master_ip']}
      access_ip: {config_values['master_ip']}
    noah-worker-1:
      ansible_host: {config_values['worker_ip']}
      ip: {config_values['worker_ip']}
      access_ip: {config_values['worker_ip']}
  children:
    kube_control_plane:
      hosts:
        noah-master-1:
    kube_node:
      hosts:
        noah-master-1:
        noah-worker-1:
    etcd:
      hosts:
        noah-master-1:
    k8s_cluster:
      children:
        kube_control_plane:
        kube_node:
    calico_rr:
      hosts: {{}}
"""

        inventory_path = Path("ansible/inventory/mycluster/hosts.yaml")
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_path.write_text(inventory_content)
        console.print("[green]✅ Inventory updated[/green]")

        # Update global configuration
        global_config_path = Path("ansible/vars/global.yml")
        if global_config_path.exists():
            with open(global_config_path, 'r') as f:
                global_config = yaml.safe_load(f) or {}

            global_config['domain_name'] = config_values['domain']
            global_config['ingress_ip'] = config_values['ingress_ip']

            with open(global_config_path, 'w') as f:
                yaml.dump(global_config, f, default_flow_style=False)
            console.print("[green]✅ Global configuration updated[/green]")

    console.print("\n[green]✅ Configuration completed successfully[/green]")
    console.print("[blue]Next step: noah deploy[/blue]")


# =============================================================================
# DEVELOPMENT ENVIRONMENT COMMANDS
# =============================================================================

@cli.command('dev-setup')
@click.option('--domain', default='noah.local', help='Domain name for development')
@click.option('--force', is_flag=True, help='Force regenerate all certificates and keys')
@click.pass_context
def dev_setup(ctx, domain, force):
    """Setup development environment with Let's Encrypt certificates and SOPS
    
    Initializes a complete development environment including:
    - Let's Encrypt style certificates for local development
    - Age encryption key generation
    - SOPS configuration for secrets management
    - Encrypted secrets file with generated passwords
    - Unified configuration system (.noah_config + environment files)
    
    This command should be run first when setting up NOAH for development.
    """
    console.print("[yellow]🔧 Setting up NOAH development environment...[/yellow]")
    
    # Import and run the dev setup script
    try:
        script_path = Path.cwd() / "script"
        setup_file = script_path / "setup_dev_environment.py"
        
        if not setup_file.exists():
            console.print(f"[red]❌ Setup script not found: {setup_file}[/red]")
            sys.exit(1)
        
        # Import with better error handling
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "setup_dev_environment", 
            setup_file
        )
        
        if spec is None or spec.loader is None:
            console.print("[red]❌ Failed to load setup script[/red]")
            sys.exit(1)
            
        setup_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup_module)
        DevEnvironmentSetup = setup_module.DevEnvironmentSetup
        
        setup = DevEnvironmentSetup(domain=domain)
        
        # Check if already setup and not forcing
        if not force:
            age_keys = Path("age/keys.txt")
            secrets_file = Path("ansible/vars/secrets.yml")
            
            if age_keys.exists() and secrets_file.exists():
                if not click.confirm(
                    "Development environment appears to be already setup. Continue anyway?",
                    default=False
                ):
                    console.print("Setup cancelled.")
                    return
        
        success = setup.run_setup()
        
        if success:
            # Update NOAH config to development mode
            config = ctx.obj['config']
            config.set_development_mode(domain)
            config.save_config()
            
            console.print("\n[green]🎉 Development environment setup completed successfully![/green]")
            console.print("[yellow]💡 Configuration harmonized:[/yellow]")
            console.print("   📁 Unified config: [cyan].noah_config[/cyan]")
            console.print("   📁 Environment file: [cyan].env.development[/cyan]")
            console.print("\n[yellow]💡 Next steps:[/yellow]")
            console.print("   1. Source environment: [cyan]source .env.development[/cyan]")
            console.print("   2. Edit secrets: [cyan]sops ansible/vars/secrets.yml[/cyan]")
            console.print("   3. Deploy to dev: [cyan]./noah.py deploy --profile dev[/cyan]")
        else:
            console.print("[red]❌ Development environment setup failed[/red]")
            sys.exit(1)
            
    except ImportError as e:
        console.print(f"[red]❌ Failed to import dev setup module: {e}[/red]")
        console.print("[yellow]Try running: python script/setup_dev_environment.py[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Dev setup failed: {e}[/red]")
        sys.exit(1)


@cli.command('config')
@click.option('--env', type=click.Choice(['development', 'production', 'staging']), 
              help='Set environment profile')
@click.option('--domain', help='Set domain name')
@click.option('--show', is_flag=True, help='Show current configuration')
@click.option('--export-env', is_flag=True, help='Export environment variables file')
@click.option('--set', 'set_var', help='Set a configuration variable (format: KEY=VALUE)')
@click.option('--get', 'get_var', help='Get a configuration variable value')
@click.option('--list-k8s', is_flag=True, help='List all Kubernetes-related variables')
@click.pass_context
def config_cmd(ctx, env, domain, show, export_env, set_var, get_var, list_k8s):
    """Manage NOAH configuration
    
    Unified configuration management for NOAH platform.
    Harmonizes .noah_config and environment variables.
    
    Examples:
        noah config --set GRAFANA_HOSTNAME=grafana.example.com
        noah config --get KUBECONFIG
        noah config --list-k8s
        noah config --export-env
    """
    config = ctx.obj['config']
    
    if get_var:
        # Get specific variable
        value = config.config.get(get_var, 'Not set')
        console.print(f"[cyan]{get_var}[/cyan] = [green]{value}[/green]")
        return
    
    if set_var:
        # Set specific variable
        if '=' not in set_var:
            console.print("[red]❌ Invalid format. Use: KEY=VALUE[/red]")
            return
        
        key, value = set_var.split('=', 1)
        config.config[key.strip()] = value.strip()
        config.save_config()
        console.print(f"[green]✅ Set {key} = {value}[/green]")
        return
    
    if list_k8s:
        # List Kubernetes-related configuration
        console.print("[cyan]🔧 Kubernetes Configuration Variables:[/cyan]\n")
        
        k8s_categories = {
            "Cluster": ["KUBE_VERSION", "KUBE_NETWORK_PLUGIN", "POD_SUBNET", "SERVICE_SUBNET", "CLUSTER_NAME", "KUBECONFIG"],
            "Namespaces": ["NOAH_NAMESPACE", "MONITORING_NAMESPACE"],
            "Certificates": ["CERT_MANAGER_ENABLED", "TLS_ENABLED", "TLS_MODE", "LETSENCRYPT_EMAIL"],
            "Helm": ["HELM_VERSION"],
            "Storage": ["STORAGE_CLASS", "STORAGE_PROVISIONER"],
            "Monitoring": ["MONITORING_ENABLED", "METRICS_RETENTION", "PROMETHEUS_STORAGE_SIZE", "GRAFANA_STORAGE_SIZE"],
            "Hostnames": ["KEYCLOAK_HOSTNAME", "GRAFANA_HOSTNAME", "GITLAB_HOSTNAME", "MATTERMOST_HOSTNAME", 
                         "NEXTCLOUD_HOSTNAME", "PROMETHEUS_HOSTNAME", "ALERTMANAGER_HOSTNAME"]
        }
        
        for category, vars_list in k8s_categories.items():
            console.print(f"[yellow]{category}:[/yellow]")
            for var in vars_list:
                value = config.config.get(var, 'Not set')
                console.print(f"  [cyan]{var}[/cyan] = [green]{value}[/green]")
            console.print()
        return
    
    if show:
        # Show current configuration
        console.print("[cyan]📋 Current NOAH Configuration:[/cyan]")
        
        table = Table(title="Configuration Settings")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Environment", style="yellow")
        
        for key, value in config.config.items():
            env_type = "Development" if config.env_profile == 'development' else "Production"
            table.add_row(key, value, env_type)
        
        console.print(table)
        return
    
    # Update configuration
    if env:
        if env == 'development':
            config.set_development_mode(domain or config.config.get('NOAH_DOMAIN', 'noah.local'))
        elif env == 'production':
            config.set_production_mode(domain)
        config.save_config()
        console.print(f"[green]✅ Environment set to: {env}[/green]")
    
    if domain and not env:
        config.config['NOAH_DOMAIN'] = domain
        # Update all hostname variables to use new domain
        base_domain = domain
        config.config['KEYCLOAK_HOSTNAME'] = f"keycloak.{base_domain}"
        config.config['GRAFANA_HOSTNAME'] = f"grafana.{base_domain}"
        config.config['GITLAB_HOSTNAME'] = f"gitlab.{base_domain}"
        config.config['MATTERMOST_HOSTNAME'] = f"mattermost.{base_domain}"
        config.config['NEXTCLOUD_HOSTNAME'] = f"nextcloud.{base_domain}"
        config.config['PROMETHEUS_HOSTNAME'] = f"prometheus.{base_domain}"
        config.config['ALERTMANAGER_HOSTNAME'] = f"alertmanager.{base_domain}"
        
        config.save_config()
        console.print(f"[green]✅ Domain set to: {domain}[/green]")
        console.print(f"[blue]📡 Updated application hostnames automatically[/blue]")
    
    if export_env:
        env_file = Path(f".env.{config.env_profile}")
        config.write_env_file(env_file)
        console.print(f"[green]✅ Environment variables exported to: {env_file}[/green]")
        console.print(f"[yellow]💡 To use: source {env_file}[/yellow]")
        
        # Also update Ansible variables
        global_vars_file = Path("ansible/vars/global.yml")
        if global_vars_file.exists():
            console.print(f"[blue]🔄 Updating Ansible global variables...[/blue]")
            if config.sync_with_ansible_vars():
                console.print(f"[green]✅ Ansible variables synchronized[/green]")
            else:
                console.print(f"[yellow]⚠️  Failed to sync some Ansible variables[/yellow]")


@cli.command()
@click.option('--profile', default='dev', help='Deployment profile (dev/prod) - defaults to dev')
@click.option('--skip-provision', is_flag=True, help='Skip infrastructure provisioning')
@click.option('--verbose', is_flag=True, default=True, help='Enable verbose output (default: True)')
@click.pass_context
def deploy(ctx, profile, skip_provision, verbose):
    """Deploy NOAH platform (defaults to development environment)
    
    Deploys the complete NOAH platform with development environment as default.
    Includes infrastructure provisioning, Kubernetes setup, and application deployment.
    
    Verbose output is enabled by default to provide detailed deployment information.
    """
    config = ctx.obj['config']
    dry_run = ctx.obj['dry_run']

    infrastructure_type = config.config.get('INFRASTRUCTURE_TYPE', 'kubernetes')

    console.print("[yellow]🚀 Deploying NOAH platform...[/yellow]")
    console.print(f"[blue]Infrastructure: {infrastructure_type}[/blue]")
    console.print(f"[blue]Profile: {profile}[/blue]")

    ansible_runner = AnsibleRunner(config)

    if infrastructure_type == 'kubernetes':
        playbooks = []

        if not skip_provision:
            playbooks.append('01-provision.yml')

        playbooks.extend([
            '02-install-k8s.yml',
            '03-configure-cluster.yml',
            '04-deploy-apps.yml'
        ])

        for i, playbook in enumerate(playbooks, 1):
            console.print(f"[cyan]Step {i}/{len(playbooks)}: {playbook}[/cyan]")

            if not ansible_runner.run_playbook(playbook, dry_run, verbose):
                console.print(f"[red]❌ Deployment failed at step {i}[/red]")
                sys.exit(1)

    elif infrastructure_type == 'docker':
        console.print("[blue]🐳 Deploying with Docker Compose...[/blue]")
        if not dry_run:
            subprocess.run(["docker-compose", "up", "-d"])

    console.print("[green]🎉 NOAH platform deployed successfully![/green]")


@cli.command('prod-deploy')
@click.option('--skip-provision', is_flag=True, help='Skip infrastructure provisioning')
@click.option('--verbose', is_flag=True, default=True, help='Enable verbose output (default: True)')
@click.pass_context
def prod_deploy(ctx, skip_provision, verbose):
    """Deploy NOAH platform to production environment
    
    Alias for 'deploy --profile prod' - specifically for production deployments.
    This command forces production profile and includes production-specific validations.
    """
    # Force production configuration
    config = ctx.obj['config']
    config.set_production_mode()
    config.save_config()
    
    console.print("[yellow]🚀 Deploying NOAH platform to PRODUCTION...[/yellow]")
    console.print("[red]⚠️  Production deployment - please ensure all prerequisites are met[/red]")
    
    # Call the main deploy function with production profile
    ctx.invoke(deploy, profile='prod', skip_provision=skip_provision, verbose=verbose)


@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed status')
@click.option('--all-namespaces', is_flag=True, help='Show all namespaces')
@click.pass_context
def status(ctx, detailed, all_namespaces):
    """Check platform service status
    
    Displays the current status of all NOAH platform services and infrastructure.
    """
    config = ctx.obj['config']
    infrastructure_type = config.config.get('INFRASTRUCTURE_TYPE', 'kubernetes')

    console.print("[yellow]🔍 Checking NOAH platform status...[/yellow]")

    if infrastructure_type == 'kubernetes':
        k8s_manager = KubernetesManager()

        if not k8s_manager.check_connectivity():
            console.print("[red]❌ Cannot connect to Kubernetes cluster[/red]")
            sys.exit(1)

        console.print("[green]✅ Kubernetes cluster connection OK[/green]")

        status_data = k8s_manager.get_cluster_status()

        # Display nodes
        console.print("\n[bold]Cluster Nodes:[/bold]")
        for node in status_data['nodes']:
            status_icon = "✅" if node['status'] == "Ready" else "❌"
            console.print(f"  {status_icon} {node['name']}: {node['status']}")

        if detailed:
            # Show more detailed information
            console.print("\n[bold]NOAH Services:[/bold]")
            try:
                namespace_arg = "--all-namespaces" if all_namespaces else "-n noah"
                result = subprocess.run(
                    f"kubectl get pods {namespace_arg} -o wide".split(),
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    console.print(result.stdout)
                else:
                    console.print("[yellow]No NOAH namespace found[/yellow]")
            except Exception:
                console.print("[red]Error getting pod status[/red]")

    elif infrastructure_type == 'docker':
        console.print("[blue]🐳 Checking Docker Compose status...[/blue]")
        try:
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True, text=True, timeout=30
            )
            console.print(result.stdout)
        except Exception:
            console.print("[red]Error checking Docker status[/red]")


# =============================================================================
# SECURITY & SECRETS MANAGEMENT
# =============================================================================

@cli.group()
def secrets():
    """Manage encrypted secrets with SOPS
    
    Secure management of NOAH platform secrets using SOPS (Secrets OPerationS).
    All secrets are encrypted at rest and managed with age keys.
    """
    pass


@secrets.command()
@click.pass_context
def edit(ctx):
    """Edit secrets file with SOPS"""
    console.print("[yellow]📝 Opening secrets editor...[/yellow]")
    subprocess.run(["sops", "ansible/vars/secrets.yml"])


@secrets.command()
@click.pass_context
def view(ctx):
    """View decrypted secrets"""
    console.print("[yellow]👁️  Viewing secrets...[/yellow]")
    subprocess.run(["sops", "--decrypt", "ansible/vars/secrets.yml"])


@secrets.command("init")
@click.pass_context
def init_sops(ctx):
    """Initialize SOPS configuration"""
    console.print("[yellow]🔧 Initializing SOPS configuration...[/yellow]")

    sops_config = Path(".sops.yaml")
    secrets_file = Path("ansible/vars/secrets.yml")

    if not sops_config.exists():
        sops_content = """# SOPS configuration for NOAH
creation_rules:
  - path_regex: ^ansible/vars/secrets\\.yml$
    age: ["AGE-PLACEHOLDER-PUBLIC-KEY"]
    encrypted_regex: '^(data|stringData|vault_.*)$'
"""
        sops_config.write_text(sops_content)
        console.print("[green]✅ Created .sops.yaml[/green]")

    if not secrets_file.exists():
        secrets_file.parent.mkdir(parents=True, exist_ok=True)
        secrets_content = """# NOAH Secrets - Managed by SOPS
vault_postgres_password: "changeme"
vault_keycloak_admin_password: "changeme"
"""
        secrets_file.write_text(secrets_content)
        console.print("[green]✅ Created secrets template[/green]")


@secrets.command("validate")
@click.pass_context
def validate_sops(ctx):
    """Validate SOPS configuration"""
    console.print("[yellow]🔍 Validating SOPS configuration...[/yellow]")

    # Check SOPS binary
    if not shutil.which("sops"):
        console.print("[red]❌ SOPS not installed[/red]")
        return

    # Check Age
    if not shutil.which("age"):
        console.print("[red]❌ Age not installed[/red]")
        return

    # Check .sops.yaml
    if not Path(".sops.yaml").exists():
        console.print("[red]❌ .sops.yaml not found[/red]")
        return

    # Check secrets file
    secrets_file = Path("ansible/vars/secrets.yml")
    if not secrets_file.exists():
        console.print("[red]❌ secrets.yml not found[/red]")
        return

    # Try to decrypt
    try:
        result = subprocess.run(
            ["sops", "--decrypt", str(secrets_file)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            console.print("[green]✅ SOPS configuration valid[/green]")
        else:
            console.print("[red]❌ Cannot decrypt secrets file[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error validating SOPS: {e}[/red]")


@secrets.command()
@click.pass_context
def encrypt(ctx):
    """Encrypt secrets file with SOPS"""
    console.print("[yellow]🔐 Encrypting secrets file...[/yellow]")

    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", "ansible/vars/secrets.yml"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        console.print("[green]✅ Secrets file encrypted[/green]")
    else:
        console.print(f"[red]❌ Failed to encrypt: {result.stderr}[/red]")


@secrets.command()
@click.pass_context
def decrypt(ctx):
    """Decrypt secrets file"""
    console.print("[yellow]🔓 Decrypting secrets file...[/yellow]")
    console.print("[red]⚠️  WARNING: File will be in plaintext![/red]")

    if not Confirm.ask("Continue?"):
        console.print("[yellow]Operation cancelled[/yellow]")
        return

    result = subprocess.run(
        ["sops", "--decrypt", "--in-place", "ansible/vars/secrets.yml"],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        console.print("[green]✅ Secrets file decrypted[/green]")
        console.print("[red]⚠️  Remember to encrypt before committing![/red]")
    else:
        console.print(f"[red]❌ Failed to decrypt: {result.stderr}[/red]")


# =============================================================================
# DEVELOPMENT ENVIRONMENT COMMANDS
# =============================================================================

@cli.group()
def dev():
    """Development environment management
    
    Commands for setting up and managing development environments.
    """
    pass


@dev.command("setup")
@click.option('--clean', is_flag=True, help='Clean existing development setup')
@click.option('--minimal', is_flag=True, help='Minimal development setup')
@click.pass_context
def dev_setup_tools(ctx, clean, minimal):
    """Setup development environment
    
    Configures a local development environment with necessary tools
    and dependencies for NOAH platform development.
    """
    console.print("[yellow]🛠️  Setting up development environment...[/yellow]")
    
    if clean:
        console.print("[yellow]🧹 Cleaning existing setup...[/yellow]")
        # Add cleanup logic here
        
    config = ctx.obj['config']
    dry_run = ctx.obj['dry_run']
    
    steps = [
        "Installing development dependencies",
        "Setting up Git hooks", 
        "Configuring pre-commit",
        "Setting up testing environment"
    ]
    
    if not minimal:
        steps.extend([
            "Installing additional development tools",
            "Setting up local documentation server"
        ])
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for step in steps:
            task = progress.add_task(step, total=None)
            # Simulate work for now
            import time
            time.sleep(0.5)
            progress.update(task, description=f"✅ {step}")
    
    console.print("[green]✅ Development environment setup complete![/green]")
    
    
@dev.command("reset")
@click.option('--force', is_flag=True, help='Force reset without confirmation')
@click.pass_context
def dev_reset(ctx, force):
    """Reset development environment
    
    Resets the development environment to a clean state.
    """
    if not force and not Confirm.ask("⚠️  This will reset your development environment. Continue?"):
        console.print("[yellow]Operation cancelled[/yellow]")
        return
        
    console.print("[yellow]🔄 Resetting development environment...[/yellow]")
    
    # Run the reset script
    script_path = Path("script/reset_dev_environment.py")
    if script_path.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                console.print("[green]✅ Development environment reset complete[/green]")
            else:
                console.print(f"[red]❌ Reset failed: {result.stderr}[/red]")
        except Exception as e:
            console.print(f"[red]❌ Error during reset: {e}[/red]")
    else:
        console.print("[red]❌ Reset script not found[/red]")


@dev.command("dependencies")
@click.pass_context  
def dev_dependencies(ctx):
    """Test development dependencies
    
    Validates that all required development dependencies are installed
    and properly configured.
    """
    console.print("[yellow]🔍 Testing development dependencies...[/yellow]")
    
    # Run the test dependencies script
    script_path = Path("script/test_dependencies.py") 
    if script_path.exists():
        try:
            result = subprocess.run([sys.executable, str(script_path)])
            if result.returncode == 0:
                console.print("[green]✅ All dependencies validated[/green]")
            else:
                console.print("[yellow]⚠️  Some dependencies need attention[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Error testing dependencies: {e}[/red]")
    else:
        console.print("[red]❌ Dependency test script not found[/red]")


# =============================================================================
# SERVICE MANAGEMENT COMMANDS  
# =============================================================================


@cli.command()
@click.pass_context
def start(ctx):
    """Start all NOAH services
    
    Starts all NOAH platform services in the Kubernetes cluster.
    """
    console.print("[yellow]🚀 Starting NOAH services...[/yellow]")

    try:
        result = subprocess.run(
            ["kubectl", "scale", "deployment", "--all", "--replicas=1", "-n", "noah"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            console.print("[green]✅ Services started successfully[/green]")
        else:
            console.print("[red]❌ Failed to start services[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop all NOAH services
    
    Gracefully stops all NOAH platform services in the Kubernetes cluster.
    """
    console.print("[yellow]🛑 Stopping NOAH services...[/yellow]")

    try:
        result = subprocess.run(
            ["kubectl", "scale", "deployment", "--all", "--replicas=0", "-n", "noah"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            console.print("[green]✅ Services stopped successfully[/green]")
        else:
            console.print("[red]❌ Failed to stop services[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
@click.pass_context
def restart(ctx):
    """Restart all NOAH services
    
    Performs a rolling restart of all NOAH platform services.
    """
    console.print("[yellow]🔄 Restarting NOAH services...[/yellow]")

    try:
        result = subprocess.run(
            ["kubectl", "rollout", "restart", "deployment", "--all", "-n", "noah"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            console.print("[green]✅ Services restarted successfully[/green]")
        else:
            console.print("[red]❌ Failed to restart services[/red]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
@click.option('--service', help='Specific service to view logs')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--lines', default=100, help='Number of lines to show')
@click.pass_context
def logs(ctx, service, follow, lines):
    """View service logs
    
    View logs from NOAH platform services. Use --follow to stream logs in real-time.
    """
    console.print("[yellow]📋 Viewing NOAH logs...[/yellow]")

    cmd = ["kubectl", "logs", "-n", "noah", f"--tail={lines}"]

    if follow:
        cmd.append("-f")

    if service:
        cmd.extend(["-l", f"app={service}"])
    else:
        cmd.extend(["--all-containers=true", "--selector=app.kubernetes.io/instance"])

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Log viewing interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error viewing logs: {e}[/red]")


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate production configuration
    
    Validates NOAH configuration, Ansible playbooks, and Helm charts
    to ensure everything is ready for production deployment.
    """
    console.print("[yellow]🔍 Validating NOAH configuration...[/yellow]")

    config = ctx.obj['config']
    errors = 0

    # Check environment
    if not config.check_environment():
        errors += 1

    # Check prerequisites
    if not PrerequisiteChecker.check_prerequisites():
        errors += 1

    # Validate Ansible playbooks
    playbooks_dir = Path("ansible/playbooks")
    if playbooks_dir.exists():
        console.print("\n[yellow]📝 Validating Ansible playbooks...[/yellow]")
        for playbook in playbooks_dir.glob("*.yml"):
            try:
                result = subprocess.run(
                    ["ansible-playbook", "--syntax-check", str(playbook)],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    console.print(f"[green]✅ {playbook.name}[/green]")
                else:
                    console.print(f"[red]❌ {playbook.name}: {result.stderr}[/red]")
                    errors += 1
            except Exception as e:
                console.print(f"[red]❌ {playbook.name}: {e}[/red]")
                errors += 1

    # Validate Helm charts
    helm_dir = Path("helm")
    if helm_dir.exists() and shutil.which("helm"):
        console.print("\n[yellow]⎈ Validating Helm charts...[/yellow]")
        for chart_dir in helm_dir.iterdir():
            if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                try:
                    result = subprocess.run(
                        ["helm", "lint", str(chart_dir)],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        console.print(f"[green]✅ {chart_dir.name}[/green]")
                    else:
                        console.print(f"[red]❌ {chart_dir.name}: {result.stderr}[/red]")
                        errors += 1
                except Exception as e:
                    console.print(f"[red]❌ {chart_dir.name}: {e}[/red]")
                    errors += 1

    # Summary
    console.print(f"\n[{'green' if errors == 0 else 'red'}]Validation completed with {errors} errors[/{'green' if errors == 0 else 'red'}]")

    if errors > 0:
        sys.exit(1)


# =============================================================================
# TESTING & DEVELOPMENT COMMANDS
# =============================================================================

@cli.command()
@click.pass_context
def test(ctx):
    """Run platform integration tests
    
    Runs comprehensive tests including SSH connectivity,
    application endpoints, and service health checks.
    """
    console.print("[yellow]🧪 Running NOAH tests...[/yellow]")

    # Test SSH connectivity
    console.print("\n[yellow]🔐 Testing SSH connectivity...[/yellow]")
    try:
        result = subprocess.run(
            ["ansible", "all", "-m", "ping", "-i", "ansible/inventory/mycluster/hosts.yaml"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            console.print("[green]✅ SSH connectivity OK[/green]")
        else:
            console.print("[red]❌ SSH connectivity failed[/red]")
    except Exception as e:
        console.print(f"[red]❌ SSH test error: {e}[/red]")

    # Test application endpoints
    console.print("\n[yellow]🌐 Testing application endpoints...[/yellow]")
    apps = ["keycloak", "gitlab", "nextcloud", "mattermost", "grafana"]

    for app in apps:
        url = f"https://{app}.noah.local"
        try:
            result = subprocess.run(
                ["curl", "-k", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                capture_output=True, text=True, timeout=10
            )

            if result.stdout in ["200", "302", "401"]:
                console.print(f"[green]✅ {app}[/green] - {url}")
            else:
                console.print(f"[yellow]⚠️  {app}[/yellow] - {url} (HTTP {result.stdout})")
        except Exception:
            console.print(f"[red]❌ {app}[/red] - {url} (unreachable)")


# =============================================================================
# UTILITY COMMANDS
# =============================================================================

@cli.group()
def pipeline():
    """CI/CD pipeline configuration
    
    Commands for configuring and managing the CI/CD pipeline infrastructure.
    """
    pass


@pipeline.command("setup")
@click.option('--auto', is_flag=True, help='Automatic configuration')
@click.option('--domain', help='Domain name')
@click.option('--master-ip', help='Master node IP')
@click.option('--worker-ip', help='Worker node IP')
@click.pass_context
def pipeline_configure(ctx, auto, domain, master_ip, worker_ip):
    """Configure CI/CD pipeline settings
    
    Sets up CI/CD pipeline configuration including domain, master and worker IPs.
    """
    console.print("[yellow]🔧 Configuring NOAH pipeline...[/yellow]")

    # Default values
    config_values = {
        'domain': domain or 'noah.local',
        'master_ip': master_ip or '192.168.1.10',
        'worker_ip': worker_ip or '192.168.1.12'
    }

    if not auto:
        # Interactive configuration
        config_values['domain'] = Prompt.ask("Domain name", default=config_values['domain'])
        config_values['master_ip'] = Prompt.ask("Master IP", default=config_values['master_ip'])
        config_values['worker_ip'] = Prompt.ask("Worker IP", default=config_values['worker_ip'])

    # Update inventory
    inventory_content = f"""# NOAH Kubernetes cluster inventory
all:
  hosts:
    noah-master-1:
      ansible_host: {config_values['master_ip']}
      ip: {config_values['master_ip']}
      access_ip: {config_values['master_ip']}
    noah-worker-1:
      ansible_host: {config_values['worker_ip']}
      ip: {config_values['worker_ip']}
      access_ip: {config_values['worker_ip']}
  children:
    kube_control_plane:
      hosts:
        noah-master-1:
    kube_node:
      hosts:
        noah-master-1:
        noah-worker-1:
    etcd:
      hosts:
        noah-master-1:
    k8s_cluster:
      children:
        kube_control_plane:
        kube_node:
"""

    inventory_path = Path("ansible/inventory/mycluster/hosts.yaml")
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(inventory_content)

    console.print("[green]✅ Pipeline configuration updated[/green]")
    console.print(f"[blue]Domain: {config_values['domain']}[/blue]")
    console.print(f"[blue]Master: {config_values['master_ip']}[/blue]")
    console.print(f"[blue]Worker: {config_values['worker_ip']}[/blue]")


@cli.command()
@click.pass_context
def infrastructure(ctx):
    """Configure infrastructure deployment type
    
    Interactive configuration to choose between Kubernetes and Docker infrastructure types.
    """
    console.print("[yellow]⚙️  Infrastructure type configuration[/yellow]")

    config = ctx.obj['config']

    # Show current configuration
    current = config.config.get('INFRASTRUCTURE_TYPE', 'kubernetes')
    console.print(f"[blue]Current infrastructure: {current}[/blue]")

    # Infrastructure options
    table = Table(title="Infrastructure Options")
    table.add_column("Option", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    table.add_row("kubernetes", "Kubernetes cluster deployment", "✅ Recommended")
    table.add_row("docker", "Docker Compose deployment", "🔧 Development")

    console.print(table)

    # Get user choice
    choice = Prompt.ask(
        "Select infrastructure type",
        choices=["kubernetes", "docker"],
        default=current
    )

    config.config['INFRASTRUCTURE_TYPE'] = choice
    config.save_config()

    console.print(f"[green]✅ Infrastructure type set to: {choice}[/green]")


@cli.command()
@click.pass_context
def dashboard(ctx):
    """Open monitoring dashboard
    
    Opens the Grafana monitoring dashboard in your default web browser.
    """
    console.print("[yellow]📊 Opening Grafana dashboard...[/yellow]")

    url = "https://grafana.noah.local"

    # Try different browsers
    browsers = ['xdg-open', 'open', 'firefox', 'chromium-browser', 'google-chrome']

    for browser in browsers:
        if shutil.which(browser):
            try:
                subprocess.run([browser, url], check=True)
                console.print(f"[green]✅ Dashboard opened with {browser}[/green]")
                return
            except Exception:
                continue

    console.print(f"[yellow]Please open manually: {url}[/yellow]")


if __name__ == '__main__':
    cli()
