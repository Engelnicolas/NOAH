#!/usr/bin/env python3
"""
NOAH CLI - Redeploy Utilities
Comprehensive infrastructure redeploy functionality
"""

import click
import sys
import yaml
import time
from pathlib import Path

def execute_redeploy(ctx, name, domain, force, config_file, 
                    ensure_security_initialized, get_security_config, 
                    get_helm_values_for_service, get_ansible_vars_for_service):
    """Execute complete NOAH infrastructure redeploy
    
    This command combines cluster creation and service deployment into a single operation.
    It performs the following steps:
    1. Destroys existing cluster (if any)
    2. Creates new cluster with specified name and domain
    3. Validates cluster is ready
    4. Deploys complete NOAH stack (Samba4, Authentik, Cilium)
    5. Validates all services are running
    
    Equivalent to running:
    - python noah.py cluster create --name <name> --domain <domain>
    - python noah.py deploy all --domain <domain>
    
    Args:
        ctx: Click context object
        name: Cluster name
        domain: Domain for TLS certificates and services
        force: Force redeploy without confirmation
        config_file: Export configuration to file
        ensure_security_initialized: Function to ensure security is initialized
        get_security_config: Function to get security configuration
        get_helm_values_for_service: Function to get Helm values for service
        get_ansible_vars_for_service: Function to get Ansible variables for service
    """
    
    if not force:
        click.confirm(
            f'This will completely redeploy cluster "{name}" with domain "{domain}". '
            f'All existing data will be lost. Continue?', 
            abort=True
        )
    
    click.echo("🚀 NOAH Complete Infrastructure Redeploy")
    click.echo("=" * 50)
    click.echo(f"[VERBOSE] Starting complete infrastructure redeploy...")
    click.echo(f"[VERBOSE] Cluster name: {name}")
    click.echo(f"[VERBOSE] Domain: {domain}")
    click.echo(f"[VERBOSE] Force mode: {force}")
    
    # Ensure security is initialized before redeploy
    ensure_security_initialized(ctx)
    
    # Get security configuration for redeploy
    security_config = get_security_config(domain)
    
    # Export configuration if requested
    if config_file:
        click.echo(f"[VERBOSE] Exporting redeploy configuration to {config_file}")
        redeploy_config = {
            'cluster': {
                'name': name,
                'domain': domain,
                'security_config': security_config
            },
            'services': {
                'samba4': {
                    'namespace': 'identity',
                    'helm_values': get_helm_values_for_service('samba4', 'identity', domain),
                    'ansible_vars': get_ansible_vars_for_service('samba4', 'identity', domain)
                },
                'authentik': {
                    'namespace': 'identity',
                    'helm_values': get_helm_values_for_service('authentik', 'identity', domain),
                    'ansible_vars': get_ansible_vars_for_service('authentik', 'identity', domain)
                },
                'cilium': {
                    'namespace': 'kube-system',
                    'helm_values': get_helm_values_for_service('cilium', 'kube-system', domain),
                    'ansible_vars': get_ansible_vars_for_service('cilium', 'kube-system', domain)
                }
            },
            'redeploy_timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        with open(config_file, 'w') as f:
            yaml.dump(redeploy_config, f, default_flow_style=False)
        click.echo(f"[VERBOSE] Configuration exported to {config_file}")
    
    click.echo(f"Running complete infrastructure redeploy for cluster: {name}")
    click.echo(f"[VERBOSE] Using domain: {domain}")
    click.echo(f"[VERBOSE] Running Ansible playbook: cluster-redeploy.yml")
    
    # Run the comprehensive redeploy playbook
    try:
        ctx.obj['ansible'].run_playbook('cluster-redeploy.yml', {
            'cluster_name': name,
            'domain': domain,
            'security_config': security_config
        })
        
        click.echo("")
        click.echo("🎉 NOAH Infrastructure Redeploy Complete!")
        click.echo("=" * 45)
        click.echo(f"Cluster: {name}")
        click.echo(f"Domain: {domain}")
        click.echo("")
        click.echo("Services deployed:")
        click.echo("✓ Samba4 Active Directory")
        click.echo("✓ Authentik SSO")
        click.echo("✓ Cilium CNI with Hubble")
        click.echo("")
        click.echo("Access URLs:")
        click.echo(f"- Authentik SSO: https://auth.{domain}")
        click.echo(f"- Hubble UI: https://hubble.{domain}")
        click.echo("")
        click.echo("Next steps:")
        click.echo("1. Test SSO: python noah.py test sso")
        click.echo("2. Check status: python noah.py status")
        click.echo("[VERBOSE] Complete infrastructure redeploy completed successfully!")
        
    except Exception as e:
        click.echo("")
        click.echo("❌ NOAH Infrastructure Redeploy Failed!")
        click.echo("=" * 40)
        click.echo(f"Error: {str(e)}")
        click.echo("")
        click.echo("Recovery options:")
        click.echo("1. Check cluster state: kubectl get pods --all-namespaces")
        click.echo("2. Manual recovery:")
        click.echo(f"   python noah.py cluster destroy --force")
        click.echo(f"   python noah.py cluster create --name {name} --domain {domain}")
        click.echo(f"   python noah.py deploy all --domain {domain}")
        click.echo("[VERBOSE] Redeploy failed - see error messages above")
        sys.exit(1)


def create_redeploy_command(ensure_security_initialized, get_security_config, 
                          get_helm_values_for_service, get_ansible_vars_for_service,
                          DEFAULT_DOMAIN):
    """Create the redeploy Click command with injected dependencies
    
    Args:
        ensure_security_initialized: Function to ensure security is initialized
        get_security_config: Function to get security configuration
        get_helm_values_for_service: Function to get Helm values for service
        get_ansible_vars_for_service: Function to get Ansible variables for service
        DEFAULT_DOMAIN: Default domain value
        
    Returns:
        Click command function
    """
    
    @click.option('--name', default='noah-production', help='Cluster name')
    @click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for TLS certificates and services')
    @click.option('--force', is_flag=True, help='Force redeploy without confirmation')
    @click.option('--config-file', type=click.Path(exists=False), help='Export configuration to file')
    @click.pass_context
    def redeploy_command(ctx, name, domain, force, config_file):
        """Redeploy complete NOAH infrastructure (cluster + all services)"""
        execute_redeploy(
            ctx, name, domain, force, config_file,
            ensure_security_initialized, get_security_config,
            get_helm_values_for_service, get_ansible_vars_for_service
        )
    
    return redeploy_command
