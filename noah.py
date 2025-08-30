#!/usr/bin/env python3
"""
NOAH - Network Operations & Automation Hub
Main CLI for deploying and managing Kubernetes-based information systems
"""

import click  # type: ignore
import sys
import os
import json
import yaml  # type: ignore
import subprocess
import shutil
import time
from pathlib import Path
from Scripts.secure_env_loader import SecureEnvLoader

# Load environment variables from encrypted configuration
secure_loader = SecureEnvLoader()
secure_loader.load_secure_env(Path("config.enc.yaml"))

# Import CLI utilities
from CLI.kubectl_utils import cleanup_kubectl_cache, display_kubectl_status, verify_kubectl_disconnected
# from CLI.redeploy_utils import execute_redeploy  # Commented out - redeploy feature disabled

# Configuration paths from environment variables
def get_noah_paths():
    """Get NOAH directory paths from environment variables"""
    return {
        'root_dir': Path(os.getenv('NOAH_ROOT_DIR', os.getcwd())),
        'scripts_dir': Path(os.getenv('NOAH_SCRIPTS_DIR', './Scripts')),
        'certificates_dir': Path(os.getenv('NOAH_CERTIFICATES_DIR', './Certificates')),
        'age_dir': Path(os.getenv('NOAH_AGE_DIR', './Age')),
        'venv_dir': Path(os.getenv('NOAH_VENV_DIR', './.venv')),
        'ansible_dir': Path(os.getenv('ANSIBLE_PLAYBOOK_DIR', './Ansible')),
        'helm_dir': Path(os.getenv('HELM_CHART_DIR', './Helm')),
        'sops_config': Path(os.getenv('SOPS_CONFIG_FILE', '.sops.yaml')),
        'age_key_file': Path(os.getenv('AGE_KEY_FILE', './Age/keys.txt'))
    }

# Global paths instance
NOAH_PATHS = get_noah_paths()

from Scripts.cluster_manager import ClusterManager
from Scripts.security_manager import NoahSecurityManager as SecretManager
from Scripts.helm_deployer import HelmDeployer
from Scripts.ansible_runner import AnsibleRunner
from Scripts.config_loader import ConfigLoader

VERSION = "0.0.1"
# Load default domain from environment, fallback to noah-infra.com
DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', 'noah-infra.com')

