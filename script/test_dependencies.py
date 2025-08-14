#!/usr/bin/env python3
"""
Test script to verify Ansible collections and dependencies
"""

import importlib
import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class DependencyTester:
    """Test NOAH infrastructure dependencies"""

    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def test_python_dependencies(self) -> bool:
        """Test Python installation and dependencies"""
        console.print("\n[yellow]Testing Python dependencies...[/yellow]")

        # Test Python 3
        try:
            result = subprocess.run(["python3", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                console.print(f"[green]✅ Python 3 is available: {result.stdout.strip()}[/green]")
            else:
                console.print("[red]❌ Python 3 not found[/red]")
                self.errors += 1
                return False
        except FileNotFoundError:
            console.print("[red]❌ Python 3 not found[/red]")
            self.errors += 1
            return False

        # Test required packages
        required_packages = ["ansible", "requests", "kubernetes", "yaml", "rich", "click"]

        for package in required_packages:
            try:
                importlib.import_module(package)
                console.print(f"[green]✅ {package} is installed[/green]")
            except ImportError:
                console.print(
                    f"[yellow]⚠️  {package} not found - install with: pip install -r script/requirements.txt[/yellow]")
                self.warnings += 1

        # Test system kubernetes package for Ansible
        try:
            # Try to import kubernetes using the system Python path
            result = subprocess.run(
                ["/usr/bin/python3", "-c", "import kubernetes; print('System kubernetes package available')"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                console.print("[green]✅ System kubernetes package (python3-kubernetes) is installed[/green]")
            else:
                console.print(
                    "[yellow]⚠️  System kubernetes package not found - install with: sudo apt install python3-kubernetes[/yellow]")
                console.print("[yellow]   This is required for Ansible kubernetes.core modules[/yellow]")
                self.warnings += 1
        except Exception:
            console.print(
                "[yellow]⚠️  Could not check system kubernetes package - install with: sudo apt install python3-kubernetes[/yellow]")
            self.warnings += 1

        return True

    def test_ansible_installation(self) -> bool:
        """Test Ansible installation"""
        console.print("\n[yellow]Testing Ansible installation...[/yellow]")

        try:
            result = subprocess.run(["ansible", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                console.print(f"[green]✅ Ansible is available: {version_line}[/green]")
                return True
            else:
                console.print("[red]❌ Ansible not found[/red]")
                self.errors += 1
                return False
        except FileNotFoundError:
            console.print("[red]❌ Ansible not found[/red]")
            self.errors += 1
            return False

    def test_ansible_collections(self) -> bool:
        """Test Ansible collections"""
        console.print("\n[yellow]Testing Ansible collections...[/yellow]")

        required_collections = [
            "community.general",
            "kubernetes.core",
            "community.kubernetes",
            "ansible.posix",
            "community.crypto"
        ]

        for collection in required_collections:
            try:
                result = subprocess.run(
                    ["ansible-galaxy", "collection", "list", collection],
                    capture_output=True, text=True
                )
                if result.returncode == 0 and collection in result.stdout:
                    console.print(f"[green]✅ {collection} is installed[/green]")
                else:
                    console.print(
                        f"[yellow]⚠️  {collection} not found - install with: ansible-galaxy collection install -r ansible/requirements.yml --force[/yellow]")
                    self.warnings += 1
            except Exception:
                console.print(f"[yellow]⚠️  Could not check {collection}[/yellow]")
                self.warnings += 1

        return True

    def test_ansible_modules(self) -> bool:
        """Test specific Ansible modules"""
        console.print("\n[yellow]Testing specific Ansible modules...[/yellow]")

        modules = [
            "kubernetes.core.k8s",
            "community.kubernetes.helm",
            "community.general.docker_container"
        ]

        for module in modules:
            try:
                result = subprocess.run(
                    ["ansible-doc", module],
                    capture_output=True, text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    console.print(f"[green]✅ {module} module is available[/green]")
                else:
                    console.print(f"[yellow]⚠️  {module} module not found[/yellow]")
                    self.warnings += 1
            except subprocess.TimeoutExpired:
                console.print(f"[yellow]⚠️  {module} module check timed out[/yellow]")
                self.warnings += 1
            except Exception:
                console.print(f"[yellow]⚠️  Could not check {module} module[/yellow]")
                self.warnings += 1

        return True

    def test_playbook_syntax(self) -> bool:
        """Test playbook syntax"""
        console.print("\n[yellow]Testing playbook syntax...[/yellow]")

        # Change to project root
        project_root = Path(__file__).parent.parent

        playbooks = [
            "ansible/playbooks/01-provision.yml",
            "ansible/playbooks/02-install-k8s.yml",
            "ansible/playbooks/03-configure-cluster.yml",
            "ansible/playbooks/04-deploy-apps.yml",
            "ansible/playbooks/05-verify-deployment.yml"
        ]

        for playbook_path in playbooks:
            full_path = project_root / playbook_path
            if full_path.exists():
                try:
                    result = subprocess.run([
                        "ansible-playbook",
                        "--syntax-check",
                        str(full_path),
                        "-i", str(project_root / "ansible/inventory/mycluster/hosts.yaml")
                    ], capture_output=True, text=True, cwd=project_root)

                    if result.returncode == 0:
                        console.print(f"[green]✅ {playbook_path} syntax is valid[/green]")
                    else:
                        console.print(f"[yellow]⚠️  {playbook_path} syntax check failed[/yellow]")
                        self.warnings += 1
                except Exception as e:
                    console.print(f"[yellow]⚠️  Could not check {playbook_path}: {e}[/yellow]")
                    self.warnings += 1
            else:
                console.print(f"[red]❌ {playbook_path} not found[/red]")
                self.errors += 1

        return True

    def test_inventory_configuration(self) -> bool:
        """Test inventory configuration"""
        console.print("\n[yellow]Testing inventory configuration...[/yellow]")

        project_root = Path(__file__).parent.parent
        inventory_path = project_root / "ansible/inventory/mycluster/hosts.yaml"

        if inventory_path.exists():
            console.print("[green]✅ Inventory file exists[/green]")

            try:
                result = subprocess.run([
                    "ansible-inventory",
                    "--list",
                    "-i", str(inventory_path)
                ], capture_output=True, text=True, cwd=project_root)

                if result.returncode == 0:
                    console.print("[green]✅ Inventory syntax is valid[/green]")
                else:
                    console.print("[yellow]⚠️  Inventory syntax check failed[/yellow]")
                    self.warnings += 1
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not validate inventory: {e}[/yellow]")
                self.warnings += 1
        else:
            console.print("[red]❌ Inventory file not found[/red]")
            self.errors += 1

        return True

    def test_ssh_configuration_script(self) -> bool:
        """Test SSH configuration script"""
        console.print("\n[yellow]Testing SSH configuration script...[/yellow]")

        ssh_script = Path(__file__).parent / "configure_ssh.py"

        if ssh_script.exists():
            console.print("[green]✅ SSH configuration script exists[/green]")

            if ssh_script.stat().st_mode & 0o111:  # Check if executable
                console.print("[green]✅ SSH configuration script is executable[/green]")
            else:
                console.print("[yellow]⚠️  SSH configuration script is not executable[/yellow]")
                self.warnings += 1
        else:
            console.print("[red]❌ SSH configuration script not found[/red]")
            self.errors += 1

        return True

    def display_summary(self):
        """Display test summary"""
        console.print("\n[blue]📊 Test Summary[/blue]")

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Category", style="cyan")
        table.add_column("Status", style="green")

        if self.errors == 0 and self.warnings == 0:
            table.add_row("Overall Status", "✅ All tests passed")
        elif self.errors == 0:
            table.add_row("Overall Status", f"⚠️  {self.warnings} warnings")
        else:
            table.add_row("Overall Status", f"❌ {self.errors} errors, {self.warnings} warnings")

        table.add_row("Errors", str(self.errors))
        table.add_row("Warnings", str(self.warnings))

        console.print(table)

        if self.warnings > 0:
            console.print("\n[yellow]To fix warnings, install missing dependencies:[/yellow]")
            console.print("[cyan]  pip install -r script/requirements.txt[/cyan]")
            console.print(
                "[cyan]  ansible-galaxy collection install -r ansible/requirements.yml --force[/cyan]")

    def run_all_tests(self) -> bool:
        """Run all tests"""
        console.print("[bold blue]🔍 NOAH Infrastructure Test Script[/bold blue]")
        console.print("==================================")

        tests = [
            self.test_python_dependencies,
            self.test_ansible_installation,
            self.test_ansible_collections,
            self.test_ansible_modules,
            self.test_playbook_syntax,
            self.test_inventory_configuration,
            self.test_ssh_configuration_script
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for test in tests:
                task = progress.add_task(f"Running {test.__name__}...", total=1)
                test()
                progress.update(task, advance=1)

        self.display_summary()

        console.print("\n[green]🎉 Test completed![/green]")

        return self.errors == 0


def main():
    """Main entry point"""
    tester = DependencyTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
