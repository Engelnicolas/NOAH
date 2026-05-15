#!/usr/bin/env python3
"""
Tests for noah.py CLI commands.
"""

import sys
import os
from unittest.mock import Mock, patch
from click.testing import CliRunner

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import noah


def test_cluster_create_removed():
    """Verify the deprecated cluster create command no longer exists."""
    print("Testing cluster create is removed...")

    runner = CliRunner()

    with patch('noah.ConfigLoader'), \
         patch('noah.ClusterManager'), \
         patch('noah.SecretManager'), \
         patch('noah.AnsibleRunner'):

        result = runner.invoke(noah.cli, ['cluster', 'create', '--help'])
        assert result.exit_code != 0, "cluster create should not exist"

    print("✓ Cluster create correctly removed")


def test_deploy_group_removed():
    """Verify the deprecated deploy group no longer exists."""
    print("Testing deploy group is removed...")

    runner = CliRunner()

    with patch('noah.ConfigLoader'), \
         patch('noah.ClusterManager'), \
         patch('noah.SecretManager'), \
         patch('noah.AnsibleRunner'):

        result = runner.invoke(noah.cli, ['deploy', '--help'])
        assert result.exit_code != 0, "deploy group should not exist"

    print("✓ Deploy group correctly removed")


def test_verbose_output_presence():
    """Test that verbose output is present in active commands."""
    print("Testing verbose output presence...")

    runner = CliRunner()

    commands_to_test = [
        (['secrets', 'init'], '[VERBOSE] Starting secret management initialization...'),
        (['secrets', 'generate', '--service', 'authentik'],
         '[VERBOSE] Starting secret generation process...'),
    ]

    for cmd, expected_verbose in commands_to_test:
        with patch('noah.ConfigLoader'), \
             patch('noah.ClusterManager'), \
             patch('noah.SecretManager'), \
             patch('noah.AnsibleRunner'), \
             patch('noah.ensure_security_initialized'):

            result = runner.invoke(noah.cli, cmd)

            assert expected_verbose in result.output, \
                f"Verbose output missing in {' '.join(cmd)}: {result.output}"
            print(f"✓ Verbose output found in: {' '.join(cmd)}")


def main():
    """Run all tests."""
    tests = [
        test_cluster_create_removed,
        test_deploy_group_removed,
        test_verbose_output_presence,
    ]

    passed = sum(1 for t in tests if _run(t))
    print(f"\nTest Results: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


def _run(test_fn):
    try:
        test_fn()
        return True
    except Exception as e:
        print(f"✗ {test_fn.__name__} failed: {e}")
        return False


if __name__ == '__main__':
    sys.exit(main())
