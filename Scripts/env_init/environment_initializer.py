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


def check_kernel_config(config_name, required_value='y'):
    """Check if a kernel configuration option is set to the required value"""
    try:
        # Check /proc/config.gz if available
        config_paths = [
            '/proc/config.gz',
            f'/boot/config-{subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip()}',
            '/boot/config',
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                if config_path.endswith('.gz'):
                    import gzip
                    with gzip.open(config_path, 'rt') as f:
                        content = f.read()
                else:
                    with open(config_path, 'r') as f:
                        content = f.read()
                
                # Look for the config option
                for line in content.split('\n'):
                    if line.startswith(f'{config_name}='):
                        value = line.split('=', 1)[1]
                        return value == required_value
                    elif line.startswith(f'# {config_name} is not set'):
                        return required_value == 'n'
                break
        
        # If no config file found, try modprobe to check if module can be loaded
        if config_name.startswith('CONFIG_') and required_value in ['m', 'y']:
            module_name = config_name.replace('CONFIG_', '').lower()
            result = subprocess.run(['modprobe', '-n', module_name], capture_output=True, text=True)
            return result.returncode == 0
        
        return None  # Unable to determine
        
    except Exception:
        return None


def verify_kubernetes_client(venv_python: Path, print_status):
    """Verify that the Kubernetes Python client is installed inside the virtualenv.

    Tries to import kubernetes and report its version. If the import fails, it will
    attempt an explicit installation (even though requirements should have handled it)
    and re-verify. Exits the process with error if still unavailable so the user gets
    a clear actionable message.
    """
    try:
        # First attempt: import using the virtualenv interpreter
        result = subprocess.run(
            [str(venv_python), "-c", "import kubernetes, json; import sys; print(kubernetes.__version__)"] ,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            version = result.stdout.strip().splitlines()[-1]
            if version:
                print_status(f"[SUCCESS] Kubernetes Python client available (version {version})", "SUCCESS")
            else:
                print_status("[SUCCESS] Kubernetes Python client available", "SUCCESS")
            return True
        else:
            print_status("[WARNING] Kubernetes Python client import failed on first attempt", "WARNING")
            print_status(f"[INFO] stderr: {result.stderr.strip()}", "INFO")
    except Exception as e:
        print_status(f"[WARNING] Kubernetes import raised exception: {e}", "WARNING")

    # Attempt (re)installation explicitly
    print_status("[INFO] Attempting to (re)install kubernetes client explicitly...", "INFO")
    try:
        reinstall = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--no-cache-dir", "kubernetes"],
            capture_output=True,
            text=True,
        )
        if reinstall.returncode != 0:
            print_status("[ERROR] pip failed installing kubernetes package", "ERROR")
            print_status(f"[ERROR] pip stderr: {reinstall.stderr.strip()[:500]}", "ERROR")
            return False
    except Exception as e:
        print_status(f"[ERROR] Exception during kubernetes installation: {e}", "ERROR")
        return False

    # Re-verify import
    second = subprocess.run(
        [str(venv_python), "-c", "import kubernetes; print(kubernetes.__version__)"] ,
        capture_output=True,
        text=True,
    )
    if second.returncode == 0:
        version = second.stdout.strip().splitlines()[-1]
        print_status(f"[SUCCESS] Kubernetes Python client installed (version {version})", "SUCCESS")
        return True
    else:
        print_status("[ERROR] Unable to import kubernetes client after installation attempt", "ERROR")
        print_status(f"[ERROR] stderr: {second.stderr.strip()[:500]}", "ERROR")
        return False


def validate_kernel_requirements(print_status):
    """Validate kernel configuration requirements for Cilium"""
    
    print_status("[INFO] Validating kernel configuration for Cilium...", "INFO")
    
    # Critical BPF requirements
    bpf_configs = {
        'CONFIG_BPF': 'y',
        'CONFIG_BPF_SYSCALL': 'y', 
        'CONFIG_BPF_JIT': 'y',
        'CONFIG_CGROUP_BPF': 'y',
        'CONFIG_PERF_EVENTS': 'y',
        'CONFIG_SCHEDSTATS': 'y'
    }
    
    # Networking requirements
    # NOTE: VXLAN and GENEVE are acceptable as built-in (y) OR loadable module (m) if the module
    # can be resolved via modprobe dry-run. We keep CONFIG_FIB_RULES strict.
    network_configs = {
        'CONFIG_VXLAN': 'y',
        'CONFIG_GENEVE': 'y',
        'CONFIG_FIB_RULES': 'y'
    }
    
    # Optional but recommended for iptables masquerading
    iptables_configs = {
        'CONFIG_NETFILTER_XT_SET': 'm',
        'CONFIG_IP_SET': 'm', 
        'CONFIG_IP_SET_HASH_IP': 'm',
        'CONFIG_NETFILTER_XT_MATCH_COMMENT': 'm'
    }
    
    warnings = []
    errors = []
    
    # Check BPF configs (critical)
    for config, required_value in bpf_configs.items():
        result = check_kernel_config(config, required_value)
        if result is True:
            print_status(f"[SUCCESS] {config}={required_value} ✓", "SUCCESS")
        elif result is False:
            errors.append(f"{config} should be {required_value}")
            print_status(f"[ERROR] {config} is not set to {required_value}", "ERROR")
        else:
            warnings.append(f"Unable to verify {config}")
            print_status(f"[WARNING] Unable to verify {config}", "WARNING")
    
    # Check networking configs (VXLAN/GENEVE allow module fallback)
    for config, required_value in network_configs.items():
        result = check_kernel_config(config, required_value)
        if result is True:
            print_status(f"[SUCCESS] {config}={required_value} ✓", "SUCCESS")
            continue
        # For VXLAN / GENEVE attempt module load fallback if not built-in
        if result is False and config in ("CONFIG_VXLAN", "CONFIG_GENEVE"):
            module_name = config.replace('CONFIG_', '').lower()
            modprobe = subprocess.run(['modprobe', '-n', module_name], capture_output=True, text=True)
            if modprobe.returncode == 0:
                print_status(f"[SUCCESS] {config} available as module (modprobe {module_name}) ✓", "SUCCESS")
                continue
            else:
                errors.append(f"{config} should be built-in or available as module")
                print_status(f"[ERROR] {config} not built-in and module not found", "ERROR")
                continue
        if result is False:
            errors.append(f"{config} should be {required_value}")
            print_status(f"[ERROR] {config} is not set to {required_value}", "ERROR")
        else:
            warnings.append(f"Unable to verify {config}")
            print_status(f"[WARNING] Unable to verify {config}", "WARNING")
    
    # Check iptables configs (optional)
    for config, required_value in iptables_configs.items():
        result = check_kernel_config(config, required_value)
        if result is True:
            print_status(f"[SUCCESS] {config}={required_value} ✓", "SUCCESS")
        elif result is False:
            warnings.append(f"{config} should be {required_value} for iptables masquerading")
            print_status(f"[WARNING] {config} not set - iptables masquerading may not work", "WARNING")
        else:
            print_status(f"[INFO] Unable to verify {config} (optional)", "INFO")
    
    return len(errors) == 0, warnings, errors


def validate_kernel_version(print_status):
    """Validate minimum kernel version for Cilium"""
    
    try:
        # Get kernel version
        result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
        if result.returncode != 0:
            print_status("[ERROR] Unable to determine kernel version", "ERROR")
            return False
            
        kernel_version = result.stdout.strip()
        print_status(f"[INFO] Current kernel version: {kernel_version}", "INFO")
        
        # Parse version numbers
        version_parts = kernel_version.split('.')
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        
        # Check minimum requirements
        min_major = 5
        min_minor = 10
        
        # Special case for RHEL 8.6+ which has backported features to 4.18
        rhel_exception = False
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read()
                if 'Red Hat' in os_info or 'RHEL' in os_info:
                    if major == 4 and minor >= 18:
                        rhel_exception = True
                        print_status("[INFO] RHEL detected - kernel 4.18+ acceptable with backports", "INFO")
        except Exception:
            pass
        
        # Validate version
        if major > min_major or (major == min_major and minor >= min_minor):
            print_status(f"[SUCCESS] Kernel version {kernel_version} meets minimum requirements (≥ 5.10)", "SUCCESS")
            return True
        elif rhel_exception:
            print_status(f"[SUCCESS] Kernel version {kernel_version} acceptable for RHEL (≥ 4.18)", "SUCCESS")
            return True
        else:
            print_status(f"[ERROR] Kernel version {kernel_version} below minimum requirement (≥ 5.10)", "ERROR")
            print_status("[ERROR] Please upgrade your kernel or use a compatible distribution", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"[ERROR] Failed to validate kernel version: {e}", "ERROR")
        return False


def ensure_bpf_filesystem(print_status):
    """Ensure BPF filesystem is mounted"""
    
    try:
        bpf_mount_point = '/sys/fs/bpf'
        
        # Check if BPF filesystem is already mounted
        result = subprocess.run(['mount'], capture_output=True, text=True)
        if f'{bpf_mount_point} type bpf' in result.stdout:
            print_status(f"[SUCCESS] BPF filesystem already mounted at {bpf_mount_point}", "SUCCESS")
            return True
        
        # Check if mount point exists
        if not os.path.exists(bpf_mount_point):
            print_status(f"[INFO] Creating BPF mount point {bpf_mount_point}...", "INFO")
            os.makedirs(bpf_mount_point, exist_ok=True)
        
        # Mount BPF filesystem
        print_status(f"[INFO] Mounting BPF filesystem at {bpf_mount_point}...", "INFO")
        result = subprocess.run(['mount', '-t', 'bpf', 'bpf', bpf_mount_point], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_status(f"[SUCCESS] BPF filesystem mounted at {bpf_mount_point}", "SUCCESS")
            return True
        else:
            print_status(f"[ERROR] Failed to mount BPF filesystem: {result.stderr}", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"[ERROR] BPF filesystem setup failed: {e}", "ERROR")
        return False
    
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
            
            # Install kernel headers for BPF compilation (required for Cilium)
            print_status("[INFO] Installing kernel headers for BPF compilation...", "INFO")
            kernel_version = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip()
            subprocess.run(['apt-get', 'install', '-y', f'linux-headers-{kernel_version}'], check=True, capture_output=True)
            print_status("[SUCCESS] Kernel headers installed", "SUCCESS")
            
            # Install clang and llvm for BPF compilation
            clang_result = subprocess.run(['which', 'clang'], capture_output=True, text=True)
            if clang_result.returncode != 0:
                print_status("[INFO] Installing clang and llvm for BPF compilation...", "INFO")
                subprocess.run(['apt-get', 'install', '-y', 'clang', 'llvm'], check=True, capture_output=True)
                print_status("[SUCCESS] clang and llvm installed", "SUCCESS")
            else:
                print_status("[SUCCESS] clang and llvm already available", "SUCCESS")
            
            # Install essential Cilium runtime dependencies
            print_status("[INFO] Installing Cilium runtime dependencies...", "INFO")
            cilium_runtime_packages = [
                'iproute2',       # Network interface management
                'iptables',       # Netfilter rules (for non-BPF masquerading)
                'ipset',          # IP set management
                'kmod',           # Kernel module loading
                'ca-certificates' # TLS/SSL operations
            ]
            
            packages_to_install = []
            for package in cilium_runtime_packages:
                # Check if package is already installed
                result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
                if result.returncode != 0:
                    packages_to_install.append(package)
            
            if packages_to_install:
                print_status(f"[INFO] Installing missing packages: {', '.join(packages_to_install)}", "INFO")
                subprocess.run(['apt-get', 'install', '-y'] + packages_to_install, check=True, capture_output=True)
                print_status("[SUCCESS] Cilium runtime dependencies installed", "SUCCESS")
            else:
                print_status("[SUCCESS] All Cilium runtime dependencies already available", "SUCCESS")
                
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

    # Explicit verification of Kubernetes Python client (user requested assurance)
    print_status("[INFO] Verifying Kubernetes Python client installation...", "INFO")
    if not verify_kubernetes_client(venv_python, print_status):
        print_status("[ERROR] Kubernetes Python client is required but could not be verified.", "ERROR")
        print_status("[ERROR] Please check network connectivity or install manually: .venv/bin/pip install kubernetes", "ERROR")
        sys.exit(1)
    
    # Validate kernel and system requirements for Cilium
    if not skip_deps:
        print_status("[INFO] Validating system requirements for Cilium...", "INFO")
        
        # Validate kernel version
        kernel_valid = validate_kernel_version(print_status)
        if not kernel_valid:
            print_status("[WARNING] Kernel version may cause issues with Cilium", "WARNING")
        
        # Validate kernel configuration
        config_valid, warnings, errors = validate_kernel_requirements(print_status)
        if errors:
            print_status("[ERROR] Critical kernel configuration issues found:", "ERROR")
            for error in errors:
                print_status(f"[ERROR]   - {error}", "ERROR")
            print_status("[ERROR] These configurations are required for Cilium to function properly", "ERROR")
            print_status("[INFO] Consider recompiling your kernel with the required options", "INFO")
        
        if warnings:
            print_status("[WARNING] Kernel configuration warnings:", "WARNING")
            for warning in warnings:
                print_status(f"[WARNING]   - {warning}", "WARNING")
        
        # Ensure BPF filesystem is mounted (try to mount if needed)
        if is_root:
            ensure_bpf_filesystem(print_status)
        else:
            print_status("[INFO] Checking BPF filesystem mount (requires root to fix)...", "INFO")
            bpf_mount_point = '/sys/fs/bpf'
            result = subprocess.run(['mount'], capture_output=True, text=True)
            if f'{bpf_mount_point} type bpf' in result.stdout:
                print_status(f"[SUCCESS] BPF filesystem mounted at {bpf_mount_point}", "SUCCESS")
            else:
                print_status(f"[WARNING] BPF filesystem not mounted at {bpf_mount_point}", "WARNING")
                print_status("[INFO] Run 'sudo mount -t bpf bpf /sys/fs/bpf' to mount it", "INFO")
    
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
    click.echo("2. Use NOAH: python noah.py --help")
    click.echo("")
    click.echo("Quick start:")
    click.echo("  python noah.py cluster create --name my-cluster")
    click.echo("  python noah.py deploy all --domain my-domain.com")
    click.echo("")
    print_status("[SUCCESS] Setup completed successfully!", "SUCCESS")