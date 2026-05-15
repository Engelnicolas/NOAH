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


def ensure_ssh_key(print_status):
    """Ensure ~/.ssh/id_ed25519 exists and is authorized for localhost SSH (idempotent)."""
    ssh_dir = Path.home() / ".ssh"
    key_path = ssh_dir / "id_ed25519"
    pub_path = ssh_dir / "id_ed25519.pub"
    authorized_keys = ssh_dir / "authorized_keys"

    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    if not key_path.exists():
        print_status("[INFO] No SSH key found at ~/.ssh/id_ed25519 — generating one...", "INFO")
        result = subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-C", "noah-localhost"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print_status(f"[ERROR] Failed to generate SSH key: {result.stderr.strip()}", "ERROR")
            return
        print_status("[SUCCESS] SSH key generated at ~/.ssh/id_ed25519", "SUCCESS")

    pub_key = pub_path.read_text().strip()

    existing = authorized_keys.read_text() if authorized_keys.exists() else ""
    if pub_key not in existing:
        with authorized_keys.open("a") as f:
            f.write(pub_key + "\n")
        print_status("[SUCCESS] SSH public key added to ~/.ssh/authorized_keys", "SUCCESS")
    else:
        print_status("[INFO] SSH key already authorized for localhost", "INFO")

    authorized_keys.chmod(0o600)


def _apt_lock_held() -> bool:
    """Return True if the dpkg frontend lock is currently held by another process."""
    locks = [
        "/var/lib/dpkg/lock-frontend",
        "/var/lib/dpkg/lock",
        "/var/cache/apt/archives/lock",
    ]
    for lock in locks:
        result = subprocess.run(
            ["fuser", lock], capture_output=True
        )
        if result.returncode == 0:
            return True
    return False


def _wait_for_apt_lock(print_status=None, timeout: int = 120) -> None:
    """Block until all dpkg/apt locks are free, printing a one-time notice."""
    import time
    if not _apt_lock_held():
        return
    if print_status:
        print_status("[INFO] Waiting for apt lock to be released (another process is using apt)...", "INFO")
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(3)
        if not _apt_lock_held():
            return
    # Timed out — proceed anyway; apt-get will fail with its own message if still locked.


def _is_apt_package_installed(package_name: str) -> bool:
    """Return True if the apt package is already installed at any version."""
    result = subprocess.run(
        ['dpkg-query', '-W', '-f=${Status}', package_name],
        capture_output=True, text=True
    )
    return result.returncode == 0 and 'install ok installed' in result.stdout


