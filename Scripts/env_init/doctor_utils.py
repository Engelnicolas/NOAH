# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH - Network Operations & Automation Hub
# Copyright (C) 2026 Nicolas Engel <contact@nicolasengel.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
NOAH environment diagnosis utilities
"""

import click
import sys
import subprocess
from pathlib import Path
from .environment_initializer import check_command_exists


def print_status(message, status="INFO"):
    """Print colored status messages"""
    colors = {
        "INFO": "\033[0;34m",     # Blue
        "SUCCESS": "\033[0;32m",   # Green
        "WARNING": "\033[1;33m",   # Yellow
        "ERROR": "\033[0;31m",     # Red
    }
    reset = "\033[0m"
    click.echo(f"{colors.get(status, '')}{message}{reset}")


def diagnose_noah_environment(ctx):
    """Diagnose NOAH environment and dependencies"""
    click.echo("🔍 NOAH Environment Diagnosis")
    click.echo("=" * 35)
    click.echo("")
    
    issues = []
    
    # Check Python version
    python_version = sys.version.split()[0]
    if sys.version_info >= (3, 8):
        print_status(f"✓ Python {python_version}", "SUCCESS")
    else:
        print_status(f"✗ Python {python_version} (3.8+ required)", "ERROR")
        issues.append("Python version too old")
    
    # Check virtual environment
    venv_path = Path(".venv")
    if venv_path.exists():
        print_status("✓ Virtual environment exists", "SUCCESS")
    else:
        print_status("✗ Virtual environment missing", "ERROR")
        issues.append("No virtual environment")
    
    # Check requirements file (may live at Scripts/utils/ or Scripts/)
    req_file = next(
        (p for p in [Path("Scripts/utils/requirements.txt"), Path("Scripts/requirements.txt")] if p.exists()),
        None,
    )
    if req_file:
        print_status(f"✓ Requirements file found ({req_file})", "SUCCESS")
    else:
        print_status("✗ Requirements file missing", "ERROR")
        issues.append("Missing requirements.txt")
    
    # Check external dependencies
    external_deps = ['kubectl', 'helm', 'ansible', 'age']
    for cmd in external_deps:
        if check_command_exists(cmd):
            print_status(f"✓ {cmd} available", "SUCCESS")
        else:
            print_status(f"✗ {cmd} missing", "WARNING")
            issues.append(f"Missing {cmd}")
    
    # Check SOPS version specifically
    if check_command_exists('sops'):
        try:
            result = subprocess.run(['sops', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                # Extract version from output
                version = "unknown"
                for line in result.stdout.split('\n'):
                    if 'sops' in line.lower():
                        parts = line.split()
                        for part in parts:
                            if part.replace('.', '').replace('-', '').isdigit() or '.' in part:
                                version = part
                                break
                        break
                print_status(f"✓ SOPS version {version}", "SUCCESS")
                # Check if version is recent (3.8+)
                try:
                    major, minor = map(int, version.split('.')[:2])
                    if major < 3 or (major == 3 and minor < 8):
                        print_status("⚠ SOPS version is outdated (consider updating)", "WARNING")
                        issues.append("SOPS version outdated")
                except Exception:
                    pass
            else:
                print_status("✗ SOPS version check failed", "WARNING")
                issues.append("SOPS version check failed")
        except Exception:
            print_status("✗ SOPS available but version check failed", "WARNING")
            issues.append("SOPS version check failed")
    else:
        print_status("✗ SOPS missing", "ERROR")
        issues.append("Missing SOPS")
    
    # Check NOAH files
    noah_files = ['noah.py', 'Scripts/', 'Ansible/', 'flux-repo/']
    for file_path in noah_files:
        if Path(file_path).exists():
            print_status(f"✓ {file_path} exists", "SUCCESS")
        else:
            print_status(f"✗ {file_path} missing", "ERROR")
            issues.append(f"Missing {file_path}")
    
    # Check Age keys
    age_dir = Path("Age")
    if age_dir.exists() and (any(age_dir.glob("*.key")) or (age_dir / "keys.txt").exists()):
        print_status("✓ Age keys configured", "SUCCESS")
    else:
        print_status("⚠ Age keys not initialized", "WARNING")
        issues.append("Age keys need initialization")
    
    # Summary
    click.echo("")
    if not issues:
        print_status("🎉 All checks passed! NOAH is ready.", "SUCCESS")
    else:
        print_status(f"⚠ Found {len(issues)} issues:", "WARNING")
        for issue in issues:
            click.echo(f"  • {issue}")
        click.echo("")
        click.echo("Run 'python noah.py setup initialize' to fix most issues automatically.")