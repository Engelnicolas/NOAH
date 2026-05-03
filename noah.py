#!/usr/bin/env python3
"""
NOAH - Network Operations & Automation Hub
Main CLI for deploying and managing Kubernetes-based information systems
"""

import sys
import os

# Re-exec under the venv interpreter as soon as possible so all subsequent
# imports see the venv's packages.  Skip when:
#   - the venv doesn't exist yet (first run / setup initialize)
#   - we're already running inside it (avoid infinite loop)
def _bootstrap_venv():
    from pathlib import Path
    venv_python = Path(__file__).parent / ".venv" / "bin" / "python3"
    if not venv_python.exists():
        return
    if os.path.realpath(sys.executable) == os.path.realpath(str(venv_python)):
        return
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)

_bootstrap_venv()

import click  # type: ignore
import json
import yaml  # type: ignore
import subprocess
import shutil
import time
from pathlib import Path
from Scripts.utils.paths import get_noah_paths, NOAH_PATHS
from Scripts.security.secure_env_loader import SecureEnvLoader

# Load environment variables from encrypted configuration (best-effort on startup;
# missing file is expected on first run — ensure_security_initialized will create it)
_CONFIG_ENC = Path("Config/config.enc.yaml")
secure_loader = SecureEnvLoader()
if _CONFIG_ENC.exists():
    secure_loader.load_secure_env(_CONFIG_ENC)

# Import CLI utilities
from Scripts.cluster_destroy.kubectl_utils import cleanup_kubectl_cache, display_kubectl_status, verify_kubectl_disconnected

## Paths now provided by Scripts.utils.paths (get_noah_paths, NOAH_PATHS)

from Scripts.core_helm.cluster_manager import ClusterManager
from Scripts.security.security_manager import NoahSecurityManager as SecretManager
from Scripts.utils.helm_deployer import HelmDeployer
from Scripts.utils.ansible_runner import AnsibleRunner
from Scripts.utils.config_loader import ConfigLoader
from Scripts.env_init.environment_initializer import initialize_noah_environment, check_command_exists, update_sops_version
from Scripts.env_init.doctor_utils import print_status, diagnose_noah_environment
from Scripts.utils import (
    config_show_command,
    config_domains_command, 
    config_helm_values_command,
    config_override_command
)
from Scripts.security import ensure_security_initialized, get_security_config
from Scripts.security.rotate_cli import register_rotate_command  # type: ignore
from Scripts.core_helm import (
    cilium,
    get_ansible_vars_for_service,
    get_authentik_credentials,
    regenerate_authentik_password,
    get_helm_values_for_service
)
from Scripts.cluster_create.status_utils import show_cluster_status
from Scripts.cluster_create.cluster_validation_utils import check_existing_cluster
from Scripts.cluster_create.cluster_create_utils import create_cluster
from Scripts.cluster_create.bootstrap_utils import (
    run_bootstrap as cluster_bootstrap,
    run_add_nodes as cluster_add_nodes,
    show_cluster_status_v2,
)
from Scripts.cluster_create.flux_utils import (
    cmd_sync as flux_cmd_sync,
    cmd_status as flux_cmd_status,
    cmd_logs as flux_cmd_logs,
)
from Scripts.cluster_destroy.cluster_destroy_utils import destroy_cluster_command

VERSION = "0.0.8"
DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', '')
def check_repository_root():
    """Check if the current directory is the root of the NOAH repository"""
    current_dir = Path.cwd()
    
    # Check for key repository files/directories that should exist in the root
    required_items = [
        'Scripts',
        'Helm', 
        'Ansible',
        'noah.py'
    ]
    
    missing_items = []
    for item in required_items:
        if not (current_dir / item).exists():
            missing_items.append(item)
    
    if missing_items:
        click.echo(f"❌ Error: NOAH must be run from the repository root directory!", err=True)
        click.echo(f"", err=True)
        click.echo(f"Current directory: {current_dir}", err=True)
        click.echo(f"Missing required items: {', '.join(missing_items)}", err=True)
        click.echo(f"", err=True)
        click.echo(f"💡 Please change to the NOAH repository root directory and try again:", err=True)
        click.echo(f"   cd /path/to/noah-repository", err=True)
        click.echo(f"   python noah.py <command>", err=True)
        sys.exit(1)

@click.group()
@click.version_option(version=VERSION, prog_name="NOAH")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """NOAH - Network Operations & Automation Hub
    
    Automates deployment of open source information systems on Kubernetes
    """
    # Check if running from repository root before initializing
    check_repository_root()
    
    ctx.ensure_object(dict)
    ctx.obj['config'] = ConfigLoader()
    ctx.obj['cluster'] = ClusterManager(ctx.obj['config'])
    ctx.obj['secrets'] = SecretManager(ctx.obj['config'])
    ctx.obj['helm'] = HelmDeployer(ctx.obj['config'])
    ctx.obj['ansible'] = AnsibleRunner(ctx.obj['config'])

@cli.group()  # type: ignore
@click.pass_context
def cluster(ctx):
    """Manage Kubernetes cluster lifecycle"""
    pass

@cluster.command()
@click.option('--name', default='noah-cluster', help='Cluster name')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for TLS certificates')
@click.pass_context
def create(ctx, name, domain):
    """Create a new Kubernetes cluster"""
    create_cluster(ctx, name, domain, ensure_security_initialized, get_security_config, DEFAULT_DOMAIN)