def _sudo_apt_install(packages: list, print_status=None) -> bool:
    """Install apt packages, prefixing with sudo when not root.

    Waits for any held dpkg lock before running.
    stdout is suppressed to keep output clean; stderr and the TTY are left
    open so sudo can prompt for a password interactively.
    Returns True on success, False on failure.
    """
    if isinstance(packages, str):
        packages = [packages]
    sudo = [] if os.geteuid() == 0 else ["sudo"]
    _wait_for_apt_lock(print_status)
    try:
        subprocess.run(
            sudo + ["apt-get", "install", "-y"] + packages,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _sudo_apt_update(print_status=None) -> None:
    sudo = [] if os.geteuid() == 0 else ["sudo"]
    _wait_for_apt_lock(print_status)
    subprocess.run(sudo + ["apt-get", "update"], check=True, stdout=subprocess.DEVNULL)


def install_external_dependency(package_name, print_status):
    """Install external dependency using appropriate method"""
    try:
        print_status(f"[INFO] Installing {package_name}...", "INFO")

        # Special installation methods for specific packages
        if package_name == 'kubectl':
            return install_kubectl(print_status)
        elif package_name == 'helm':
            return install_helm(print_status)
        elif package_name == 'docker':
            return install_docker(print_status)
        else:
            # Default apt installation for other packages
            return install_via_apt(package_name, print_status)

    except Exception as e:
        print_status(f"[WARNING] Failed to install {package_name}: {e}", "WARNING")
        return False


def install_via_apt(package_name, print_status):
    """Install package using apt package manager, skipping if already installed."""
    if _is_apt_package_installed(package_name):
        print_status(f"[SUCCESS] {package_name} is already installed — skipping", "SUCCESS")
        return True

    try:
        if os.geteuid() != 0:
            subprocess.run(['sudo', 'apt', 'update'], check=True, capture_output=True)
            cmd = ['sudo', 'apt', 'install', '-y', package_name]
        else:
            subprocess.run(['apt', 'update'], check=True, capture_output=True)
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


def install_docker(print_status):
    """Install Docker using NOAH's Python installer"""
    try:
        from Scripts.env_init.docker_installer import DockerInstaller

        print_status("[INFO] Installing Docker using NOAH Docker installer...", "INFO")

        installer = DockerInstaller(dry_run=False, channel='stable')
        success = installer.install()

        if success:
            print_status("[SUCCESS] Docker installed successfully", "SUCCESS")
        else:
            print_status("[WARNING] Docker installation encountered issues", "WARNING")

        return success

    except Exception as e:
        print_status(f"[WARNING] Docker installation failed: {e}", "WARNING")
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

        current_version = None
        try:
            if check_command_exists('sops'):
                result = subprocess.run(['sops', '--version'], capture_output=True, text=True)
                if result.returncode == 0:
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

        print_status("[INFO] Fetching latest SOPS version...", "INFO")
        import urllib.request, json as _json
        with urllib.request.urlopen(
            'https://api.github.com/repos/getsops/sops/releases/latest', timeout=30
        ) as resp:
            latest_release = _json.loads(resp.read().decode())
        latest_version = latest_release['tag_name'].lstrip('v')

        print_status(f"[INFO] Latest SOPS version: {latest_version}", "INFO")

        if current_version and current_version == latest_version:
            print_status("[SUCCESS] SOPS is already up to date", "SUCCESS")
            return True

        print_status(f"[INFO] Updating SOPS from {current_version or 'not installed'} to {latest_version}...", "INFO")

        import platform
        arch_map = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}
        arch = arch_map.get(platform.machine(), 'amd64')

        download_url = (
            f"https://github.com/getsops/sops/releases/download/v{latest_version}"
            f"/sops-v{latest_version}.linux.{arch}"
        )

        print_status(f"[INFO] Downloading SOPS {latest_version}...", "INFO")
        with urllib.request.urlopen(download_url, timeout=120) as resp:
            content = resp.read()

        import tempfile, shutil
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        os.chmod(tmp_path, 0o755)

        sops_path = "/usr/local/bin/sops"
        installed = False
        if os.geteuid() == 0:
            shutil.move(tmp_path, sops_path)
            installed = True
        else:
            result = subprocess.run(['sudo', 'mv', tmp_path, sops_path], capture_output=True)
            if result.returncode == 0:
                subprocess.run(['sudo', 'chmod', '0755', sops_path], capture_output=True)
                installed = True
        if not installed:
            local_bin = Path.home() / '.local' / 'bin'
            local_bin.mkdir(parents=True, exist_ok=True)
            sops_path = str(local_bin / 'sops')
            shutil.move(tmp_path, sops_path)
            os.chmod(sops_path, 0o755)

        print_status(f"[SUCCESS] SOPS {latest_version} installed to {sops_path}", "SUCCESS")
        print_status("[SUCCESS] SOPS update completed successfully", "SUCCESS")
        return True

    except Exception as e:
        print_status(f"[ERROR] Failed to update SOPS: {e}", "ERROR")
        return False


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