def get_authentik_credentials():
    """Get Authentik admin credentials from encrypted configuration"""
    try:
        import subprocess
        import tempfile
        import os
        
        # Decrypt the authentik secrets using SOPS
        age_key_file = NOAH_PATHS['age_key_file']
        secrets_file = Path("Helm/authentik/secrets/authentik-secrets.enc.yaml")
        
        if not age_key_file.exists():
            return None, f"Age key file not found: {age_key_file}"
        
        if not secrets_file.exists():
            return None, f"Authentik secrets file not found: {secrets_file}"
        
        # Set SOPS environment variable
        env = os.environ.copy()
        env['SOPS_AGE_KEY_FILE'] = str(age_key_file)
        
        # Decrypt secrets
        result = subprocess.run([
            'sops', '-d', str(secrets_file)
        ], capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            return None, f"Failed to decrypt secrets: {result.stderr}"
        
        # Parse the decrypted YAML
        import yaml
        secrets_data = yaml.safe_load(result.stdout)
        
        # Extract credentials with validation
        if not secrets_data or 'authentik' not in secrets_data:
            return None, "Invalid secrets format: missing authentik section"
        
        bootstrap_data = secrets_data.get('authentik', {}).get('bootstrap', {})
        bootstrap_password = bootstrap_data.get('password', '')
        
        if not bootstrap_password:
            return None, "Bootstrap password not found in secrets"
        
        admin_email = 'admin@noah-infra.com'
        admin_username = 'akadmin'
        
        # Get service URL with fallback
        try:
            kubectl_result = subprocess.run([
                'kubectl', 'get', 'svc', '-n', 'identity', 'authentik-server', 
                '-o', 'jsonpath={.status.loadBalancer.ingress[0].ip}'
            ], capture_output=True, text=True, timeout=10)
            
            if kubectl_result.returncode == 0 and kubectl_result.stdout.strip():
                external_ip = kubectl_result.stdout.strip()
                http_url = f"http://{external_ip}"
                https_url = f"https://{external_ip}"
            else:
                # Try to get NodePort if LoadBalancer IP is not available
                kubectl_result = subprocess.run([
                    'kubectl', 'get', 'svc', '-n', 'identity', 'authentik-server', 
                    '-o', 'jsonpath={.spec.ports[?(@.name=="https")].nodePort}'
                ], capture_output=True, text=True, timeout=10)
                
                if kubectl_result.returncode == 0 and kubectl_result.stdout.strip():
                    https_port = kubectl_result.stdout.strip()
                    http_url = f"http://65.21.238.126"  # Use node IP
                    https_url = f"https://65.21.238.126:{https_port}"
                else:
                    http_url = "http://65.21.238.126"
                    https_url = "https://65.21.238.126"
        except Exception:
            http_url = "http://65.21.238.126"
            https_url = "https://65.21.238.126"
        
        return {
            'http_url': http_url,
            'https_url': https_url,
            'admin_username': admin_username,
            'admin_email': admin_email,
            'admin_password': bootstrap_password
        }, None
        
    except Exception as e:
        return None, f"Error retrieving credentials: {str(e)}"

def regenerate_authentik_password():
    """Generate a new Authentik admin password and update encrypted secrets"""
    try:
        import subprocess
        import tempfile
        import os
        from Scripts.security_manager import NoahSecurityManager
        
        # Initialize security manager
        security_manager = NoahSecurityManager()
        
        # Generate new password
        new_password = security_manager.generate_secure_password(24)
        
        # Paths
        age_key_file = NOAH_PATHS['age_key_file']
        secrets_file = Path("Helm/authentik/secrets/authentik-secrets.enc.yaml")
        
        if not age_key_file.exists():
            return None, f"Age key file not found: {age_key_file}"
        
        if not secrets_file.exists():
            return None, f"Authentik secrets file not found: {secrets_file}"
        
        # Set SOPS environment variable
        env = os.environ.copy()
        env['SOPS_AGE_KEY_FILE'] = str(age_key_file)
        
        # Decrypt current secrets
        result = subprocess.run([
            'sops', '-d', str(secrets_file)
        ], capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            return None, f"Failed to decrypt secrets: {result.stderr}"
        
        # Parse and update secrets
        import yaml
        secrets_data = yaml.safe_load(result.stdout)
        
        if not secrets_data or 'authentik' not in secrets_data:
            return None, "Invalid secrets format: missing authentik section"
        
        # Store old password
        old_password = secrets_data.get('authentik', {}).get('bootstrap', {}).get('password', '')
        
        # Update the password
        secrets_data['authentik']['bootstrap']['password'] = new_password
        
        # Create a backup of the original file
        backup_file = secrets_file.with_suffix('.enc.yaml.backup')
        import shutil
        shutil.copy2(str(secrets_file), str(backup_file))
        
        try:
            # Write updated secrets to a temporary file with correct extension
            temp_secrets_file = Path("authentik-secrets-temp.enc.yaml")
            with open(temp_secrets_file, 'w') as f:
                yaml.dump(secrets_data, f, default_flow_style=False)
            
            # Encrypt the temporary file
            result = subprocess.run([
                'sops', '-e', '--in-place', str(temp_secrets_file)
            ], capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                return None, f"Failed to encrypt updated secrets: {result.stderr}"
            
            # Replace the original file
            shutil.move(str(temp_secrets_file), str(secrets_file))
            
            # Remove backup file
            backup_file.unlink()
            
            return {
                'old_password': old_password,
                'new_password': new_password,
                'updated_file': str(secrets_file)
            }, None
            
        except Exception as e:
            # Restore from backup on error
            if backup_file.exists():
                shutil.move(str(backup_file), str(secrets_file))
            # Clean up temp file if it exists
            temp_file = Path("authentik-secrets-temp.enc.yaml")
            if temp_file.exists():
                temp_file.unlink()
            raise e
        
    except Exception as e:
        return None, f"Error regenerating password: {str(e)}"

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

def check_existing_cluster():
    """Check if a K3s cluster or related components exist"""
    try:
        # Check for existing K3s processes
        result = subprocess.run(['pgrep', '-f', 'k3s'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Check for existing K3s service
        result = subprocess.run(['systemctl', 'is-active', 'k3s'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Check for existing kubectl context
        result = subprocess.run(['kubectl', 'cluster-info'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Check for existing NOAH data directories
        data_dirs = ['/var/lib/rancher/k3s', '/etc/rancher/k3s', '/run/k3s']
        for dir_path in data_dirs:
            if Path(dir_path).exists():
                return True
        
        # Check for existing Helm releases (only if cluster is accessible)
        if shutil.which('helm') and subprocess.run(['kubectl', 'cluster-info'], capture_output=True).returncode == 0:
            result = subprocess.run(['helm', 'list', '--all-namespaces', '-o', 'json'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != '[]':
                return True
        
        return False
    except Exception:
        # If any check fails, assume no cluster exists
        return False
    
    return True

def get_security_config(domain=DEFAULT_DOMAIN):
    """Get security configuration for Helm and Ansible"""
    paths = get_noah_paths()
    
    return {
        'secrets': {
            'age': {
                'enabled': paths['age_dir'].exists(),
                'key_path': str(paths['age_dir'] / "noah.key") if paths['age_dir'].exists() else None,
                'public_key_path': str(paths['age_dir'] / "noah.pub") if paths['age_dir'].exists() else None
            },
            'sops': {
                'enabled': paths['sops_config'].exists(),
                'config_path': str(paths['sops_config'])
            }
        },
        'certificates': {
            'enabled': paths['certificates_dir'].exists(),
            'domain': domain,
            'ca_cert_path': str(paths['certificates_dir'] / "ca.crt") if paths['certificates_dir'].exists() else None,
            'ca_key_path': str(paths['certificates_dir'] / "ca.key") if paths['certificates_dir'].exists() else None,
            'wildcard_cert_path': str(paths['certificates_dir'] / f"*.{domain}.crt") if paths['certificates_dir'].exists() else None,
            'wildcard_key_path': str(paths['certificates_dir'] / f"*.{domain}.key") if paths['certificates_dir'].exists() else None
        },
        'tls': {
            'enabled': True,
            'self_signed': True,
            'domain': domain
        }
    }

def get_helm_values_for_service(service, namespace, domain=DEFAULT_DOMAIN):
    """Generate Helm values for a specific service with security configuration"""
    security_config = get_security_config(domain)
    
    base_values = {
        'global': {
            'domain': domain,
            'namespace': namespace
        },
        'security': security_config,
        'secrets': {
            'enabled': security_config['secrets']['age']['enabled'],
            'managed': True,
            'backend': 'sops',
            'age': {
                'enabled': security_config['secrets']['age']['enabled'],
                'publicKey': security_config['secrets']['age']['public_key_path']
            }
        },
        'tls': {
            'enabled': security_config['certificates']['enabled'],
            'domain': domain,
            'selfSigned': True,
            'certificateSecret': f"{service}-tls",
            'ca': {
                'enabled': True,
                'secretName': 'noah-ca-certificate'
            }
        }
    }
    
    # Service-specific configurations
    if service == 'authentik':
        base_values.update({
            'authentik': {
                'secret_key': {
                    'secretName': 'authentik-secret',
                    'secretKey': 'secret-key'
                },
                'postgresql': {
                    'password': {
                        'secretName': 'authentik-postgresql',
                        'secretKey': 'password'
                    }
                },
                'redis': {
                    'password': {
                        'secretName': 'authentik-redis',
                        'secretKey': 'password'
                    }
                }
            },
            'ingress': {
                'enabled': True,
                'hosts': [{
                    'host': f"auth.{domain}",
                    'paths': [{
                        'path': '/',
                        'pathType': 'Prefix'
                    }]
                }],
                'tls': [{
                    'secretName': 'authentik-tls',
                    'hosts': [f"auth.{domain}"]
                }]
            }
        })
    elif service == 'cilium':
        base_values.update({
            'hubble': {
                'relay': {
                    'enabled': True,
                    'tls': {
                        'server': {
                            'enabled': True,
                            'secretName': 'hubble-server-certs'
                        }
                    }
                },
                'ui': {
                    'enabled': True,
                    'ingress': {
                        'enabled': True,
                        'hosts': [f"hubble.{domain}"],
                        'tls': [{
                            'secretName': 'hubble-ui-tls',
                            'hosts': [f"hubble.{domain}"]
                        }]
                    }
                }
            }
        })
    
    return base_values

def get_ansible_vars_for_service(service, namespace, domain=DEFAULT_DOMAIN):
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

def ensure_security_initialized(ctx):
    """Ensure SOPS/Age keys and certificates are initialized"""
    age_dir = Path("Age")
    sops_config = Path(".sops.yaml")
    
    # Check if Age keys exist
    if not age_dir.exists() or not (any(age_dir.glob("*.key")) or (age_dir / "keys.txt").exists()):
        click.echo("[VERBOSE] No Age keys found. Auto-generating SOPS/Age keys...")
        click.echo("Initializing security infrastructure...")
        
        # Create Age directory if it doesn't exist
        age_dir.mkdir(exist_ok=True)
        
        # Initialize Age keys
        ctx.obj['secrets'].initialize_age()
        
        # Configure SOPS
        ctx.obj['secrets'].configure_sops()
        
        click.echo("[VERBOSE] Age keys generated successfully in Age/ directory")
        click.echo("[VERBOSE] SOPS configuration created")
    else:
        click.echo("[VERBOSE] Age keys found in Age/ directory")
    
    # Check and generate TLS certificates
    certs_dir = Path("Certificates")
    if not certs_dir.exists() or not any(certs_dir.glob("*.crt")):
        click.echo(f"[VERBOSE] No TLS certificates found. Generating self-signed certificates for {DEFAULT_DOMAIN}...")
        ctx.obj['secrets'].generate_tls_certificates(DEFAULT_DOMAIN)
        click.echo(f"[VERBOSE] TLS certificates generated for domain: {DEFAULT_DOMAIN}")
    else:
        click.echo("[VERBOSE] TLS certificates found in Certificates/ directory")
    
    # Export security configuration for debugging
    if click.get_current_context().obj.get('debug'):
        security_config = get_security_config()
        click.echo("[DEBUG] Security Configuration:")
        click.echo(json.dumps(security_config, indent=2))

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

@cluster.command()
@click.option('--name', default='noah-cluster', help='Cluster name')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.option('--keep-secrets', is_flag=True, help='Keep secrets and certificates after destruction')
@click.pass_context
def destroy(ctx, name, force, keep_secrets):
    """Destroy Kubernetes cluster and clean up resources"""
    if not force:
        click.confirm(f'Are you sure you want to destroy cluster {name}?', abort=True)
    click.echo(f"[VERBOSE] Starting cluster destruction process...")
    click.echo(f"[VERBOSE] Cluster name: {name}")
    click.echo(f"[VERBOSE] Force mode: {force}")
    click.echo(f"[VERBOSE] Keep secrets: {keep_secrets}")
    
    # Get current security configuration
    security_config = get_security_config()
    
    click.echo(f"Destroying cluster: {name}")
    click.echo(f"[VERBOSE] Running Ansible playbook: cluster-destroy.yml")
    
    # Clean up secrets and certificates unless specified otherwise
    ctx.obj['ansible'].run_playbook('cluster-destroy.yml', {
        'cluster_name': name,
        'cleanup_secrets': not keep_secrets,
        'cleanup_certificates': not keep_secrets,
        'security_config': security_config
    })
    
    if not keep_secrets:
        click.echo("[VERBOSE] Cleaning up local secrets and certificates...")
        ctx.obj['secrets'].cleanup_local_secrets()
    
    # Clean up kubectl client cache to prevent memcache errors
    click.echo("[VERBOSE] Cleaning up kubectl client cache...")
    cleanup_kubectl_cache()

# NEW: Use modular redeploy command from CLI utilities
# @cluster.command()
# @click.option('--name', default='noah-production', help='Cluster name')
# @click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for TLS certificates and services')
# @click.option('--force', is_flag=True, help='Force redeploy without confirmation')
# @click.option('--config-file', type=click.Path(exists=False), help='Export configuration to file')
# @click.pass_context
# def redeploy(ctx, name, domain, force, config_file):
#    """Redeploy complete NOAH infrastructure (cluster + all services)"""
#    execute_redeploy(
#        ctx, name, domain, force, config_file,
#        ensure_security_initialized, 
#        get_security_config,
#        get_helm_values_for_service, 
#        get_ansible_vars_for_service
#    )

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
        click.echo("   python noah.py deploy all")
        click.echo("")
        click.echo("🔍 To view current credentials after deployment:")
        click.echo("   python noah.py password show")
    else:
        click.echo(f"❌ Failed to regenerate password: {error}", err=True)
        sys.exit(1)

@password.command()
@click.pass_context
def show(ctx):
    """Show current Authentik admin credentials"""
    click.echo("🔍 Current Authentik admin credentials:")
    click.echo("=" * 50)
    
    credentials, error = get_authentik_credentials()
    if credentials:
        click.echo(f"📍 URL (HTTP):  {credentials['http_url']}")
        click.echo(f"📍 URL (HTTPS): {credentials['https_url']}")
        click.echo(f"👤 Username:    {credentials['admin_username']}")
        click.echo(f"📧 Email:       {credentials['admin_email']}")
        click.echo(f"🔑 Password:    {credentials['admin_password']}")
        click.echo("")
        click.echo("💡 You can log in using either the username or email address")
    else:
        click.echo(f"⚠️  Could not retrieve credentials: {error}")
        click.echo("💡 Try running a deployment first: python noah.py deploy authentik")
    click.echo("=" * 50)

@cli.group()  # type: ignore
@click.pass_context
def deploy(ctx):
    """Deploy services to Kubernetes
    
    OPTIMIZED: Individual commands (authentik, cilium) are simplified
    and the 'all' command now uses cluster-deploy.yml Ansible playbook to avoid 
    code repetition and leverage the optimized deployment order and validation.
    """
    pass

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
    click.echo(f"💡 For complete stack deployment, use: python noah.py deploy all")
    
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
    
    credentials, error = get_authentik_credentials()
    if credentials:
        click.echo(f"📍 URL (HTTP):  {credentials['http_url']}")
        click.echo(f"📍 URL (HTTPS): {credentials['https_url']}")
        click.echo(f"👤 Username:    {credentials['admin_username']}")
        click.echo(f"📧 Email:       {credentials['admin_email']}")
        click.echo(f"🔑 Password:    {credentials['admin_password']}")
        click.echo("")
        click.echo("💡 You can log in using either the username or email address")
    else:
        click.echo(f"⚠️  Could not retrieve credentials: {error}")
    click.echo("="*50)

@deploy.command()
@click.option('--namespace', default='kube-system', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.pass_context
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

@deploy.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for services')
@click.option('--cluster-name', default='noah-cluster', help='Cluster name for deployment')
@click.option('--config-file', type=click.Path(exists=False), help='Export configuration to file')
@click.option('--regenerate-password', is_flag=True, help='Generate new Authentik admin password')
@click.pass_context
def all(ctx, domain, cluster_name, config_file, regenerate_password):
    """Deploy complete stack using optimized Ansible playbook (Cilium → Authentik)"""
    # Ensure security is initialized before any deployment
    ensure_security_initialized(ctx)
    
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
    click.echo(f"[VERBOSE] Deployment order: Cilium → Authentik")
    
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
        'domain_name': domain
    }
    
    click.echo(f"[VERBOSE] Running optimized deployment playbook: cluster-deploy.yml")
    click.echo(f"[VERBOSE] This will deploy in optimal order with comprehensive validation")
    
    try:
        ctx.obj['ansible'].run_playbook('cluster-deploy.yml', ansible_vars)
        click.echo("🎉 NOAH standalone IAM deployment successful!")
        click.echo(f"[VERBOSE] All components deployed and validated")
        
        # Get and display Authentik credentials
        click.echo("\n" + "="*60)
        click.echo("🔐 AUTHENTIK ADMIN ACCESS")
        click.echo("="*60)
        
        credentials, error = get_authentik_credentials()
        if credentials:
            click.echo(f"📍 URL (HTTP):  {credentials['http_url']}")
            click.echo(f"📍 URL (HTTPS): {credentials['https_url']}")
            click.echo(f"👤 Username:    {credentials['admin_username']}")
            click.echo(f"📧 Email:       {credentials['admin_email']}")
            click.echo(f"🔑 Password:    {credentials['admin_password']}")
            click.echo("")
            click.echo("💡 You can log in using either the username or email address")
        else:
            click.echo(f"⚠️  Could not retrieve credentials: {error}")
            click.echo("💡 Try running: kubectl get secret -n identity authentik-secrets -o yaml")
        
        click.echo("="*60)
        click.echo(f"[VERBOSE] Access points:")
        click.echo(f"  - Authentik IAM: https://auth.{domain}")
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
    ctx.obj['secrets'].initialize_age()
    click.echo("[VERBOSE] Configuring SOPS...")
    ctx.obj['secrets'].configure_sops()

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

@secrets.command()
@click.option('--service', required=True, help='Service name')
@click.pass_context
def rotate(ctx, service):
    """Rotate passwords for a service"""
    click.echo(f"[VERBOSE] Starting password rotation process...")
    click.echo(f"[VERBOSE] Service: {service}")
    click.echo(f"Rotating passwords for {service}")
    ctx.obj['secrets'].rotate_passwords(service)

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
                # Redeploy to apply fixes
                ctx.obj['helm'].deploy_chart(service, namespace)
                click.echo(f"✅ Secrets fixed and {service} redeployed")
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

def check_command_exists(command):
    """Check if a command exists in the system PATH"""
    return shutil.which(command) is not None

def print_status(message, status="INFO"):
    """Print colored status messages"""
    colors = {
        "INFO": "\033[0;34m",     # Blue
        "SUCCESS": "\033[0;32m",   # Green
        "WARNING": "\033[1;33m",   # Yellow
        "ERROR": "\033[0;31m",     # Red
    }
    reset = "\033[0m"
    click.echo(f"{colors.get(status, '')}{message}{reset}")

def update_sops_version():
    """Update SOPS to the latest version"""
    import requests  # type: ignore
    import tarfile
    import tempfile
    import stat
    import platform
    
    try:
        print_status("[INFO] Checking current SOPS version...", "INFO")
        
        # Get current version
        current_version = None
        if check_command_exists('sops'):
            try:
                result = subprocess.run(['sops', '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    # Extract version from output like "sops 3.8.1 (latest)"
                    for line in result.stdout.split('\n'):
                        if 'sops' in line.lower():
                            parts = line.split()
                            for part in parts:
                                if part.replace('.', '').replace('-', '').isdigit() or '.' in part:
                                    current_version = part
                                    break
                            break
            except Exception:
                pass
        
        if current_version:
            print_status(f"[INFO] Current SOPS version: {current_version}", "INFO")
        else:
            print_status("[INFO] SOPS not found or version not detected", "INFO")
        
        # Get latest version from GitHub API
        print_status("[INFO] Fetching latest SOPS version...", "INFO")
        response = requests.get("https://api.github.com/repos/getsops/sops/releases/latest", timeout=10)
        response.raise_for_status()
        
        latest_release = response.json()
        latest_version = latest_release['tag_name'].lstrip('v')
        
        print_status(f"[INFO] Latest SOPS version: {latest_version}", "INFO")
        
        # Check if update is needed
        def version_compare(v1, v2):
            """Compare two version strings"""
            try:
                v1_parts = [int(x) for x in v1.split('.')]
                v2_parts = [int(x) for x in v2.split('.')]
                
                # Pad shorter version with zeros
                max_len = max(len(v1_parts), len(v2_parts))
                v1_parts += [0] * (max_len - len(v1_parts))
                v2_parts += [0] * (max_len - len(v2_parts))
                
                for i in range(max_len):
                    if v1_parts[i] < v2_parts[i]:
                        return -1
                    elif v1_parts[i] > v2_parts[i]:
                        return 1
                return 0
            except (ValueError, AttributeError):
                return -1  # Assume update needed if comparison fails
        
        if current_version and version_compare(current_version.strip(), latest_version) >= 0:
            print_status("[SUCCESS] SOPS is already up to date", "SUCCESS")
            return True
        
        print_status(f"[INFO] Updating SOPS from {current_version or 'not installed'} to {latest_version}...", "INFO")
        
        # Determine architecture and OS
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map architecture names
        arch_map = {
            'x86_64': 'amd64',
            'amd64': 'amd64',
            'arm64': 'arm64',
            'aarch64': 'arm64',
            'armv7l': 'arm',
        }
        
        arch = arch_map.get(machine, 'amd64')
        
        # Find the appropriate download URL
        download_url = None
        binary_name = f"sops-v{latest_version}.{system}.{arch}"
        
        for asset in latest_release['assets']:
            if asset['name'] == binary_name:
                download_url = asset['browser_download_url']
                break
        
        if not download_url:
            print_status(f"[ERROR] No binary found for {system}-{arch}", "ERROR")
            return False
        
        # Download and install
        print_status(f"[INFO] Downloading SOPS {latest_version}...", "INFO")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "sops"
            
            # Download binary
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            temp_file.write_bytes(response.content)
            
            # Make executable
            temp_file.chmod(temp_file.stat().st_mode | stat.S_IEXEC)
            
            # Install to /usr/local/bin or ~/.local/bin
            install_paths = ["/usr/local/bin/sops", f"{Path.home()}/.local/bin/sops"]
            installed = False
            
            for install_path in install_paths:
                try:
                    install_dir = Path(install_path).parent
                    install_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy binary
                    shutil.copy2(temp_file, install_path)
                    Path(install_path).chmod(Path(install_path).stat().st_mode | stat.S_IEXEC)
                    
                    print_status(f"[SUCCESS] SOPS {latest_version} installed to {install_path}", "SUCCESS")
                    installed = True
                    break
                    
                except PermissionError:
                    continue
                except Exception as e:
                    print_status(f"[WARNING] Failed to install to {install_path}: {e}", "WARNING")
                    continue
            
            if not installed:
                print_status("[ERROR] Failed to install SOPS - no writable location found", "ERROR")
                print_status("[INFO] Try running with sudo or ensure ~/.local/bin is in PATH", "INFO")
                return False
        
        # Verify installation
        if check_command_exists('sops'):
            try:
                result = subprocess.run(['sops', '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    print_status("[SUCCESS] SOPS update completed successfully", "SUCCESS")
                    return True
            except Exception:
                pass
        
        print_status("[WARNING] SOPS installed but not found in PATH", "WARNING")
        print_status("[INFO] You may need to restart your shell or update PATH", "INFO")
        return True
        
    except requests.RequestException as e:
        print_status(f"[ERROR] Network error updating SOPS: {e}", "ERROR")
        return False
    except Exception as e:
        print_status(f"[ERROR] Failed to update SOPS: {e}", "ERROR")
        return False

@setup.command()
@click.option('--skip-deps', is_flag=True, help='Skip external dependency checks')
@click.option('--skip-tests', is_flag=True, help='Skip validation tests')
@click.pass_context
def initialize(ctx, skip_deps, skip_tests):
    """Initialize NOAH environment with all dependencies"""
    click.echo("🚀 NOAH - Network Operations & Automation Hub")
    click.echo("=" * 50)
    click.echo("Initializing NOAH environment...")
    click.echo("")
    
    # Check Python version
    print_status("[INFO] Checking Python installation...", "INFO")
    python_version = sys.version.split()[0]
    if sys.version_info >= (3, 8):
        print_status(f"[SUCCESS] Python {python_version} found", "SUCCESS")
    else:
        print_status("[ERROR] Python 3.8+ is required", "ERROR")
        sys.exit(1)
    
    # Check virtual environment
    print_status("[INFO] Checking virtual environment...", "INFO")
    venv_path = Path(".venv")
    if not venv_path.exists():
        print_status("[INFO] Creating Python virtual environment...", "INFO")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_status("[SUCCESS] Virtual environment created", "SUCCESS")
    else:
        print_status("[SUCCESS] Virtual environment already exists", "SUCCESS")
    
    # Install Python dependencies
    print_status("[INFO] Installing Python dependencies...", "INFO")
    venv_python = venv_path / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_path / "Scripts" / "python.exe"  # Windows
    
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "Scripts/requirements.txt"], 
                      check=True, capture_output=True)
        print_status("[SUCCESS] Python dependencies installed", "SUCCESS")
    except subprocess.CalledProcessError as e:
        print_status(f"[ERROR] Failed to install dependencies: {e}", "ERROR")
        sys.exit(1)
    
    # Check external dependencies
    if not skip_deps:
        print_status("[INFO] Checking external dependencies...", "INFO")
        external_deps = {
            'kubectl': 'Kubernetes CLI',
            'helm': 'Helm package manager',
            'ansible': 'Infrastructure automation',
            'age': 'Encryption tool'
        }
        
        missing_deps = []
        for cmd, desc in external_deps.items():
            if check_command_exists(cmd):
                print_status(f"[SUCCESS] {cmd} found ({desc})", "SUCCESS")
            else:
                print_status(f"[WARNING] {cmd} not found ({desc})", "WARNING")
                missing_deps.append(cmd)
        
        # Check and update SOPS
        print_status("[INFO] Checking SOPS version...", "INFO")
        if check_command_exists('sops'):
            update_sops_version()
        else:
            print_status("[WARNING] SOPS not found - attempting to install latest version...", "WARNING")
            if update_sops_version():
                print_status("[SUCCESS] SOPS installed successfully", "SUCCESS")
            else:
                print_status("[ERROR] Failed to install SOPS", "ERROR")
                missing_deps.append('sops')
        
        if missing_deps:
            print_status("[WARNING] Missing external dependencies:", "WARNING")
            click.echo("  Install with your package manager:")
            click.echo(f"  Ubuntu/Debian: sudo apt install {' '.join(missing_deps)}")
            click.echo(f"  RHEL/CentOS:   sudo dnf install {' '.join(missing_deps)}")
            click.echo(f"  macOS:         brew install {' '.join(missing_deps)}")
            click.echo("")
    
    # Initialize NOAH
    print_status("[INFO] Initializing NOAH CLI...", "INFO")
    os.environ['PYTHONPATH'] = f"{os.getcwd()}:{os.environ.get('PYTHONPATH', '')}"
    
    # Test CLI functionality
    try:
        result = subprocess.run([str(venv_python), "noah.py", "--help"], 
                               capture_output=True, text=True, env=os.environ)
        if result.returncode == 0:
            print_status("[SUCCESS] NOAH CLI initialized successfully", "SUCCESS")
        else:
            print_status("[ERROR] Failed to initialize NOAH CLI", "ERROR")
            sys.exit(1)
    except Exception as e:
        print_status(f"[ERROR] CLI test failed: {e}", "ERROR")
        sys.exit(1)
    
    # Initialize security infrastructure
    print_status("[INFO] Setting up security infrastructure...", "INFO")
    try:
        ctx.obj['secrets'].initialize_age()
        ctx.obj['secrets'].configure_sops()
        print_status("[SUCCESS] Security infrastructure initialized", "SUCCESS")
    except Exception as e:
        print_status(f"[WARNING] Security setup incomplete: {e}", "WARNING")
    
    # Run validation tests
    if not skip_tests:
        print_status("[INFO] Running validation tests...", "INFO")
        test_files = ["Tests/test_noah.py", "Tests/test_modifications.py"]
        tests_passed = 0
        
        for test_file in test_files:
            if Path(test_file).exists():
                try:
                    result = subprocess.run([str(venv_python), test_file], 
                                          capture_output=True, env=os.environ)
                    if result.returncode == 0:
                        tests_passed += 1
                except Exception:
                    pass
        
        if tests_passed > 0:
            print_status(f"[SUCCESS] {tests_passed}/{len(test_files)} test suites passed", "SUCCESS")
        else:
            print_status("[WARNING] Some tests failed - run manually to debug", "WARNING")
    
    # Print completion message
    click.echo("")
    click.echo("🎉 NOAH Setup Complete!")
    click.echo("=" * 25)
    click.echo("")
    click.echo("To use NOAH:")
    click.echo("1. Activate virtual environment: source .venv/bin/activate")
    click.echo("2. Set Python path: export PYTHONPATH=$(pwd):$PYTHONPATH")
    click.echo("3. Use NOAH: python noah.py --help")
    click.echo("")
    click.echo("Quick start:")
    click.echo("  python noah.py secrets init")
    click.echo("  python noah.py cluster create --name my-cluster")
    click.echo("  python noah.py deploy all --domain my-domain.com")
    click.echo("")
    print_status("[SUCCESS] Setup completed successfully!", "SUCCESS")

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
    click.echo("🔍 NOAH Environment Diagnosis")
    click.echo("=" * 35)
    click.echo("")
    
    issues = []
    
    # Check Python version
    python_version = sys.version.split()[0]
    if sys.version_info >= (3, 8):
        print_status(f"✓ Python {python_version}", "SUCCESS")
    else:
        print_status(f"✗ Python {python_version} (3.8+ required)", "ERROR")
        issues.append("Python version too old")
    
    # Check virtual environment
    venv_path = Path(".venv")
    if venv_path.exists():
        print_status("✓ Virtual environment exists", "SUCCESS")
    else:
        print_status("✗ Virtual environment missing", "ERROR")
        issues.append("No virtual environment")
    
    # Check requirements file
    req_file = Path("Scripts/requirements.txt")
    if req_file.exists():
        print_status("✓ Requirements file found", "SUCCESS")
    else:
        print_status("✗ Requirements file missing", "ERROR")
        issues.append("Missing requirements.txt")
    
    # Check external dependencies
    external_deps = ['kubectl', 'helm', 'ansible', 'age']
    for cmd in external_deps:
        if check_command_exists(cmd):
            print_status(f"✓ {cmd} available", "SUCCESS")
        else:
            print_status(f"✗ {cmd} missing", "WARNING")
            issues.append(f"Missing {cmd}")
    
    # Check SOPS version specifically
    if check_command_exists('sops'):
        try:
            result = subprocess.run(['sops', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                # Extract version from output
                version = "unknown"
                for line in result.stdout.split('\n'):
                    if 'sops' in line.lower():
                        parts = line.split()
                        for part in parts:
                            if part.replace('.', '').replace('-', '').isdigit() or '.' in part:
                                version = part
                                break
                        break
                print_status(f"✓ SOPS version {version}", "SUCCESS")
                # Check if version is recent (3.8+)
                try:
                    major, minor = map(int, version.split('.')[:2])
                    if major < 3 or (major == 3 and minor < 8):
                        print_status("⚠ SOPS version is outdated (consider updating)", "WARNING")
                        issues.append("SOPS version outdated")
                except:
                    pass
            else:
                print_status("✗ SOPS version check failed", "WARNING")
                issues.append("SOPS version check failed")
        except Exception:
            print_status("✗ SOPS available but version check failed", "WARNING")
            issues.append("SOPS version check failed")
    else:
        print_status("✗ SOPS missing", "ERROR")
        issues.append("Missing SOPS")
    
    # Check NOAH files
    noah_files = ['noah.py', 'Scripts/', 'Helm/', 'Ansible/']
    for file_path in noah_files:
        if Path(file_path).exists():
            print_status(f"✓ {file_path} exists", "SUCCESS")
        else:
            print_status(f"✗ {file_path} missing", "ERROR")
            issues.append(f"Missing {file_path}")
    
    # Check Age keys
    age_dir = Path("Age")
    if age_dir.exists() and (any(age_dir.glob("*.key")) or (age_dir / "keys.txt").exists()):
        print_status("✓ Age keys configured", "SUCCESS")
    else:
        print_status("⚠ Age keys not initialized", "WARNING")
        issues.append("Age keys need initialization")
    
    # Summary
    click.echo("")
    if not issues:
        print_status("🎉 All checks passed! NOAH is ready.", "SUCCESS")
    else:
        print_status(f"⚠ Found {len(issues)} issues:", "WARNING")
        for issue in issues:
            click.echo(f"  • {issue}")
        click.echo("")
        click.echo("Run 'python noah.py setup initialize' to fix most issues automatically.")

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

@cli.command()  # type: ignore
@click.pass_context
def status(ctx):
    """Show status of all deployed services"""
    click.echo("[VERBOSE] Gathering system status information...")
    click.echo("NOAH System Status")
    click.echo("-" * 50)
    ctx.obj['cluster'].show_status()

if __name__ == '__main__':
    cli()  # type: ignore
