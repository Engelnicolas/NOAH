#!/usr/bin/env python3
"""
NOAH CLI - Python Implementation Preview
Network Operations & Automation Hub

This is a preview of how noah.sh could be converted to Python
while maintaining full functionality and improving maintainability.
"""

import click
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

console = Console()

class NoahConfig:
    """Configuration management for NOAH platform"""
    
    def __init__(self, config_path: Path = Path(".noah_config")):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load configuration from file or defaults"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return dict(line.strip().split('=', 1) for line in f if '=' in line)
        return {"INFRASTRUCTURE_TYPE": "kubernetes"}
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            for key, value in self.config.items():
                f.write(f"{key}={value}\n")

class AnsibleRunner:
    """Ansible playbook execution wrapper"""
    
    def __init__(self, config: NoahConfig):
        self.config = config
        self.inventory_path = Path("ansible/inventory/mycluster/hosts.yaml")
        self.playbooks_dir = Path("ansible/playbooks")
    
    def run_playbook(self, playbook: str, dry_run: bool = False, verbose: bool = False) -> bool:
        """Execute ansible playbook with progress tracking"""
        playbook_path = self.playbooks_dir / playbook
        
        if not playbook_path.exists():
            console.print(f"[red]❌ Playbook not found: {playbook_path}[/red]")
            return False
        
        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i", str(self.inventory_path),
        ]
        
        if dry_run:
            cmd.append("--check")
        if verbose:
            cmd.append("-vv")
        
        console.print(f"[blue]🚀 Executing playbook: {playbook}[/blue]")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Running {playbook}...", total=None)
                
                result = subprocess.run(
                    cmd,
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout
                )
                
                progress.remove_task(task)
            
            if result.returncode == 0:
                console.print(f"[green]✅ Playbook {playbook} completed successfully[/green]")
                if verbose:
                    console.print(result.stdout)
                return True
            else:
                console.print(f"[red]❌ Playbook {playbook} failed[/red]")
                console.print(f"[red]Error: {result.stderr}[/red]")
                return False
                
        except subprocess.TimeoutExpired:
            console.print(f"[red]❌ Playbook {playbook} timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error running playbook {playbook}: {e}[/red]")
            return False

