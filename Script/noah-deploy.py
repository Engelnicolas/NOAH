#!/usr/bin/env python3
"""
NOAH - Next Open-source Architecture Hub Deployment Script (Fixed Version)

This script handles the complete deployment process for NOAH infrastructure,
including prerequisites checks, infrastructure setup, and Helm chart deployment.

Author: NOAH Team
Version: 1.0.1
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class DependencyManager:
    """Manages automatic installation of missing Python modules."""

    def __init__(self, requirements_file: str = "requirements.txt"):
        self.requirements_file = Path(__file__).parent / requirements_file
        self.missing_modules = []

    def check_and_install_requirements(self) -> bool:
        """Check and install missing Python requirements automatically."""
        print(f"\n🔍 Vérification des dépendances Python...")

        if not self.requirements_file.exists():
            print(f"⚠️  Fichier {self.requirements_file} non trouvé")
            return True

        try:
            # Read requirements file
            with open(self.requirements_file, "r", encoding="utf-8") as f:
                requirements = []
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        # Extract package name (before any version specifiers)
                        package_name = (
                            line.split(">=")[0]
                            .split("==")[0]
                            .split("<")[0]
                            .split(">")[0]
                            .strip()
                        )
                        if package_name:
                            requirements.append((package_name, line))

            # Check each requirement
            for package_name, requirement_line in requirements:
                if not self._is_module_installed(package_name):
                    self.missing_modules.append(requirement_line)

            # Install missing modules
            if self.missing_modules:
                print(f"📦 {len(self.missing_modules)} modules manquants détectés")
                return self._install_missing_modules()
            else:
                print("✅ Toutes les dépendances sont installées")
                return True

        except Exception as e:
            print(f"❌ Erreur lors de la vérification des dépendances: {e}")
            return False

    def _is_module_installed(self, module_name: str) -> bool:
        """Check if a Python module is installed."""
        try:
            # Handle special cases
            import_name = self._get_import_name(module_name)
            __import__(import_name)
            return True
        except ImportError:
            return False

    def _get_import_name(self, package_name: str) -> str:
        """Convert package name to import name for special cases."""
        mapping = {
            "pyyaml": "yaml",
            "pillow": "PIL",
            "beautifulsoup4": "bs4",
            "python-dateutil": "dateutil",
            "msgpack-python": "msgpack",
        }
        return mapping.get(package_name.lower(), package_name)

    def _install_missing_modules(self) -> bool:
        """Install missing Python modules with retry mechanism."""
        max_retries = 3

        for requirement in self.missing_modules:
            package_name = (
                requirement.split(">=")[0]
                .split("==")[0]
                .split("<")[0]
                .split(">")[0]
                .strip()
            )

            for attempt in range(max_retries):
                try:
                    print(
                        f"📥 Installation de {package_name} (tentative {attempt + 1}/{max_retries})..."
                    )

                    # Run pip install
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", requirement],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )

                    if result.returncode == 0:
                        print(f"✅ {package_name} installé avec succès")
                        break
                    else:
                        print(f"⚠️  Échec installation {package_name}: {result.stderr}")
                        if attempt == max_retries - 1:
                            print(
                                f"❌ Impossible d'installer {package_name} après {max_retries} tentatives"
                            )
                            return False
                        else:
                            time.sleep(2)

                except subprocess.TimeoutExpired:
                    print(f"⏰ Timeout lors de l'installation de {package_name}")
                    if attempt == max_retries - 1:
                        return False
                except Exception as e:
                    print(f"❌ Erreur lors de l'installation de {package_name}: {e}")
                    if attempt == max_retries - 1:
                        return False

        print("✅ Toutes les dépendances ont été installées avec succès")
        return True


# ASCII Art Logo
ASCII_LOGO = """
███    ██  ██████   █████  ██   ██
████   ██ ██    ██ ██   ██ ██   ██
██ ██  ██ ██    ██ ███████ ███████
██  ██ ██ ██    ██ ██   ██ ██   ██
██   ████  ██████  ██   ██ ██   ██

