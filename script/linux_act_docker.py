#!/usr/bin/env python3
"""
Linux Act Docker Setup Script

This script sets up Act (GitHub Actions runner) to run locally using Docker.
Act allows you to run your GitHub Actions workflows locally for testing.

Features:
- Docker-based Act installation
- Shell function setup for easy usage
- Docker image management
- Comprehensive error handling and validation
- Rich console output with progress indicators

Usage:
    python3 linux_act_docker.py [options]
    
Options:
    --force-rebuild    Force rebuild of Act Docker image
    --skip-shell       Skip shell function setup
    --help            Show this help message
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import json

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.text import Text
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = type(None)
    Progress = type(None)
    SpinnerColumn = type(None)
    TextColumn = type(None)
    Panel = type(None)


class ActDockerInstaller:
    """Handles Act installation and setup using Docker."""
    
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.act_image_name = "local/act"
        self.home_dir = Path.home()
        self.profile_file = self.home_dir / ".bashrc"
        
    def print_message(self, message: str, style: Optional[str] = None):
        """Print message with optional styling."""
        if self.console and style:
            self.console.print(message, style=style)
        else:
            print(message)
    
    def print_panel(self, message: str, title: Optional[str] = None, style: str = "blue"):
        """Print message in a panel."""
        if self.console and RICH_AVAILABLE:
            from rich.panel import Panel
            panel = Panel(message, title=title, border_style=style)
            self.console.print(panel)
        else:
            print(f"\n=== {title or 'INFO'} ===")
            print(message)
            print("=" * 50)
    
    def run_command(self, command: List[str], capture_output: bool = True, 
                   check: bool = True) -> subprocess.CompletedProcess:
        """Run a command with error handling."""
        try:
            self.print_message(f"Running: {' '.join(command)}", "dim")
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.print_message(f"❌ Command failed: {e}", "red")
            raise
        except FileNotFoundError:
            self.print_message(f"❌ Command not found: {command[0]}", "red")
            raise
    
    def check_docker_availability(self) -> bool:
        """Check if Docker is installed and running."""
        self.print_message("🔍 Checking Docker availability...", "blue")
        
        # Check if docker command exists
        if not shutil.which("docker"):
            self.print_message("❌ Docker is not installed or not in PATH", "red")
            self.print_panel(
                "Please install Docker first:\n"
                "• Ubuntu/Debian: sudo apt install docker.io\n"
                "• Other systems: https://docs.docker.com/get-docker/",
                "Docker Installation Required"
            )
            return False
        
        # Check if Docker daemon is running
        try:
            self.run_command(["docker", "info"], capture_output=True)
            self.print_message("✅ Docker is available and running", "green")
            return True
        except subprocess.CalledProcessError:
            self.print_message("❌ Docker is installed but not running", "red")
            self.print_panel(
                "Please start Docker and try again:\n"
                "• sudo systemctl start docker\n"
                "• sudo service docker start",
                "Docker Not Running"
            )
            return False
    
    def check_act_image_exists(self) -> bool:
        """Check if Act Docker image already exists."""
        try:
            result = self.run_command(
                ["docker", "images", "--format", "json"],
                capture_output=True
            )
            
            # Parse JSON output to check for our image
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    image_info = json.loads(line)
                    if image_info.get('Repository') == 'local/act':
                        return True
            return False
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return False
    
    def build_act_docker_image(self, force_rebuild: bool = False) -> bool:
        """Build the Act Docker image."""
        if not force_rebuild and self.check_act_image_exists():
            self.print_message("✅ Act Docker image already exists", "green")
            return True
        
        self.print_message("🔨 Building Act Docker image...", "blue")
        
        dockerfile_content = """FROM golang:alpine
