#!/usr/bin/env python3
"""
Test script for NOAH deployment functionality
"""

import sys
import os
from unittest.mock import Mock, patch
from pathlib import Path

# Add the parent directory to Python path to access Scripts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_noah_imports():
    """Test that all noah.py imports work correctly"""
    print("Testing noah.py imports...")
    try:
        from Scripts.cluster_manager import ClusterManager
        from Scripts.noah_security_manager import NoahSecurityManager
        from Scripts.helm_deployer import HelmDeployer
        from Scripts.ansible_runner import AnsibleRunner
        from Scripts.config_loader import ConfigLoader
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

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
        
        # Test deploy help
        result = runner.invoke(noah.cli, ['deploy', '--help'])
        assert result.exit_code == 0
        assert 'Deploy services to Kubernetes' in result.output
        print("✓ Deploy command help works")
        
        return True
    except Exception as e:
        print(f"✗ CLI structure test failed: {e}")
        return False

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
             patch('noah.HelmDeployer'), \
             patch('noah.AnsibleRunner'):
            
            # Mock the cluster manager to avoid Kubernetes errors
            mock_cluster_instance = Mock()
            mock_cluster.return_value = mock_cluster_instance
            mock_cluster_instance.show_status.side_effect = Exception("Mocked error")
            
            result = runner.invoke(noah.cli, ['status'])
            
            # Check that verbose output appears
            assert '[VERBOSE] Gathering system status information...' in result.output
            print("✓ Verbose output detected in status command")
        
        return True
    except Exception as e:
        print(f"✗ Verbose functionality test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("NOAH Deployment Script Tests")
    print("=" * 60)
    
    tests = [
        test_noah_imports,
        test_cli_structure,
        test_verbose_functionality
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n{'-' * 40}")
        if test():
            passed += 1
        print(f"{'-' * 40}")
    
    print(f"\n{'=' * 60}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! NOAH deployment script is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
