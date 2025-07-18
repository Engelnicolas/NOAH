#!/usr/bin/env python3
"""
NOAH Linting Validator

This script unifies the functionality of setup-linting.sh and run-super-linter.sh
into a single Python tool for validating project linting.

Features:
- Setup development environment with linting tools
- Run Super-Linter locally with Docker
- Validate all project files or changed files only
- Manage pre-commit hooks
- Generate linting reports
"""

import argparse
import subprocess
import sys
import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


# Color codes for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


class NoahLinter:
    """Main linting validation class for NOAH project."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path.cwd()
        self.script_dir = Path(__file__).parent

        # Super-Linter configuration
        self.super_linter_image = "ghcr.io/super-linter/super-linter:v5.7.2"
        self.super_linter_config = {
            "DEFAULT_BRANCH": "main",
            "RUN_LOCAL": "true",
            "VALIDATE_YAML": "true",
            "VALIDATE_YAML": "true",
            "VALIDATE_BASH": "true",
            "VALIDATE_PYTHON_BLACK": "true",
            "VALIDATE_PYTHON_FLAKE8": "true",
            "VALIDATE_JSON": "true",
            "LOG_LEVEL": "INFO",
            "SUPPRESS_POSSUM": "true",
        }

    def print_status(self, message: str):
        """Print blue info message."""
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

    def print_success(self, message: str):
        """Print green success message."""
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

    def print_warning(self, message: str):
        """Print yellow warning message."""
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

    def print_error(self, message: str):
        """Print red error message."""
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

    def print_banner(self):
        """Print NOAH linting banner."""
        print(
            f"""
{Colors.CYAN}███    ██  ██████   █████  ██   ██     {Colors.NC}
{Colors.CYAN}████   ██ ██    ██ ██   ██ ██   ██     {Colors.NC}
{Colors.CYAN}██ ██  ██ ██    ██ ███████ ███████     {Colors.NC}
{Colors.CYAN}██  ██ ██ ██    ██ ██   ██ ██   ██     {Colors.NC}
{Colors.CYAN}██   ████  ██████  ██   ██ ██   ██     {Colors.NC}
{Colors.CYAN}                                       {Colors.NC}
{Colors.PURPLE}         Linting Validator            {Colors.NC}
        """
        )

    def run_command(
        self, command: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        if self.verbose:
            self.print_status(f"Running: {' '.join(command)}")

        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=check
            )

            if self.verbose and result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            return result

        except subprocess.CalledProcessError as e:
            self.print_error(f"Command failed: {' '.join(command)}")
            if e.stdout:
                print(e.stdout)
            if e.stderr:
                print(e.stderr)
            if check:
                raise
            # Return a CompletedProcess with the error information
            return subprocess.CompletedProcess(
                args=command, returncode=e.returncode, stdout=e.stdout, stderr=e.stderr
            )

    def check_prerequisites(self) -> bool:
        """Check if all required tools are available."""
        self.print_status("Checking prerequisites...")

        required_tools = {
            "python3": "Python 3 is required",
            "pip3": "pip3 is required for package installation",
            "docker": "Docker is required for Super-Linter",
        }

        all_good = True
        for tool, message in required_tools.items():
            if not shutil.which(tool):
                if tool == "docker":
                    self.print_warning(
                        f"{message} (Super-Linter will not work locally)"
                    )
                else:
                    self.print_error(message)
                    all_good = False
            else:
                self.print_success(f"Found {tool} ✓")

        # Check if we're in the right directory
        if not (self.project_root / ".pre-commit-config.yaml").exists():
            self.print_error(
                "This script must be run from the NOAH project root directory"
            )
            all_good = False

        return all_good

    def setup_environment(self) -> bool:
        """Setup the development environment with linting tools."""
        self.print_status("Setting up NOAH development environment...")

        try:
            # Install pre-commit
            self.print_status("Installing pre-commit...")
            self.run_command(["pip3", "install", "--user", "pre-commit"])

            # Verify pre-commit installation
            if not shutil.which("pre-commit"):
                self.print_warning(
                    "pre-commit not found in PATH. Adding ~/.local/bin to PATH"
                )
                os.environ["PATH"] = (
                    f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"
                )

            # Install pre-commit hooks
            self.print_status("Installing pre-commit hooks...")
            self.run_command(["pre-commit", "install"])

            # Install commit-msg hook for conventional commits
            self.print_status("Installing commit-msg hook...")
            self.run_command(["pre-commit", "install", "--hook-type", "commit-msg"])

            # Update hooks to latest versions
            self.print_status("Updating pre-commit hooks...")
            self.run_command(["pre-commit", "autoupdate"])

            self.print_success("Development environment setup completed!")
            return True

        except Exception as e:
            self.print_error(f"Failed to setup environment: {e}")
            return False

    def pull_super_linter(self) -> bool:
        """Pull the Super-Linter Docker image."""
        if not shutil.which("docker"):
            self.print_error("Docker is not available. Cannot pull Super-Linter image.")
            return False

        try:
            self.print_status("Pulling Super-Linter image...")
            self.run_command(["docker", "pull", self.super_linter_image])
            self.print_success("Super-Linter image pulled successfully!")
            return True
        except Exception as e:
            self.print_error(f"Failed to pull Super-Linter image: {e}")
            return False

    def run_super_linter(self, validate_all: bool = False) -> bool:
        """Run Super-Linter with Docker."""
        if not shutil.which("docker"):
            self.print_error("Docker is not available. Cannot run Super-Linter.")
            return False

        try:
            # Build Docker command
            docker_cmd = ["docker", "run", "--rm"]

            # Add environment variables
            env_vars = self.super_linter_config.copy()
            env_vars["VALIDATE_ALL_CODEBASE"] = "true" if validate_all else "false"

            for key, value in env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])

            # Add volume mount
            docker_cmd.extend(["-v", f"{self.project_root}:/tmp/lint"])

            # Add image
            docker_cmd.append(self.super_linter_image)

            # Run Super-Linter
            mode = "all files" if validate_all else "changed files only"
            self.print_status(f"Running Super-Linter on {mode}...")

            result = self.run_command(docker_cmd, check=False)

            if result.returncode == 0:
                self.print_success("Super-Linter completed successfully!")
                return True
            else:
                self.print_warning("Super-Linter found issues. Check the output above.")
                return False

        except Exception as e:
            self.print_error(f"Failed to run Super-Linter: {e}")
            return False

    def run_pre_commit(
        self, all_files: bool = False, hook_id: Optional[str] = None
    ) -> bool:
        """Run pre-commit hooks."""
        if not shutil.which("pre-commit"):
            self.print_error("pre-commit is not installed. Run setup first.")
            return False

        try:
            cmd = ["pre-commit", "run"]

            if hook_id:
                cmd.extend(["--hook-id", hook_id])
                self.print_status(f"Running pre-commit hook: {hook_id}")
            elif all_files:
                cmd.append("--all-files")
                self.print_status("Running all pre-commit hooks on all files...")
            else:
                self.print_status("Running pre-commit hooks on changed files...")

            result = self.run_command(cmd, check=False)

            if result.returncode == 0:
                self.print_success("All pre-commit hooks passed!")
                return True
            else:
                self.print_warning(
                    "Some pre-commit hooks failed. Check the output above."
                )
                return False

        except Exception as e:
            self.print_error(f"Failed to run pre-commit: {e}")
            return False

    def generate_report(self) -> Dict:
        """Generate a linting validation report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "checks": {},
        }

        # Check prerequisites
        report["checks"]["prerequisites"] = self.check_prerequisites()

        # Check if pre-commit is installed
        report["checks"]["pre_commit_installed"] = (
            shutil.which("pre-commit") is not None
        )

        # Check if Docker is available
        report["checks"]["docker_available"] = shutil.which("docker") is not None

        # Check configuration files
        config_files = [
            ".pre-commit-config.yaml",
            "Script/.yamllint.yml",
            "Script/.markdownlint.yml",
        ]

        report["checks"]["config_files"] = {}
        for config_file in config_files:
            path = self.project_root / config_file
            report["checks"]["config_files"][config_file] = path.exists()

        return report

    def save_report(self, report: Dict, filename: str = "linting_report.json"):
        """Save the linting report to a file."""
        report_path = self.project_root / filename

        try:
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            self.print_success(f"Report saved to: {report_path}")
        except Exception as e:
            self.print_error(f"Failed to save report: {e}")

    def show_usage_info(self):
        """Show usage information and tips."""
        print(
            f"""
{Colors.BLUE}📋 NOAH Linting Validator - Usage Information{Colors.NC}

{Colors.GREEN}🎯 Common Commands:{Colors.NC}
  • python3 noah-linter.py setup           # Setup development environment
  • python3 noah-linter.py lint            # Run linting on changed files
  • python3 noah-linter.py lint --all      # Run linting on all files
  • python3 noah-linter.py precommit       # Run pre-commit hooks
  • python3 noah-linter.py report          # Generate linting report

{Colors.GREEN}🔧 Pre-commit Commands:{Colors.NC}
  • python3 noah-linter.py precommit --all-files    # Run all hooks on all files
  • python3 noah-linter.py precommit --hook-id=<id> # Run specific hook

{Colors.GREEN}📊 Report Generation:{Colors.NC}
  • python3 noah-linter.py report --save    # Save report to file

{Colors.GREEN}💡 Tips:{Colors.NC}
  • Use --verbose for detailed output
  • Pre-commit hooks run automatically on each commit
  • Super-Linter requires Docker to be installed
  • Configuration files are in Script/ directory
        """
        )


