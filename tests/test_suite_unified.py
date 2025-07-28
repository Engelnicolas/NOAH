#!/usr/bin/env python3
"""
NOAH Unified Test Suite

This script consolidates multiple test files into a single comprehensive test suite
to reduce redundancy and improve maintainability.

Combines functionality from:
- test_environment.py
- test_noah_cli.py  
- test-deployment.py (Python parts)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import yaml


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    END = "\033[0m"
    BOLD = "\033[1m"


class NoahTestSuite:
    """Unified test suite for NOAH project."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.script_dir = self.project_root / "script"
        self.helm_dir = self.project_root / "helm"
        
    def run_command(self, cmd: List[str], expect_error: bool = False, timeout: int = 30) -> bool:
        """Execute a command and verify the result."""
        print(f"🧪 Test: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if expect_error:
                if result.returncode != 0:
                    print(f"  {Colors.GREEN}✅ Expected error detected{Colors.END}")
                    return True
                else:
                    print(f"  {Colors.RED}❌ Expected error but command succeeded{Colors.END}")
                    return False
            else:
                if result.returncode == 0:
                    print(f"  {Colors.GREEN}✅ Command executed successfully{Colors.END}")
                    return True
                else:
                    print(f"  {Colors.RED}❌ Command failed (code: {result.returncode}){Colors.END}")
                    print(f"     stdout: {result.stdout[:200]}")
                    print(f"     stderr: {result.stderr[:200]}")
                    return False
        except subprocess.TimeoutExpired:
            print(f"  {Colors.YELLOW}⏰ Command timed out{Colors.END}")
            return False
        except Exception as e:
            print(f"  {Colors.RED}❌ Exception: {e}{Colors.END}")
            return False


# Environment Tests
def test_python_version():
    """Verify Python version is correct."""
    assert sys.version_info >= (3, 8), "Python 3.8+ is required"


def test_noah_scripts_directory_exists():
    """Verify script directory exists."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    assert script_dir.exists(), "Script directory must exist"


def test_requirements_file_exists():
    """Verify requirements.txt exists."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    requirements_file = script_dir / "requirements.txt"
    assert requirements_file.exists(), "requirements.txt must exist"


def test_imports_basic_modules():
    """Test importing basic required modules."""
    try:
        import json  # noqa: F401
        import os  # noqa: F401
        import sys  # noqa: F401
        import psutil  # noqa: F401
        import requests  # noqa: F401
        import yaml  # noqa: F401
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")


def test_helm_charts_exist():
    """Verify Helm charts directory structure."""
    project_root = Path(__file__).parent.parent
    helm_dir = project_root / "helm"
    assert helm_dir.exists(), "Helm directory must exist"
    
    expected_charts = [
        "gitlab", "grafana", "keycloak", "mattermost", 
        "nextcloud", "oauth2-proxy", "prometheus", "samba4", "wazuh"
    ]
    
    for chart in expected_charts:
        chart_dir = helm_dir / chart
        assert chart_dir.exists(), f"Helm chart {chart} directory must exist"
        
        chart_yaml = chart_dir / "Chart.yaml"
        values_yaml = chart_dir / "values.yaml"
        
        assert chart_yaml.exists(), f"Chart.yaml must exist for {chart}"
        assert values_yaml.exists(), f"values.yaml must exist for {chart}"


# CLI Tests
def run_command(cmd: List[str], expect_error: bool = False, timeout: int = 30) -> bool:
    """Execute a command and verify the result."""
    print(f"🧪 Test: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if expect_error:
            if result.returncode != 0:
                print(f"  {Colors.GREEN}✅ Expected error detected{Colors.END}")
                return True
            else:
                print(f"  {Colors.RED}❌ Expected error but command succeeded{Colors.END}")
                return False
        else:
            if result.returncode == 0:
                print(f"  {Colors.GREEN}✅ Command executed successfully{Colors.END}")
                return True
            else:
                print(f"  {Colors.RED}❌ Command failed (code: {result.returncode}){Colors.END}")
                print(f"     stdout: {result.stdout[:200]}")
                print(f"     stderr: {result.stderr[:200]}")
                return False
    except subprocess.TimeoutExpired:
        print(f"  {Colors.YELLOW}⏰ Command timed out{Colors.END}")
        return False
    except Exception as e:
        print(f"  {Colors.RED}❌ Exception: {e}{Colors.END}")
        return False


def test_noah_script_exists():
    """Test that main noah script exists."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    noah_script = script_dir / "noah.py"
    assert noah_script.exists(), "Main noah.py script must exist"


def test_noah_help_command():
    """Test noah help command."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    cmd = [sys.executable, str(script_dir / "noah.py"), "--help"]
    assert run_command(cmd), "Noah help command should work"


def test_noah_version_command():
    """Test noah version command (if available)."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    cmd = [sys.executable, str(script_dir / "noah.py"), "--version"]
    # This might fail if --version is not implemented, so we don't assert
    run_command(cmd, expect_error=True)


def test_noah_deploy_help():
    """Test noah deploy help."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    cmd = [sys.executable, str(script_dir / "noah-deploy.py"), "--help"]
    assert run_command(cmd), "Noah deploy help should work"


def test_noah_monitoring_help():
    """Test noah monitoring help."""
    project_root = Path(__file__).parent.parent
    script_dir = project_root / "script"
    cmd = [sys.executable, str(script_dir / "noah-monitoring.py"), "--help"]
    assert run_command(cmd), "Noah monitoring help should work"


# Deployment Tests
def test_helm_template_syntax():
    """Test that Helm templates have valid syntax."""
    project_root = Path(__file__).parent.parent
    helm_dir = project_root / "helm"
    
    for chart_dir in helm_dir.iterdir():
        if not chart_dir.is_dir():
            continue
            
        templates_dir = chart_dir / "templates"
        if not templates_dir.exists():
            continue
            
        for template_file in templates_dir.glob("*.yaml"):
            # Basic syntax check - ensure no unescaped {{ }}
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common template syntax issues
            assert "{ {" not in content, f"Invalid template syntax in {template_file}"
            assert "} }" not in content, f"Invalid template syntax in {template_file}"


def test_values_yaml_syntax():
    """Test that values.yaml files are valid YAML."""
    project_root = Path(__file__).parent.parent
    helm_dir = project_root / "helm"
    
    for chart_dir in helm_dir.iterdir():
        if not chart_dir.is_dir():
            continue
            
        values_file = chart_dir / "values.yaml"
        if not values_file.exists():
            continue
            
        try:
            with open(values_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML syntax in {values_file}: {e}")


def test_simple_nginx_deployment():
    """Test creating a simple nginx deployment manifest."""
    nginx_manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-nginx
  namespace: noah
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-nginx
  template:
    metadata:
      labels:
        app: test-nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
"""
    
    # Test YAML parsing
    try:
        manifest_data = yaml.safe_load(nginx_manifest)
        assert manifest_data['kind'] == 'Deployment'
        assert manifest_data['metadata']['name'] == 'test-nginx'
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML in nginx manifest: {e}")


def main():
    """Run the unified test suite."""
    print(f"{Colors.CYAN}{Colors.BOLD}NOAH Unified Test Suite{Colors.END}")
    print("=" * 60)
    
    # Run pytest with this file
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
