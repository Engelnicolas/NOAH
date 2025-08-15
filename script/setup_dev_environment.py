#!/usr/bin/env python3
"""
NOAH Development Environment Setup
Automated setup for dev environment with Let's Encrypt certificates and SOPS secrets
"""

import os
import sys
import subprocess
import tempfile
import shutil
import secrets
import string
import yaml
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

console = Console()


class DevEnvironmentSetup:
    """Setup development environment for NOAH platform"""
    
    def __init__(self, domain: str = "noah.local"):
        self.domain = domain
        self.project_root = Path.cwd()
        self.cert_dir = self.project_root / "certs"
        self.age_dir = self.project_root / "age"
        self.ansible_vars_dir = self.project_root / "ansible" / "vars"
        
        # NOAH platform subdomains for Let's Encrypt style certificates
        self.subdomains = [
            self.domain,
            f"*.{self.domain}",
            f"keycloak.{self.domain}",
            f"grafana.{self.domain}",
            f"gitlab.{self.domain}",
            f"mattermost.{self.domain}",
            f"nextcloud.{self.domain}",
            f"prometheus.{self.domain}",
            f"alertmanager.{self.domain}",
            f"wazuh.{self.domain}",
            f"samba.{self.domain}",
            f"openedr.{self.domain}"
        ]
    
    def check_dependencies(self) -> bool:
        """Check if required tools are available"""
        required_tools = ["age", "sops"]
        missing_tools = []
        
        for tool in required_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            console.print(f"[red]❌ Missing required tools: {', '.join(missing_tools)}[/red]")
            console.print("[yellow]Please install missing tools:[/yellow]")
            for tool in missing_tools:
                if tool == "age":
                    console.print("  - Age: https://github.com/FiloSottile/age/releases")
                elif tool == "sops":
                    console.print("  - SOPS: https://github.com/mozilla/sops/releases")
            return False
        
        return True
    
    def generate_age_key(self) -> tuple[str, str]:
        """Generate new Age encryption key pair"""
        console.print("🔑 Generating Age encryption key...")
        
        # Create age directory
        self.age_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate Age key
        result = subprocess.run(
            ["age-keygen"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception(f"Failed to generate Age key: {result.stderr}")
        
        lines = result.stdout.strip().split('\n')
        private_key = None
        public_key = None
        
        for line in lines:
            if line.startswith('# public key: '):
                public_key = line.replace('# public key: ', '')
            elif line.startswith('AGE-SECRET-KEY-'):
                private_key = line
        
        if not private_key or not public_key:
            raise Exception("Failed to parse Age key generation output")
        
        # Save private key
        key_file = self.age_dir / "keys.txt"
        with open(key_file, 'w') as f:
            f.write(f"# created: {datetime.datetime.now().isoformat()}\n")
            f.write(f"# public key: {public_key}\n")
            f.write(f"{private_key}\n")
        
        # Set secure permissions
        os.chmod(key_file, 0o600)
        
        console.print(f"✅ Age key saved to: {key_file}")
        console.print(f"📋 Public key: {public_key}")
        
        return private_key, public_key
    
    def update_sops_config(self, public_key: str):
        """Update SOPS configuration with new Age key"""
        console.print("📝 Updating SOPS configuration...")
        
        sops_config = {
            'creation_rules': [
                {
                    'path_regex': 'ansible/vars/secrets\\.yml$',
                    'age': public_key
                },
                {
                    'path_regex': 'helm/.*/secrets\\.ya?ml$',
                    'age': public_key
                },
                {
                    'path_regex': 'manifests/.*-secrets?\\.ya?ml$',
                    'age': public_key
                },
                {
                    'path_regex': '\\.env\\.(encrypted|sops)$',
                    'age': public_key
                }
            ]
        }
        
        sops_file = self.project_root / ".sops.yaml"
        with open(sops_file, 'w') as f:
            f.write(f"# Configuration SOPS pour NOAH\n")
            f.write(f"# Génération automatique - {datetime.datetime.now().strftime('%c')}\n\n")
            yaml.dump(sops_config, f, default_flow_style=False, indent=2)
        
        console.print(f"✅ SOPS configuration updated: {sops_file}")
    
    def generate_dev_certificates(self) -> bool:
        """Generate Let's Encrypt style certificates for development"""
        console.print("🔐 Generating development certificates (Let's Encrypt style)...")
        
        try:
            # Create certificate directory
            self.cert_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate RSA private key (2048 bits for Let's Encrypt compatibility)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate subject (Let's Encrypt style)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Let's Encrypt"),
                x509.NameAttribute(NameOID.COMMON_NAME, "R3"),  # Let's Encrypt intermediate
            ])
            
            # Create Subject Alternative Names
            san_list = [x509.DNSName(subdomain) for subdomain in self.subdomains]
            
            # Build certificate (90 days validity like Let's Encrypt)
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.now(datetime.timezone.utc)
            ).not_valid_after(
                datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=90)
            ).add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=True,
            ).sign(private_key, hashes.SHA256())
            
            # Save private key
            key_path = self.cert_dir / "tls.key"
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save certificate
            cert_path = self.cert_dir / "tls.crt"
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Set secure permissions
            os.chmod(key_path, 0o600)
            os.chmod(cert_path, 0o644)
            
            console.print(f"✅ Certificate files generated:")
            console.print(f"   Private Key: {key_path}")
            console.print(f"   Certificate: {cert_path}")
            console.print(f"   Valid for: 90 days (Let's Encrypt style)")
            console.print(f"   Domains: {', '.join(self.subdomains[:3])}... (+{len(self.subdomains)-3} more)")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Certificate generation failed: {e}[/red]")
            return False
    
    def generate_secure_password(self, length: int = 32) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_secrets_template(self) -> dict:
        """Create secrets template with generated passwords"""
        console.print("🔐 Generating secure passwords for services...")
        
        secrets_data = {
            # PostgreSQL secrets
            'postgresql': {
                'password': self.generate_secure_password(),
                'postgres_password': self.generate_secure_password(),
                'replication_password': self.generate_secure_password()
            },
            
            # Keycloak secrets
            'keycloak': {
                'admin_password': self.generate_secure_password(),
                'db_password': self.generate_secure_password(),
                'client_secret': self.generate_secure_password(64)
            },
            
            # GitLab secrets
            'gitlab': {
                'root_password': self.generate_secure_password(),
                'db_password': self.generate_secure_password(),
                'redis_password': self.generate_secure_password(),
                'secret_key_base': self.generate_secure_password(128),
                'otp_key_base': self.generate_secure_password(128),
                'db_key_base': self.generate_secure_password(128),
                'runner_registration_token': self.generate_secure_password(64)
            },
            
            # Nextcloud secrets
            'nextcloud': {
                'admin_password': self.generate_secure_password(),
                'db_password': self.generate_secure_password(),
                'redis_password': self.generate_secure_password()
            },
            
            # Mattermost secrets
            'mattermost': {
                'db_password': self.generate_secure_password(),
                'file_settings_public_link_salt': self.generate_secure_password(64),
                'email_settings_smtp_password': self.generate_secure_password()
            },
            
            # Grafana secrets
            'grafana': {
                'admin_password': self.generate_secure_password(),
                'secret_key': self.generate_secure_password(64),
                'db_password': self.generate_secure_password()
            },
            
            # Prometheus secrets
            'prometheus': {
                'basic_auth_password': self.generate_secure_password()
            },
            
            # Wazuh secrets
            'wazuh': {
                'api_password': self.generate_secure_password(),
                'cluster_key': self.generate_secure_password(64),
                'indexer_password': self.generate_secure_password(),
                'dashboard_password': self.generate_secure_password()
            },
            
            # OAuth2 Proxy secrets
            'oauth2_proxy': {
                'client_secret': self.generate_secure_password(64),
                'cookie_secret': self.generate_secure_password(64)
            },
            
            # Samba4 secrets
            'samba4': {
                'admin_password': self.generate_secure_password(),
                'bind_password': self.generate_secure_password()
            },
            
            # TLS secrets (base64 encoded certificate content)
            'tls': {
                'cert': self._encode_cert_file('tls.crt'),
                'key': self._encode_cert_file('tls.key')
            }
        }
        
        return secrets_data
    
    def _encode_cert_file(self, filename: str) -> str:
        """Encode certificate file content as base64"""
        import base64
        
        cert_file = self.cert_dir / filename
        if cert_file.exists():
            with open(cert_file, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return ""
    
    def create_encrypted_secrets(self, secrets_data: dict):
        """Create SOPS-encrypted secrets file"""
        console.print("🔒 Creating SOPS-encrypted secrets file...")
        
        # Ensure ansible vars directory exists
        self.ansible_vars_dir.mkdir(parents=True, exist_ok=True)
        
        # Create secrets file path
        secrets_file = self.ansible_vars_dir / "secrets.yml"
        
        # Write secrets to file first (unencrypted)
        with open(secrets_file, 'w') as f:
            f.write("# NOAH Platform Secrets\n")
            f.write(f"# Generated: {datetime.datetime.now().isoformat()}\n")
            f.write("# This file is encrypted with SOPS\n\n")
            yaml.dump(secrets_data, f, default_flow_style=False, indent=2)
        
        # Encrypt with SOPS
        env = os.environ.copy()
        env['SOPS_AGE_KEY_FILE'] = str(self.age_dir / "keys.txt")
        
        result = subprocess.run(
            ["sops", "--encrypt", "--in-place", str(secrets_file)],
            env=env,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        if result.returncode != 0:
            console.print(f"[red]SOPS error: {result.stderr}[/red]")
            console.print(f"[yellow]Trying to encrypt: {secrets_file}[/yellow]")
            console.print(f"[yellow]Working directory: {self.project_root}[/yellow]")
            raise Exception(f"SOPS encryption failed: {result.stderr}")
        
        console.print(f"✅ Encrypted secrets saved to: {secrets_file}")
    
    def setup_noah_config(self):
        """Setup unified NOAH configuration"""
        console.print("⚙️ Setting up unified NOAH configuration...")
        
        # Import NoahConfig from main module
        sys.path.append(str(self.project_root))
        try:
            from noah import NoahConfig
            
            config = NoahConfig()
            config.set_development_mode(self.domain)
            config.save_config()
            
            # Also write environment file for backwards compatibility
            config.write_env_file()
            
            console.print(f"✅ NOAH configuration updated: .noah_config")
            console.print(f"✅ Environment file generated: .env.development")
            
        except ImportError as e:
            # Fallback to manual configuration
            console.print(f"[yellow]Warning: Could not import NoahConfig: {e}[/yellow]")
            console.print("[yellow]Using fallback configuration method[/yellow]")
            self.setup_environment_variables()

    def setup_environment_variables(self):
        """Setup environment variables (fallback method)"""
        console.print("🌍 Setting up environment variables...")
        
        # Create .env file for development
        env_file = self.project_root / ".env.dev"
        env_content = f"""# NOAH Development Environment Variables
# Generated: {datetime.datetime.now().isoformat()}

# SOPS Configuration
export SOPS_AGE_KEY_FILE={self.age_dir}/keys.txt

# Domain Configuration
export NOAH_DOMAIN={self.domain}

# Development Mode
export NOAH_ENV=development
export NOAH_DEBUG=true

# Certificate Paths
export NOAH_TLS_CERT={self.cert_dir}/tls.crt
export NOAH_TLS_KEY={self.cert_dir}/tls.key
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        console.print(f"✅ Environment variables saved to: {env_file}")
        console.print("[yellow]💡 To use these variables, run:[/yellow]")
        console.print(f"[cyan]   source {env_file}[/cyan]")
    
    def display_setup_summary(self):
        """Display setup summary and next steps"""
        console.print("\n" + "="*60)
        console.print(Panel.fit(
            "[bold green]🎉 Development Environment Setup Complete![/bold green]\n\n"
            f"[bold]Domain:[/bold] {self.domain}\n"
            f"[bold]Certificates:[/bold] {self.cert_dir}/\n"
            f"[bold]Age Keys:[/bold] {self.age_dir}/\n"
            f"[bold]Encrypted Secrets:[/bold] {self.ansible_vars_dir}/secrets.yml\n\n"
            "[bold cyan]NOAH configured for development by default![/bold cyan]\n\n"
            "[bold cyan]Next Steps:[/bold cyan]\n"
            "1. Source environment: [cyan]source .env.development[/cyan]\n"
            "2. Edit secrets: [cyan]sops ansible/vars/secrets.yml[/cyan]\n"
            "3. Deploy (dev default): [cyan]./noah.py deploy[/cyan]\n"
            "4. Or deploy explicitly: [cyan]./noah.py deploy --profile dev[/cyan]",
            title="🚀 NOAH Dev Environment Ready"
        ))
    
    def run_setup(self) -> bool:
        """Run complete development environment setup"""
        try:
            console.print(Panel.fit(
                f"🔧 Setting up NOAH Development Environment\n"
                f"Domain: {self.domain}\n"
                f"Mode: Development with Let's Encrypt style certificates",
                title="NOAH Dev Setup"
            ))
            
            # Check dependencies
            if not self.check_dependencies():
                return False
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                # Step 1: Generate Age encryption key
                task1 = progress.add_task("Generating Age encryption key...", total=None)
                private_key, public_key = self.generate_age_key()
                progress.update(task1, completed=True)
                
                # Step 2: Update SOPS configuration
                task2 = progress.add_task("Updating SOPS configuration...", total=None)
                self.update_sops_config(public_key)
                progress.update(task2, completed=True)
                
                # Step 3: Generate certificates
                task3 = progress.add_task("Generating Let's Encrypt style certificates...", total=None)
                if not self.generate_dev_certificates():
                    return False
                progress.update(task3, completed=True)
                
                # Step 4: Generate secrets
                task4 = progress.add_task("Generating secure passwords...", total=None)
                secrets_data = self.create_secrets_template()
                progress.update(task4, completed=True)
                
                # Step 5: Encrypt secrets with SOPS
                task5 = progress.add_task("Encrypting secrets with SOPS...", total=None)
                self.create_encrypted_secrets(secrets_data)
                progress.update(task5, completed=True)
                
                # Step 6: Setup unified configuration
                task6 = progress.add_task("Setting up unified NOAH configuration...", total=None)
                self.setup_noah_config()
                progress.update(task6, completed=True)
            
            # Display summary
            self.display_setup_summary()
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Setup failed: {e}[/red]")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Setup NOAH development environment with Let's Encrypt certificates and SOPS"
    )
    parser.add_argument("--domain", default="noah.local", 
                       help="Primary domain name (default: noah.local)")
    parser.add_argument("--force", action="store_true",
                       help="Force regenerate all certificates and keys")
    
    args = parser.parse_args()
    
    # Check if already setup and not forcing
    if not args.force:
        age_keys = Path("age/keys.txt")
        secrets_file = Path("ansible/vars/secrets.yml")
        
        if age_keys.exists() and secrets_file.exists():
            if not Confirm.ask(
                "Development environment appears to be already setup. Continue anyway?",
                default=False
            ):
                console.print("Setup cancelled.")
                return
    
    # Run setup
    setup = DevEnvironmentSetup(domain=args.domain)
    success = setup.run_setup()
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
