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

import os
import subprocess
import sys
from pathlib import Path

import click

# The same helpers the store itself uses. Re-deriving the encryption mode here
# is what let this check and the store drift apart in the first place; the
# private name is imported deliberately, to keep one source of truth.
from Scripts.security.canonical_store import (
    _environment_is_locked,
    plaintext_reason,
    resolve_age_key_file,
)

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
    
    # Check the canonical store's effective encryption mode.
    #
    # This replaces a glob over Age/ for "*.key or keys.txt", which reported
    # "✓ Age keys configured" for a key name the store never reads -- confirming
    # a protection that was not there. Asking the store's own function removes
    # the possibility of the two disagreeing again.
    #
    # Deliberately does NOT construct a store: in a locked environment the
    # constructor raises in exactly the case this check exists to report, which
    # would leave doctor silent precisely when it must speak.
    age_key_file = resolve_age_key_file(Path.cwd())
    reason = plaintext_reason(age_key_file)
    store_insecure = False
    if reason is None:
        print_status(f"✓ Canonical store: encrypted (Age key: {age_key_file})", "SUCCESS")
    else:
        declared = os.environ.get("NOAH_ENVIRONMENT") or "unset → treated as production"
        if _environment_is_locked():
            store_insecure = True
            print_status(f"✗ Canonical store: PLAINTEXT — {reason.value}", "ERROR")
            print_status(f"  Environment: {declared} — this configuration is refused at runtime.", "ERROR")
            issues.append(f"Canonical store would be written in plaintext: {reason.value}")
        else:
            print_status(f"⚠ Canonical store: PLAINTEXT — {reason.value}", "WARNING")
            print_status(f"  Allowed because NOAH_ENVIRONMENT={declared}.", "WARNING")
            issues.append(f"Canonical store unencrypted: {reason.value}")

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

    # Fail the command outright: a plaintext store in a locked environment is
    # not an advisory item, it is the condition that blocks every write.
    if store_insecure:
        sys.exit(1)