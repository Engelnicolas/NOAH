"""
NOAH cluster creation utilities
"""

import click
from .cluster_validation_utils import check_existing_cluster


def create_cluster(ctx, name, domain, ensure_security_initialized, get_security_config, DEFAULT_DOMAIN):
    """Create a new Kubernetes cluster"""
    click.echo(f"[VERBOSE] Starting cluster creation process...")
    click.echo(f"[VERBOSE] Cluster name: {name}")
    click.echo(f"[VERBOSE] Domain: {domain}")
    
    # Ensure security is initialized before cluster creation
    ensure_security_initialized(ctx)
    
    # Get security configuration for cluster creation
    security_config = get_security_config(domain)
    
    # Check if an existing cluster exists before running destroy
    click.echo(f"[VERBOSE] Checking for existing cluster components...")
    cluster_exists = check_existing_cluster()
    
    if cluster_exists:
        click.echo(f"[VERBOSE] Existing cluster detected - running cleanup...")
        click.echo(f"[VERBOSE] Running cluster cleanup: cluster-destroy.yml")
        ctx.obj['ansible'].run_playbook('cluster-destroy.yml', {
            'cluster_name': name,
            'cleanup_secrets': True,
            'cleanup_certificates': True,
            'security_config': security_config
        })
        click.echo(f"[VERBOSE] Cluster cleanup completed")
        
        # Regenerate certificates after cleanup
        click.echo(f"[VERBOSE] Regenerating TLS certificates for new deployment...")
        ctx.obj['secrets'].generate_tls_certificates(domain)
        
        # Update security config after regeneration
        security_config = get_security_config(domain)
    else:
        click.echo(f"[VERBOSE] No existing cluster found - proceeding with creation...")
    
    click.echo(f"Creating cluster: {name}")
    click.echo(f"[VERBOSE] Running Ansible playbook: cluster-create.yml")
    ctx.obj['ansible'].run_playbook('cluster-create.yml', {
        'cluster_name': name,
        'domain': domain,
        'security_config': security_config
    })


def create_cluster_command(cluster_group, ensure_security_initialized, get_security_config, DEFAULT_DOMAIN):
    """Create the cluster create command for the CLI"""
    @cluster_group.command()
    @click.option('--name', default='noah-cluster', help='Cluster name')
    @click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for TLS certificates')
    @click.pass_context
    def create(ctx, name, domain):
        """Create a new Kubernetes cluster"""
        create_cluster(ctx, name, domain, ensure_security_initialized, get_security_config, DEFAULT_DOMAIN)
    
    return create