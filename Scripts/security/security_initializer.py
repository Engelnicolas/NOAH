#!/usr/bin/env python3
"""
NOAH Security Initializer
Handles initialization of security infrastructure including Age keys, SOPS, and TLS certificates
"""

import click
import json
import os
from pathlib import Path
from Scripts.utils.paths import get_noah_paths  # reuse centralized implementation


def get_security_config(domain=None):
    """Get security configuration for Helm and Ansible"""
    if domain is None:
        domain = os.environ.get('NOAH_DOMAIN', 'noah-infra.com')
    
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


def ensure_security_initialized(ctx):
    """Ensure SOPS/Age keys and certificates are initialized"""
    # Get default domain from environment or fallback
    import os
    DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', 'noah-infra.com')
    
    age_dir = Path("Age")
    sops_config = Path(".sops.yaml")
    
    # Check if Age keys exist
    if not age_dir.exists() or not (any(age_dir.glob("*.key")) or (age_dir / "keys.txt").exists()):
        click.echo("[VERBOSE] No Age keys found. Auto-generating SOPS/Age keys...")
        click.echo("Initializing security infrastructure...")
        
        # Create Age directory if it doesn't exist
        age_dir.mkdir(exist_ok=True)
        
        # Initialize Age keys and configure SOPS
        ctx.obj['secrets'].initialize_encryption()
        
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
        security_config = get_security_config(DEFAULT_DOMAIN)
        click.echo("[DEBUG] Security Configuration:")
        click.echo(json.dumps(security_config, indent=2))


def initialize_security_environment():
    """Initialize security environment without click context (for standalone use)"""
    import os
    from pathlib import Path
    
    DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', 'noah-infra.com')
    
    age_dir = Path("Age")
    certs_dir = Path("Certificates")
    
    # Create directories if they don't exist
    age_dir.mkdir(exist_ok=True)
    certs_dir.mkdir(exist_ok=True)
    
    # Initialize security manager for standalone operations
    from ..security_manager import NoahSecurityManager
    from ..config_loader import ConfigLoader
    
    config = ConfigLoader()
    security_manager = NoahSecurityManager(config)
    
    # Check and initialize Age keys
    if not (any(age_dir.glob("*.key")) or (age_dir / "keys.txt").exists()):
        print("[INFO] Initializing Age encryption keys...")
        security_manager.initialize_encryption()
        print("[INFO] Age keys generated successfully")
    else:
        print("[INFO] Age keys found")
    
    # Check and generate TLS certificates
    if not any(certs_dir.glob("*.crt")):
        print(f"[INFO] Generating TLS certificates for {DEFAULT_DOMAIN}...")
        security_manager.generate_tls_certificates(DEFAULT_DOMAIN)
        print(f"[INFO] TLS certificates generated for {DEFAULT_DOMAIN}")
    else:
        print("[INFO] TLS certificates found")
    
    return security_manager