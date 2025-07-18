#!/usr/bin/env python3
"""
NOAH Monitoring Management

This script manages the NOAH monitoring stack including Prometheus and Grafana.
It provides deployment, status checking, and teardown functionality.

Features:
- Deploy monitoring stack (Prometheus, Grafana)
- Check monitoring stack status
- Teardown monitoring stack
- Dry-run mode for safe testing
- Comprehensive logging and error handling
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Color codes for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


class MonitoringError(Exception):
    """Custom exception for monitoring operations."""


class NoahMonitoring:
    """Main monitoring management class for NOAH project."""

    def __init__(
        self,
        environment: str = "dev",
        namespace: str = "noah-monitoring",
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.environment = environment
        self.namespace = namespace
        self.dry_run = dry_run
        self.verbose = verbose

        # Script metadata
        self.script_version = "3.0.0"
        self.script_name = "noah-monitoring"
        self.project_root = Path.cwd()
        self.helm_dir = self.project_root / "Helm"

        # Monitoring components
        self.monitoring_charts = {
            "prometheus": {
                "chart_path": self.helm_dir / "prometheus",
                "release_name": f"prometheus-{environment}",
                "timeout": "300s",
            },
            "grafana": {
                "chart_path": self.helm_dir / "grafana",
                "release_name": f"grafana-{environment}",
                "timeout": "300s",
            },
        }

    def log(self, message: str):
        """Print info message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.GREEN}[INFO]{Colors.NC} {timestamp} - {message}")

    def log_warn(self, message: str):
        """Print warning message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.YELLOW}[WARN]{Colors.NC} {timestamp} - {message}")

    def log_error(self, message: str):
        """Print error message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"{Colors.RED}[ERROR]{Colors.NC} {timestamp} - {message}", file=sys.stderr
        )

    def log_success(self, message: str):
        """Print success message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {timestamp} - {message}")

    def print_banner(self):
        """Print NOAH monitoring banner."""
        print(
            f"""
{Colors.CYAN}███    ██  ██████   █████  ██   ██     {Colors.NC}
{Colors.CYAN}████   ██ ██    ██ ██   ██ ██   ██     {Colors.NC}
{Colors.CYAN}██ ██  ██ ██    ██ ███████ ███████     {Colors.NC}
{Colors.CYAN}██  ██ ██ ██    ██ ██   ██ ██   ██     {Colors.NC}
{Colors.CYAN}██   ████  ██████  ██   ██ ██   ██     {Colors.NC}
{Colors.CYAN}                                       {Colors.NC}
{Colors.PURPLE}       Monitoring Management         {Colors.NC}
        """
        )

    def run_command(
        self,
        command: List[str],
        capture_output: bool = True,
        check: bool = True,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        if self.verbose:
            self.log(f"Running: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=check,
                timeout=timeout,
            )

            if self.verbose and result.stdout:
                print(result.stdout)
            if result.stderr and not capture_output:
                print(result.stderr)

            return result

        except subprocess.TimeoutExpired as e:
            self.log_error(f"Command timed out after {timeout}s: {' '.join(command)}")
            raise MonitoringError(f"Command timeout: {e}")

        except subprocess.CalledProcessError as e:
            self.log_error(f"Command failed: {' '.join(command)}")
            if e.stdout:
                print(f"STDOUT: {e.stdout}")
            if e.stderr:
                print(f"STDERR: {e.stderr}")
            if check:
                raise MonitoringError(f"Command failed with code {e.returncode}")
            return e

    def check_prerequisites(self) -> bool:
        """Check if required tools are available."""
        self.log("Checking prerequisites...")

        required_tools = ["kubectl", "helm"]
        all_good = True

        for tool in required_tools:
            try:
                self.run_command([tool, "version", "--client"], capture_output=True)
                self.log_success(f"Found {tool} ✓")
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.log_error(f"{tool} is not installed or not in PATH")
                all_good = False

        return all_good

    def ensure_namespace(self) -> bool:
        """Ensure the monitoring namespace exists."""
        if self.dry_run:
            self.log(f"DRY RUN: Would create namespace {self.namespace}")
            return True

        try:
            # Check if namespace exists
            result = self.run_command(
                ["kubectl", "get", "namespace", self.namespace],
                capture_output=True,
                check=False,
            )

            if result.returncode == 0:
                self.log(f"Namespace {self.namespace} already exists")
                return True
            else:
                # Create namespace
                self.log(f"Creating namespace: {self.namespace}")
                self.run_command(["kubectl", "create", "namespace", self.namespace])
                self.log_success(f"Namespace {self.namespace} created")
                return True

        except Exception as e:
            self.log_error(f"Failed to ensure namespace: {e}")
            return False

    def deploy_chart(self, chart_name: str, chart_info: Dict) -> bool:
        """Deploy a single monitoring chart."""
        chart_path = chart_info["chart_path"]
        release_name = chart_info["release_name"]
        timeout = chart_info["timeout"]

        if not chart_path.exists():
            self.log_warn(f"Chart directory not found: {chart_path}")
            return False

        if self.dry_run:
            self.log(f"DRY RUN: Would deploy {chart_name} chart")
            return True

        try:
            self.log(f"Deploying {chart_name}...")

            command = [
                "helm",
                "upgrade",
                "--install",
                release_name,
                str(chart_path),
                "--namespace",
                self.namespace,
                "--wait",
                "--timeout",
                timeout,
            ]

            self.run_command(command, capture_output=not self.verbose)
            self.log_success(f"✅ {chart_name.title()} deployed successfully")
            return True

        except Exception as e:
            self.log_error(f"Failed to deploy {chart_name}: {e}")
            return False

    def deploy_monitoring(self) -> bool:
        """Deploy the complete monitoring stack."""
        self.log(f"Deploying monitoring stack to namespace: {self.namespace}")

        if not self.check_prerequisites():
            return False

        if not self.ensure_namespace():
            return False

        success = True
        deployed_charts = []

        for chart_name, chart_info in self.monitoring_charts.items():
            if self.deploy_chart(chart_name, chart_info):
                deployed_charts.append(chart_name)
            else:
                success = False

        if success:
            self.log_success("Monitoring stack deployment completed successfully")
            self.log(f"Deployed components: {', '.join(deployed_charts)}")
        else:
            self.log_error("Monitoring stack deployment completed with errors")

        return success

    def get_helm_releases(self) -> List[str]:
        """Get list of helm releases in the monitoring namespace."""
        try:
            result = self.run_command(
                ["helm", "list", "-n", self.namespace, "-q"],
                capture_output=True,
                check=False,
            )

            if result.returncode == 0:
                releases = [
                    line.strip() for line in result.stdout.split("\n") if line.strip()
                ]
                return releases
            else:
                return []

        except Exception:
            return []

    def get_namespace_resources(self, resource_type: str) -> Tuple[bool, str]:
        """Get resources of a specific type in the namespace."""
        try:
            result = self.run_command(
                ["kubectl", "get", resource_type, "-n", self.namespace],
                capture_output=True,
                check=False,
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"No {resource_type} found"

        except Exception as e:
            return False, f"Error getting {resource_type}: {e}"

    def check_monitoring_status(self) -> Dict:
        """Check the status of the monitoring stack."""
        self.log(f"Checking monitoring stack status in namespace: {self.namespace}")

        status_report = {
            "timestamp": datetime.now().isoformat(),
            "namespace": self.namespace,
            "environment": self.environment,
            "namespace_exists": False,
            "helm_releases": [],
            "pods": {"exists": False, "output": ""},
            "services": {"exists": False, "output": ""},
            "ingresses": {"exists": False, "output": ""},
        }

        # Check if namespace exists
        try:
            result = self.run_command(
                ["kubectl", "get", "namespace", self.namespace],
                capture_output=True,
                check=False,
            )
            status_report["namespace_exists"] = result.returncode == 0
        except Exception:
            status_report["namespace_exists"] = False

        if not status_report["namespace_exists"]:
            self.log_warn(f"Monitoring namespace does not exist: {self.namespace}")
            return status_report

        # Get helm releases
        status_report["helm_releases"] = self.get_helm_releases()

        # Get pods
        pods_exists, pods_output = self.get_namespace_resources("pods")
        status_report["pods"] = {"exists": pods_exists, "output": pods_output}

        # Get services
        services_exists, services_output = self.get_namespace_resources("services")
        status_report["services"] = {
            "exists": services_exists,
            "output": services_output,
        }

        # Get ingresses
        ingresses_exists, ingresses_output = self.get_namespace_resources("ingresses")
        status_report["ingresses"] = {
            "exists": ingresses_exists,
            "output": ingresses_output,
        }

        return status_report

    def display_status(self, status_report: Dict):
        """Display the monitoring status in a formatted way."""
        print(f"\n{Colors.BLUE}📊 Monitoring Stack Status{Colors.NC}")
        print("=" * 50)
        print(f"Namespace: {Colors.CYAN}{status_report['namespace']}{Colors.NC}")
        print(f"Environment: {Colors.CYAN}{status_report['environment']}{Colors.NC}")
        print(f"Timestamp: {Colors.CYAN}{status_report['timestamp']}{Colors.NC}")
        print("")

        if not status_report["namespace_exists"]:
            print(f"{Colors.RED}❌ Namespace does not exist{Colors.NC}")
            return

        # helm releases
        print(f"{Colors.YELLOW}🚀 Monitoring Releases:{Colors.NC}")
        if status_report["helm_releases"]:
            for release in status_report["helm_releases"]:
                print(f"  • {Colors.GREEN}{release}{Colors.NC}")
        else:
            print(f"  {Colors.YELLOW}No releases found{Colors.NC}")
        print("")

        # Pods
        print(f"{Colors.YELLOW}📦 Monitoring Pods:{Colors.NC}")
        if status_report["pods"]["exists"]:
            print(status_report["pods"]["output"])
        else:
            print(f"  {Colors.YELLOW}No pods found{Colors.NC}")
        print("")

        # Services
        print(f"{Colors.YELLOW}🌐 Monitoring Services:{Colors.NC}")
        if status_report["services"]["exists"]:
            print(status_report["services"]["output"])
        else:
            print(f"  {Colors.YELLOW}No services found{Colors.NC}")
        print("")

        # Ingresses
        print(f"{Colors.YELLOW}🔗 Monitoring Ingresses:{Colors.NC}")
        if status_report["ingresses"]["exists"]:
            print(status_report["ingresses"]["output"])
        else:
            print(f"  {Colors.YELLOW}No ingresses found{Colors.NC}")
        print("")

    def teardown_monitoring(self) -> bool:
        """Teardown the monitoring stack."""
        self.log(f"Tearing down monitoring stack in namespace: {self.namespace}")

        if not self.check_prerequisites():
            return False

        if self.dry_run:
            self.log("DRY RUN: Would teardown monitoring stack")
            return True

        success = True

        # Get and uninstall helm releases
        releases = self.get_helm_releases()
        if releases:
            for release in releases:
                try:
                    self.log(f"Uninstalling: {release}")
                    self.run_command(
                        ["helm", "uninstall", release, "-n", self.namespace],
                        capture_output=not self.verbose,
                    )
                    self.log_success(f"✅ {release} uninstalled")
                except Exception as e:
                    self.log_error(f"Failed to uninstall {release}: {e}")
                    success = False
        else:
            self.log("No helm releases to uninstall")

        # Delete namespace
        try:
            self.log(f"Deleting namespace: {self.namespace}")
            self.run_command(
                ["kubectl", "delete", "namespace", self.namespace, "--timeout=60s"],
                capture_output=not self.verbose,
                check=False,
            )
            self.log_success(f"✅ Namespace {self.namespace} deleted")
        except Exception as e:
            self.log_error(f"Failed to delete namespace: {e}")
            success = False

        if success:
            self.log_success("Monitoring stack teardown completed successfully")
        else:
            self.log_error("Monitoring stack teardown completed with errors")

        return success

    def save_status_report(
        self, status_report: Dict, filename: str = "monitoring_status.json"
    ):
        """Save the monitoring status report to a file."""
        report_path = self.project_root / filename

        try:
            with open(report_path, "w") as f:
                json.dump(status_report, f, indent=2)
            self.log_success(f"Status report saved to: {report_path}")
        except Exception as e:
            self.log_error(f"Failed to save status report: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="NOAH Monitoring Management - Deploy, manage, and monitor the NOAH monitoring stack"
    )

    parser.add_argument(
        "action", choices=["deploy", "status", "teardown"], help="Action to perform"
    )

    parser.add_argument(
        "-e",
        "--environment",
        default="dev",
        help="Environment (dev, staging, prod) (default: dev)",
    )

    parser.add_argument(
        "-n",
        "--namespace",
        default="noah-monitoring",
        help="Kubernetes namespace (default: noah-monitoring)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save status report to file (used with status action)",
    )

    args = parser.parse_args()

    # Create monitoring instance
    monitoring = NoahMonitoring(
        environment=args.environment,
        namespace=args.namespace,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    # Print banner
    monitoring.print_banner()

    # Execute action
    success = True

    try:
        if args.action == "deploy":
            success = monitoring.deploy_monitoring()

        elif args.action == "status":
            status_report = monitoring.check_monitoring_status()
            monitoring.display_status(status_report)

            if args.save_report:
                monitoring.save_status_report(status_report)

        elif args.action == "teardown":
            success = monitoring.teardown_monitoring()

    except KeyboardInterrupt:
        monitoring.log_error("Operation interrupted by user")
        success = False
    except Exception as e:
        monitoring.log_error(f"Unexpected error: {e}")
        success = False

    if success:
        monitoring.log_success("NOAH Monitoring operation completed successfully! 🚀")
    else:
        monitoring.log_error("NOAH Monitoring operation completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
