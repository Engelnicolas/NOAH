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
        domain = os.environ.get('NOAH_DOMAIN', '')
    
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


def _config_enc_readable(config_path: Path, age_key_file: Path) -> bool:
    """Return True if config_path exists and can be decrypted with the current age key."""
    if not config_path.exists():
        return False
    import subprocess
    import os
    env = os.environ.copy()
    env['SOPS_AGE_KEY_FILE'] = str(age_key_file)
    result = subprocess.run(
        ['sops', '--decrypt', str(config_path)],
        capture_output=True, env=env
    )
    return result.returncode == 0


def _create_fresh_config_enc(config_path: Path, age_key_file: Path, domain: str):
    """Create a new config.enc.yaml encrypted with the current age key."""
    import subprocess
    import os
    import secrets
    import tempfile
    import shutil
    import yaml  # type: ignore

    # Pull authentik secret_key from canonical store if available
    authentik_secret_key = secrets.token_urlsafe(38)
    try:
        from Scripts.security.canonical_store import get_canonical_store
        store = get_canonical_store()
        stored = store.get_secret('authentik', 'secret_key')
        if stored:
            authentik_secret_key = stored
    except Exception:
        pass

    config_data = {
        'noah': {'version': '0.0.4', 'domain': domain},
        'kubernetes': {
            'cluster_name': 'noah-cluster',
            'namespace_identity': 'authentik',
            'namespace_network': 'kube-system',
            'api_version': '1.32',
        },
        'authentik': {'secret_key': authentik_secret_key},
        'certificates': {'ca_key_password': secrets.token_urlsafe(24)},
        'secrets': {'encryption_key': secrets.token_hex(32)},
        'paths': {'secrets_dir': 'Scripts/Secrets'},
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    # Write plaintext to a temp file that matches the .enc.yaml pattern so .sops.yaml applies
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.enc.yaml', dir=str(config_path.parent),
        delete=False, prefix='noah_cfg_tmp_'
    ) as tmp:
        yaml.dump(config_data, tmp, default_flow_style=False, allow_unicode=True)
        tmp_path = Path(tmp.name)

    env = os.environ.copy()
    env['SOPS_AGE_KEY_FILE'] = str(age_key_file)
    result = subprocess.run(
        ['sops', '--encrypt', '--in-place', str(tmp_path)],
        capture_output=True, env=env
    )
    if result.returncode != 0:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"SOPS encryption failed: {result.stderr.decode().strip()}")

    shutil.move(str(tmp_path), str(config_path))


def ensure_security_initialized(ctx):
    """Ensure SOPS/Age keys and certificates are initialized"""
    # Get default domain from environment or fallback
    import os
    DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', '')

    age_dir = Path("Age")
    age_key_file = age_dir / "keys.txt"

    # Check if Age keys exist
    if not age_dir.exists() or not (any(age_dir.glob("*.key")) or age_key_file.exists()):
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

    # Check if config.enc.yaml is readable with the current age key; recreate if not
    config_enc = Path("Config/config.enc.yaml")
    config_was_created = False
    if not _config_enc_readable(config_enc, age_key_file):
        if config_enc.exists():
            click.echo("[VERBOSE] config.enc.yaml exists but cannot be decrypted with current age key — recreating...")
        else:
            click.echo("[VERBOSE] config.enc.yaml not found — creating fresh configuration...")
        try:
            _create_fresh_config_enc(config_enc, age_key_file, DEFAULT_DOMAIN)
            click.echo("[VERBOSE] config.enc.yaml created and encrypted with current age key")
            config_was_created = True
        except Exception as exc:
            click.echo(f"[WARNING] Could not create config.enc.yaml: {exc}")

    # Reload config into os.environ if it was just created (startup load was skipped)
    if config_was_created and config_enc.exists():
        from Scripts.security.secure_env_loader import SecureEnvLoader
        SecureEnvLoader().load_secure_env(config_enc)

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
    
    DEFAULT_DOMAIN = os.environ.get('NOAH_DOMAIN', '')
    
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