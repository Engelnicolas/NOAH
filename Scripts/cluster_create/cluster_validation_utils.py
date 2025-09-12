"""
NOAH cluster validation utilities
"""

import subprocess
import shutil
from pathlib import Path


def check_existing_cluster():
    """Check if a K3s cluster or related components exist"""
    try:
        # Check for existing K3s processes
        result = subprocess.run(['pgrep', '-f', 'k3s'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Check for existing K3s service
        result = subprocess.run(['systemctl', 'is-active', 'k3s'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Check for existing kubectl context
        result = subprocess.run(['kubectl', 'cluster-info'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Check for existing NOAH data directories
        data_dirs = ['/var/lib/rancher/k3s', '/etc/rancher/k3s', '/run/k3s']
        for dir_path in data_dirs:
            if Path(dir_path).exists():
                return True
        
        # Check for existing Helm releases (only if cluster is accessible)
        if shutil.which('helm') and subprocess.run(['kubectl', 'cluster-info'], capture_output=True).returncode == 0:
            result = subprocess.run(['helm', 'list', '--all-namespaces', '-o', 'json'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != '[]':
                return True
        
        return False
    except Exception:
        # If any check fails, assume no cluster exists
        return False
    
    return True