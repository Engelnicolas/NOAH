#!/usr/bin/env python3
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

"""
NOAH - Network Operations & Automation Hub
Main CLI for deploying and managing Kubernetes-based information systems
"""
# ruff: noqa: E402 — every module-level import below intentionally follows the
# venv re-exec in _bootstrap_venv(), so it runs under the venv interpreter.

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
import subprocess
import shutil
from pathlib import Path
from Scripts.security.secure_env_loader import SecureEnvLoader

# Load environment variables from encrypted configuration (best-effort on startup;
# missing file is expected on first run — ensure_security_initialized will create it)
_CONFIG_ENC = Path("Config/config.enc.yaml")
secure_loader = SecureEnvLoader()
if _CONFIG_ENC.exists():
    secure_loader.load_secure_env(_CONFIG_ENC)

# Import CLI utilities
from Scripts.core_helm.cluster_manager import ClusterManager
from Scripts.security.security_manager import NoahSecurityManager as SecretManager
from Scripts.utils.ansible_runner import AnsibleRunner
from Scripts.utils.config_loader import ConfigLoader
from Scripts.env_init.environment_initializer import initialize_noah_environment, update_sops_version
from Scripts.env_init.doctor_utils import print_status, diagnose_noah_environment
from Scripts.security import ensure_security_initialized, get_security_config
from Scripts.security.rotate_cli import register_rotate_command  # type: ignore
from Scripts.core_helm import (
    get_admin_credentials,
    regenerate_authentik_password,
)
from Scripts.cluster_create.status_utils import show_cluster_status
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

VERSION = "0.0.9"
DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', '')


def _print_banner() -> None:
    """Print the NOAH ASCII logo, tagline and version.

    Shown only on interactive launches (TTY) so piped/CI output stays clean.
    """
    click.echo(rf"""
   _   _   ___      _     _   _
  | \ | | / _ \    / \   | | | |
  |  \| || | | |  / _ \  | |_| |
  | |\  || |_| | / ___ \ |  _  |
  |_| \_| \___/ /_/   \_\|_| |_|

  Network Operations & Automation Hub
  v{VERSION}
""")


def check_repository_root():
    """Check if the current directory is the root of the NOAH repository"""
    current_dir = Path.cwd()

    # Check for key repository files/directories that should exist in the root
    required_items = [
        'Scripts',
        'Ansible',
        'noah.py'
    ]

    missing_items = []
    for item in required_items:
        if not (current_dir / item).exists():
            missing_items.append(item)

    if missing_items:
        click.echo("❌ Error: NOAH must be run from the repository root directory!", err=True)
        click.echo("", err=True)
        click.echo(f"Current directory: {current_dir}", err=True)
        click.echo(f"Missing required items: {', '.join(missing_items)}", err=True)
        click.echo("", err=True)
        click.echo("💡 Please change to the NOAH repository root directory and try again:", err=True)
        click.echo("   cd /path/to/noah-repository", err=True)
        click.echo("   python noah.py <command>", err=True)
        sys.exit(1)

@click.group(invoke_without_command=True)
@click.version_option(version=VERSION, prog_name="NOAH")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """NOAH - Network Operations & Automation Hub

    Automates deployment of open source information systems on Kubernetes
    """
    # Show the ASCII banner on interactive launches only (skipped when output
    # is piped/redirected or under CI, to keep machine-readable output clean).
    if sys.stdout.isatty():
        _print_banner()

    # No subcommand → show help and stop before building the heavy managers.
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit()

    # Check if running from repository root before initializing
    check_repository_root()

    ctx.ensure_object(dict)
    ctx.obj['config'] = ConfigLoader()
    ctx.obj['cluster'] = ClusterManager(ctx.obj['config'])
    ctx.obj['secrets'] = SecretManager(ctx.obj['config'])
    ctx.obj['ansible'] = AnsibleRunner(ctx.obj['config'])

@cli.group()  # type: ignore
@click.pass_context
def cluster(ctx):
    """Manage Kubernetes cluster lifecycle"""
    pass

@cluster.command()
@click.option('--name', default='noah-cluster', help='Cluster name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.option('--keep-secrets/--purge-secrets', 'keep_secrets', default=True, show_default=True,
              help='Keep secrets and certificates after destruction (default). '
                   'Pass --purge-secrets to also delete the canonical store '
                   '(including the Cloudflare token), generated secrets, and certificates.')
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
@click.option('--domain', default=None,
              help='Primary domain for the cluster '
                   '(default: the domain recorded by `setup gitops`)')
