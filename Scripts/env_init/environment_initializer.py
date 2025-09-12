#!/usr/bin/env python3
"""
NOAH Environment Initializer
Handles the complete initialization of NOAH development environment
"""

import os
import sys
import subprocess
import click
from pathlib import Path


def check_command_exists(command):
    """Check if a command exists in the system PATH"""
    try:
        subprocess.run(['which', command], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


def install_external_dependency(package_name, print_status):
    """Install external dependency using appropriate method"""
    try:
        print_status(f"[INFO] Installing {package_name}...", "INFO")
        
        # Special installation methods for specific packages
        if package_name == 'kubectl':
            return install_kubectl(print_status)
        elif package_name == 'helm':
            return install_helm(print_status)
        else:
            # Default apt installation for other packages
            return install_via_apt(package_name, print_status)
            
    except Exception as e:
        print_status(f"[WARNING] Failed to install {package_name}: {e}", "WARNING")
        return False


def install_via_apt(package_name, print_status):
    """Install package using apt package manager"""
    try:
        # Check if running with sudo privileges
        if os.geteuid() != 0:
            cmd = ['sudo', 'apt', 'update']
            subprocess.run(cmd, check=True, capture_output=True)
            cmd = ['sudo', 'apt', 'install', '-y', package_name]
        else:
            cmd = ['apt', 'update']
            subprocess.run(cmd, check=True, capture_output=True)
            cmd = ['apt', 'install', '-y', package_name]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print_status(f"[SUCCESS] {package_name} installed successfully", "SUCCESS")
            return True
        else:
            print_status(f"[WARNING] Failed to install {package_name}: {result.stderr}", "WARNING")
            return False
            
    except subprocess.CalledProcessError as e:
        print_status(f"[WARNING] Failed to install {package_name}: {e}", "WARNING")
        return False
    except PermissionError:
        print_status(f"[WARNING] Permission denied installing {package_name}. Run with sudo.", "WARNING")
        return False


def install_kubectl(print_status):
    """Install kubectl using official method"""
    try:
        # Download and install kubectl
        commands = [
            ['curl', '-LO', 'https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl'],
            ['sudo', 'install', '-o', 'root', '-g', 'root', '-m', '0755', 'kubectl', '/usr/local/bin/kubectl'],
            ['rm', 'kubectl']
        ]
        
        # Use shell for the first command to handle $() substitution
        result = subprocess.run('curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"', 
                               shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return False
            
        # Install kubectl
        if os.geteuid() != 0:
            result = subprocess.run(['sudo', 'install', '-o', 'root', '-g', 'root', '-m', '0755', 'kubectl', '/usr/local/bin/kubectl'], 
                                   capture_output=True, text=True)
        else:
            result = subprocess.run(['install', '-o', 'root', '-g', 'root', '-m', '0755', 'kubectl', '/usr/local/bin/kubectl'], 
                                   capture_output=True, text=True)
        
        # Clean up
        subprocess.run(['rm', '-f', 'kubectl'], capture_output=True)
        
        return result.returncode == 0
        
    except Exception as e:
        print_status(f"[WARNING] kubectl installation failed: {e}", "WARNING")
        return False


def install_helm(print_status):
    """Install Helm using official script"""
    try:
        # Download and run Helm install script
        result = subprocess.run(['curl', 'https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3'], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            return False
            
        # Save script to temp file and execute
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(result.stdout)
            script_path = f.name
            
        # Make executable and run
        subprocess.run(['chmod', '+x', script_path], check=True)
        if os.geteuid() != 0:
            result = subprocess.run(['sudo', 'bash', script_path], capture_output=True, text=True)
        else:
            result = subprocess.run(['bash', script_path], capture_output=True, text=True)
            
        # Clean up
        subprocess.run(['rm', '-f', script_path], capture_output=True)
        
        return result.returncode == 0
        
    except Exception as e:
        print_status(f"[WARNING] Helm installation failed: {e}", "WARNING")
        return False


def update_sops_version(print_status=None):
    """Update SOPS to the latest version"""
    
    # Default print_status function if none provided
    if print_status is None:
        def print_status(message, status_type="INFO"):
            icons = {
                "INFO": "[INFO]",
                "SUCCESS": "[SUCCESS]",
                "WARNING": "[WARNING]",
                "ERROR": "[ERROR]"
            }
            icon = icons.get(status_type, "[INFO]")
            print(f"{icon} {message}")
    
    try:
        print_status("[INFO] Checking current SOPS version...", "INFO")
        
        # Get current version
        current_version = None
        try:
            if check_command_exists('sops'):
                result = subprocess.run(['sops', '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    # Extract version from output like "sops 3.8.1 (latest)"
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines:
                        if 'sops' in line.lower():
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.lower() == 'sops' and i + 1 < len(parts):
                                    current_version = parts[i + 1]
                                    break
                            break
        except Exception:
            pass
        
        if current_version:
            print_status(f"[INFO] Current SOPS version: {current_version}", "INFO")
        else:
            print_status("[INFO] SOPS not found or version not detected", "INFO")
        
        # Get latest version from GitHub API
        print_status("[INFO] Fetching latest SOPS version...", "INFO")
        import requests
        response = requests.get('https://api.github.com/repos/getsops/sops/releases/latest')
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release['tag_name'].lstrip('v')
        
        print_status(f"[INFO] Latest SOPS version: {latest_version}", "INFO")
        
        # Check if update is needed
        if current_version and current_version == latest_version:
            print_status("[SUCCESS] SOPS is already up to date", "SUCCESS")
            return True
        
        # Download and install SOPS
        print_status(f"[INFO] Updating SOPS from {current_version or 'not installed'} to {latest_version}...", "INFO")
        
        # Determine architecture
        import platform
        arch_map = {
            'x86_64': 'amd64',
            'aarch64': 'arm64',
            'arm64': 'arm64'
        }
        arch = arch_map.get(platform.machine(), 'amd64')
        
        # Download URL
        download_url = f"https://github.com/getsops/sops/releases/download/v{latest_version}/sops-v{latest_version}.linux.{arch}"
        
        print_status(f"[INFO] Downloading SOPS {latest_version}...", "INFO")
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Install to /usr/local/bin
        sops_path = "/usr/local/bin/sops"
        with open(sops_path, 'wb') as f:
            f.write(response.content)
        
        # Make executable
        os.chmod(sops_path, 0o755)
        
        print_status(f"[SUCCESS] SOPS {latest_version} installed to {sops_path}", "SUCCESS")
        print_status("[SUCCESS] SOPS update completed successfully", "SUCCESS")
        return True
        
    except Exception as e:
        print_status(f"[ERROR] Failed to update SOPS: {e}", "ERROR")
        return False


def initialize_noah_environment(ctx, skip_deps=False, skip_tests=False, print_status=None):
    """Initialize NOAH environment with all dependencies"""
    
    # Default print_status function if none provided
    if print_status is None:
        def print_status(message, status_type="INFO"):
            icons = {
                "INFO": "[INFO]",
                "SUCCESS": "[SUCCESS]",
                "WARNING": "[WARNING]",
                "ERROR": "[ERROR]"
            }
            icon = icons.get(status_type, "[INFO]")
            print(f"{icon} {message}")
    
    click.echo("🚀 NOAH - Network Operations & Automation Hub")
    click.echo("=" * 50)
    click.echo("Initializing NOAH environment...")
    click.echo("")
    
    # Check if running as root (sudo) and install system packages
    is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
    if is_root:
        print_status("[INFO] Running with elevated privileges", "INFO")
        
        # Install required system packages
        print_status("[INFO] Installing required system packages...", "INFO")
        try:
            subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
            
            # Install python-is-python3 package if needed
            result = subprocess.run(['which', 'python'], capture_output=True, text=True)
            if result.returncode != 0:
                print_status("[INFO] Installing python-is-python3...", "INFO")
                subprocess.run(['apt-get', 'install', '-y', 'python-is-python3'], check=True, capture_output=True)
                print_status("[SUCCESS] python-is-python3 installed", "SUCCESS")
            else:
                print_status("[SUCCESS] python command already available", "SUCCESS")
            
            # Install age package if needed
            age_result = subprocess.run(['which', 'age'], capture_output=True, text=True)
            if age_result.returncode != 0:
                print_status("[INFO] Installing age encryption tool...", "INFO")
                subprocess.run(['apt-get', 'install', '-y', 'age'], check=True, capture_output=True)
                print_status("[SUCCESS] age encryption tool installed", "SUCCESS")
            else:
                print_status("[SUCCESS] age encryption tool already available", "SUCCESS")
                
        except subprocess.CalledProcessError as e:
            print_status(f"[WARNING] Could not install system packages: {e}", "WARNING")
            print_status("[INFO] Continuing without system package installation...", "INFO")
    
    # Check Python version
    print_status("[INFO] Checking Python installation...", "INFO")
    python_version = sys.version.split()[0]
    if sys.version_info >= (3, 8):
        print_status(f"[SUCCESS] Python {python_version} found", "SUCCESS")
    else:
        print_status("[ERROR] Python 3.8+ is required", "ERROR")
        sys.exit(1)
    
    # Check virtual environment
    print_status("[INFO] Checking virtual environment...", "INFO")
    venv_path = Path(".venv")
    if not venv_path.exists():
        print_status("[INFO] Creating Python virtual environment...", "INFO")
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print_status("[SUCCESS] Virtual environment created", "SUCCESS")
    else:
        print_status("[SUCCESS] Virtual environment already exists", "SUCCESS")
    
    # Install Python dependencies
    print_status("[INFO] Installing Python dependencies...", "INFO")
    venv_python = venv_path / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_path / "Scripts" / "python.exe"  # Windows
    
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "Scripts/requirements.txt"], 
                      check=True, capture_output=True)
        print_status("[SUCCESS] Python dependencies installed", "SUCCESS")
    except subprocess.CalledProcessError as e:
        print_status(f"[ERROR] Failed to install dependencies: {e}", "ERROR")
        sys.exit(1)
    
    # Check external dependencies
    if not skip_deps:
        print_status("[INFO] Checking external dependencies...", "INFO")
        external_deps = {
            'kubectl': 'Kubernetes CLI',
            'helm': 'Helm package manager',
            'ansible': 'Infrastructure automation',
            'age': 'Encryption tool'
        }
        
        missing_deps = []
        for cmd, desc in external_deps.items():
            if check_command_exists(cmd):
                print_status(f"[SUCCESS] {cmd} found ({desc})", "SUCCESS")
            else:
                print_status(f"[WARNING] {cmd} not found ({desc})", "WARNING")
                # Try to install the missing dependency automatically
                print_status(f"[INFO] Attempting to install {cmd} automatically...", "INFO")
                if install_external_dependency(cmd, print_status):
                    # Verify installation
                    if check_command_exists(cmd):
                        print_status(f"[SUCCESS] {cmd} installed and verified ({desc})", "SUCCESS")
                    else:
                        print_status(f"[WARNING] {cmd} installation completed but not found in PATH", "WARNING")
                        missing_deps.append(cmd)
                else:
                    missing_deps.append(cmd)
        
        # Check and update SOPS
        print_status("[INFO] Checking SOPS version...", "INFO")
        if check_command_exists('sops'):
            update_sops_version(print_status)
        else:
            print_status("[WARNING] SOPS not found - attempting to install latest version...", "WARNING")
            if update_sops_version(print_status):
                print_status("[SUCCESS] SOPS installed successfully", "SUCCESS")
            else:
                print_status("[ERROR] Failed to install SOPS", "ERROR")
                missing_deps.append('sops')
        
        if missing_deps:
            print_status("[WARNING] Some external dependencies could not be installed automatically:", "WARNING")
            click.echo("  Please install manually with your package manager:")
            click.echo(f"  Ubuntu/Debian: sudo apt install {' '.join(missing_deps)}")
            click.echo(f"  RHEL/CentOS:   sudo dnf install {' '.join(missing_deps)}")
            click.echo(f"  macOS:         brew install {' '.join(missing_deps)}")
            click.echo("")
    
    # Initialize NOAH
    print_status("[INFO] Initializing NOAH CLI...", "INFO")
    os.environ['PYTHONPATH'] = f"{os.getcwd()}:{os.environ.get('PYTHONPATH', '')}"
    
    # Test CLI functionality
    try:
        result = subprocess.run([str(venv_python), "noah.py", "--help"], 
                               capture_output=True, text=True, env=os.environ)
        if result.returncode == 0:
            print_status("[SUCCESS] NOAH CLI initialized successfully", "SUCCESS")
        else:
            print_status("[ERROR] Failed to initialize NOAH CLI", "ERROR")
            sys.exit(1)
    except Exception as e:
        print_status(f"[ERROR] CLI test failed: {e}", "ERROR")
        sys.exit(1)
    
    # Initialize security infrastructure
    print_status("[INFO] Setting up security infrastructure...", "INFO")
    try:
        ctx.obj['secrets'].initialize_encryption()
        print_status("[SUCCESS] Security infrastructure initialized", "SUCCESS")
    except Exception as e:
        print_status(f"[WARNING] Security setup incomplete: {e}", "WARNING")
    
    # Run validation tests
    if not skip_tests:
        print_status("[INFO] Running validation tests...", "INFO")
        test_files = ["Tests/test_noah.py", "Tests/test_modifications.py"]
        tests_passed = 0
        
        for test_file in test_files:
            if Path(test_file).exists():
                try:
                    result = subprocess.run([str(venv_python), test_file], 
                                          capture_output=True, env=os.environ)
                    if result.returncode == 0:
                        tests_passed += 1
                except Exception:
                    pass
        
        if tests_passed > 0:
            print_status(f"[SUCCESS] {tests_passed}/{len(test_files)} test suites passed", "SUCCESS")
        else:
            print_status("[WARNING] Some tests failed - run manually to debug", "WARNING")
    
    # Print completion message
    click.echo("")
    click.echo("🎉 NOAH Setup Complete!")
    click.echo("=" * 25)
    click.echo("")
    click.echo("To use NOAH:")
    click.echo("1. Activate virtual environment: source .venv/bin/activate")
    click.echo("2. Set Python path: export PYTHONPATH=$(pwd):$PYTHONPATH")
    click.echo("3. Use NOAH: python noah.py --help")
    click.echo("")
    click.echo("Quick start:")
    click.echo("  python noah.py cluster create --name my-cluster")
    click.echo("  python noah.py deploy all --domain my-domain.com")
    click.echo("")
    print_status("[SUCCESS] Setup completed successfully!", "SUCCESS")