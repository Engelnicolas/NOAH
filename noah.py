#!/usr/bin/env python3
"""
NOAH - Network Operations & Automation Hub
Main CLI for deploying and managing Kubernetes-based information systems
"""

import click
import sys
import os
from pathlib import Path
from Scripts.cluster_manager import ClusterManager
from Scripts.secret_manager import SecretManager
from Scripts.helm_deployer import HelmDeployer
from Scripts.ansible_runner import AnsibleRunner
from Scripts.config_loader import ConfigLoader

VERSION = "0.0.1"

@click.group()
@click.version_option(version=VERSION, prog_name="NOAH")
@click.pass_context
def cli(ctx):
    """NOAH - Network Operations & Automation Hub
    
    Automates deployment of open source information systems on Kubernetes
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = ConfigLoader()
    ctx.obj['cluster'] = ClusterManager(ctx.obj['config'])
    ctx.obj['secrets'] = SecretManager(ctx.obj['config'])
    ctx.obj['helm'] = HelmDeployer(ctx.obj['config'])
    ctx.obj['ansible'] = AnsibleRunner(ctx.obj['config'])

@cli.group()
@click.pass_context
def cluster(ctx):
    """Manage Kubernetes cluster lifecycle"""
    pass

@cluster.command()
@click.option('--name', default='noah-cluster', help='Cluster name')
@click.pass_context
def create(ctx, name):
    """Create a new Kubernetes cluster"""
    click.echo(f"[VERBOSE] Starting cluster creation process...")
    click.echo(f"[VERBOSE] Cluster name: {name}")
    
    # First ensure no existing cluster exists by running destroy playbook
    click.echo(f"[VERBOSE] Ensuring no existing cluster exists...")
    click.echo(f"[VERBOSE] Running cluster cleanup: cluster-destroy.yml")
    ctx.obj['ansible'].run_playbook('cluster-destroy.yml', {'cluster_name': name})
    click.echo(f"[VERBOSE] Cluster cleanup completed")
    
    click.echo(f"Creating cluster: {name}")
    click.echo(f"[VERBOSE] Running Ansible playbook: cluster-create.yml")
    ctx.obj['ansible'].run_playbook('cluster-create.yml', {'cluster_name': name})

@cluster.command()
@click.option('--name', default='noah-cluster', help='Cluster name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def destroy(ctx, name, force):
    """Destroy Kubernetes cluster and clean up resources"""
    if not force:
        click.confirm(f'Are you sure you want to destroy cluster {name}?', abort=True)
    click.echo(f"[VERBOSE] Starting cluster destruction process...")
    click.echo(f"[VERBOSE] Cluster name: {name}")
    click.echo(f"[VERBOSE] Force mode: {force}")
    click.echo(f"Destroying cluster: {name}")
    click.echo(f"[VERBOSE] Running Ansible playbook: cluster-destroy.yml")
    ctx.obj['ansible'].run_playbook('cluster-destroy.yml', {'cluster_name': name})

@cli.group()
@click.pass_context
def secrets(ctx):
    """Manage secrets with SOPS and Age"""
    pass

@secrets.command()
@click.pass_context
def init(ctx):
    """Initialize Age keys and SOPS configuration"""
    click.echo("[VERBOSE] Starting secret management initialization...")
    click.echo("Initializing secret management...")
    click.echo("[VERBOSE] Initializing Age keys...")
    ctx.obj['secrets'].initialize_age()
    click.echo("[VERBOSE] Configuring SOPS...")
    ctx.obj['secrets'].configure_sops()

@secrets.command()
@click.option('--service', required=True, help='Service name')
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.pass_context
def generate(ctx, service, namespace):
    """Generate encrypted secrets for a service"""
    click.echo(f"[VERBOSE] Starting secret generation process...")
    click.echo(f"[VERBOSE] Service: {service}")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"Generating secrets for {service} in namespace {namespace}")
    ctx.obj['secrets'].generate_service_secrets(service, namespace)

@secrets.command()
@click.option('--service', required=True, help='Service name')
@click.pass_context
def rotate(ctx, service):
    """Rotate passwords for a service"""
    click.echo(f"[VERBOSE] Starting password rotation process...")
    click.echo(f"[VERBOSE] Service: {service}")
    click.echo(f"Rotating passwords for {service}")
    ctx.obj['secrets'].rotate_passwords(service)

@cli.group()
@click.pass_context
def deploy(ctx):
    """Deploy services to Kubernetes"""
    pass

@deploy.command()
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.pass_context
def samba4(ctx, namespace):
    """Deploy Samba4 Active Directory"""
    click.echo(f"[VERBOSE] Starting Samba4 deployment process...")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"Deploying Samba4 to namespace {namespace}")
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-samba4.yml")
    ctx.obj['ansible'].run_playbook('deploy-samba4.yml', {'namespace': namespace})
    click.echo(f"[VERBOSE] Deploying Helm chart: samba4")
    ctx.obj['helm'].deploy_chart('samba4', namespace)

@deploy.command()
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.pass_context
def authentik(ctx, namespace):
    """Deploy Authentik for SSO"""
    click.echo(f"[VERBOSE] Starting Authentik deployment process...")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    
    # Validate Samba4 deployment before proceeding with Authentik
    click.echo(f"[VERBOSE] Validating Samba4 deployment before Authentik installation...")
    click.echo("Checking Samba4 deployment status...")
    try:
        ctx.obj['cluster'].wait_for_deployment('samba4', namespace)
        click.echo("[VERBOSE] Samba4 deployment validated successfully")
    except Exception as e:
        click.echo(f"[VERBOSE] Samba4 validation failed: {str(e)}")
        click.echo("✗ Samba4 deployment not ready. Please ensure Samba4 is deployed and running before installing Authentik.", err=True)
        sys.exit(1)
    
    click.echo(f"Deploying Authentik to namespace {namespace}")
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-authentik.yml")
    ctx.obj['ansible'].run_playbook('deploy-authentik.yml', {'namespace': namespace})
    click.echo(f"[VERBOSE] Deploying Helm chart: authentik")
    ctx.obj['helm'].deploy_chart('authentik', namespace)

@deploy.command()
@click.option('--namespace', default='kube-system', help='Kubernetes namespace')
@click.pass_context
def cilium(ctx, namespace):
    """Deploy Cilium CNI with SSO integration"""
    click.echo(f"[VERBOSE] Starting Cilium deployment process...")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"Deploying Cilium to namespace {namespace}")
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-cilium.yml")
    ctx.obj['ansible'].run_playbook('deploy-cilium.yml', {'namespace': namespace})
    click.echo(f"[VERBOSE] Deploying Helm chart: cilium")
    ctx.obj['helm'].deploy_chart('cilium', namespace)

@deploy.command()
@click.pass_context
def all(ctx):
    """Deploy complete stack (Samba4, Authentik, Cilium)"""
    click.echo("[VERBOSE] Starting complete NOAH stack deployment...")
    click.echo("Deploying complete NOAH stack...")
    
    click.echo("[VERBOSE] Step 1: Deploying Samba4...")
    ctx.invoke(samba4)
    click.echo("Waiting for Samba4 to be ready...")
    click.echo("[VERBOSE] Checking Samba4 deployment status...")
    ctx.obj['cluster'].wait_for_deployment('samba4', 'identity')
    
    click.echo("[VERBOSE] Step 2: Deploying Authentik...")
    ctx.invoke(authentik)
    click.echo("Waiting for Authentik to be ready...")
    click.echo("[VERBOSE] Checking Authentik deployment status...")
    ctx.obj['cluster'].wait_for_deployment('authentik', 'identity')
    
    click.echo("[VERBOSE] Step 3: Deploying Cilium...")
    ctx.invoke(cilium)
    click.echo("NOAH stack deployment complete!")
    click.echo("[VERBOSE] All components successfully deployed!")

@cli.group()
@click.pass_context
def test(ctx):
    """Test deployed services"""
    pass

@test.command()
@click.pass_context
def sso(ctx):
    """Test SSO functionality"""
    click.echo("[VERBOSE] Starting SSO integration test...")
    click.echo("Testing SSO integration...")
    from Scripts.sso_tester import SSOTester
    tester = SSOTester(ctx.obj['config'])
    click.echo("[VERBOSE] Executing authentication test...")
    if tester.test_authentication():
        click.echo("✓ SSO test successful")
        click.echo("[VERBOSE] All SSO tests passed")
    else:
        click.echo("✗ SSO test failed", err=True)
        click.echo("[VERBOSE] SSO test failed - check logs for details")
        sys.exit(1)

@cli.command()
@click.pass_context
def status(ctx):
    """Show status of all deployed services"""
    click.echo("[VERBOSE] Gathering system status information...")
    click.echo("NOAH System Status")
    click.echo("-" * 50)
    ctx.obj['cluster'].show_status()

if __name__ == '__main__':
    cli()