@click.option('--flux-repo', default=None,
              help='GitOps repository URL, HTTPS or SSH '
                   "(default: this repo's origin remote)")
@click.option('--flux-branch', default='main', show_default=True, help='GitOps branch')
@click.option('--flux-path', default='clusters/production', show_default=True,
              help='Path inside the GitOps repo Flux will reconcile')
@click.option('--ssh-user', default='ubuntu', show_default=True, help='SSH user on target nodes')
@click.option('--ssh-key', default=None, help='SSH private key path for Ansible (optional)')
@click.option('--age-key-file', default='Age/keys.txt', show_default=True,
              help='Path to the Age private key file')
@click.option('--k3s-version', default=None,
              help='Override K3s version (default: pinned in the role)')
@click.option('--force-reset', is_flag=True, default=False,
              help='Allow bootstrap on top of an existing K3s install (DESTRUCTIVE)')
@click.option('--git-token', default=None, envvar=['GIT_TOKEN', 'GITHUB_TOKEN'],
              help='API token for your git provider (GitHub/GitLab/Gitea) — '
                   'auto-registers the SSH deploy key and skips the manual prompt. '
                   'Also read from $GIT_TOKEN or $GITHUB_TOKEN.')
@click.option('--git-provider', default=None,
              type=click.Choice(['github', 'gitlab', 'gitea'], case_sensitive=False),
              help='Force git provider for deploy-key API (auto-detected from URL by default). '
                   'Use for self-hosted GitLab or Gitea instances.')
@click.option('--no-wait', is_flag=True, default=False,
              help='Skip the post-bootstrap readiness wait/verdict (reconciliation is async).')
@click.option('--verify-timeout', default=600, show_default=True,
              help='Seconds to wait for Flux to converge after bootstrap.')
@click.option('--url-timeout', 'url_timeout', default=300, show_default=True,
              help='Seconds to wait for the public URLs to become reachable after Flux converges.')
@click.pass_context
def bootstrap(ctx, node, nodes, ha, domain, flux_repo, flux_branch, flux_path,
              ssh_user, ssh_key, age_key_file, k3s_version, force_reset,
              git_token, git_provider, no_wait, verify_timeout, url_timeout):
    """Provision K3s + bootstrap FluxCD against a GitOps repo (SSH deploy key)."""
    from Scripts.security.canonical_store import get_canonical_store
    store = get_canonical_store(Path(__file__).parent)

    # Same fallback pattern as --node below: `setup gitops` records the domain
    # in the canonical store, and gitops/ lives in this repo, so its origin
    # remote IS the GitOps repo (run_bootstrap normalizes any URL form).
    # Explicit flags always win; prompt only when nothing is recorded.
    if not domain:
        domain = store.get_cluster_domain() or click.prompt('Primary domain for the cluster')
    if not flux_repo:
        try:
            r = subprocess.run(['git', '-C', str(Path(__file__).parent),
                                'remote', 'get-url', 'origin'],
                               capture_output=True, text=True, check=True)
            flux_repo = r.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            flux_repo = ''
        flux_repo = flux_repo or click.prompt('GitOps repository URL (HTTPS or SSH)')

    # Single-node mode: default --node to the public IP recorded by `setup gitops
    # --node-ip` so the operator doesn't re-enter the same IP. If nothing was
    # recorded, prompt for it rather than erroring out. An explicit --node always
    # wins; --nodes / --ha are unaffected (HA mode still requires explicit --nodes).
    if not node and not nodes and not ha:
        node = store.get_node_public_ip() or click.prompt('Single node IP (single-node mode)')

    rc = cluster_bootstrap(
        node=node,
        nodes=nodes,
        ha=ha,
        domain=domain,
        flux_repo=flux_repo,
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        age_key_file=Path(age_key_file),
        k3s_version=k3s_version,
        flux_branch=flux_branch,
        flux_path=flux_path,
        force_reset=force_reset,
        ansible_dir=Path('Ansible').resolve(),
        git_token=git_token,
        git_provider=git_provider,
    )

    # Ansible finishing only means Flux was *installed*; reconciliation of the
    # apps is asynchronous. Wait for convergence and print a clear verdict so
    # the operator knows whether the cluster actually deployed.
    if rc == 0 and not no_wait:
        from Scripts.cluster_create.verify_utils import verify_deployment
        if not verify_deployment(domain=domain, timeout=verify_timeout, url_timeout=url_timeout):
            rc = 1
    elif rc == 0 and no_wait:
        click.echo("\nℹ️  Flux reconciles asynchronously. Check the deployment with:")
        click.echo("     python3 noah.py cluster verify")

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


