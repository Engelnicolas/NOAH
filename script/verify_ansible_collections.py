#!/usr/bin/env python3
"""
Verify Ansible collections and modules are properly installed
This script helps diagnose collection installation issues in CI/CD
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


class AnsibleCollectionVerifier:
    """Verify Ansible collections and modules installation"""

    def __init__(self):
        self.errors = 0

    def check_ansible_version(self) -> bool:
        """Check Ansible version"""
        console.print("[yellow]Checking Ansible version...[/yellow]")

        try:
            result = subprocess.run(["ansible", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                console.print(f"[green]Ansible version: {version_line}[/green]")
                return True
            else:
                console.print("[red]❌ Could not get Ansible version[/red]")
                self.errors += 1
                return False
        except FileNotFoundError:
            console.print("[red]❌ Ansible not found[/red]")
            self.errors += 1
            return False

    def check_critical_collections(self) -> bool:
        """Check if critical collections are installed"""
        console.print("\n[yellow]📦 Checking critical collections...[/yellow]")

        collections = [
            "kubernetes.core",
            "community.general",
            "community.kubernetes",
            "ansible.posix",
            "community.crypto"
        ]

        collection_status = []

        for collection in collections:
            try:
                result = subprocess.run([
                    "ansible-galaxy", "collection", "list", collection
                ], capture_output=True, text=True)

                if result.returncode == 0 and collection in result.stdout:
                    # Try to extract version from output
                    lines = result.stdout.split('\n')
                    version = "installed"
                    for line in lines:
                        if collection in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                version = parts[1]
                            break

                    console.print(f"[green]✅ {collection} {version}[/green]")
                    collection_status.append((collection, version, True))
                else:
                    console.print(f"[red]❌ {collection} NOT FOUND[/red]")
                    collection_status.append((collection, "missing", False))
                    self.errors += 1

            except Exception as e:
                console.print(f"[red]❌ Error checking {collection}: {e}[/red]")
                collection_status.append((collection, "error", False))
                self.errors += 1

        return self.errors == 0

    def test_critical_modules(self) -> bool:
        """Test critical modules"""
        console.print("\n[yellow]🔧 Testing critical modules...[/yellow]")

        modules = [
            "kubernetes.core.k8s",
            "community.kubernetes.helm",
            "community.general.docker_container",
            "ansible.posix.mount"
        ]

        for module in modules:
            try:
                result = subprocess.run([
                    "ansible-doc", module
                ], capture_output=True, text=True, timeout=15)

                if result.returncode == 0:
                    console.print(f"[green]✅ {module} module available[/green]")
                else:
                    console.print(f"[red]❌ {module} module NOT FOUND[/red]")
                    self.errors += 1

            except subprocess.TimeoutExpired:
                console.print(f"[red]❌ {module} module check timed out[/red]")
                self.errors += 1
            except Exception as e:
                console.print(f"[red]❌ Error checking {module}: {e}[/red]")
                self.errors += 1

        return self.errors == 0

    def test_playbook_syntax(self) -> bool:
        """Test playbook syntax"""
        console.print("\n[yellow]🎯 Testing playbook syntax...[/yellow]")

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
            playbook_name = Path(playbook_path).name

            if full_path.exists():
                try:
                    result = subprocess.run([
                        "ansible-playbook",
                        "--syntax-check",
                        str(full_path)
                    ], capture_output=True, text=True, cwd=project_root)

                    if result.returncode == 0:
                        console.print(f"[green]✅ {playbook_name} syntax valid[/green]")
                    else:
                        console.print(f"[red]❌ {playbook_name} syntax ERROR[/red]")
                        if result.stderr:
                            console.print(f"[red]   Error: {result.stderr.strip()}[/red]")
                        self.errors += 1

                except Exception as e:
                    console.print(f"[red]❌ {playbook_name} check failed: {e}[/red]")
                    self.errors += 1
            else:
                console.print(f"[yellow]⚠️  {playbook_name} not found (skipping)[/yellow]")

        return self.errors == 0

    def generate_summary_table(self) -> None:
        """Generate a summary table of the verification results"""
        table = Table(title="Ansible Collection Verification Summary")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="white")

        if self.errors == 0:
            table.add_row("Overall Status", "✅ PASSED", "All collections and modules ready")
        else:
            table.add_row("Overall Status", "❌ FAILED", f"{self.errors} errors found")

        console.print(table)

    def provide_remediation_instructions(self) -> None:
        """Provide instructions to fix issues if any errors were found"""
        if self.errors > 0:
            console.print("\n[yellow]🔧 Remediation Instructions:[/yellow]")
            console.print("[cyan]To fix missing collections, run:[/cyan]")
            console.print(
                "[white]  ansible-galaxy collection install -r ansible/requirements.yml --force[/white]")
            console.print("\n[cyan]To update all collections, run:[/cyan]")
            console.print(
                "[white]  ansible-galaxy collection install -r ansible/requirements.yml --force --upgrade[/white]")

    def verify(self) -> bool:
        """Main verification method"""
        console.print("[bold blue]🔍 NOAH Ansible Collection Verification[/bold blue]")
        console.print("=======================================")

        success = True

        # Run all checks
        if not self.check_ansible_version():
            success = False

        if not self.check_critical_collections():
            success = False

        if not self.test_critical_modules():
            success = False

        if not self.test_playbook_syntax():
            success = False

        # Generate summary
        self.generate_summary_table()

        if success:
            console.print(
                "\n[green]🎉 All checks passed! Ansible collections and modules are ready.[/green]")
            console.print("[green]Ready to run NOAH deployment playbooks.[/green]")
        else:
            console.print(f"\n[red]❌ Verification failed with {self.errors} errors.[/red]")
            self.provide_remediation_instructions()

        return success


def main():
    """Main entry point"""
    verifier = AnsibleCollectionVerifier()
    success = verifier.verify()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