RUN apk add --no-cache git docker-cli
RUN go install github.com/nektos/act@latest
ENTRYPOINT ["/go/bin/act"]
"""
        
        try:
            if self.console and RICH_AVAILABLE:
                from rich.progress import Progress, SpinnerColumn, TextColumn
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=self.console,
                ) as progress:
                    task = progress.add_task("Building Docker image...", total=None)
                    
                    process = subprocess.Popen(
                        ["docker", "build", "-t", self.act_image_name, "-"],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    
                    stdout, _ = process.communicate(input=dockerfile_content)
                    
                    if process.returncode == 0:
                        progress.update(task, description="✅ Docker image built successfully")
                    else:
                        progress.update(task, description="❌ Docker image build failed")
                        self.print_message(f"Build output:\n{stdout}", "red")
                        return False
            else:
                process = subprocess.Popen(
                    ["docker", "build", "-t", self.act_image_name, "-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                stdout, _ = process.communicate(input=dockerfile_content)
                
                if process.returncode != 0:
                    self.print_message(f"❌ Docker image build failed:\n{stdout}", "red")
                    return False
            
            self.print_message("✅ Act Docker image built successfully", "green")
            return True
            
        except Exception as e:
            self.print_message(f"❌ Failed to build Docker image: {e}", "red")
            return False
    
    def setup_shell_function(self, skip_shell: bool = False) -> bool:
        """Set up the act function in the shell profile."""
        if skip_shell:
            self.print_message("⏭️  Skipping shell function setup", "yellow")
            return True
        
        self.print_message("🔧 Setting up shell function...", "blue")
        
        # Check if function already exists
        if self.profile_file.exists():
            content = self.profile_file.read_text()
            if "act()" in content and "local/act" in content:
                self.print_message("✅ Act function already exists in profile", "green")
                return True
        
        shell_function = '''

# Act function for running GitHub Actions locally
act() {
    ensure_act_docker
    docker run --rm \\
        -v /var/run/docker.sock:/var/run/docker.sock \\
        -v "$PWD:$PWD" \\
        -w "$PWD" \\
        local/act "$@"
}

# Function to ensure act Docker image exists
ensure_act_docker() {
    if ! docker images --format "table {{.Repository}}" | grep -q "^local/act$"; then
        echo "❌ Act Docker image not found. Please run the setup script again."
        return 1
    fi
}
'''
        
        try:
            with open(self.profile_file, "a") as f:
                f.write(shell_function)
            
            self.print_message("✅ Shell function added to profile", "green")
            return True
            
        except Exception as e:
            self.print_message(f"❌ Failed to update shell profile: {e}", "red")
            return False
    
    def verify_installation(self) -> bool:
        """Verify that the installation was successful."""
        self.print_message("🔍 Verifying installation...", "blue")
        
        # Check if image exists
        if not self.check_act_image_exists():
            self.print_message("❌ Act Docker image not found", "red")
            return False
        
        # Test run act --version
        try:
            result = self.run_command([
                "docker", "run", "--rm", self.act_image_name, "--version"
            ], capture_output=True)
            
            version_info = result.stdout.strip()
            self.print_message(f"✅ Act version: {version_info}", "green")
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_message(f"❌ Failed to verify installation: {e}", "red")
            return False
    
    def print_usage_instructions(self):
        """Print usage instructions after successful installation."""
        instructions = """
🎉 Act installation completed successfully!

To use Act, you have several options:

1. 📁 Source your profile to enable the shell function:
   source ~/.bashrc

2. 🔄 Open a new terminal (automatic)

3. 🐳 Use Docker directly:
   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:$PWD" -w "$PWD" local/act

Common Act commands:
• act --list                    # List available workflows
• act                          # Run all workflows
• act push                     # Run workflows triggered by push
• act pull_request             # Run workflows triggered by pull request
• act -j job_name             # Run specific job
• act --dry-run               # Show what would be run

For more information: https://github.com/nektos/act
"""
        
        if self.console and RICH_AVAILABLE:
            from rich.panel import Panel
            panel = Panel(instructions.strip(), title="🚀 Installation Complete", border_style="green")
            self.console.print(panel)
        else:
            print(instructions)
    
    def install(self, force_rebuild: bool = False, skip_shell: bool = False) -> bool:
        """Main installation process."""
        self.print_panel("🚀 Installing Act for GitHub Actions local execution", "Act Docker Installer")
        
        # Check Docker availability
        if not self.check_docker_availability():
            return False
        
        # Build Docker image
        if not self.build_act_docker_image(force_rebuild):
            return False
        
        # Setup shell function
        if not self.setup_shell_function(skip_shell):
            return False
        
        # Verify installation
        if not self.verify_installation():
            return False
        
        # Print usage instructions
        self.print_usage_instructions()
        
        return True


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Install Act for GitHub Actions local execution using Docker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 linux_act_docker.py                    # Normal installation
  python3 linux_act_docker.py --force-rebuild   # Force rebuild Docker image
  python3 linux_act_docker.py --skip-shell      # Skip shell function setup
        """
    )
    
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild of Act Docker image even if it exists"
    )
    
    parser.add_argument(
        "--skip-shell",
        action="store_true",
        help="Skip shell function setup"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    try:
        args = parse_arguments()
        
        installer = ActDockerInstaller()
        success = installer.install(
            force_rebuild=args.force_rebuild,
            skip_shell=args.skip_shell
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()