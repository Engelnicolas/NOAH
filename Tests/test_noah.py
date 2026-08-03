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
Test script for NOAH deployment functionality
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the parent directory to Python path to access Scripts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_noah_imports():
    """Test that all noah.py imports work correctly"""
    print("Testing noah.py imports...")
    try:
        from Scripts.core_helm.cluster_manager import ClusterManager  # noqa: F401
        from Scripts.security.security_manager import NoahSecurityManager  # noqa: F401
        from Scripts.utils.ansible_runner import AnsibleRunner  # noqa: F401
        from Scripts.utils.config_loader import ConfigLoader  # noqa: F401
        print("✓ All imports successful")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        assert False

def test_cli_structure():
    """Test that the CLI structure is correct"""
    print("Testing CLI structure...")
    try:
        import noah
        from click.testing import CliRunner

        runner = CliRunner()

        # Test main help
        result = runner.invoke(noah.cli, ['--help'])
        assert result.exit_code == 0
        assert 'NOAH - Network Operations & Automation Hub' in result.output
        print("✓ Main CLI help works")

        # Test cluster help
        result = runner.invoke(noah.cli, ['cluster', '--help'])
        assert result.exit_code == 0
        assert 'Manage Kubernetes cluster lifecycle' in result.output
        print("✓ Cluster command help works")

        # deploy group has been removed — verify it no longer exists
        result = runner.invoke(noah.cli, ['deploy', '--help'])
        assert result.exit_code != 0, "deploy group should have been removed"
        print("✓ Deploy command correctly removed")

        # flux group exists (current GitOps path)
        result = runner.invoke(noah.cli, ['flux', '--help'])
        assert result.exit_code == 0
        print("✓ Flux command help works")

    except Exception as e:
        print(f"✗ CLI structure test failed: {e}")
        assert False


def test_verbose_functionality():
    """Test that verbose output is included"""
    print("Testing verbose functionality...")
    try:
        import noah
        from click.testing import CliRunner

        runner = CliRunner()

        # Test status command for verbose output
        with patch('noah.ConfigLoader'), \
             patch('noah.ClusterManager') as mock_cluster, \
             patch('noah.SecretManager'), \
             patch('noah.AnsibleRunner'):

            mock_cluster_instance = Mock()
            mock_cluster.return_value = mock_cluster_instance
            mock_cluster_instance.show_status.side_effect = Exception("Mocked error")

            result = runner.invoke(noah.cli, ['status'])

            assert '[VERBOSE] Gathering system status information...' in result.output
            print("✓ Verbose output detected in status command")

    except Exception as e:
        print(f"✗ Verbose functionality test failed: {e}")
        assert False

"""Pytest collects functions above; legacy main harness removed."""
