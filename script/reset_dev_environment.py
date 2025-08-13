#!/usr/bin/env python3
"""
Reset development environment script for NOAH
This script cleans and reinitializes the NOAH development environment
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
import shutil

console = Console()


class DevEnvironmentResetter:
    """Handle development environment reset operations"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.errors = 0

    def clean_docker_environment(self) -> bool:
        """Clean Docker containers, images, and volumes"""
        console.print("[yellow]🐳 Cleaning Docker environment...[/yellow]")

        if not shutil.which("docker"):
            console.print("[yellow]⚠️  Docker not found, skipping Docker cleanup[/yellow]")
            return True

        try:
            # Stop and remove all containers
            console.print("[blue]Stopping and removing all Docker containers...[/blue]")
            result = subprocess.run([
                "docker", "ps", "-aq"
            ], capture_output=True, text=True)

            if result.stdout.strip():
                subprocess.run(["docker", "stop"] + result.stdout.strip().split('\n'))
                subprocess.run(["docker", "rm"] + result.stdout.strip().split('\n'))
                console.print("[green]✅ Docker containers cleaned[/green]")
            else:
                console.print("[green]✅ No Docker containers to clean[/green]")

            # Clean Docker system
            console.print("[blue]Removing unused Docker images, volumes, and networks...[/blue]")
            result = subprocess.run([
                "docker", "system", "prune", "-af", "--volumes"
            ], capture_output=True, text=True)

            if result.returncode == 0:
                console.print("[green]✅ Docker system cleaned[/green]")
                return True
            else:
                console.print("[red]❌ Failed to clean Docker system[/red]")
                self.errors += 1
                return False

        except Exception as e:
            console.print(f"[red]❌ Error cleaning Docker environment: {e}[/red]")
            self.errors += 1
            return False

    def reset_git_repository(self) -> bool:
        """Reset local Git repository"""
        console.print("[yellow]📦 Resetting local Git repository...[/yellow]")

        if not (self.project_root / ".git").exists():
            console.print("[yellow]⚠️  Not a Git repository, skipping Git reset[/yellow]")
            return True

        # Ask for confirmation
        if not Confirm.ask("This will reset all local changes. Continue?"):
            console.print("[yellow]Git reset cancelled[/yellow]")
            return True

        try:
            # Reset to HEAD
            console.print("[blue]Resetting to HEAD...[/blue]")
            result = subprocess.run([
                "git", "reset", "--hard", "HEAD"
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                console.print(f"[red]❌ Git reset failed: {result.stderr}[/red]")
                self.errors += 1
                return False

            # Clean untracked files
            console.print("[blue]Cleaning untracked files...[/blue]")
            result = subprocess.run([
                "git", "clean", "-fd"
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                console.print(f"[red]❌ Git clean failed: {result.stderr}[/red]")
                self.errors += 1
                return False

            # Pull latest changes
            console.print("[blue]Pulling latest changes...[/blue]")
            result = subprocess.run([
                "git", "pull", "origin", "main"
            ], cwd=self.project_root, capture_output=True, text=True)

            if result.returncode == 0:
                console.print("[green]✅ Git repository reset[/green]")
                return True
            else:
                console.print(f"[yellow]⚠️  Git pull warning: {result.stderr}[/yellow]")
                return True  # Continue even if pull fails

        except Exception as e:
            console.print(f"[red]❌ Error resetting Git repository: {e}[/red]")
            self.errors += 1
            return False

    def reinstall_python_dependencies(self) -> bool:
        """Reinstall Python dependencies"""
        console.print("[yellow]🐍 Reinstalling Python dependencies...[/yellow]")

        requirements_file = self.project_root / "script" / "requirements.txt"

        if not requirements_file.exists():
            console.print(
                "[yellow]⚠️  requirements.txt not found, skipping Python dependencies[/yellow]")
            return True

        try:
            result = subprocess.run([
                "pip", "install", "-r", str(requirements_file)
            ], cwd=self.project_root)

            if result.returncode == 0:
                console.print("[green]✅ Python dependencies reinstalled[/green]")
                return True
            else:
                console.print("[red]❌ Failed to install Python dependencies[/red]")
                self.errors += 1
                return False

        except Exception as e:
            console.print(f"[red]❌ Error installing Python dependencies: {e}[/red]")
            self.errors += 1
            return False

    def install_ansible_collections(self) -> bool:
        """Install Ansible collections"""
        console.print("[yellow]📚 Installing Ansible collections...[/yellow]")

        requirements_file = self.project_root / "ansible" / "requirements.yml"

        if not requirements_file.exists():
            console.print(
                "[yellow]⚠️  ansible/requirements.yml not found, skipping Ansible collections[/yellow]")
            return True

        if not shutil.which("ansible-galaxy"):
            console.print(
                "[yellow]⚠️  ansible-galaxy not found, skipping Ansible collections[/yellow]")
            return True

        try:
            result = subprocess.run([
                "ansible-galaxy", "collection", "install",
                "-r", str(requirements_file), "--force"
            ], cwd=self.project_root)

            if result.returncode == 0:
                console.print("[green]✅ Ansible collections installed[/green]")
                return True
            else:
                console.print("[red]❌ Failed to install Ansible collections[/red]")
                self.errors += 1
                return False

        except Exception as e:
            console.print(f"[red]❌ Error installing Ansible collections: {e}[/red]")
            self.errors += 1
            return False

    def update_helm_dependencies(self) -> bool:
        """Update Helm dependencies"""
        console.print("[yellow]⎈ Updating Helm dependencies...[/yellow]")

        if not shutil.which("helm"):
            console.print("[yellow]⚠️  Helm not found, skipping Helm dependencies[/yellow]")
            return True

        helm_dir = self.project_root / "helm"
        if not helm_dir.exists():
            console.print(
                "[yellow]⚠️  helm directory not found, skipping Helm dependencies[/yellow]")
            return True

        try:
            # Update dependencies for each chart
            for chart_dir in helm_dir.iterdir():
                if chart_dir.is_dir() and (chart_dir / "Chart.yaml").exists():
                    console.print(f"[blue]Updating {chart_dir.name} dependencies...[/blue]")

                    result = subprocess.run([
                        "helm", "dependency", "update", str(chart_dir)
                    ], cwd=self.project_root, capture_output=True, text=True)

                    if result.returncode == 0:
                        console.print(f"[green]✅ {chart_dir.name} dependencies updated[/green]")
                    else:
                        console.print(
                            f"[yellow]⚠️  {chart_dir.name} dependency update failed[/yellow]")

            return True

        except Exception as e:
            console.print(f"[red]❌ Error updating Helm dependencies: {e}[/red]")
            self.errors += 1
            return False

    def reinitialize_noah_environment(self) -> bool:
        """Reinitialize NOAH environment"""
        console.print("[yellow]🚀 Reinitializing NOAH environment...[/yellow]")

        noah_script = self.project_root / "noah.py"

        if noah_script.exists():
            try:
                # Initialize NOAH
                console.print("[blue]Running noah init...[/blue]")
                result = subprocess.run([
                    "python3", str(noah_script), "init"
                ], cwd=self.project_root)

                if result.returncode == 0:
                    console.print("[green]✅ NOAH initialized[/green]")
                else:
                    console.print("[yellow]⚠️  NOAH initialization had warnings[/yellow]")

                return True

            except Exception as e:
                console.print(f"[red]❌ Error initializing NOAH: {e}[/red]")
                self.errors += 1
                return False
        else:
            console.print("[yellow]⚠️  noah.py not found, skipping NOAH initialization[/yellow]")
            return True

    def validate_environment(self) -> bool:
        """Validate the reset environment"""
        console.print("[yellow]🔍 Validating environment...[/yellow]")

        # Check if test dependencies script exists and run it
        test_script = self.project_root / "script" / "test_dependencies.py"

        if test_script.exists():
            try:
                console.print("[blue]Running dependency tests...[/blue]")
                result = subprocess.run([
                    "python3", str(test_script)
                ], cwd=self.project_root)

                if result.returncode == 0:
                    console.print("[green]✅ Environment validation passed[/green]")
                    return True
                else:
                    console.print("[yellow]⚠️  Environment validation had warnings[/yellow]")
                    return True  # Don't fail the reset for validation warnings

            except Exception as e:
                console.print(f"[red]❌ Error validating environment: {e}[/red]")
                return True  # Don't fail the reset for validation errors
        else:
            console.print(
                "[yellow]⚠️  test_dependencies.py not found, skipping validation[/yellow]")
            return True

    def run_act_test(self) -> bool:
        """Run Act test job locally (if available)"""
        console.print("[yellow]🎭 Running CI test job locally...[/yellow]")

        if not shutil.which("act"):
            console.print("[yellow]⚠️  act not found, skipping CI test[/yellow]")
            return True

        github_dir = self.project_root / ".github"
        if not github_dir.exists():
            console.print("[yellow]⚠️  .github directory not found, skipping CI test[/yellow]")
            return True

        try:
            result = subprocess.run([
                "act", "-j", "test",
                "-P", "ubuntu-latest=catthehacker/ubuntu:act-latest"
            ], cwd=self.project_root, timeout=300)  # 5 minute timeout

            if result.returncode == 0:
                console.print("[green]✅ CI test passed[/green]")
            else:
                console.print("[yellow]⚠️  CI test had issues (non-blocking)[/yellow]")

            return True  # Don't fail reset for CI test issues

        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠️  CI test timed out (non-blocking)[/yellow]")
            return True
        except Exception as e:
            console.print(f"[yellow]⚠️  CI test error (non-blocking): {e}[/yellow]")
            return True

    def display_summary(self):
        """Display reset summary"""
        console.print("\n[blue]📊 Reset Summary[/blue]")

        if self.errors == 0:
            console.print("[green]🎉 Development environment reset complete![/green]")
            console.print("[green]All operations completed successfully.[/green]")
        else:
            console.print(
                f"[yellow]⚠️  Development environment reset completed with {self.errors} errors.[/yellow]")
            console.print("[yellow]Some operations may need manual attention.[/yellow]")

        console.print("\n[blue]📋 Next Steps:[/blue]")
        console.print("[cyan]1. Review any error messages above[/cyan]")
        console.print("[cyan]2. Run 'python3 noah.py validate' to check the environment[/cyan]")
        console.print("[cyan]3. Configure your deployment with 'python3 noah.py configure'[/cyan]")

    def reset_environment(self) -> bool:
        """Main reset method"""
        console.print("[bold blue]🔄 NOAH Development Environment Reset[/bold blue]")
        console.print("=====================================")

        console.print(
            "\n[yellow]⚠️  This will clean Docker, reset Git, and reinstall dependencies![/yellow]")
        if not Confirm.ask("Continue with environment reset?"):
            console.print("[yellow]Reset cancelled[/yellow]")
            return False

        operations = [
            ("Cleaning Docker environment", self.clean_docker_environment),
            ("Resetting Git repository", self.reset_git_repository),
            ("Reinstalling Python dependencies", self.reinstall_python_dependencies),
            ("Installing Ansible collections", self.install_ansible_collections),
            ("Updating Helm dependencies", self.update_helm_dependencies),
            ("Reinitializing NOAH environment", self.reinitialize_noah_environment),
            ("Validating environment", self.validate_environment),
            ("Running CI test", self.run_act_test)
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for description, operation in operations:
                task = progress.add_task(description, total=1)
                operation()
                progress.update(task, advance=1)

        self.display_summary()
        return self.errors == 0


def main():
    """Main entry point"""
    resetter = DevEnvironmentResetter()
    success = resetter.reset_environment()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
