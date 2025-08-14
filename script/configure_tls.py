#!/usr/bin/env python3
"""
NOAH TLS Configuration Helper
Interactive TLS configuration for NOAH platform
"""

import yaml
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()


class TLSConfigurator:
    """Interactive TLS configuration for NOAH platform"""
    
    def __init__(self, global_config: str = "ansible/vars/global.yml", 
                 secrets_file: str = "ansible/vars/secrets.yml"):
        self.global_config_path = Path(global_config)
        self.secrets_file_path = Path(secrets_file)
    
    def load_global_config(self) -> dict:
        """Load global configuration"""
        try:
            with open(self.global_config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            console.print(f"[red]❌ Global config file not found: {self.global_config_path}[/red]")
            return {}
        except Exception as e:
            console.print(f"[red]❌ Error loading global config: {e}[/red]")
            return {}
    
    def save_global_config(self, config: dict) -> bool:
        """Save global configuration"""
        try:
            with open(self.global_config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            return True
        except Exception as e:
            console.print(f"[red]❌ Error saving global config: {e}[/red]")
            return False
    
    def show_current_config(self, config: dict):
        """Display current TLS configuration"""
        table = Table(title="Current TLS Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        tls_settings = {
            'tls_mode': config.get('tls_mode', 'Not set'),
            'cert_manager_enabled': config.get('cert_manager_enabled', 'Not set'),
            'domain_name': config.get('domain_name', 'Not set'),
            'letsencrypt_email': config.get('letsencrypt_email', 'Not set')
        }
        
        for key, value in tls_settings.items():
            table.add_row(key, str(value))
        
        console.print(table)
    
    def configure_self_signed(self, config: dict) -> bool:
        """Configure self-signed certificates"""
        console.print("\n🔧 [bold yellow]Configuring self-signed certificates...[/bold yellow]")
        
        # Update configuration
        config['tls_mode'] = 'manual'
        config['cert_manager_enabled'] = False
        
        if not self.save_global_config(config):
            return False
        
        console.print("📋 Configuration updated for self-signed certificates")
        
        # Generate certificates
        console.print("🔐 Generating self-signed certificates...")
        try:
            result = subprocess.run([
                "python", "script/generate_certificates.py"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Certificate generation failed: {result.stderr}[/red]")
                return False
            
            console.print(result.stdout)
        except Exception as e:
            console.print(f"[red]❌ Error running certificate generator: {e}[/red]")
            return False
        
        # Update secrets
        console.print("🔐 Updating SOPS secrets...")
        try:
            result = subprocess.run([
                "python", "script/update_tls_secrets.py"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print(f"[red]❌ Secrets update failed: {result.stderr}[/red]")
                return False
            
            console.print(result.stdout)
        except Exception as e:
            console.print(f"[red]❌ Error updating secrets: {e}[/red]")
            return False
        
        console.print("\n✅ [bold green]Self-signed certificates configured![/bold green]")
        console.print("⚠️  [yellow]Your browser will show security warnings[/yellow]")
        console.print("🚀 Run: [bold cyan]./noah.py deploy[/bold cyan]")
        
        return True
    
    def configure_letsencrypt(self, config: dict) -> bool:
        """Configure Let's Encrypt certificates"""
        console.print("\n🌐 [bold green]Configuring Let's Encrypt certificates...[/bold green]")
        
        # Get domain and email
        domain = Prompt.ask("Enter your domain name (e.g., noah.example.com)")
        email = Prompt.ask("Enter your email for Let's Encrypt notifications")
        
        if not domain or not email:
            console.print("[red]❌ Domain and email are required[/red]")
            return False
        
        # Update configuration
        config['tls_mode'] = 'letsencrypt'
        config['cert_manager_enabled'] = True
        config['domain_name'] = domain
        config['letsencrypt_email'] = email
        
        if not self.save_global_config(config):
            return False
        
        console.print("\n✅ [bold green]Let's Encrypt certificates configured![/bold green]")
        console.print(f"📋 Domain: [cyan]{domain}[/cyan]")
        console.print(f"📧 Email: [cyan]{email}[/cyan]")
        console.print(
            "\n⚠️  [yellow]Make sure your domain points to your cluster's external IP[/yellow]")
        console.print("🚀 Run: [bold cyan]./noah.py deploy[/bold cyan]")
        
        return True
    
    def configure_manual(self, config: dict) -> bool:
        """Configure manual certificate management"""
        console.print("\n🏢 [bold blue]Manual certificate management selected...[/bold blue]")
        
        # Update configuration
        config['tls_mode'] = 'manual'
        config['cert_manager_enabled'] = False
        
        if not self.save_global_config(config):
            return False
        
        console.print("\n📋 [bold yellow]Manual steps required:[/bold yellow]")
        console.print("   1. Place your certificate in: [cyan]./certs/tls.crt[/cyan]")
        console.print("   2. Place your private key in: [cyan]./certs/tls.key[/cyan]")
        console.print("   3. Run: [bold cyan]python script/update_tls_secrets.py[/bold cyan]")
        console.print("   4. Run: [bold cyan]./noah.py deploy[/bold cyan]")
        
        return True
    
    def run_interactive_config(self) -> bool:
        """Run interactive TLS configuration"""
        console.print(Panel.fit(
            "🔐 NOAH TLS Configuration Helper",
            title="TLS Configuration"
        ))
        
        # Load current configuration
        config = self.load_global_config()
        
        # Show current configuration
        console.print("\n📋 Current Configuration:")
        self.show_current_config(config)
        
        # Show options
        console.print("\n🛠️  Select your TLS configuration:")
        console.print("1) Self-signed certificates (Development/Testing)")
        console.print("2) Let's Encrypt automatic certificates (Production)")
        console.print("3) Manual certificate management (Enterprise)")
        
        choice = Prompt.ask("Choose option", choices=["1", "2", "3"])
        
        if choice == "1":
            return self.configure_self_signed(config)
        elif choice == "2":
            return self.configure_letsencrypt(config)
        elif choice == "3":
            return self.configure_manual(config)
        else:
            console.print("[red]❌ Invalid option[/red]")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Interactive TLS configuration for NOAH platform")
    parser.add_argument("--global-config", default="ansible/vars/global.yml", 
                       help="Global configuration file")
    parser.add_argument("--secrets-file", default="ansible/vars/secrets.yml", 
                       help="SOPS-encrypted secrets file")
    
    args = parser.parse_args()
    
    configurator = TLSConfigurator(
        global_config=args.global_config,
        secrets_file=args.secrets_file
    )
    
    success = configurator.run_interactive_config()
    
    if success:
        console.print(
            f"\n🔍 [bold]Updated configuration saved to:[/bold] "
            f"[cyan]{args.global_config}[/cyan]")
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
