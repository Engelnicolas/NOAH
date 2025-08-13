#!/usr/bin/env python3
"""
SSH configuration script for NOAH deployment
This script safely configures SSH authentication with proper error handling
"""

import os
import subprocess
import sys
from pathlib import Path
from rich.console import Console

console = Console()


class SSHConfigurator:
    """Handle SSH configuration for NOAH deployment"""

    def __init__(self):
        self.ssh_dir = Path.home() / ".ssh"
        self.private_key_path = self.ssh_dir / "id_rsa"
        self.known_hosts_path = self.ssh_dir / "known_hosts"

    def setup_ssh_directory(self):
        """Create and configure SSH directory with proper permissions"""
        console.print("[yellow]🔧 Configuring SSH authentication...[/yellow]")

        # Create SSH directory
        self.ssh_dir.mkdir(mode=0o700, exist_ok=True)
        console.print(f"[green]✅ SSH directory created: {self.ssh_dir}[/green]")

    def configure_private_key(self):
        """Configure SSH private key from environment variable"""
        ssh_private_key = os.getenv("SSH_PRIVATE_KEY")

        if ssh_private_key:
            with open(self.private_key_path, 'w') as f:
                f.write(ssh_private_key)

            # Set proper permissions
            self.private_key_path.chmod(0o600)
            console.print("[green]✅ SSH private key configured[/green]")
            return True
        else:
            console.print(
                "[yellow]⚠️  Warning: SSH_PRIVATE_KEY environment variable not set[/yellow]")
            console.print("[yellow]   SSH authentication may not work properly[/yellow]")
            return False

    def add_host_keys(self, hosts: str, host_type: str):
        """Add host keys safely to known_hosts"""
        if not hosts:
            console.print(f"[yellow]⚠️  {host_type} not specified, skipping host key scan[/yellow]")
            return

        console.print(f"[blue]🔍 Adding {host_type} to known_hosts: {hosts}[/blue]")

        # Handle multiple hosts separated by spaces, commas, or newlines
        host_list = []
        for separator in [',', ' ', '\n']:
            hosts = hosts.replace(separator, '\n')

        for host in hosts.split('\n'):
            host = host.strip()
            if host:
                host_list.append(host)

        for host in host_list:
            try:
                # Run ssh-keyscan to get host key
                result = subprocess.run(
                    ["ssh-keyscan", "-H", host],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and result.stdout:
                    # Append to known_hosts
                    with open(self.known_hosts_path, 'a') as f:
                        f.write(result.stdout)
                    console.print(f"[green]  ✅ Added {host} to known_hosts[/green]")
                else:
                    console.print(
                        f"[yellow]  ⚠️  Warning: Could not scan {host_type} host: {host}[/yellow]")

            except subprocess.TimeoutExpired:
                console.print(
                    f"[yellow]  ⚠️  Warning: Timeout scanning {host_type} host: {host}[/yellow]")
            except Exception as e:
                console.print(f"[red]  ❌ Error scanning {host_type} host {host}: {e}[/red]")

    def set_known_hosts_permissions(self):
        """Set proper permissions for known_hosts file"""
        if self.known_hosts_path.exists():
            try:
                self.known_hosts_path.chmod(0o644)
            except Exception:
                pass  # Ignore permission errors

    def display_summary(self):
        """Display configuration summary without revealing sensitive info"""
        console.print("[blue]📋 SSH Configuration Summary:[/blue]")

        # Check private key
        if self.private_key_path.exists():
            console.print("[green]   - Private key: ✅ Configured[/green]")
        else:
            console.print("[red]   - Private key: ❌ Not configured[/red]")

        # Check known hosts
        if self.known_hosts_path.exists():
            try:
                with open(self.known_hosts_path, 'r') as f:
                    host_count = len([line for line in f if line.strip()])
                console.print(f"[green]   - Known hosts: {host_count} entries[/green]")
            except Exception:
                console.print("[yellow]   - Known hosts: Error reading file[/yellow]")
        else:
            console.print("[yellow]   - Known hosts: 0 entries[/yellow]")

    def configure(self):
        """Main configuration method"""
        try:
            self.setup_ssh_directory()
            self.configure_private_key()

            # Add master host to known_hosts
            master_host = os.getenv("MASTER_HOST", "")
            self.add_host_keys(master_host, "master host")

            # Add worker hosts to known_hosts
            worker_hosts = os.getenv("WORKER_HOSTS", "")
            self.add_host_keys(worker_hosts, "worker hosts")

            # Set proper permissions
            self.set_known_hosts_permissions()

            console.print("[green]✅ SSH configuration completed[/green]")
            self.display_summary()

            return True

        except Exception as e:
            console.print(f"[red]❌ Error during SSH configuration: {e}[/red]")
            return False


def main():
    """Main entry point"""
    configurator = SSHConfigurator()
    success = configurator.configure()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