@cluster.command('verify')
@click.option('--domain', default=None, help='Cluster domain (defaults to the value stored in the canonical store)')
@click.option('--timeout', default=600, show_default=True, help='Seconds to wait for Flux to converge')
@click.option('--url-timeout', 'url_timeout', default=300, show_default=True,
              help='Seconds to wait for the public URLs to become reachable (HTTPS) after Flux converges')
@click.pass_context
def cluster_verify(ctx, domain, timeout, url_timeout):
    """Wait for Flux to converge and the URLs to serve, then print a pass/fail verdict."""
    from Scripts.cluster_create.verify_utils import verify_deployment
    if not domain:
        from Scripts.security.canonical_store import get_canonical_store  # type: ignore
        domain = get_canonical_store().get_cluster_domain()
    ok = verify_deployment(domain=domain, timeout=timeout, url_timeout=url_timeout)
    sys.exit(0 if ok else 1)


@cli.group()  # type: ignore
@click.pass_context
def flux(ctx):
    """Interact with the FluxCD GitOps controller."""
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
        click.echo("[VERBOSE] TLS certificates already exist. Use --force to regenerate.")
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
    click.echo("cert-manager is now managed by FluxCD. Run 'python3 noah.py flux sync' to reconcile.")

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
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service URLs (defaults to the domain recorded by `setup gitops`)')
@click.pass_context
def show_password(ctx, domain):
    """Show current admin credentials for NOAH services"""
    click.echo("🔍 Current admin credentials:")
    click.echo("=" * 50)
    credentials, error = get_admin_credentials(domain=domain)
    if credentials:
        # External IP and resolution are node-level: identical for every service.
        node = credentials[0]
        if node.get('external_ip'):
            click.echo(f"🌐 External IP:  {node['external_ip']}")
        click.echo(f"📶 Resolution:   {node.get('resolution_status','unknown')}")
        for cred in credentials:
            click.echo("")
            click.echo(f"[{cred['service']}]")
            click.echo(f"📍 URL (HTTP):   {cred['http_url']}")
            click.echo(f"📍 URL (HTTPS):  {cred['https_url']}")
            click.echo(f"👤 Username:     {cred['admin_username']}")
            if cred.get('admin_email'):
                click.echo(f"📧 Email:        {cred['admin_email']}")
            click.echo(f"🔑 Password:     {cred['admin_password']}")
        click.echo("")
        click.echo("💡 Authentik accepts either the username or the email address")
        if node.get('resolution_status') in ('pending','lookup_error'):
            click.echo("💡 Node IP not resolved yet; ensure the cluster is reachable and DNS is configured.")
    else:
        click.echo(f"⚠️  Could not retrieve credentials: {error}")
        click.echo("💡 Check FluxCD reconciliation: python3 noah.py flux status")
    click.echo("=" * 50)


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

    click.echo("[VERBOSE] Starting secret generation process...")
    click.echo(f"[VERBOSE] Service: {service}")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"Generating secrets for {service} in namespace {namespace}")
    ctx.obj['secrets'].generate_service_secrets(service)

## Legacy rotate command removed in favor of unified canonical rotate

@secrets.command()
@click.option('--service', required=True, help='Service to validate (authentik)')
@click.option('--namespace', default='authentik', help='Kubernetes namespace')
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
            click.echo("🔧 Attempting to fix secret inconsistencies...")

            # Re-deploy with synchronized secrets
            if service == 'authentik':
                ctx.obj['secrets'].generate_service_secrets(service)
                click.echo(f"✅ Secrets regenerated for {service}. Run 'python3 noah.py flux sync' to apply.")
            else:
                click.echo(f"❌ Auto-fix not implemented for {service}")
        else:
            click.echo("💡 Run with --fix to automatically resolve inconsistencies")

