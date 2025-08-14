#!/usr/bin/env python3
"""
NOAH TLS Secrets Updater
Update TLS secrets in SOPS-encrypted configuration
"""

import os
import tempfile
import subprocess
import yaml
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()


class TLSSecretsUpdater:
    """Update TLS certificates in SOPS-encrypted secrets file"""
    
    def __init__(self, cert_dir: str = "./certs", secrets_file: str = "ansible/vars/secrets.yml"):
        self.cert_dir = Path(cert_dir)
        self.secrets_file = Path(secrets_file)
        self.cert_file = self.cert_dir / "tls.crt"
        self.key_file = self.cert_dir / "tls.key"
    
    def check_certificates_exist(self) -> bool:
        """Check if certificate files exist"""
        if not self.cert_file.exists():
            console.print(f"[red]❌ Certificate file not found: {self.cert_file}[/red]")
            return False
        
        if not self.key_file.exists():
            console.print(f"[red]❌ Private key file not found: {self.key_file}[/red]")
            return False
        
        console.print("✅ Certificate files found")
        return True
    
    def check_sops_available(self) -> bool:
        """Check if SOPS is available"""
        try:
            result = subprocess.run(["sops", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                console.print("✅ SOPS is available")
                return True
            else:
                console.print("[red]❌ SOPS is not available or not working[/red]")
                return False
        except FileNotFoundError:
            console.print("[red]❌ SOPS is not installed[/red]")
            console.print("Install SOPS: https://github.com/mozilla/sops#download")
            return False
    
    def read_certificates(self) -> tuple[str, str]:
        """Read certificate and key files"""
        console.print("📖 Reading certificate files...")
        
        with open(self.cert_file, 'r') as f:
            cert_content = f.read()
        
        with open(self.key_file, 'r') as f:
            key_content = f.read()
        
        return cert_content, key_content
    
    def decrypt_secrets_file(self, temp_file: Path) -> bool:
        """Decrypt SOPS-encrypted secrets file"""
        console.print(f"🔓 Decrypting {self.secrets_file}...")
        
        try:
            result = subprocess.run([
                "sops", "-d", str(self.secrets_file)
            ], stdout=open(temp_file, 'w'), stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Failed to decrypt secrets file: {result.stderr}[/red]")
                return False
            
            return True
        except Exception as e:
            console.print(f"[red]❌ Error decrypting secrets file: {e}[/red]")
            return False
    
    def update_yaml_secrets(self, yaml_file: Path, cert_content: str, key_content: str) -> bool:
        """Update TLS secrets in YAML file"""
        console.print("✏️  Updating TLS secrets in configuration...")
        
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                data = {}
            
            # Update TLS secrets
            data['vault_tls_cert'] = cert_content
            data['vault_tls_key'] = key_content
            
            with open(yaml_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            
            console.print("✅ TLS secrets updated in YAML")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Error updating YAML file: {e}[/red]")
            return False
    
    def encrypt_secrets_file(self, temp_file: Path) -> bool:
        """Encrypt updated secrets file with SOPS"""
        console.print(f"🔐 Encrypting updated secrets file...")
        
        try:
            result = subprocess.run([
                "sops", "-e", str(temp_file)
            ], stdout=open(self.secrets_file, 'w'), stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Failed to encrypt secrets file: {result.stderr}[/red]")
                return False
            
            return True
        except Exception as e:
            console.print(f"[red]❌ Error encrypting secrets file: {e}[/red]")
            return False
    
    def update_secrets(self) -> bool:
        """Update TLS secrets in SOPS-encrypted file"""
        try:
            console.print(Panel.fit(
                f"🔐 Updating TLS Secrets\nSecrets file: {self.secrets_file}",
                title="NOAH TLS Secrets Updater"
            ))
            
            # Check prerequisites
            if not self.check_certificates_exist():
                console.print(
                    "\n[yellow]💡 Run: [bold cyan]python script/generate_certificates.py"
                    "[/bold cyan] first[/yellow]")
                return False
            
            if not self.check_sops_available():
                return False
            
            # Read certificates
            cert_content, key_content = self.read_certificates()
            
            # Create temporary file for decrypted content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_f:
                temp_file = Path(temp_f.name)
            
            try:
                # Decrypt secrets file
                if not self.decrypt_secrets_file(temp_file):
                    return False
                
                # Update YAML with TLS secrets
                if not self.update_yaml_secrets(temp_file, cert_content, key_content):
                    return False
                
                # Copy updated file back and encrypt in place
                console.print("🔐 Re-encrypting secrets file...")
                
                # Copy temp file to original location
                import shutil
                shutil.copy2(temp_file, self.secrets_file)
                
                # Encrypt in place
                result = subprocess.run([
                    "sops", "-e", "-i", str(self.secrets_file)
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    console.print(f"[red]❌ Failed to encrypt secrets file: {result.stderr}[/red]")
                    return False
                
                console.print("\n✅ [bold green]TLS secrets updated successfully![/bold green]")
                console.print("🚀 You can now run: [bold cyan]./noah.py deploy[/bold cyan]")
                
                return True
                
            finally:
                # Clean up temporary file
                if temp_file.exists():
                    temp_file.unlink()
            
        except Exception as e:
            console.print(f"[red]❌ TLS secrets update failed: {e}[/red]")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update TLS secrets in SOPS-encrypted configuration")
    parser.add_argument("--cert-dir", default="./certs", 
                       help="Certificate directory")
    parser.add_argument("--secrets-file", default="ansible/vars/secrets.yml", 
                       help="SOPS-encrypted secrets file")
    
    args = parser.parse_args()
    
    updater = TLSSecretsUpdater(
        cert_dir=args.cert_dir,
        secrets_file=args.secrets_file
    )
    
    success = updater.update_secrets()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
