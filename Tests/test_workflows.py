#!/usr/bin/env python3
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
NOAH Workflow Test Simulation
Test script to simulate GitHub Workflow actions and validate project structure.
"""

import subprocess
from pathlib import Path


def run_command(command, description):
    """Run a shell command; assert success."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    assert result.returncode == 0, f"{description} failed: {result.stderr.strip()}"
    print(f"✅ {description}")


def test_python_syntax():
    """Test Python syntax validation for all Python files."""
    print("📍 Testing Python syntax...")
    
    # Test main noah.py file
    run_command("python3 -m py_compile noah.py", "noah.py syntax validation")
    
    # Test all Scripts/*.py files
    scripts_dir = Path("Scripts")
    if scripts_dir.exists():
        for script_file in scripts_dir.glob("*.py"):
            run_command(f"python3 -m py_compile {script_file}", f"{script_file.name} syntax validation")
    
        # Always succeed


def test_noah_cli():
    """Test NOAH CLI functionality."""
    print("\n📍 Testing NOAH CLI...")
    run_command("python3 noah.py --help > /dev/null 2>&1", "NOAH CLI functionality")
        # Always succeed


def test_module_imports():
    """Test module imports."""
    print("\n📍 Testing module imports...")
    try:
        # Direct package-style imports reflecting actual structure
        from Scripts.utils.config_loader import ConfigLoader  # noqa: F401
        from Scripts.security.security_manager import NoahSecurityManager  # noqa: F401
        from Scripts.core_helm.cluster_manager import ClusterManager  # noqa: F401
        from Scripts.gitops.gitops_init import setup_gitops  # noqa: F401
        print("✅ Module imports successful")
    except Exception as e:
        assert False, f"Module import errors: {e}"


def test_ansible_playbooks():
    """Test Ansible playbook syntax."""
    print("\n📍 Testing Ansible playbooks...")
    
    ansible_dir = Path("Ansible")
    if not ansible_dir.exists():
        print("⚠️  Ansible directory not found")
        return
    
    import shutil
    import subprocess
    if shutil.which("ansible-playbook") is None:
        print("⚠️  ansible-playbook not installed; skipping syntax checks")
        return

    failures = []
    for playbook in ansible_dir.glob("*.yml"):
        result = subprocess.run(
            ["ansible-playbook", "--syntax-check", str(playbook)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"✅ {playbook.name} syntax validation")
        else:
            print(f"❌ {playbook.name} syntax error (rc={result.returncode})")
            failures.append(playbook.name)
    if failures:
        assert False, f"Ansible syntax failures: {', '.join(failures)}"
    
        # Always succeed


def generate_statistics():
    """Generate project statistics."""
    print("\n📍 Generating statistics...")
    
    # Best-effort statistics; shouldn't fail tests
    try:
        python_files = len(list(Path(".").rglob("*.py")))
        ansible_files = len(list(Path("Ansible").glob("*.yml"))) if Path("Ansible").exists() else 0
        helm_charts = len([d for d in Path("Helm").iterdir() if d.is_dir() and (d / "templates").exists()]) if Path("Helm").exists() else 0
        doc_files = len(list(Path("Docs").glob("*.md"))) if Path("Docs").exists() else 0
        workflow_files = len(list(Path(".github/workflows").glob("*.yml"))) if Path(".github/workflows").exists() else 0
        print("📊 Statistics:")
        print(f"   - Python files: {python_files}")
        print(f"   - Ansible playbooks: {ansible_files}")
        print(f"   - Helm charts: {helm_charts}")
        print(f"   - Documentation files: {doc_files}")
        print(f"   - Workflow files: {workflow_files}")
    except Exception as e:
        print(f"❌ Error generating statistics: {e}")


def test_generate_statistics():
    """Non-failing statistics helper as a test for visibility."""
    generate_statistics()

