#!/usr/bin/env python3
"""
NOAH - Cilium CNI Deployment Module
Handles Cilium CNI deployment with SSO integration
"""

import click
from Scripts.security import get_security_config, ensure_security_initialized


def get_ansible_vars_for_service(service, namespace, domain):
    """Generate Ansible variables for a specific service with security configuration"""
    security_config = get_security_config(domain)
    
    ansible_vars = {
        'namespace': namespace,
        'domain': domain,
        'service_name': service,
        'security_config': security_config,
        'use_generated_secrets': True,
        'secrets_backend': 'sops',
        'age_key_path': security_config['secrets']['age']['key_path'],
        'sops_config_path': security_config['secrets']['sops']['config_path'],
        'tls_enabled': security_config['certificates']['enabled'],
        'ca_cert_path': security_config['certificates']['ca_cert_path'],
        'ca_key_path': security_config['certificates']['ca_key_path']
    }
    
    # Service-specific Ansible variables
    if service == 'authentik':
        ansible_vars.update({
            'create_db_secrets': True,
            'postgresql_secret_name': 'authentik-postgresql',
            'redis_secret_name': 'authentik-redis',
            'app_secret_name': 'authentik-secret'
        })
    elif service == 'cilium':
        ansible_vars.update({
            'enable_hubble': True,
            'hubble_tls_enabled': True,
            'create_hubble_certs': True,
            'hubble_cert_secret': 'hubble-server-certs'
        })
    
    return ansible_vars


def cilium(ctx, namespace, domain):
    """Deploy Cilium CNI with SSO integration (individual component)"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)
    
    click.echo(f"[VERBOSE] Deploying Cilium CNI with SSO integration...")
    click.echo(f"[VERBOSE] Namespace: {namespace}, Domain: {domain}")
    click.echo(f"💡 For complete stack deployment, use: python noah.py deploy all")
    
    # Generate secrets for Cilium before deployment
    click.echo(f"[VERBOSE] Generating secrets for Cilium...")
    ctx.obj['secrets'].generate_service_secrets('cilium')
    
    # Get Ansible variables with security configuration
    ansible_vars = get_ansible_vars_for_service('cilium', namespace, domain)
    
    # Deploy Cilium using Ansible playbook
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-cilium.yml")
    ctx.obj['ansible'].run_playbook('deploy-cilium.yml', ansible_vars)
    
    click.echo(f"✅ Cilium CNI deployed to namespace {namespace}")
    click.echo(f"[VERBOSE] Hubble UI available at: https://hubble.{domain}")
    click.echo(f"[VERBOSE] Network foundation ready for SSO services")