class KubernetesManager:
    """Kubernetes cluster management"""
    
    @staticmethod
    def check_connectivity() -> bool:
        """Check if kubectl can connect to cluster"""
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info", "--request-timeout=10s"],
                capture_output=True,
                text=True,
                timeout=15
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    @staticmethod
    def get_cluster_status() -> Dict:
        """Get comprehensive cluster status"""
        status = {
            "nodes": [],
            "pods": [],
            "services": [],
            "ingress": []
        }
        
        try:
            # Get nodes
            result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                nodes_data = json.loads(result.stdout)
                status["nodes"] = [
                    {
                        "name": node["metadata"]["name"],
                        "status": next(
                            cond["type"] for cond in node["status"]["conditions"]
                            if cond["status"] == "True" and cond["type"] == "Ready"
                        ) if "conditions" in node["status"] else "Unknown"
                    }
                    for node in nodes_data.get("items", [])
                ]
        except Exception:
            pass
        
        return status

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--dry-run', is_flag=True, help='Simulate actions without execution')
@click.pass_context
def cli(ctx, verbose, dry_run):
    """
    NOAH CLI - Network Operations & Automation Hub
    
    Modern Python-based infrastructure management tool
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    ctx.obj['config'] = NoahConfig()
    
    # Display banner
    if not ctx.resilient_parsing:
        banner = Panel(
            Text("NOAH CLI - Network Operations & Automation Hub\nPython Implementation", 
                 style="bold blue", justify="center"),
            style="blue",
            padding=(1, 2)
        )
        console.print(banner)

@cli.command()
@click.option('--infrastructure-type', 
              type=click.Choice(['kubernetes', 'docker']),
              help='Infrastructure deployment type')
@click.pass_context
def init(ctx, infrastructure_type):
    """Initialize NOAH environment"""
    config = ctx.obj['config']
    dry_run = ctx.obj['dry_run']
    verbose = ctx.obj['verbose']
    
    console.print("[yellow]🔄 Initializing NOAH environment...[/yellow]")
    
    # Configure infrastructure type
    if infrastructure_type:
        config.config['INFRASTRUCTURE_TYPE'] = infrastructure_type
    elif 'INFRASTRUCTURE_TYPE' not in config.config:
        infrastructure_type = click.prompt(
            "Choose infrastructure type",
            type=click.Choice(['kubernetes', 'docker']),
            default='kubernetes'
        )
        config.config['INFRASTRUCTURE_TYPE'] = infrastructure_type
    
    if not dry_run:
        config.save_config()
    
    console.print(f"[green]✅ Infrastructure type set to: {config.config['INFRASTRUCTURE_TYPE']}[/green]")
    
    # Initialize Ansible environment
    ansible_runner = AnsibleRunner(config)
    
    console.print("[blue]📦 Installing Ansible collections...[/blue]")
    if not dry_run:
        subprocess.run([
            "ansible-galaxy", "collection", "install", 
            "-r", "ansible/requirements.yml", "--force"
        ])
    
    console.print("[green]✅ NOAH environment initialized successfully[/green]")

@cli.command()
@click.option('--profile', default='prod', help='Deployment profile (dev/prod)')
@click.option('--skip-provision', is_flag=True, help='Skip infrastructure provisioning')
@click.pass_context
def deploy(ctx, profile, skip_provision):
    """Deploy NOAH platform"""
    config = ctx.obj['config']
    dry_run = ctx.obj['dry_run']
    verbose = ctx.obj['verbose']
    
    infrastructure_type = config.config.get('INFRASTRUCTURE_TYPE', 'kubernetes')
    
    console.print(f"[yellow]🚀 Deploying NOAH platform...[/yellow]")
    console.print(f"[blue]Infrastructure: {infrastructure_type}[/blue]")
    console.print(f"[blue]Profile: {profile}[/blue]")
    
    ansible_runner = AnsibleRunner(config)
    
    if infrastructure_type == 'kubernetes':
        playbooks = []
        
        if not skip_provision:
            playbooks.append('01-provision.yml')
        
        playbooks.extend([
            '02-install-k8s.yml',
            '03-configure-cluster.yml', 
            '04-deploy-apps.yml'
        ])
        
        for i, playbook in enumerate(playbooks, 1):
            console.print(f"[cyan]Step {i}/{len(playbooks)}: {playbook}[/cyan]")
            
            if not ansible_runner.run_playbook(playbook, dry_run, verbose):
                console.print(f"[red]❌ Deployment failed at step {i}[/red]")
                sys.exit(1)
    
    elif infrastructure_type == 'docker':
        console.print("[blue]🐳 Deploying with Docker Compose...[/blue]")
        if not dry_run:
            subprocess.run(["docker-compose", "up", "-d"])
    
    console.print("[green]🎉 NOAH platform deployed successfully![/green]")

@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed status')
@click.option('--all-namespaces', is_flag=True, help='Show all namespaces')
@click.pass_context
def status(ctx, detailed, all_namespaces):
    """Check NOAH platform status"""
    config = ctx.obj['config']
    infrastructure_type = config.config.get('INFRASTRUCTURE_TYPE', 'kubernetes')
    
    console.print("[yellow]🔍 Checking NOAH platform status...[/yellow]")
    
    if infrastructure_type == 'kubernetes':
        k8s_manager = KubernetesManager()
        
        if not k8s_manager.check_connectivity():
            console.print("[red]❌ Cannot connect to Kubernetes cluster[/red]")
            sys.exit(1)
        
        console.print("[green]✅ Kubernetes cluster connection OK[/green]")
        
        status_data = k8s_manager.get_cluster_status()
        
        # Display nodes
        console.print("\n[bold]Cluster Nodes:[/bold]")
        for node in status_data['nodes']:
            status_icon = "✅" if node['status'] == "Ready" else "❌"
            console.print(f"  {status_icon} {node['name']}: {node['status']}")
        
        if detailed:
            # Show more detailed information
            console.print("\n[bold]NOAH Services:[/bold]")
            try:
                result = subprocess.run(
                    ["kubectl", "get", "pods", "-n", "noah", "-o", "wide"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    console.print(result.stdout)
                else:
                    console.print("[yellow]No NOAH namespace found[/yellow]")
            except Exception:
                console.print("[red]Error getting pod status[/red]")
    
    elif infrastructure_type == 'docker':
        console.print("[blue]🐳 Checking Docker Compose status...[/blue]")
        try:
            result = subprocess.run(
                ["docker-compose", "ps"],
                capture_output=True, text=True, timeout=30
            )
            console.print(result.stdout)
        except Exception:
            console.print("[red]Error checking Docker status[/red]")

@cli.group()
def secrets():
    """Manage NOAH secrets with SOPS"""
    pass

@secrets.command()
@click.pass_context
def edit(ctx):
    """Edit secrets file with SOPS"""
    console.print("[yellow]📝 Opening secrets editor...[/yellow]")
    subprocess.run(["sops", "ansible/vars/secrets.yml"])

@secrets.command()
@click.pass_context
def view(ctx):
    """View decrypted secrets"""
    console.print("[yellow]👁️  Viewing secrets...[/yellow]")
    subprocess.run(["sops", "--decrypt", "ansible/vars/secrets.yml"])

if __name__ == '__main__':
    cli()
