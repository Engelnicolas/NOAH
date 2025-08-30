#!/usr/bin/env python3
"""
Test the specific modifications we made to noah.py
"""

import sys
import os
from unittest.mock import Mock, patch
from click.testing import CliRunner

# Add project root to sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import noah

def test_cluster_create_with_destroy():
    """Test that cluster create runs destroy first"""
    print("Testing cluster create with pre-destroy...")
    
    runner = CliRunner()
    
    with patch('noah.ConfigLoader'), \
         patch('noah.ClusterManager'), \
         patch('noah.SecretManager'), \
         patch('noah.HelmDeployer'), \
         patch('noah.AnsibleRunner') as mock_ansible:
        
        mock_ansible_instance = Mock()
        mock_ansible.return_value = mock_ansible_instance
        
        result = runner.invoke(noah.cli, ['cluster', 'create', '--name', 'test-cluster'])
        
        # Check that verbose output shows destroy then create
        output = result.output
        assert '[VERBOSE] Starting cluster creation process...' in output
        assert '[VERBOSE] Ensuring no existing cluster exists...' in output
        assert '[VERBOSE] Running cluster cleanup: cluster-destroy.yml' in output
        assert '[VERBOSE] Cluster cleanup completed' in output
        assert '[VERBOSE] Running Ansible playbook: cluster-create.yml' in output
        
        print("✓ Cluster create correctly runs destroy first")
        return True

def test_authentik_standalone_deployment():
    """Test that authentik deployment works in standalone mode"""
    print("Testing Authentik standalone deployment...")
    
    runner = CliRunner()
    
    with patch('noah.ConfigLoader'), \
         patch('noah.SecretManager'), \
         patch('noah.HelmDeployer'), \
         patch('noah.AnsibleRunner'):
        
        result = runner.invoke(noah.cli, ['deploy', 'authentik'])
        
        # Check that it deploys directly without dependencies
        output = result.output
        assert '[VERBOSE] Deploying Authentik SSO...' in output
        assert '[VERBOSE] Generating secrets for Authentik...' in output
        assert '[VERBOSE] Running Ansible playbook: deploy-authentik.yml' in output
        
        print("✓ Authentik deployment works in standalone mode")
        return True

def test_verbose_output_presence():
    """Test that verbose output is present in all commands"""
    print("Testing verbose output presence...")
    
    runner = CliRunner()
    
    # Test various commands for verbose output
    commands_to_test = [
        (['secrets', 'init'], '[VERBOSE] Starting secret management initialization...'),
        (['deploy', 'authentik'], '[VERBOSE] Deploying Authentik SSO...'),
        (['deploy', 'cilium'], '[VERBOSE] Starting Cilium deployment process...'),
    ]
    
    for cmd, expected_verbose in commands_to_test:
        with patch('noah.ConfigLoader'), \
             patch('noah.ClusterManager'), \
             patch('noah.SecretManager'), \
             patch('noah.HelmDeployer'), \
             patch('noah.AnsibleRunner'):
            
            result = runner.invoke(noah.cli, cmd)
            
            if expected_verbose in result.output:
                print(f"✓ Verbose output found in: {' '.join(cmd)}")
            else:
                print(f"✗ Verbose output missing in: {' '.join(cmd)}")
                return False
    
    return True

def main():
    """Run modification-specific tests"""
    print("=" * 60)
    print("NOAH Modification Tests")
    print("=" * 60)
    
    tests = [
        test_cluster_create_with_destroy,
        test_authentik_standalone_deployment,
        test_verbose_output_presence
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n{'-' * 40}")
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
        print(f"{'-' * 40}")
    
    print(f"\n{'=' * 60}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All modification tests passed!")
        return 0
    else:
        print("❌ Some modification tests failed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