def main():
    parser = argparse.ArgumentParser(
        description="NOAH Linting Validator - Unified linting tool for NOAH project"
    )

    parser.add_argument(
        "command",
        choices=["setup", "lint", "precommit", "report", "help"],
        help="Command to execute",
    )

    parser.add_argument(
        "--all",
        "--all-files",
        action="store_true",
        help="Run on all files instead of changed files only",
    )

    parser.add_argument("--hook-id", help="Specific pre-commit hook to run")

    parser.add_argument(
        "--save",
        action="store_true",
        help="Save report to file (used with report command)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Create linter instance
    linter = NoahLinter(verbose=args.verbose)

    # Print banner
    linter.print_banner()

    # Execute command
    success = True

    if args.command == "setup":
        if not linter.check_prerequisites():
            sys.exit(1)
        success = linter.setup_environment()

    elif args.command == "lint":
        if not linter.check_prerequisites():
            sys.exit(1)
        linter.pull_super_linter()
        success = linter.run_super_linter(validate_all=args.all)

    elif args.command == "precommit":
        success = linter.run_pre_commit(all_files=args.all, hook_id=args.hook_id)

    elif args.command == "report":
        report = linter.generate_report()

        if args.save:
            linter.save_report(report)
        else:
            print(json.dumps(report, indent=2))

    elif args.command == "help":
        linter.show_usage_info()

    if not success:
        sys.exit(1)

    linter.print_success("NOAH Linting Validator completed successfully! 🚀")


if __name__ == "__main__":
    main()