@cluster.command()
@click.option('--name', default='noah-cluster', help='Cluster name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.option('--keep-secrets', is_flag=True, help='Keep secrets and certificates after destruction')
@click.pass_context
def destroy(ctx, name, force, keep_secrets):
    """Destroy Kubernetes cluster and clean up resources"""
    destroy_cluster_command(ctx, name, force, keep_secrets, get_security_config)


# ──────────────────────────────────────────────────────────────────────
# v0.0.9 — GitOps bootstrap commands
# ──────────────────────────────────────────────────────────────────────

@cluster.command()
@click.option('--node', default=None, help='Single node IP (default single-node mode)')
@click.option('--nodes', default=None, help='Comma-separated IPs for HA mode (>=3, odd)')
@click.option('--ha', is_flag=True, default=False, help='Enable 3-node embedded-etcd HA mode')
@click.option('--domain', required=True, help='Primary domain for the cluster')
@click.option('--flux-repo', required=True, help='GitOps repository URL or owner/repo')
@click.option('--flux-branch', default='main', show_default=True, help='GitOps branch')
@click.option('--flux-path', default='clusters/production', show_default=True,
              help='Path inside the GitOps repo Flux will reconcile')
@click.option('--github-token', envvar='GITHUB_TOKEN',
              help='GitHub PAT with repo:write (or env GITHUB_TOKEN)')
@click.option('--ssh-user', default='ubuntu', show_default=True, help='SSH user on target nodes')
@click.option('--ssh-key', default=None, help='SSH private key path (optional)')
@click.option('--age-key-file', default='Age/keys.txt', show_default=True,
              help='Path to the Age private key file')
@click.option('--k3s-version', default=None,
              help='Override K3s version (default: pinned in the role)')
@click.option('--force-reset', is_flag=True, default=False,
              help='Allow bootstrap on top of an existing K3s install (DESTRUCTIVE)')
@click.pass_context
def bootstrap(ctx, node, nodes, ha, domain, flux_repo, flux_branch, flux_path,
              github_token, ssh_user, ssh_key, age_key_file,
              k3s_version, force_reset):
    """Provision K3s + bootstrap FluxCD against a GitOps repo (v0.0.9)."""
    rc = cluster_bootstrap(
        node=node,
        nodes=nodes,
        ha=ha,
        domain=domain,
        flux_repo=flux_repo,
        github_token=github_token,
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        age_key_file=Path(age_key_file),
        k3s_version=k3s_version,
        flux_branch=flux_branch,
        flux_path=flux_path,
        force_reset=force_reset,
        ansible_dir=Path('Ansible').resolve(),
    )
    sys.exit(rc)


@cluster.command('add-nodes')
@click.option('--primary', required=True, help='IP of the existing primary node')
@click.option('--nodes', required=True, help='Comma-separated IPs of NEW joiner nodes')
@click.option('--ssh-user', default='ubuntu', show_default=True)
@click.option('--ssh-key', default=None, help='SSH private key path (optional)')
@click.option('--k3s-version', default=None)
@click.pass_context
def add_nodes(ctx, primary, nodes, ssh_user, ssh_key, k3s_version):
    """Scale a single-node cluster to HA by joining new server nodes."""
    new_nodes = [n.strip() for n in nodes.split(',') if n.strip()]
    rc = cluster_add_nodes(
        primary=primary,
        new_nodes=new_nodes,
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ansible_dir=Path('Ansible').resolve(),
        k3s_version=k3s_version,
    )
    sys.exit(rc)


@cluster.command('status')
@click.pass_context
def cluster_status(ctx):
    """Show node, etcd quorum, and FluxCD reconciliation state."""
    sys.exit(show_cluster_status_v2())


@cli.group()  # type: ignore
@click.pass_context
def flux(ctx):
    """Interact with the FluxCD GitOps controller (v0.0.9+)."""
    pass


@flux.command('sync')
@click.pass_context
def flux_sync(ctx):
    """Force immediate reconciliation of every Kustomization + HelmRelease."""
    sys.exit(flux_cmd_sync())


@flux.command('status')
@click.pass_context
def flux_status_cmd(ctx):
    """Show the state of every Flux resource in the cluster."""
    sys.exit(flux_cmd_status())


@flux.command('logs')
@click.option('-f', '--follow', is_flag=True, default=False, help='Stream new log lines')
@click.option('--tail', type=int, default=100, show_default=True, help='Lines per controller')
@click.pass_context
def flux_logs(ctx, follow, tail):
    """Aggregate logs from the Flux controllers."""
    sys.exit(flux_cmd_logs(follow=follow, tail=tail))


@cli.group()  # type: ignore
@click.pass_context
def certificates(ctx):
    """Manage TLS certificates"""
    pass

@certificates.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for TLS certificates')
@click.option('--force', is_flag=True, help='Force regeneration of existing certificates')
@click.pass_context
def generate_certs(ctx, domain, force):
    """Generate self-signed TLS certificates"""
    certs_dir = Path("Certificates")
    
    if certs_dir.exists() and any(certs_dir.glob("*.crt")) and not force:
        click.echo(f"[VERBOSE] TLS certificates already exist. Use --force to regenerate.")
        return
    
    click.echo(f"[VERBOSE] Generating TLS certificates for domain: {domain}")
    ctx.obj['secrets'].generate_tls_certificates(domain)
    click.echo(f"✓ TLS certificates generated for {domain}")

@certificates.command()
@click.pass_context
def list(ctx):
    """List existing TLS certificates"""
    click.echo("[VERBOSE] Listing TLS certificates...")
    ctx.obj['secrets'].list_certificates()

@certificates.command()
@click.option('--namespace', default='cert-manager', help='Kubernetes namespace')
@click.pass_context
def deploy_manager(ctx, namespace):
    """Deploy cert-manager for automatic certificate management"""
    click.echo(f"[VERBOSE] Deploying cert-manager to namespace {namespace}")
    ctx.obj['helm'].deploy_chart('cert-manager', namespace)

@cli.group()  # type: ignore
@click.pass_context
def password(ctx):
    """Manage Authentik admin passwords"""
    pass

@password.command()
@click.pass_context
def new(ctx):
    """Generate a new Authentik admin password"""
    click.echo("🔄 Regenerating Authentik admin password...")
    
    result, error = regenerate_authentik_password()
    if result:
        click.echo("✅ Password regenerated successfully!")
        click.echo("")
        click.echo("📋 Password Change Summary:")
        click.echo("=" * 50)
        click.echo(f"Old password: {result['old_password']}")
        click.echo(f"New password: {result['new_password']}")
        click.echo(f"Updated file: {result['updated_file']}")
        click.echo("=" * 50)
        click.echo("")
        click.echo("💡 The new password will be active after next deployment:")
        click.echo("   python noah.py deploy authentik")
        click.echo("   # or")
        click.echo("   python noah.py deploy core")
        click.echo("")
        click.echo("🔍 To view current credentials after deployment:")
        click.echo("   python noah.py password show")
    else:
        click.echo(f"❌ Failed to regenerate password: {error}", err=True)
        sys.exit(1)

@password.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for Authentik (used for URL display)')
@click.pass_context
def show_password(ctx, domain):
    """Show current Authentik admin credentials"""
    click.echo("🔍 Current Authentik admin credentials:")
    click.echo("=" * 50)
    credentials, error = get_authentik_credentials(domain=domain)
    if credentials:
        click.echo(f"📍 URL (HTTP):   {credentials['http_url']}")
        click.echo(f"📍 URL (HTTPS):  {credentials['https_url']}")
        if credentials.get('external_ip'):
            click.echo(f"🌐 External IP:  {credentials['external_ip']}")
        click.echo(f"📶 Resolution:   {credentials.get('resolution_status','unknown')}")
        click.echo(f"👤 Username:     {credentials['admin_username']}")
        click.echo(f"📧 Email:        {credentials['admin_email']}")
        click.echo(f"🔑 Password:     {credentials['admin_password']}")
        click.echo("")
        click.echo("💡 You can log in using either the username or email address")
        if credentials.get('resolution_status') in ('pending','lookup_error'):
            click.echo("💡 External IP not ready yet; ensure LoadBalancer/Ingress and DNS are configured.")
    else:
        click.echo(f"⚠️  Could not retrieve credentials: {error}")
        click.echo("💡 Try running a deployment first: python noah.py deploy authentik")
    click.echo("=" * 50)

@cli.group()  # type: ignore
@click.pass_context
def deploy(ctx):
    """[DEPRECATED in v0.0.9] Imperative service deployment.

    Application services are now reconciled by FluxCD from the GitOps
    repository (see docs/GITOPS_GUIDE.md). These commands are kept for
    one release to ease migration from v0.0.8 and will be removed in
    v0.1.0. Use:

        noah cluster bootstrap   # provision K3s + bootstrap FluxCD
        noah flux sync           # force reconciliation
        noah flux status         # inspect reconciliation state

    Edit flux-repo/ and `git push` to change a service.
    """
    click.echo(
        "⚠️  `noah deploy ...` is deprecated since v0.0.9. "
        "FluxCD reconciles services from your GitOps repo — see "
        "docs/MIGRATION_GUIDE.md for the new workflow.",
        err=True,
    )

@deploy.command()
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.option('--regenerate-password', is_flag=True, help='Generate new Authentik admin password')
@click.pass_context
def authentik(ctx, namespace, domain, regenerate_password):
    """Deploy Authentik SSO (individual component)"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)
    
    # Regenerate Authentik password if requested
    if regenerate_password:
        click.echo("🔄 Regenerating Authentik admin password...")
        result, error = regenerate_authentik_password()
        if result:
            click.echo(f"✅ Password updated successfully!")
            click.echo(f"   Old password: {result['old_password']}")
            click.echo(f"   New password: {result['new_password']}")
        else:
            click.echo(f"❌ Failed to regenerate password: {error}", err=True)
            sys.exit(1)
    
    click.echo(f"[VERBOSE] Deploying Authentik SSO...")
    click.echo(f"[VERBOSE] Namespace: {namespace}, Domain: {domain}")
    click.echo(f"💡 For complete stack deployment, use: python noah.py deploy core")
    
    # Generate secrets for Authentik before deployment
    click.echo(f"[VERBOSE] Generating secrets for Authentik...")
    ctx.obj['secrets'].generate_service_secrets('authentik')
    
    # Get Ansible variables with security configuration
    ansible_vars = get_ansible_vars_for_service('authentik', namespace, domain)
    
    # Deploy Authentik using Ansible playbook
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-authentik.yml")
    ctx.obj['ansible'].run_playbook('deploy-authentik.yml', ansible_vars)
    
    click.echo(f"✅ Authentik deployed to namespace {namespace}")
    click.echo(f"[VERBOSE] Access SSO at: https://auth.{domain}")
    
    # Display Authentik credentials
    click.echo("\n" + "="*50)
    click.echo("🔐 AUTHENTIK ADMIN ACCESS")
    click.echo("="*50)
    
    credentials, error = get_authentik_credentials(domain=domain)
    if credentials:
        click.echo(f"📍 URL (HTTP):  {credentials['http_url']}")
        click.echo(f"📍 URL (HTTPS): {credentials['https_url']}")
        if credentials.get('external_ip'):
            click.echo(f"🌐 External IP: {credentials['external_ip']}")
        click.echo(f"📶 Resolution:  {credentials.get('resolution_status','unknown')}")
        click.echo(f"👤 Username:    {credentials['admin_username']}")
        click.echo(f"📧 Email:       {credentials['admin_email']}")
        click.echo(f"🔑 Password:    {credentials['admin_password']}")
        click.echo("")
        click.echo("💡 You can log in using either the username or email address")
    else:
        click.echo(f"⚠️  Could not retrieve credentials: {error}")
    click.echo("="*50)

@deploy.command(name='cilium')
@click.option('--namespace', default='kube-system', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.pass_context
def cilium_cmd(ctx, namespace, domain):
    """Deploy Cilium CNI with SSO integration (individual component)"""
    cilium(ctx, namespace, domain)

@deploy.command()
@click.option('--namespace', default='kube-system', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.pass_context
def headlamp(ctx, namespace, domain):
    """Deploy Headlamp Kubernetes Dashboard with Authentik SSO (individual component)"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)

    click.echo(f"[VERBOSE] Deploying Headlamp Kubernetes Dashboard...")
    click.echo(f"[VERBOSE] Namespace: {namespace}, Domain: {domain}")
    click.echo(f"💡 For complete stack deployment, use: python noah.py deploy core")

    # Generate secrets for Headlamp before deployment
    click.echo(f"[VERBOSE] Generating secrets for Headlamp...")
    ctx.obj['secrets'].generate_service_secrets('headlamp')

    # Get Ansible variables with security configuration
    ansible_vars = get_ansible_vars_for_service('headlamp', namespace, domain)

    # Deploy Headlamp using Ansible playbook
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-headlamp.yml")
    ctx.obj['ansible'].run_playbook('deploy-headlamp.yml', ansible_vars)

    click.echo(f"✅ Headlamp deployed to namespace {namespace}")
    click.echo(f"[VERBOSE] Access Kubernetes Dashboard at: https://headlamp.{domain}")
    click.echo(f"[VERBOSE] SSO authentication via Authentik: https://auth.{domain}")

@deploy.command(name='nginx-ingress')
@click.option('--namespace', default='ingress-nginx', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain (for DNS hints)')
@click.option('--lb-pool-cidr', envvar='NOAH_LB_IP_POOL_CIDR', default='',
              help='Cilium LB IPAM pool CIDR for bare-metal (e.g. 192.168.1.200/29). '
                   'Leave empty on AWS without secondary ENI IPs.')
@click.pass_context
def nginx_ingress(ctx, namespace, domain, lb_pool_cidr):
    """Deploy nginx-ingress Controller (DaemonSet + hostNetwork, AWS bare-metal compatible)"""
    click.echo("[VERBOSE] Deploying nginx-ingress controller...")
    click.echo(f"[VERBOSE] Namespace: {namespace}, Domain: {domain}")
    if lb_pool_cidr:
        click.echo(f"[VERBOSE] Cilium LB IPAM pool: {lb_pool_cidr}")
    else:
        click.echo("[VERBOSE] No LB pool configured — hostNetwork is primary access path")

    ansible_vars = {
        'nginx_ingress_namespace': namespace,
        'domain_name': domain,
        'nginx_ingress_helm_timeout': '300s'
    }

    env_override = {}
    if lb_pool_cidr:
        env_override['NOAH_LB_IP_POOL_CIDR'] = lb_pool_cidr

    # Temporarily set env var so AnsibleRunner passes it through
    if env_override:
        for k, v in env_override.items():
            os.environ[k] = v

    click.echo("[VERBOSE] Running Ansible playbook: deploy-nginx-ingress.yml")
    ctx.obj['ansible'].run_playbook('deploy-nginx-ingress.yml', ansible_vars)

    click.echo(f"✅ nginx-ingress deployed to namespace {namespace}")
    click.echo("✓ IngressClass 'nginx' registered as cluster default")
    click.echo("✓ Ports 80/443 bound on host via hostNetwork")
    if lb_pool_cidr:
        click.echo(f"✓ Cilium LB IPAM pool created: {lb_pool_cidr}")
    else:
        click.echo("")
        click.echo("💡 To enable Cilium LB IPAM on bare-metal:")
        click.echo(f"   python noah.py deploy nginx-ingress --lb-pool-cidr 192.168.x.y/z")
        click.echo("   or: export NOAH_LB_IP_POOL_CIDR=192.168.x.y/z")


@deploy.command()
@click.option('--namespace', default='kube-system', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for DNS management')
@click.option('--provider', default='cloudflare', type=click.Choice(['cloudflare']), help='DNS provider')
@click.option('--api-token', envvar='CLOUDFLARE_API_TOKEN', help='Cloudflare API token (or set CLOUDFLARE_API_TOKEN env var)')
@click.option('--policy', default='upsert-only', type=click.Choice(['sync', 'upsert-only']), help='DNS record management policy')
@click.pass_context
def dns(ctx, namespace, domain, provider, api_token, policy):
    """Deploy external-dns for automatic DNS management"""

    click.echo(f"[VERBOSE] Deploying external-dns for automatic DNS management...")
    click.echo(f"[VERBOSE] Provider: {provider}, Domain: {domain}, Policy: {policy}")

    # Validate configuration
    config_loader = ctx.obj['config']

    if provider == 'cloudflare':
        if not api_token:
            click.echo("❌ Cloudflare API token is required!", err=True)
            click.echo("", err=True)
            click.echo("Please provide the API token using one of these methods:", err=True)
            click.echo("  1. Command line: --api-token YOUR_TOKEN", err=True)
            click.echo("  2. Environment variable: export CLOUDFLARE_API_TOKEN='YOUR_TOKEN'", err=True)
            click.echo("", err=True)
            click.echo("To create a Cloudflare API token:", err=True)
            click.echo("  1. Log in to https://dash.cloudflare.com", err=True)
            click.echo("  2. Go to My Profile > API Tokens", err=True)
            click.echo("  3. Click 'Create Token'", err=True)
            click.echo("  4. Use 'Edit zone DNS' template or create custom token with:", err=True)
            click.echo("     - Zone > DNS > Edit", err=True)
            click.echo("     - Zone > Zone > Read", err=True)
            click.echo("  5. Select your domain zone", err=True)
            click.echo("  6. Copy the generated token", err=True)
            sys.exit(1)

        click.echo(f"[VERBOSE] Using Cloudflare API token: {api_token[:8]}...{api_token[-4:]}")

    # Get Ansible variables
    ansible_vars = {
        'external_dns_namespace': namespace,
        'domain_name': domain,
        'dns_provider': provider,
        'dns_policy': policy,
        'cloudflare_api_token': api_token,
        'cluster_name': config_loader.get_cluster_name(domain=domain)
    }

    # Deploy external-dns using Ansible playbook
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-external-dns.yml")
    ctx.obj['ansible'].run_playbook('deploy-external-dns.yml', ansible_vars)

    click.echo(f"✅ External-DNS deployed to namespace {namespace}")
    click.echo("")
    click.echo("External-DNS will now automatically manage DNS records for:")
    click.echo(f"  - Ingress resources with annotation: external-dns.alpha.kubernetes.io/hostname")
    click.echo(f"  - LoadBalancer services with annotation: external-dns.alpha.kubernetes.io/hostname")
    click.echo("")
    click.echo(f"Domain filter: {domain}")
    click.echo(f"Policy: {policy}")
    click.echo("")
    click.echo("Monitor logs:")
    click.echo(f"  kubectl logs -n {namespace} -l app.kubernetes.io/name=external-dns -f")
    click.echo("")
    click.echo("Expected DNS records (will be created automatically):")
    click.echo(f"  - auth.{domain} → Authentik SSO")
    click.echo(f"  - hubble.{domain} → Cilium Hubble UI")
    click.echo(f"  - headlamp.{domain} → Headlamp Dashboard")

@deploy.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for services')
@click.option('--cluster-name', default=None, help='Cluster name (default: derived from domain)')
@click.option('--config-file', type=click.Path(exists=False), help='Export configuration to file')
@click.option('--regenerate-password', is_flag=True, help='Generate new Authentik admin password')
@click.option('--validation-mode', type=click.Choice(['development','production']), default='production', show_default=True, help='Validation strictness for deployment playbook')
@click.pass_context
def core(ctx, domain, cluster_name, config_file, regenerate_password, validation_mode):
    """Deploy complete stack using optimized Ansible playbook (Cilium → Authentik → Headlamp)"""
    # Ensure security is initialized before any deployment
    ensure_security_initialized(ctx)

    # Derive cluster name from domain when not explicitly provided.
    # This gives each deployment a unique external-dns txtOwnerId automatically.
    if not cluster_name:
        cluster_name = ctx.obj['config'].get_cluster_name(domain=domain)

    # Regenerate Authentik password if requested
    if regenerate_password:
        click.echo("🔄 Regenerating Authentik admin password...")
        result, error = regenerate_authentik_password()
        if result:
            click.echo(f"✅ Password updated successfully!")
            click.echo(f"   Old password: {result['old_password']}")
            click.echo(f"   New password: {result['new_password']}")
            click.echo(f"   Updated file: {result['updated_file']}")
        else:
            click.echo(f"❌ Failed to regenerate password: {error}", err=True)
            sys.exit(1)

    click.echo("[VERBOSE] Starting complete NOAH stack deployment using cluster-deploy.yml...")
    click.echo(f"[VERBOSE] Using domain: {domain}")
    click.echo(f"[VERBOSE] Using cluster name: {cluster_name}")
    click.echo(f"[VERBOSE] Deployment order: Cilium → Authentik → Headlamp")
    click.echo(f"[VERBOSE] Validation mode: {validation_mode}")

    # Ensure Authentik and Headlamp secrets exist early (mirrors individual deployments)
    click.echo(f"[VERBOSE] Ensuring canonical secrets are generated before playbook run...")
    try:
        ctx.obj['secrets'].generate_service_secrets('authentik')
        ctx.obj['secrets'].generate_service_secrets('headlamp')
        # Force persistence in case underlying store deferred save or encryption unavailable
        try:
            from Scripts.security.canonical_store import get_canonical_store  # type: ignore
            store = get_canonical_store()
            store.save()
        except Exception:
            pass
    except Exception as gen_err:
        click.echo(f"❌ Failed to generate secrets prior to deployment: {gen_err}", err=True)
        sys.exit(1)

    # If skipping Ansible (CI fast path), exit early after credential display prerequisites
    if os.environ.get('NOAH_SKIP_ANSIBLE', '').lower() in ('1','true','yes'):  # fast path for tests
        click.echo("[VERBOSE] NOAH_SKIP_ANSIBLE active - skipping Ansible playbook execution.")
        # Minimal success output to align with test expectations
        credentials, error = get_authentik_credentials(domain=domain)
        if credentials:
            click.echo("\n" + "="*60)
            click.echo("🔐 AUTHENTIK ADMIN ACCESS")
            click.echo("="*60)
            click.echo(f"📍 URL (HTTP):  {credentials['http_url']}")
            click.echo(f"📍 URL (HTTPS): {credentials['https_url']}")
            click.echo(f"👤 Username:    {credentials['admin_username']}")
            click.echo(f"📧 Email:       {credentials['admin_email']}")
            click.echo(f"🔑 Password:    {credentials['admin_password']}")
            click.echo("="*60)
        else:
            click.echo(f"⚠️  Could not retrieve credentials: {error}")
        return
    
    # Export configuration if requested
    if config_file:
        click.echo(f"[VERBOSE] Exporting configuration to {config_file}")
        full_config = {
            'cluster_name': cluster_name,
            'domain_name': domain,
            'security': get_security_config(domain),
            'deployment_method': 'cluster-deploy.yml',
            'services': {
                'authentik': {
                    'helm_values': get_helm_values_for_service('authentik', 'identity', domain),
                    'ansible_vars': get_ansible_vars_for_service('authentik', 'identity', domain)
                },
                'cilium': {
                    'helm_values': get_helm_values_for_service('cilium', 'kube-system', domain),
                    'ansible_vars': get_ansible_vars_for_service('cilium', 'kube-system', domain)
                }
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(full_config, f, default_flow_style=False)
        click.echo(f"[VERBOSE] Configuration exported to {config_file}")
    
    # Use the optimized cluster-deploy.yml playbook
    click.echo("Deploying complete NOAH stack using optimized playbook...")
    
    # Prepare variables for cluster-deploy.yml
    ansible_vars = {
        'cluster_name': cluster_name,
        'domain_name': domain,
        'validation_mode': validation_mode
    }
    
    click.echo(f"[VERBOSE] Running optimized deployment playbook: cluster-deploy.yml")
    click.echo(f"[VERBOSE] This will deploy in optimal order with comprehensive validation")
    # Production mode preflight: verify cluster connectivity (lightweight)
    if validation_mode == 'production':
        try:
            import subprocess
            preflight = subprocess.run(['kubectl','cluster-info'], capture_output=True, text=True)
            if preflight.returncode != 0:
                click.echo("❌ kubectl cluster-info failed; cluster not reachable. Aborting production deployment.", err=True)
                click.echo(preflight.stderr.strip(), err=True)
                sys.exit(1)
            else:
                click.echo("[VERBOSE] kubectl cluster-info succeeded – proceeding with production deployment")
        except FileNotFoundError:
            click.echo("❌ kubectl not found in PATH. Install kubectl or switch to --validation-mode development.", err=True)
            sys.exit(1)
    
    try:
        play_success = ctx.obj['ansible'].run_playbook('cluster-deploy.yml', ansible_vars)
        if not play_success:
            raise RuntimeError("Ansible playbook cluster-deploy.yml reported failure (non-zero exit code)")
        click.echo("🎉 NOAH standalone IAM deployment successful!")
        click.echo(f"[VERBOSE] All components deployed and validated")
        
        # Get and display Authentik credentials
        click.echo("\n" + "="*60)
        click.echo("🔐 AUTHENTIK ADMIN ACCESS")
        click.echo("="*60)
        
        credentials, error = get_authentik_credentials(domain=domain)
        if credentials:
            click_echo_http = credentials['http_url']
            click_echo_https = credentials['https_url']
            click.echo(f"📍 URL (HTTP):  {click_echo_http}")
            click.echo(f"📍 URL (HTTPS): {click_echo_https}")
            if credentials.get('external_ip'):
                click.echo(f"🌐 External IP: {credentials['external_ip']}")
            click.echo(f"📶 Resolution:  {credentials.get('resolution_status','unknown')}")
            click.echo(f"👤 Username:    {credentials['admin_username']}")
            click.echo(f"📧 Email:       {credentials['admin_email']}")
            click.echo(f"🔑 Password:    {credentials['admin_password']}")
            click.echo("")
            click.echo("💡 You can log in using either the username or email address")
        else:
            click.echo(f"⚠️  Could not retrieve credentials from canonical store: {error}")
            click.echo("💡 Ensure playbook created Kubernetes secret 'authentik-secret' and canonical-secrets.yaml contains authentik.admin_password")
            click.echo("💡 You can inspect secret: kubectl get secret -n identity authentik-secret -o yaml")
        
        click.echo("="*60)
        click.echo(f"[VERBOSE] Access points:")
        click.echo(f"  - Authentik IAM: https://auth.{domain}")
        click.echo(f"  - Headlamp Dashboard: https://headlamp.{domain}")
        click.echo(f"  - Hubble UI: https://hubble.{domain}")
        
        # Run post-deployment validation
        click.echo("[VERBOSE] Running post-deployment validation...")
        click.echo("💡 Run 'python noah.py test sso' to validate IAM integration")
        click.echo("💡 Run 'python noah.py status --all' to check overall status")
        
    except Exception as e:
        click.echo(f"❌ Deployment failed: {str(e)}", err=True)
        click.echo("[VERBOSE] For troubleshooting:")
        click.echo("  - Check cluster connectivity: kubectl cluster-info")
        click.echo("  - Check pod status: kubectl get pods --all-namespaces")
        click.echo("  - Check events: kubectl get events --sort-by=.metadata.creationTimestamp")
        click.echo("  - Run status check: python noah.py status --all")
        sys.exit(1)

@cli.group()  # type: ignore
@click.pass_context
def setup(ctx):
    """Setup and initialize NOAH environment"""
    pass

@cli.group()  # type: ignore
@click.pass_context
def secrets(ctx):
    """Manage and validate service secrets"""
    pass

# Dynamically register rotate command (externalized) AFTER group definition
register_rotate_command(secrets)

@secrets.command()
@click.pass_context
def init(ctx):
    """Initialize Age keys and SOPS configuration"""
    click.echo("[VERBOSE] Starting secret management initialization...")
    click.echo("Initializing secret management...")
    
    # Create Age directory if it doesn't exist
    age_dir = Path("Age")
    age_dir.mkdir(exist_ok=True)
    
    click.echo("[VERBOSE] Initializing Age keys...")
    ctx.obj['secrets'].initialize_encryption()
    click.echo("[VERBOSE] SOPS configuration completed.")

@secrets.command()
@click.option('--service', required=True, help='Service name')
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.pass_context
def generate(ctx, service, namespace):
    """Generate encrypted secrets for a service"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)
    
    click.echo(f"[VERBOSE] Starting secret generation process...")
    click.echo(f"[VERBOSE] Service: {service}")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"Generating secrets for {service} in namespace {namespace}")
    ctx.obj['secrets'].generate_service_secrets(service)

## Legacy rotate command removed in favor of unified canonical rotate

@secrets.command()
@click.option('--service', required=True, help='Service to validate (authentik)')
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.option('--fix', is_flag=True, help='Automatically fix inconsistencies')
@click.pass_context
def validate(ctx, service, namespace, fix):
    """Validate service secrets consistency"""
    ensure_security_initialized(ctx)
    
    click.echo(f"🔍 Validating secrets for {service} in namespace {namespace}...")
    
    is_valid = ctx.obj['secrets'].validate_service_secrets(service, namespace)
    
    if is_valid:
        click.echo(f"✅ All secrets for {service} are consistent")
    else:
        click.echo(f"❌ Secret inconsistencies found for {service}")
        
        if fix:
            click.echo(f"🔧 Attempting to fix secret inconsistencies...")
            
            # Re-deploy with synchronized secrets
            if service == 'authentik':
                # Force regeneration with existing passwords
                ctx.obj['secrets'].generate_service_secrets(service)
                ctx.obj['helm'].deploy_chart(service, namespace)
                click.echo(f"✅ Secrets fixed and {service} deployed")
            else:
                click.echo(f"❌ Auto-fix not implemented for {service}")
        else:
            click.echo(f"💡 Run with --fix to automatically resolve inconsistencies")

@secrets.command()
@click.option('--service', required=True, help='Service to regenerate secrets for')
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.pass_context
def regenerate(ctx, service, namespace):
    """Regenerate secrets for a service (preserves existing passwords)"""
    ensure_security_initialized(ctx)
    
    click.echo(f"🔄 Regenerating secrets for {service} in namespace {namespace}...")
    ctx.obj['secrets'].generate_service_secrets(service)
    click.echo(f"✅ Secrets regenerated for {service}")

@secrets.command(name='canonical')
@click.option('--show', is_flag=True, help='Display canonical secrets (redacted by default)')
@click.option('--service', help='Filter to a specific service')
@click.option('--raw', is_flag=True, help='Show raw secret values (unsafe; do not use in shared terminals)')
@click.pass_context
def canonical_secrets(ctx, show, service, raw):
    """Interact with canonical secrets store (read-only)."""
    from Scripts.security.canonical_store import get_canonical_store  # type: ignore
    store = get_canonical_store()
    data = store.data
    if not show:
        click.echo("Canonical secrets store present.")
        click.echo(f"Encrypted: {store.encrypted}")
        click.echo(f"Services: {', '.join(sorted(data.get('services', {}).keys()))}")
        click.echo("Use --show to display entries (redacted by default).")
        return
    services = data.get('services', {})
    target = {service: services.get(service, {})} if service else services
    click.echo("Canonical Secrets (" + ('RAW' if raw else 'REDACTED') + ")")
    click.echo("Integrity: " + data.get('integrity', 'n/a'))
    for svc, kv in sorted(target.items()):
        click.echo(f"\n[{svc}]")
        for k, v in sorted(kv.items()):
            if isinstance(v, dict) and 'value' in v:
                raw_val = v.get('value') or ''
                display_val = raw_val if raw else (raw_val[:4] + '...' if raw_val else '')
                ver = v.get('version', '?')
                rotated = v.get('rotated_at', '')
                click.echo(f"  {k}: {display_val}  (v{ver} rotated:{rotated})")
            else:
                display = v if raw else (v[:4] + '...' if v else '')
                click.echo(f"  {k}: {display}")

## Rotation command moved to Scripts/security/rotate_cli.py to simplify this file

@setup.command()
@click.option('--skip-deps', is_flag=True, help='Skip external dependency checks')
@click.option('--skip-tests', is_flag=True, help='Skip validation tests')
@click.option('--skip-dns-wizard', is_flag=True, help='Skip the interactive Cloudflare DNS wizard')
@click.pass_context
def initialize(ctx, skip_deps, skip_tests, skip_dns_wizard):
    """Initialize NOAH environment with all dependencies"""
    initialize_noah_environment(ctx, skip_deps, skip_tests, print_status, skip_dns_wizard)

@setup.command()
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def reset(force):
    """Remove everything created by setup initialize (venv, Age keys, secrets store, SOPS config)."""
    targets = [
        (Path(".venv"),      "Python virtual environment"),
        (Path("Age"),        "Age encryption keys"),
        (Path("Secrets"),    "Canonical secrets store"),
        (Path(".sops.yaml"), "SOPS configuration"),
    ]

    existing = [(p, desc) for p, desc in targets if p.exists()]
    if not existing:
        click.echo("Nothing to remove — environment is already clean.")
        return

    click.echo("The following will be permanently deleted:")
    for p, desc in existing:
        click.echo(f"  {str(p):<20} ({desc})")
    click.echo("")

    if not force and not click.confirm("Proceed?", default=False):
        click.echo("Aborted.")
        return

    removed, failed = [], []
    for p, desc in existing:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed.append(str(p))
            print_status(f"Removed {p}", "SUCCESS")
        except Exception as e:
            failed.append(str(p))
            print_status(f"Failed to remove {p}: {e}", "ERROR")

    click.echo("")
    if removed:
        click.echo(f"Removed: {', '.join(removed)}")
    if failed:
        click.echo(f"Failed:  {', '.join(failed)}")
        sys.exit(1)
    else:
        click.echo("Environment reset. Run 'python3 noah.py setup initialize' to start fresh.")

@setup.command()
def update_sops():
    """Update SOPS to the latest version"""
    click.echo("🔄 SOPS Version Update")
    click.echo("=" * 25)
    click.echo("")
    
    if update_sops_version():
        click.echo("")
        print_status("SOPS update completed successfully!", "SUCCESS")
    else:
        click.echo("")
        print_status("SOPS update failed - check messages above", "ERROR")
        sys.exit(1)

@setup.command()
@click.pass_context
def doctor(ctx):
    """Diagnose NOAH environment and dependencies"""
    diagnose_noah_environment(ctx)

@cli.group()  # type: ignore
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
    from Tests.sso_tester import SSOTester
    tester = SSOTester(ctx.obj['config'])
    click.echo("[VERBOSE] Executing authentication test...")
    if tester.test_authentication():
        click.echo("✓ SSO test successful")
        click.echo("[VERBOSE] All SSO tests passed")
    else:
        click.echo("✗ SSO test failed", err=True)
        click.echo("[VERBOSE] SSO test failed - check logs for details")
        sys.exit(1)

@test.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for services')
@click.pass_context
def headlamp(ctx, domain):
    """Test Headlamp Kubernetes Dashboard deployment and SSO integration"""
    click.echo("[VERBOSE] Starting Headlamp integration test...")
    click.echo("Testing Headlamp deployment and SSO integration...")
    from Tests.test_headlamp_sso import HeadlampSSOTester
    tester = HeadlampSSOTester(domain=domain)
    click.echo("[VERBOSE] Executing Headlamp tests...")
    if tester.run_all_tests():
        click.echo("✓ Headlamp test successful")
        click.echo("[VERBOSE] All Headlamp tests passed")
    else:
        click.echo("✗ Headlamp test failed", err=True)
        click.echo("[VERBOSE] Headlamp test failed - check logs for details")
        sys.exit(1)

@cli.command()  # type: ignore
@click.pass_context
def status(ctx):
    """Show status of all deployed services"""
    show_cluster_status(ctx)

@cli.group()  # type: ignore
@click.pass_context
def config(ctx):
    """Configuration management with dynamic domain support"""
    pass

@config.command()
@click.option('--service', help='Show configuration for specific service')
@click.option('--format', type=click.Choice(['yaml', 'json', 'env']), default='yaml', help='Output format')
@click.pass_context
def show(ctx, service, format):
    """Show current configuration"""
    from Scripts.utils.config_utils import show_configuration
    show_configuration(service, format, ctx)

@config.command()
@click.argument('service')
@click.option('--output', '-o', help='Output file path')
@click.option('--custom-values', help='Custom values YAML file to merge')
@click.pass_context
def helm_values(ctx, service, output, custom_values):
    """Generate Helm values for a service with dynamic domains"""
    from Scripts.utils.config_utils import generate_helm_values
    generate_helm_values(service, output, custom_values, ctx)

@config.command()
@click.pass_context
def domains(ctx):
    """List all service domains and FQDNs"""
    from Scripts.utils.config_utils import show_domains
    show_domains(ctx)

@config.command()
@click.argument('service')
@click.option('--domain', help='Override service domain')
@click.option('--subdomain', help='Override service subdomain') 
@click.option('--namespace', help='Override service namespace')
@click.pass_context
def override(ctx, service, domain, subdomain, namespace):
    """Set service-specific configuration overrides"""
    from Scripts.utils.config_utils import override_service_configuration
    result = override_service_configuration(service, domain, subdomain, namespace, ctx)
    
    if result:
        # Show updated configuration
        click.echo(f"\nUpdated configuration for {service}:")
        click.echo(f"  FQDN: {result['fqdn']}")
        click.echo(f"  Namespace: {result['namespace']}")

if __name__ == '__main__':
    cli()  # type: ignore