@secrets.command(name='apply')
@click.option('--domain', help='Cluster domain (defaults to the value stored in the canonical store)')
@click.pass_context
def apply_secrets(ctx, domain):
    """Apply application secrets to the running cluster (out-of-band, no Git commit).

    Renders secrets from the canonical store and kubectl-applies them directly.
    Use after `secrets rotate` to propagate new secrets without re-bootstrapping.
    """
    from Scripts.gitops.gitops_init import apply_app_secrets
    try:
        apply_app_secrets(domain=domain, project_root=Path(__file__).parent,
                          print_status=print_status)
    except Exception as e:
        print_status(f"[ERROR] {e}", "ERROR")
        sys.exit(1)
    click.echo("✅ Application secrets applied to the cluster.")
    click.echo("💡 Authentik picks up changes automatically (Flux watches its values Secret).")
    click.echo("   Env-mounted consumers may need a restart, e.g.:")
    click.echo("     kubectl rollout restart deploy -n headlamp")

@secrets.command()
@click.option('--service', required=True, help='Service to regenerate secrets for')
@click.option('--namespace', default='authentik', help='Kubernetes namespace')
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
@click.option('--domain', required=True, prompt='Your domain (e.g. example.com)',
              help='Your domain (replaces example.com / ${DOMAIN} throughout gitops/)')
@click.option('--node-ip', 'node_ip', default=None,
              help='Public IP (EC2 EIP) external-dns should publish; replaces '
                   '${NODE_PUBLIC_IP}. Defaults to the value stored in the canonical store.')
@click.pass_context
def gitops(ctx, domain, node_ip):
    """Prepare gitops/: substitute domain, fill secrets, encrypt. Then git push to GitHub."""
    from Scripts.gitops.gitops_init import setup_gitops
    from Scripts.security.canonical_store import get_canonical_store

    project_root = Path(__file__).parent

    if not node_ip:
        node_ip = get_canonical_store(project_root).get_node_public_ip()

    click.echo("🚀 NOAH GitOps Repository Setup")
    click.echo("=" * 35)
    click.echo(f"  Domain  : {domain}")
    click.echo(f"  Node IP : {node_ip or '(none — ${NODE_PUBLIC_IP} left unsubstituted)'}")
    click.echo(f"  GitOps  : {project_root / 'gitops'}")
    click.echo("")

    try:
        setup_gitops(
            domain=domain,
            project_root=project_root,
            print_status=print_status,
            node_public_ip=node_ip,
        )
    except Exception as e:
        print_status(f"[ERROR] {e}", "ERROR")
        sys.exit(1)

    click.echo("")
    click.echo("✅ GitOps directory ready.")
    click.echo("")

    # Auto-detect the current branch so the suggested commands match this
    # checkout. bootstrap now defaults --domain/--node to the values recorded
    # above and --flux-repo to the origin remote, but it tracks `main` unless
    # told otherwise — surface --flux-branch only when it matters.
    def _git(args):
        try:
            r = subprocess.run(['git', '-C', str(project_root), *args],
                               capture_output=True, text=True, check=True)
            return r.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ''

    branch = _git(['rev-parse', '--abbrev-ref', 'HEAD']) or '<branch>'
    flux_branch_opt = f' --flux-branch {branch}' if branch not in ('main', '<branch>') else ''

    click.echo("Next steps:")
    click.echo("  1. Commit and push so Flux can reconcile this repo:")
    click.echo("       git add gitops/ && git commit -m 'chore: update GitOps configuration'")
    click.echo(f"       git push origin {branch}")
    click.echo("")
    click.echo("  2. Bootstrap the cluster (this repo is the Flux source — gitops/ lives here;")
    click.echo("     the domain and node IP recorded above are reused as defaults):")
    click.echo("       export GITHUB_TOKEN=<token>   # or GIT_TOKEN — auto-registers the deploy key")
    click.echo(f"       python3 noah.py cluster bootstrap{flux_branch_opt}")
    click.echo("     (co-located on the target node itself? add: --node 127.0.0.1)")

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

@test.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for services')
@click.pass_context
def hubble(ctx, domain):
    """Test Hubble UI deployment and Authentik forward-auth integration"""
    click.echo("Testing Hubble UI deployment and Authentik integration...")
    from Tests.test_hubble_auth import HubbleAuthTester
    tester = HubbleAuthTester(domain=domain)
    if tester.run_all_tests():
        click.echo("✓ Hubble test successful")
    else:
        click.echo("✗ Hubble test failed", err=True)
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