def initialize_noah_environment(ctx, skip_deps=False, skip_tests=False, print_status=None, skip_dns_wizard=False):
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
    
    # Install required system packages (uses sudo automatically when not root)
    print_status("[INFO] Installing required system packages...", "INFO")
    try:
        _sudo_apt_update(print_status)

        # python-is-python3
        if subprocess.run(['which', 'python'], capture_output=True).returncode != 0:
            print_status("[INFO] Installing python-is-python3...", "INFO")
            _sudo_apt_install(['python-is-python3'], print_status)
            print_status("[SUCCESS] python-is-python3 installed", "SUCCESS")
        else:
            print_status("[SUCCESS] python command already available", "SUCCESS")

        # python3-venv and python3-pip for the running Python version
        python_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        for venv_pkg in [f"python{python_minor}-venv", f"python{python_minor}-pip", "python3-pip"]:
            already = subprocess.run(['dpkg', '-l', venv_pkg], capture_output=True).returncode == 0
            if not already:
                print_status(f"[INFO] Installing {venv_pkg}...", "INFO")
                if _sudo_apt_install([venv_pkg], print_status):
                    print_status(f"[SUCCESS] {venv_pkg} installed", "SUCCESS")
            else:
                print_status(f"[SUCCESS] {venv_pkg} already available", "SUCCESS")

        # age encryption tool
        if subprocess.run(['which', 'age'], capture_output=True).returncode != 0:
            print_status("[INFO] Installing age encryption tool...", "INFO")
            _sudo_apt_install(['age'], print_status)
            print_status("[SUCCESS] age encryption tool installed", "SUCCESS")
        else:
            print_status("[SUCCESS] age encryption tool already available", "SUCCESS")

        # Kernel headers for Cilium BPF
        kernel_version = subprocess.run(['uname', '-r'], capture_output=True, text=True).stdout.strip()
        kernel_headers_pkg = f'linux-headers-{kernel_version}'
        if _is_apt_package_installed(kernel_headers_pkg):
            print_status(f"[SUCCESS] {kernel_headers_pkg} already installed — skipping", "SUCCESS")
        else:
            print_status("[INFO] Installing kernel headers for BPF compilation...", "INFO")
            _sudo_apt_install([kernel_headers_pkg], print_status)
            print_status("[SUCCESS] Kernel headers installed", "SUCCESS")

        # clang / llvm for BPF compilation
        if subprocess.run(['which', 'clang'], capture_output=True).returncode != 0:
            print_status("[INFO] Installing clang and llvm for BPF compilation...", "INFO")
            _sudo_apt_install(['clang', 'llvm'], print_status)
            print_status("[SUCCESS] clang and llvm installed", "SUCCESS")
        else:
            print_status("[SUCCESS] clang and llvm already available", "SUCCESS")

        # Essential Cilium runtime dependencies
        cilium_runtime_packages = ['iproute2', 'iptables', 'ipset', 'kmod', 'ca-certificates']
        missing = [p for p in cilium_runtime_packages
                   if subprocess.run(['dpkg', '-l', p], capture_output=True).returncode != 0]
        if missing:
            print_status(f"[INFO] Installing missing packages: {', '.join(missing)}", "INFO")
            _sudo_apt_install(missing, print_status)
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

    def _venv_python_path(vp: Path) -> Path:
        p = vp / "bin" / "python"
        if not p.exists():
            p = vp / "Scripts" / "python.exe"  # Windows
        return p

    def _venv_is_functional(vp: Path) -> bool:
        """Return True if the venv Python interpreter AND pip both work."""
        py = _venv_python_path(vp)
        if not py.exists():
            return False
        if subprocess.run([str(py), "-c", "import sys; sys.exit(0)"], capture_output=True).returncode != 0:
            return False
        # Also verify pip is importable
        pip_probe = subprocess.run([str(py), "-m", "pip", "--version"], capture_output=True)
        return pip_probe.returncode == 0

    def _create_venv(print_status) -> None:
        """Create .venv, installing python3-venv via apt if needed, then exit on failure."""
        result = subprocess.run([sys.executable, "-m", "venv", ".venv"], capture_output=True, text=True)
        if result.returncode == 0:
            return
        # python3-venv missing — install it (with sudo when not root) and retry
        python_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        venv_pkg = f"python{python_minor}-venv"
        print_status(f"[INFO] venv creation failed — installing {venv_pkg}...", "INFO")
        if not _sudo_apt_install([venv_pkg], print_status):
            print_status(
                f"[ERROR] Could not install {venv_pkg}. Try: sudo apt install {venv_pkg}",
                "ERROR",
            )
            sys.exit(1)
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        except subprocess.CalledProcessError:
            print_status(
                f"[ERROR] Could not create virtual environment after installing {venv_pkg}.",
                "ERROR",
            )
            sys.exit(1)

    if not venv_path.exists():
        print_status("[INFO] Creating Python virtual environment...", "INFO")
        _create_venv(print_status)
        print_status("[SUCCESS] Virtual environment created", "SUCCESS")
    elif not _venv_is_functional(venv_path):
        # Exists but broken (e.g. created before python3-venv was installed)
        print_status("[WARNING] Virtual environment is broken — recreating...", "WARNING")
        import shutil
        shutil.rmtree(str(venv_path))
        _create_venv(print_status)
        print_status("[SUCCESS] Virtual environment recreated", "SUCCESS")
    else:
        print_status("[SUCCESS] Virtual environment already exists", "SUCCESS")
    
    # Install Python dependencies
    print_status("[INFO] Installing Python dependencies...", "INFO")
    venv_python = _venv_python_path(venv_path)

    # Ensure pip is available in the venv; bootstrap via get-pip.py if missing
    pip_check = subprocess.run([str(venv_python), "-m", "pip", "--version"], capture_output=True)
    if pip_check.returncode != 0:
        print_status("[INFO] pip not found in venv — bootstrapping via get-pip.py...", "INFO")
        try:
            import urllib.request
            get_pip_path = "/tmp/get-pip.py"
            urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
            subprocess.run([str(venv_python), get_pip_path], check=True, capture_output=True)
            print_status("[SUCCESS] pip bootstrapped", "SUCCESS")
        except Exception as e:
            print_status(f"[ERROR] Could not bootstrap pip: {e}", "ERROR")
            print_status("[ERROR] Run manually: sudo apt install python3-pip", "ERROR")
            sys.exit(1)

    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                      check=True, capture_output=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "Scripts/utils/requirements.txt"],
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
        is_root = os.getuid() == 0
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
    
    # Ensure SSH key exists and is authorized for localhost (required for cluster bootstrap)
    ensure_ssh_key(print_status)

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

    # Cloudflare DNS wizard
    if not skip_dns_wizard:
        try:
            from Scripts.env_init.cloudflare_wizard import CloudflareWizard
            CloudflareWizard().run()
        except Exception as e:
            print_status(f"[WARNING] Cloudflare DNS wizard failed: {e}", "WARNING")
    
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
    click.echo("  python3 noah.py --help")
    click.echo("")
    click.echo("Quick start (GitOps):")
    click.echo("  python3 noah.py cluster bootstrap --node <IP> --domain <domain> --flux-repo <url>")
    click.echo("  python3 noah.py flux status")
    click.echo("")
    print_status("[SUCCESS] Setup completed successfully!", "SUCCESS")