Next Open-source Architecture Hub
"""


class Color:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[0;37m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


class NoahDeploymentError(Exception):
    """Custom exception for deployment errors."""


class NoahLogger:
    """Enhanced logging system for NOAH deployment."""

    def __init__(self, log_dir: str = "logs", verbose: bool = False):
        self.log_dir = Path(log_dir)
        self.verbose = verbose
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create log directories
        self.log_dir.mkdir(exist_ok=True)
        (self.log_dir / "errors").mkdir(exist_ok=True)
        (self.log_dir / "deployments").mkdir(exist_ok=True)

        # Setup logging
        self.setup_logging()

    def setup_logging(self):
        """Setup file and console logging."""
        log_file = self.log_dir / "deployments" / f"deployment_{self.timestamp}.log"

        # Create file handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Setup logger
        self.logger = logging.getLogger("noah-deploy")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Log deployment start
        self.logger.info("=== NOAH Deployment Started ===")

    def info(self, message: str, color: str = Color.GREEN):
        """Log info message with color."""
        console_msg = f"{color}[INFO]{Color.RESET} {message}"
        print(console_msg)
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message."""
        console_msg = f"{Color.YELLOW}[WARN]{Color.RESET} {message}"
        print(console_msg)
        self.logger.warning(message)

    def error(self, message: str, error_details: str = ""):
        """Log error message with optional details."""
        console_msg = f"{Color.RED}[ERROR]{Color.RESET} {message}"
        print(console_msg, file=sys.stderr)
        self.logger.error(message)

        if error_details:
            # Save detailed error log
            error_file = self.log_dir / "errors" / f"error_{self.timestamp}.log"
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(f"Error: {message}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Details:\n{error_details}\n")
            self.logger.error(f"Detailed error saved to: {error_file}")

    def debug(self, message: str):
        """Log debug message."""
        if self.verbose:
            console_msg = f"{Color.BLUE}[DEBUG]{Color.RESET} {message}"
            print(console_msg)
        self.logger.debug(message)

    def success(self, message: str):
        """Log success message."""
        console_msg = f"{Color.GREEN}✅ {message}{Color.RESET}"
        print(console_msg)
        self.logger.info(f"SUCCESS: {message}")


