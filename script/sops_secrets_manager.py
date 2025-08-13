#!/usr/bin/env python3
"""
NOAH secrets manager with SOPS
Usage: python3 sops_secrets_manager.py {edit|view|rotate|deploy}
"""

import argparse
import subprocess
import sys
import tempfile
import secrets
import string
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
import shutil

console = Console()


class SOPSSecretsManager:
    """Manage NOAH secrets with SOPS encryption"""

    def __init__(self):
        self.secrets_file = Path("ansible/vars/secrets.yml")
        self.project_root = Path.cwd()

    def check_dependencies(self) -> bool:
        """Check if required tools are available"""
        required_tools = ["sops", "helm"]
        missing_tools = []

        for tool in required_tools:
            if not shutil.which(tool):
                missing_tools.append(tool)

        if missing_tools:
            console.print(f"[red]❌ Missing required tools: {', '.join(missing_tools)}[/red]")
            return False

        return True

    def generate_password(self, length: int = 32) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def edit_secrets(self) -> bool:
        """Edit secrets file with SOPS"""
        console.print("[yellow]📝 Opening secrets editor with SOPS...[/yellow]")

        if not self.secrets_file.exists():
            console.print("[yellow]⚠️  Secrets file doesn't exist. Creating template...[/yellow]")
            self.create_secrets_template()

        try:
            result = subprocess.run(["sops", str(self.secrets_file)], cwd=self.project_root)
            if result.returncode == 0:
                console.print("[green]✅ Secrets edited successfully[/green]")
                return True
            else:
                console.print("[red]❌ Failed to edit secrets[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error editing secrets: {e}[/red]")
            return False

    def view_secrets(self) -> bool:
        """View decrypted secrets"""
        console.print("[yellow]👁️  Viewing secrets...[/yellow]")

        if not self.secrets_file.exists():
            console.print("[red]❌ Secrets file not found[/red]")
            return False

        try:
            result = subprocess.run([
                "sops", "--decrypt", str(self.secrets_file)
            ], cwd=self.project_root)

            if result.returncode == 0:
                return True
            else:
                console.print("[red]❌ Failed to decrypt secrets[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error viewing secrets: {e}[/red]")
            return False

    def rotate_secrets(self) -> bool:
        """Rotate passwords in secrets file"""
        console.print("[yellow]🔄 Rotating secrets...[/yellow]")

        if not self.secrets_file.exists():
            console.print("[red]❌ Secrets file not found[/red]")
            return False

        if not Confirm.ask("This will generate new passwords. Continue?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return False

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.yml', delete=False) as temp_file:
                temp_path = Path(temp_file.name)

                # Decrypt to temporary file
                decrypt_result = subprocess.run([
                    "sops", "--decrypt", str(self.secrets_file)
                ], stdout=temp_file, text=True, cwd=self.project_root)

                if decrypt_result.returncode != 0:
                    console.print("[red]❌ Failed to decrypt secrets for rotation[/red]")
                    temp_path.unlink()
                    return False

            # Read and modify content
            with open(temp_path, 'r') as f:
                content = f.read()

            # Generate new passwords
            new_postgres_password = self.generate_password(32)
            new_keycloak_password = self.generate_password(24)

            # Replace passwords (simple regex replacement)
            import re
            content = re.sub(
                r'vault_postgres_password:\s*"[^"]*"',
                f'vault_postgres_password: "{new_postgres_password}"',
                content
            )
            content = re.sub(
                r'vault_keycloak_admin_password:\s*"[^"]*"',
                f'vault_keycloak_admin_password: "{new_keycloak_password}"',
                content
            )

            # Write back to temp file
            with open(temp_path, 'w') as f:
                f.write(content)

            # Re-encrypt
            encrypt_result = subprocess.run([
                "sops", "--encrypt", str(temp_path)
            ], capture_output=True, text=True, cwd=self.project_root)

            if encrypt_result.returncode == 0:
                # Write encrypted content back to secrets file
                with open(self.secrets_file, 'w') as f:
                    f.write(encrypt_result.stdout)

                console.print("[green]✅ Secrets rotation completed[/green]")
                console.print("[blue]📋 Rotated passwords:[/blue]")
                console.print("[blue]   - PostgreSQL admin password[/blue]")
                console.print("[blue]   - Keycloak admin password[/blue]")

                # Clean up
                temp_path.unlink()
                return True
            else:
                console.print("[red]❌ Failed to re-encrypt secrets[/red]")
                temp_path.unlink()
                return False

        except Exception as e:
            console.print(f"[red]❌ Error during rotation: {e}[/red]")
            return False

    def deploy_with_secrets(self) -> bool:
        """Deploy using secrets with helm-secrets"""
        console.print("[yellow]🚀 Deploying with secrets...[/yellow]")

        if not shutil.which("helm"):
            console.print("[red]❌ Helm not found[/red]")
            return False

        # Check if helm-secrets plugin is installed
        try:
            result = subprocess.run([
                "helm", "plugin", "list"
            ], capture_output=True, text=True)

            if "secrets" in result.stdout:
                console.print("[green]✅ helm-secrets plugin found[/green]")

                # Deploy with helm-secrets
                deploy_result = subprocess.run([
                    "helm", "secrets", "upgrade", "--install",
                    "noah", "./helm/noah-chart",
                    "-f", str(self.secrets_file)
                ], cwd=self.project_root)

                if deploy_result.returncode == 0:
                    console.print("[green]✅ Deployment with secrets completed[/green]")
                    return True
                else:
                    console.print("[red]❌ Deployment failed[/red]")
                    return False
            else:
                console.print("[yellow]⚠️  helm-secrets plugin not installed[/yellow]")
                console.print(
                    "[blue]Install with: helm plugin install https://github.com/jkroepke/helm-secrets[/blue]")
                return False

        except Exception as e:
            console.print(f"[red]❌ Error during deployment: {e}[/red]")
            return False

    def create_secrets_template(self) -> bool:
        """Create a basic secrets template"""
        console.print("[yellow]📝 Creating secrets template...[/yellow]")

        # Ensure directory exists
        self.secrets_file.parent.mkdir(parents=True, exist_ok=True)

        template_content = """# NOAH Secrets - Managed by SOPS
# DO NOT commit this file unencrypted!

# Database passwords
vault_postgres_password: "changeme-postgres-password"
vault_redis_password: "changeme-redis-password"

# Application passwords
vault_keycloak_admin_password: "changeme-keycloak-admin"
vault_gitlab_root_password: "changeme-gitlab-root"
vault_nextcloud_admin_password: "changeme-nextcloud-admin"

# API keys and tokens
vault_monitoring_api_key: "changeme-monitoring-key"
vault_backup_encryption_key: "changeme-backup-key"

# SSL/TLS certificates (if using custom certs)
# vault_tls_cert: |
#   -----BEGIN CERTIFICATE-----
#   ... your certificate here ...
#   -----END CERTIFICATE-----
# vault_tls_key: |
#   -----BEGIN PRIVATE KEY-----
#   ... your private key here ...
#   -----END PRIVATE KEY-----
"""

        try:
            with open(self.secrets_file, 'w') as f:
                f.write(template_content)

            console.print(f"[green]✅ Secrets template created: {self.secrets_file}[/green]")
            console.print(
                "[yellow]⚠️  Remember to encrypt this file with SOPS before committing![/yellow]")
            console.print("[blue]Run: sops --encrypt --in-place ansible/vars/secrets.yml[/blue]")
            return True

        except Exception as e:
            console.print(f"[red]❌ Error creating template: {e}[/red]")
            return False

    def encrypt_secrets(self) -> bool:
        """Encrypt secrets file in place"""
        console.print("[yellow]🔐 Encrypting secrets file...[/yellow]")

        if not self.secrets_file.exists():
            console.print("[red]❌ Secrets file not found[/red]")
            return False

        try:
            result = subprocess.run([
                "sops", "--encrypt", "--in-place", str(self.secrets_file)
            ], cwd=self.project_root)

            if result.returncode == 0:
                console.print("[green]✅ Secrets file encrypted[/green]")
                return True
            else:
                console.print("[red]❌ Failed to encrypt secrets[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error encrypting secrets: {e}[/red]")
            return False

    def decrypt_secrets(self) -> bool:
        """Decrypt secrets file in place (WARNING: leaves plaintext)"""
        console.print("[yellow]🔓 Decrypting secrets file...[/yellow]")
        console.print("[red]⚠️  WARNING: File will be in plaintext![/red]")

        if not Confirm.ask("Continue with decryption?"):
            console.print("[yellow]Operation cancelled[/yellow]")
            return False

        if not self.secrets_file.exists():
            console.print("[red]❌ Secrets file not found[/red]")
            return False

        try:
            result = subprocess.run([
                "sops", "--decrypt", "--in-place", str(self.secrets_file)
            ], cwd=self.project_root)

            if result.returncode == 0:
                console.print("[green]✅ Secrets file decrypted[/green]")
                console.print("[red]⚠️  Remember to encrypt before committing![/red]")
                return True
            else:
                console.print("[red]❌ Failed to decrypt secrets[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error decrypting secrets: {e}[/red]")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="NOAH secrets manager with SOPS")
    parser.add_argument("command", choices=[
        "edit", "view", "rotate", "deploy", "encrypt", "decrypt", "template"
    ], help="Command to execute")

    args = parser.parse_args()

    manager = SOPSSecretsManager()

    # Check dependencies for most commands
    if args.command in ["edit", "view", "rotate", "deploy", "encrypt", "decrypt"]:
        if not manager.check_dependencies():
            sys.exit(1)

    success = False

    if args.command == "edit":
        success = manager.edit_secrets()
    elif args.command == "view":
        success = manager.view_secrets()
    elif args.command == "rotate":
        success = manager.rotate_secrets()
    elif args.command == "deploy":
        success = manager.deploy_with_secrets()
    elif args.command == "encrypt":
        success = manager.encrypt_secrets()
    elif args.command == "decrypt":
        success = manager.decrypt_secrets()
    elif args.command == "template":
        success = manager.create_secrets_template()
    else:
        console.print(f"[red]❌ Unknown command: {args.command}[/red]")
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
