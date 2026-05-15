#!/usr/bin/env python3
"""
NOAH Docker Installer
Simplified Python version of Docker's official installation script.
Based on: https://github.com/docker/docker-install/

This script provides a convenient way to install Docker Engine on Linux systems.
For production environments, refer to official Docker documentation.
"""

import os
import sys
import subprocess
import platform
import urllib.request
from pathlib import Path


class DockerInstaller:
    """Docker installation manager for NOAH environment"""

    def __init__(self, dry_run=False, channel="stable", version=None):
        """
        Initialize Docker installer

        Args:
            dry_run: If True, show commands without executing
            channel: Docker channel (stable or test)
            version: Specific Docker version to install (None for latest)
        """
        self.dry_run = dry_run
        self.channel = channel
        self.version = version
        self.os_type = self._detect_os()
        self.os_version = self._detect_os_version()

    def _detect_os(self):
        """Detect Linux distribution"""
        if not sys.platform.startswith('linux'):
            raise RuntimeError("This installer only supports Linux systems")

        # Try to read os-release file
        os_release_file = Path('/etc/os-release')
        if os_release_file.exists():
            with open(os_release_file) as f:
                for line in f:
                    if line.startswith('ID='):
                        return line.split('=')[1].strip().strip('"').lower()

        # Fallback detection
        if Path('/etc/debian_version').exists():
            return 'debian'
        elif Path('/etc/redhat-release').exists():
            return 'rhel'

        raise RuntimeError("Unable to detect Linux distribution")

    def _detect_os_version(self):
        """Detect OS version"""
        os_release_file = Path('/etc/os-release')
        if os_release_file.exists():
            with open(os_release_file) as f:
                for line in f:
                    if line.startswith('VERSION_ID='):
                        return line.split('=')[1].strip().strip('"')
        return ""

    def _run_command(self, cmd, description=None, check=True, shell=False):
        """Execute a command with optional dry-run mode"""
        if description:
            print(f"[INFO] {description}")

        if self.dry_run:
            print(f"[DRY-RUN] Would execute: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
            return True

        try:
            if shell:
                result = subprocess.run(cmd, shell=True, check=check,
                                       capture_output=True, text=True)
            else:
                result = subprocess.run(cmd, check=check,
                                       capture_output=True, text=True)

            if result.stdout:
                print(result.stdout)

            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Command failed: {e}")
            if e.stderr:
                print(e.stderr)
            if check:
                raise
            return False

    def check_prerequisites(self):
        """Check if system meets prerequisites"""
        print("🔍 Checking prerequisites...")

        # Check if running as root or with sudo
        if os.geteuid() != 0:
            print("❌ This script must be run as root or with sudo")
            return False

        # Check system architecture
        arch = platform.machine()
        if arch not in ['x86_64', 'aarch64', 'armv7l']:
            print(f"❌ Unsupported architecture: {arch}")
            return False

        print(f"✅ Running on {self.os_type} {self.os_version} ({arch})")
        return True

    def is_docker_installed(self):
        """Check if Docker is already installed"""
        try:
            result = subprocess.run(['docker', '--version'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Docker is already installed: {result.stdout.strip()}")
                return True
        except FileNotFoundError:
            pass

        return False

    def install_docker_debian(self):
        """Install Docker on Debian/Ubuntu systems"""
        print("📦 Installing Docker on Debian-based system...")

        # Update package index
        self._run_command(
            ['apt-get', 'update'],
            "Updating package index"
        )

        # Install prerequisites
        self._run_command(
            ['apt-get', 'install', '-y',
             'ca-certificates', 'curl', 'gnupg', 'lsb-release'],
            "Installing prerequisites"
        )

        # Add Docker's official GPG key
        self._run_command(
            'install -m 0755 -d /etc/apt/keyrings',
            "Creating keyrings directory",
            shell=True
        )

        self._run_command(
            'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | '
            'gpg --dearmor -o /etc/apt/keyrings/docker.gpg',
            "Adding Docker GPG key",
            shell=True
        )

        self._run_command(
            'chmod a+r /etc/apt/keyrings/docker.gpg',
            "Setting GPG key permissions",
            shell=True
        )

        # Add Docker repository
        repo_cmd = (
            'echo "deb [arch=$(dpkg --print-architecture) '
            'signed-by=/etc/apt/keyrings/docker.gpg] '
            'https://download.docker.com/linux/ubuntu '
            '$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | '
            'tee /etc/apt/sources.list.d/docker.list > /dev/null'
        )
        self._run_command(repo_cmd, "Adding Docker repository", shell=True)

        # Update package index again
        self._run_command(
            ['apt-get', 'update'],
            "Updating package index with Docker repository"
        )

        # Install Docker packages
        docker_packages = [
            'docker-ce',
            'docker-ce-cli',
            'containerd.io',
            'docker-buildx-plugin',
            'docker-compose-plugin'
        ]

        if self.version:
            # Install specific version (simplified - would need version lookup)
            print(f"⚠️  Specific version installation ({self.version}) not fully implemented")
            print("    Installing latest stable version instead")

        self._run_command(
            ['apt-get', 'install', '-y'] + docker_packages,
            "Installing Docker packages"
        )

        return True

    def install_docker_rhel(self):
        """Install Docker on RHEL/CentOS/Fedora systems"""
        print("📦 Installing Docker on RHEL-based system...")

        # Install yum-utils
        self._run_command(
            ['yum', 'install', '-y', 'yum-utils'],
            "Installing prerequisites"
        )

        # Add Docker repository
        self._run_command(
            ['yum-config-manager', '--add-repo',
             'https://download.docker.com/linux/centos/docker-ce.repo'],
            "Adding Docker repository"
        )

        # Install Docker packages
        docker_packages = [
            'docker-ce',
            'docker-ce-cli',
            'containerd.io',
            'docker-buildx-plugin',
            'docker-compose-plugin'
        ]

        self._run_command(
            ['yum', 'install', '-y'] + docker_packages,
            "Installing Docker packages"
        )

        return True

    def start_docker_service(self):
        """Start and enable Docker service"""
        print("🚀 Starting Docker service...")

        self._run_command(
            ['systemctl', 'start', 'docker'],
            "Starting Docker daemon"
        )

        self._run_command(
            ['systemctl', 'enable', 'docker'],
            "Enabling Docker to start on boot"
        )

        return True

    def verify_installation(self):
        """Verify Docker installation"""
        print("✅ Verifying Docker installation...")

        # Check Docker version
        result = subprocess.run(['docker', '--version'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   Docker version: {result.stdout.strip()}")
        else:
            print("❌ Docker installation verification failed")
            return False

        # Run hello-world container
        print("   Testing Docker with hello-world container...")
        result = subprocess.run(['docker', 'run', '--rm', 'hello-world'],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("   ✅ Docker is working correctly!")
            return True
        else:
            print("   ❌ Docker test container failed")
            return False

    def install(self):
        """Main installation method"""
        print("=" * 70)
        print("🐳 NOAH Docker Installer")
        print("=" * 70)

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Check if already installed
        if self.is_docker_installed() and not self.dry_run:
            print("\n💡 Docker is already installed. Use --force to reinstall.")
            return True

        # Install based on OS type
        try:
            if self.os_type in ['ubuntu', 'debian']:
                success = self.install_docker_debian()
            elif self.os_type in ['rhel', 'centos', 'fedora']:
                success = self.install_docker_rhel()
            else:
                print(f"❌ Unsupported OS: {self.os_type}")
                return False

            if not success:
                return False

            # Start Docker service
            if not self.start_docker_service():
                return False

            # Verify installation
            if not self.dry_run:
                return self.verify_installation()

            return True

        except Exception as e:
            print(f"❌ Installation failed: {e}")
            return False


def main():
    """Command-line interface for Docker installer"""
    import argparse

    parser = argparse.ArgumentParser(
        description='NOAH Docker Installer - Simplified Python version'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    parser.add_argument('--channel', choices=['stable', 'test'],
                       default='stable',
                       help='Docker channel to install from')
    parser.add_argument('--version', type=str,
                       help='Specific Docker version to install')
    parser.add_argument('--force', action='store_true',
                       help='Force reinstall even if Docker exists')

    args = parser.parse_args()

    installer = DockerInstaller(
        dry_run=args.dry_run,
        channel=args.channel,
        version=args.version
    )

    success = installer.install()

    if success:
        print("\n" + "=" * 70)
        print("✅ Docker installation completed successfully!")
        print("=" * 70)
        print("\n💡 Next steps:")
        print("   - Add your user to the docker group: sudo usermod -aG docker $USER")
        print("   - Log out and back in for group changes to take effect")
        print("   - Test Docker: docker run hello-world")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ Docker installation failed")
        print("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