class KubernetesChecker:
    """Simplified Kubernetes cluster checker."""

    def __init__(self, logger: NoahLogger):
        self.logger = logger

    def check_kubernetes_cluster(self) -> bool:
        """Check if Kubernetes cluster is accessible."""
        self.logger.info("Checking Kubernetes cluster...")

        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0:
                self.logger.success("Kubernetes cluster is accessible")
                return True
            self.logger.warning("Kubernetes cluster not accessible")
            return self._start_minikube()
        except subprocess.TimeoutExpired:
            self.logger.error("Kubernetes cluster check timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error checking Kubernetes cluster: {str(e)}")
            return False

    def _start_minikube(self) -> bool:
        """Start minikube cluster."""
        self.logger.info("Starting minikube cluster...")

        try:
            # Check if minikube is already running
            result = subprocess.run(
                ["minikube", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            if result.returncode == 0 and "Running" in result.stdout:
                self.logger.success("Minikube cluster is already running")
                return True

            # Start minikube
            result = subprocess.run(
                ["minikube", "start", "--driver=docker", "--force"],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )

            if result.returncode == 0:
                self.logger.success("Minikube cluster started successfully")
                return True
            self.logger.error(f"Failed to start minikube: {result.stderr}")
            return False

        except subprocess.TimeoutExpired:
            self.logger.error("Minikube start timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error starting minikube: {str(e)}")
            return False


class HelmDeployer:
    """Helm chart deployment manager."""

    def __init__(
        self, logger: NoahLogger, namespace: str = "noah", timeout: str = "600s"
    ):
        self.logger = logger
        self.namespace = namespace
        self.timeout = timeout
        self.script_dir = Path(__file__).parent
        self.helm_dir = self.script_dir.parent / "Helm"
        self.values_file = self.helm_dir / "values" / "values-root.yaml"

        # Deployment order - exact sequence required
        # Phase 1: Infrastructure foundations
        self.priority_charts = [
            "noah-common",  # Common resources and shared configurations
            "samba4",  # LDAP/AD directory services
            "keycloak",  # Authentication and authorization
            "oauth2-proxy",  # OAuth2 proxy for SSO
        ]

        # Phase 2: Core services (depend on authentication)
        self.core_services = [
            "nextcloud",  # File sharing and collaboration
            "mattermost",  # Team communication and collaboration
            "gitlab",  # Git repository and CI/CD
        ]

        # Phase 3: Monitoring and security
        self.monitoring_security = [
            "prometheus",  # Monitoring stack
            "grafana",  # Dashboards and visualization
            "wazuh",  # SIEM and security monitoring
            "openedr",  # Endpoint detection and response
        ]

        # Complete deployment order
        self.deployment_order = (
            self.priority_charts + self.core_services + self.monitoring_security
        )

    def create_namespace(self) -> bool:
        """Create Kubernetes namespace if it doesn't exist."""
        self.logger.info(f"Creating namespace: {self.namespace}")

        try:
            # Check if namespace exists
            result = subprocess.run(
                ["kubectl", "get", "namespace", self.namespace],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info(f"Namespace {self.namespace} already exists")
                return True

            # Create namespace
            result = subprocess.run(
                ["kubectl", "create", "namespace", self.namespace],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                self.logger.success(f"Namespace {self.namespace} created")
                return True
            self.logger.error(f"Failed to create namespace: {result.stderr}")
            return False

        except Exception as e:
            self.logger.error(f"Error creating namespace: {str(e)}")
            return False

    def deploy_chart(self, chart_name: str, dry_run: bool = False) -> bool:
        """Deploy a single Helm chart."""
        chart_path = self.helm_dir / chart_name

        # Check if chart exists
        if not chart_path.exists():
            self.logger.warning(f"Chart directory not found: {chart_path}")
            return True  # Skip missing charts

        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            self.logger.warning(f"Chart.yaml not found in {chart_path}")
            return True  # Skip invalid charts

        self.logger.info(f"Deploying chart: {chart_name}")

        if dry_run:
            self.logger.info(f"DRY RUN: Would deploy {chart_name}")
            return True

        try:
            # Update dependencies if Chart.lock exists
            chart_lock = chart_path / "Chart.lock"
            if chart_lock.exists():
                self.logger.debug(f"Updating dependencies for {chart_name}")
                subprocess.run(
                    ["helm", "dependency", "update", str(chart_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )

            # Prepare helm command
            helm_cmd = [
                "helm",
                "upgrade",
                "--install",
                chart_name,  # release name
                str(chart_path),  # chart path
                "--namespace",
                self.namespace,
                "--timeout",
                self.timeout,
                "--wait",
            ]

            # Add values file if it exists
            if self.values_file.exists():
                helm_cmd.extend(["-f", str(self.values_file)])

            # Execute helm command
            result = subprocess.run(
                helm_cmd,
                capture_output=True,
                text=True,
                timeout=int(self.timeout[:-1]),  # Remove 's' from timeout
                check=False,
            )

            if result.returncode == 0:
                self.logger.success(f"Successfully deployed: {chart_name}")
                return True
            error_details = (
                f"Command: {' '.join(helm_cmd)}\n"
                f"Stdout: {result.stdout}\n"
                f"Stderr: {result.stderr}"
            )
            self.logger.error(f"Failed to deploy {chart_name}", error_details)
            return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Deployment of {chart_name} timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error deploying {chart_name}: {str(e)}")
            return False

    def deploy_all_charts(self, dry_run: bool = False) -> bool:
        """Deploy all charts in the specified order with phases."""
        self.logger.info("Starting comprehensive Helm charts deployment...")

        # Create namespace first
        if not self.create_namespace():
            return False

        # Deploy in phases
        phases = [
            ("Priority Infrastructure", self.priority_charts),
            ("Core Services", self.core_services),
            ("Monitoring & Security", self.monitoring_security),
        ]

        total_success = 0
        total_charts = len(self.deployment_order)

        for phase_name, charts in phases:
            self.logger.info(f"=== Phase: {phase_name} ===")
            phase_success = 0

            for chart_name in charts:
                if self.deploy_chart(chart_name, dry_run):
                    phase_success += 1
                    total_success += 1
                else:
                    self.logger.error(
                        f"Deployment failed for {chart_name} in phase '{phase_name}'"
                    )
                    # Continue with other charts in the phase rather than stopping completely
                    continue

            self.logger.info(
                f"Phase '{phase_name}' completed: {phase_success}/{len(charts)} charts deployed"
            )

            # Add a small delay between phases to allow services to stabilize
            if not dry_run and phase_success > 0:
                self.logger.debug("Waiting 10 seconds for services to stabilize...")
                time.sleep(10)

        self.logger.info(f"=== Complete Deployment Summary ===")
        self.logger.info(
            f"Total deployment: {total_success}/{total_charts} charts deployed successfully"
        )

        # Show detailed breakdown
        self.logger.info("Deployment breakdown:")
        for phase_name, charts in phases:
            deployed = sum(
                1 for chart in charts if chart in self.deployment_order[:total_success]
            )
            self.logger.info(f"  {phase_name}: {deployed}/{len(charts)} charts")

        return total_success == total_charts

    def deploy_priority_charts_only(self, dry_run: bool = False) -> bool:
        """Deploy only the priority infrastructure charts."""
        self.logger.info("Starting priority charts deployment...")

        # Create namespace first
        if not self.create_namespace():
            return False

        success_count = 0
        total_charts = len(self.priority_charts)

        for chart_name in self.priority_charts:
            if self.deploy_chart(chart_name, dry_run):
                success_count += 1
            else:
                self.logger.error(f"Priority deployment failed for {chart_name}")
                # Continue with other priority charts
                continue

        self.logger.info(
            f"Priority deployment summary: {success_count}/{total_charts} charts deployed successfully"
        )
        return success_count == total_charts

    def list_available_charts(self) -> dict:
        """List all available charts organized by phase."""
        return {
            "Priority Infrastructure": self.priority_charts,
            "Core Services": self.core_services,
            "Monitoring & Security": self.monitoring_security,
        }

    def check_deployment_status(self) -> bool:
        """Check the status of deployed charts."""
        self.logger.info("Checking deployment status...")

        try:
            # Get Helm releases
            result = subprocess.run(
                ["helm", "list", "-n", self.namespace],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info("Helm releases:")
                print(result.stdout)

            # Get pod status
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                self.logger.info("Pod status:")
                print(result.stdout)

            return True

        except Exception as e:
            self.logger.error(f"Error checking deployment status: {str(e)}")
            return False


class NoahDeployer:
    """Main NOAH deployment orchestrator."""

    def __init__(
        self,
        namespace: str = "noah",
        timeout: str = "600s",
        verbose: bool = False,
        priority_only: bool = False,
    ):
        self.namespace = namespace
        self.timeout = timeout
        self.verbose = verbose
        self.priority_only = priority_only
        self.logger = NoahLogger(verbose=verbose)
        self.k8s_checker = KubernetesChecker(self.logger)
        self.helm_deployer = HelmDeployer(self.logger, namespace, timeout)

    def run_deployment(self, dry_run: bool = False) -> bool:
        """Run the complete deployment process."""
        self.logger.info("Starting NOAH deployment process...")
        print(f"{Color.CYAN}{ASCII_LOGO}{Color.RESET}")

        # Step 1: Check technical requirements
        if not self.run_tech_requirements():
            self.logger.error("Technical requirements check failed")
            return False

        # Step 2: Install dependencies
        if not self.run_deps_manager():
            self.logger.error("Dependencies installation failed")
            return False

        # Step 3: Check Kubernetes cluster
        if not self.k8s_checker.check_kubernetes_cluster():
            self.logger.error("Kubernetes cluster check failed")
            return False

        # Step 4: Deploy Helm charts
        if self.priority_only:
            self.logger.info("Deploying priority charts only...")
            if not self.helm_deployer.deploy_priority_charts_only(dry_run):
                self.logger.error("Priority Helm deployment failed")
                return False
        else:
            self.logger.info("Deploying all available charts...")
            if not self.helm_deployer.deploy_all_charts(dry_run):
                self.logger.error("Complete Helm deployment failed")
                return False

        # Step 5: Check deployment status
        if not dry_run:
            self.helm_deployer.check_deployment_status()

        self.logger.success("NOAH deployment completed successfully!")
        return True

    def run_tech_requirements(self) -> bool:
        """Run noah-tech-requirements to validate technical requirements."""
        self.logger.info("Checking technical requirements...")

        script_path = Path(__file__).parent / "noah-tech-requirements"

        if not script_path.exists():
            self.logger.error(f"Script not found: {script_path}")
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--profile", "root"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode == 0:
                self.logger.success("Technical requirements check passed")
                return True
            else:
                self.logger.error(
                    f"Technical requirements check failed: {result.stderr}"
                )
                if self.verbose:
                    self.logger.debug(f"Output: {result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Technical requirements check timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error running technical requirements check: {str(e)}")
            return False

    def run_deps_manager(self) -> bool:
        """Run noah-deps-manager to install dependencies."""
        self.logger.info("Installing Python dependencies...")

        script_path = Path(__file__).parent / "noah-deps-manager"

        if not script_path.exists():
            self.logger.error(f"Script not found: {script_path}")
            return False

        try:
            cmd = [sys.executable, str(script_path), "--install-only"]
            if self.verbose:
                cmd.append("--verbose")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, check=False
            )

            if result.returncode == 0:
                self.logger.success("Dependencies installed successfully")
                return True
            else:
                self.logger.error(f"Dependencies installation failed: {result.stderr}")
                if self.verbose:
                    self.logger.debug(f"Output: {result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Dependencies installation timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error installing dependencies: {str(e)}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="NOAH - Next Open-source Architecture Hub Deployment Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Deploy all charts (11 charts in 3 phases)
  %(prog)s --priority-only          # Deploy only priority infrastructure (4 charts)
  %(prog)s --dry-run                # Show what would be deployed
  %(prog)s --list-charts            # List all available charts by phase
  %(prog)s --verbose                # Deploy with verbose output
  %(prog)s --namespace mynoah       # Deploy to custom namespace
  %(prog)s --timeout 900s           # Use custom timeout for deployments

Chart Deployment Phases:
  1. Priority Infrastructure: noah-common, samba4, keycloak, oauth2-proxy
  2. Core Services: nextcloud, mattermost, gitlab
  3. Monitoring & Security: prometheus, grafana, wazuh, openedr
        """,
    )

    parser.add_argument(
        "--namespace",
        "-n",
        default="noah",
        help="Kubernetes namespace to deploy to (default: noah)",
    )

    parser.add_argument(
        "--timeout",
        "-t",
        default="600s",
        help="Helm deployment timeout (default: 600s)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )

    parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Deploy only priority infrastructure charts (noah-common, samba4, keycloak, oauth2-proxy)",
    )

    parser.add_argument(
        "--list-charts",
        action="store_true",
        help="List all available charts organized by deployment phase",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--version", action="version", version="NOAH Deployment Script v1.0.1"
    )

    args = parser.parse_args()

    # Check and install Python dependencies first
    print(f"{Color.CYAN}NOAH - Deployment Script v1.0.1{Color.RESET}")
    dependency_manager = DependencyManager()
    if not dependency_manager.check_and_install_requirements():
        print(
            f"{Color.RED}❌ Échec de l'installation des dépendances Python{Color.RESET}"
        )
        sys.exit(1)

    # Handle list-charts option
    if args.list_charts:
        print(f"{Color.CYAN}NOAH - Available Helm Charts{Color.RESET}")
        print("=" * 40)

        # Create a temporary deployer to get chart information
        temp_deployer = NoahDeployer()
        charts_by_phase = temp_deployer.helm_deployer.list_available_charts()

        for phase, charts in charts_by_phase.items():
            print(f"\n{Color.BOLD}{phase}:{Color.RESET}")
            for i, chart in enumerate(charts, 1):
                print(f"  {i}. {chart}")

        print(
            f"\n{Color.YELLOW}Total: {sum(len(charts) for charts in charts_by_phase.values())} charts{Color.RESET}"
        )
        print(f"\n{Color.GREEN}Usage examples:{Color.RESET}")
        print(
            f"  sudo python3 {sys.argv[0]} --priority-only  # Deploy only priority charts"
        )
        print(
            f"  sudo python3 {sys.argv[0]} --dry-run        # Show what would be deployed"
        )
        print(f"  sudo python3 {sys.argv[0]}                  # Deploy all charts")
        sys.exit(0)

    # Check if running as root
    if os.geteuid() != 0:
        print(f"{Color.RED}Error: This script must be run as root user{Color.RESET}")
        print(f"{Color.YELLOW}Please run with: sudo python3 {sys.argv[0]}{Color.RESET}")
        sys.exit(1)

    # Create deployer and run deployment
    deployer = NoahDeployer(
        namespace=args.namespace,
        timeout=args.timeout,
        verbose=args.verbose,
        priority_only=args.priority_only,
    )

    try:
        success = deployer.run_deployment(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Deployment interrupted by user{Color.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{Color.RED}Unexpected error: {e}{Color.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
