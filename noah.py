#!/usr/bin/env python3
"""
NOAH - Network Operations & Automation Hub
Main CLI for deploying and managing Kubernetes-based information systems
"""

import click
import sys
import os
import json
import yaml
import subprocess
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from Scripts.cluster_manager import ClusterManager
from Scripts.secret_manager import SecretManager
from Scripts.helm_deployer import HelmDeployer
from Scripts.ansible_runner import AnsibleRunner
from Scripts.config_loader import ConfigLoader

VERSION = "0.0.1"
# Load default domain from environment, fallback to noah-infra.org
DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', 'noah-infra.org')

def get_security_config(domain=DEFAULT_DOMAIN):
    """Get security configuration for Helm and Ansible"""
    age_dir = Path("Age")
    certs_dir = Path("Certificates")
    
    return {
        'secrets': {
            'age': {
                'enabled': age_dir.exists(),
                'key_path': str(age_dir / "noah.key") if age_dir.exists() else None,
                'public_key_path': str(age_dir / "noah.pub") if age_dir.exists() else None
            },
            'sops': {
                'enabled': Path(".sops.yaml").exists(),
                'config_path': ".sops.yaml"
            }
        },
        'certificates': {
            'enabled': certs_dir.exists(),
            'domain': domain,
            'ca_cert_path': str(certs_dir / "ca.crt") if certs_dir.exists() else None,
            'ca_key_path': str(certs_dir / "ca.key") if certs_dir.exists() else None,
            'wildcard_cert_path': str(certs_dir / f"*.{domain}.crt") if certs_dir.exists() else None,
            'wildcard_key_path': str(certs_dir / f"*.{domain}.key") if certs_dir.exists() else None
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
    if service == 'samba4':
        base_values.update({
            'samba': {
                'domain': domain.upper().replace('.', '_'),
                'realm': domain.upper(),
                'adminPassword': {
                    'secretName': 'samba4-admin-secret',
                    'secretKey': 'password'
                }
            }
        })
    elif service == 'authentik':
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
                'hosts': [f"auth.{domain}"],
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
    if service == 'samba4':
        ansible_vars.update({
            'samba_realm': domain.upper(),
            'samba_domain': domain.upper().replace('.', '_'),
            'create_admin_secret': True,
            'admin_secret_name': 'samba4-admin-secret'
        })
    elif service == 'authentik':
        ansible_vars.update({
            'create_db_secrets': True,
            'postgresql_secret_name': 'authentik-postgresql',
            'redis_secret_name': 'authentik-redis',
            'app_secret_name': 'authentik-secret',
            'ldap_integration': True,
            'ldap_base_dn': f"dc={',dc='.join(domain.split('.'))}"
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
    if not age_dir.exists() or not any(age_dir.glob("*.key")):
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
    
    # First ensure no existing cluster exists by running destroy playbook
    click.echo(f"[VERBOSE] Ensuring no existing cluster exists...")
    click.echo(f"[VERBOSE] Running cluster cleanup: cluster-destroy.yml")
    ctx.obj['ansible'].run_playbook('cluster-destroy.yml', {
        'cluster_name': name,
        'cleanup_secrets': True,
        'cleanup_certificates': True,
        'security_config': security_config
    })
    click.echo(f"[VERBOSE] Cluster cleanup completed")
    
    # Regenerate certificates for the new deployment
    click.echo(f"[VERBOSE] Regenerating TLS certificates for new deployment...")
    ctx.obj['secrets'].generate_tls_certificates(domain)
    
    # Update security config after regeneration
    security_config = get_security_config(domain)
    
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
def certificates(ctx):
    """Manage TLS certificates"""
    pass

@certificates.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for TLS certificates')
@click.option('--force', is_flag=True, help='Force regeneration of existing certificates')
@click.pass_context
def generate(ctx, domain, force):
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

@cli.group()
@click.pass_context
def deploy(ctx):
    """Deploy services to Kubernetes"""
    pass

@deploy.command()
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.pass_context
def samba4(ctx, namespace, domain):
    """Deploy Samba4 Active Directory"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)
    
    click.echo(f"[VERBOSE] Starting Samba4 deployment process...")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"[VERBOSE] Domain: {domain}")
    
    # Generate secrets for Samba4 before deployment
    click.echo(f"[VERBOSE] Generating secrets for Samba4...")
    ctx.obj['secrets'].generate_service_secrets('samba4', namespace)
    
    # Get Ansible variables with security configuration
    ansible_vars = get_ansible_vars_for_service('samba4', namespace, domain)
    
    # Deploy Samba4 with secrets
    click.echo(f"Deploying Samba4 to namespace {namespace}")
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-samba4.yml")
    ctx.obj['ansible'].run_playbook('deploy-samba4.yml', ansible_vars)
    
    # Get Helm values with security configuration
    helm_values = get_helm_values_for_service('samba4', namespace, domain)
    
    # Deploy Helm chart with generated configuration
    click.echo(f"[VERBOSE] Deploying Helm chart: samba4 with security configuration")
    ctx.obj['helm'].deploy_chart('samba4', namespace, values=helm_values)

@deploy.command()
@click.option('--namespace', default='identity', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.pass_context
def authentik(ctx, namespace, domain):
    """Deploy Authentik for SSO"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)
    
    click.echo(f"[VERBOSE] Starting Authentik deployment process...")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    click.echo(f"[VERBOSE] Domain: {domain}")
    
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
    
    # Generate secrets for Authentik before deployment
    click.echo(f"[VERBOSE] Generating secrets for Authentik...")
    ctx.obj['secrets'].generate_service_secrets('authentik', namespace)
    
    # Get Ansible variables with security configuration
    ansible_vars = get_ansible_vars_for_service('authentik', namespace, domain)
    
    # Deploy Authentik with secrets
    click.echo(f"Deploying Authentik to namespace {namespace}")
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-authentik.yml")
    ctx.obj['ansible'].run_playbook('deploy-authentik.yml', ansible_vars)
    
    # Get Helm values with security configuration
    helm_values = get_helm_values_for_service('authentik', namespace, domain)
    
    # Deploy Helm chart with generated configuration
    click.echo(f"[VERBOSE] Deploying Helm chart: authentik with security configuration")
    ctx.obj['helm'].deploy_chart('authentik', namespace, values=helm_values)

@deploy.command()
@click.option('--namespace', default='kube-system', help='Kubernetes namespace')
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for service')
@click.pass_context
def cilium(ctx, namespace, domain):
    """Deploy Cilium CNI with SSO integration"""
    # Ensure security is initialized
    ensure_security_initialized(ctx)
    
    click.echo(f"[VERBOSE] Starting Cilium deployment process...")
    click.echo(f"[VERBOSE] Namespace: {namespace}")
    
    # Generate secrets for Cilium if needed
    click.echo(f"[VERBOSE] Generating secrets for Cilium...")
    ctx.obj['secrets'].generate_service_secrets('cilium', namespace)
    
    # Get Ansible variables with security configuration
    ansible_vars = get_ansible_vars_for_service('cilium', namespace, domain)
    
    click.echo(f"Deploying Cilium to namespace {namespace}")
    click.echo(f"[VERBOSE] Running Ansible playbook: deploy-cilium.yml")
    ctx.obj['ansible'].run_playbook('deploy-cilium.yml', ansible_vars)
    
    # Get Helm values with security configuration
    helm_values = get_helm_values_for_service('cilium', namespace, domain)
    
    # Deploy Helm chart with generated configuration
    click.echo(f"[VERBOSE] Deploying Helm chart: cilium with security configuration")
    ctx.obj['helm'].deploy_chart('cilium', namespace, values=helm_values)

@deploy.command()
@click.option('--domain', default=DEFAULT_DOMAIN, help='Domain for services')
@click.option('--config-file', type=click.Path(exists=False), help='Export configuration to file')
@click.pass_context
def all(ctx, domain, config_file):
    """Deploy complete stack (Samba4, Authentik, Cilium)"""
    # Ensure security is initialized before any deployment
    ensure_security_initialized(ctx)
    
    click.echo("[VERBOSE] Starting complete NOAH stack deployment...")
    click.echo(f"[VERBOSE] Using domain: {domain}")
    
    # Export configuration if requested
    if config_file:
        click.echo(f"[VERBOSE] Exporting configuration to {config_file}")
        full_config = {
            'domain': domain,
            'security': get_security_config(domain),
            'services': {
                'samba4': {
                    'helm_values': get_helm_values_for_service('samba4', 'identity', domain),
                    'ansible_vars': get_ansible_vars_for_service('samba4', 'identity', domain)
                },
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
    
    click.echo("Deploying complete NOAH stack...")
    
    click.echo("[VERBOSE] Step 1: Deploying Samba4...")
    ctx.invoke(samba4, domain=domain)
    click.echo("Waiting for Samba4 to be ready...")
    click.echo("[VERBOSE] Checking Samba4 deployment status...")
    ctx.obj['cluster'].wait_for_deployment('samba4', 'identity')
    
    click.echo("[VERBOSE] Step 2: Deploying Authentik...")
    ctx.invoke(authentik, domain=domain)
    click.echo("Waiting for Authentik to be ready...")
    click.echo("[VERBOSE] Checking Authentik deployment status...")
    ctx.obj['cluster'].wait_for_deployment('authentik', 'identity')
    
    click.echo("[VERBOSE] Step 3: Deploying Cilium...")
    ctx.invoke(cilium, domain=domain)
    click.echo("NOAH stack deployment complete!")
    click.echo("[VERBOSE] All components successfully deployed!")
    click.echo(f"[VERBOSE] Services available at: https://*.{domain}")

@cli.group()
@click.pass_context
def setup(ctx):
    """Setup and initialize NOAH environment"""
    pass

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
    if age_dir.exists() and any(age_dir.glob("*.key")):
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
