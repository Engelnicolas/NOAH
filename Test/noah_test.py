#!/usr/bin/env python3
"""
N.O.A.H Comprehensive Test Suite
================================

A single script that handles all testing functionality for the NOAH project.
Combines Helm chart validation, YAML syntax checking, and project structure validation.
"""

import os
import sys
import yaml
import json
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class NOAHTestSuite:
    """Comprehensive test suite for NOAH project."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.setup_logging()
        self.charts_dir = Path("../Helm").resolve()
        self.project_root = Path("..").resolve()
        self.results = []
        self.errors = []
        self.warnings = []
        
        # Test configuration
        self.charts = [
            "gitlab", "grafana", "keycloak", "mattermost", "nextcloud",
            "oauth2-proxy", "openedr", "prometheus", "samba4", "wazuh"
        ]
    
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger('noah_tests')
    
    def run_command(self, command: List[str], cwd: Optional[str] = None, timeout: int = 300) -> Tuple[bool, str, str]:
        """Execute a shell command and return results."""
        try:
            self.logger.debug(f"Executing: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except FileNotFoundError:
            return False, "", f"Command not found: {command[0]}"
        except Exception as e:
            return False, "", str(e)
    
    def validate_yaml_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Validate YAML syntax of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)
        except Exception as e:
            return False, f"File error: {e}"
    
    def test_project_structure(self) -> bool:
        """Test basic project structure."""
        self.logger.info("🏗️  Testing project structure...")
        
        required_dirs = ["Helm", "Ansible", "Script", "Test", "docs"]
        required_files = ["README.md", "LICENSE", "CONTRIBUTING.md"]
        
        all_passed = True
        
        # Check directories
        for directory in required_dirs:
            dir_path = self.project_root / directory
            if not dir_path.exists() or not dir_path.is_dir():
                self.errors.append(f"Missing required directory: {directory}")
                all_passed = False
            else:
                self.logger.debug(f"✅ Directory found: {directory}")
        
        # Check files
        for file_name in required_files:
            file_path = self.project_root / file_name
            if not file_path.exists() or not file_path.is_file():
                self.errors.append(f"Missing required file: {file_name}")
                all_passed = False
            else:
                self.logger.debug(f"✅ File found: {file_name}")
        
        if all_passed:
            self.logger.info("✅ Project structure: PASSED")
        else:
            self.logger.error("❌ Project structure: FAILED")
        
        return all_passed
    
    def test_yaml_syntax(self) -> bool:
        """Test YAML syntax for configuration files."""
        self.logger.info("📝 Testing YAML syntax...")
        
        yaml_files = [
            "test_config.yaml",
            "../Ansible/vars/global.yml",
            "../Script/.yamllint.yml"
        ]
        
        all_passed = True
        
        for yaml_file in yaml_files:
            file_path = Path(yaml_file)
            if not file_path.is_absolute():
                file_path = self.project_root / file_path
            
            if file_path.exists():
                is_valid, error = self.validate_yaml_file(file_path)
                if not is_valid:
                    self.errors.append(f"YAML syntax error in {yaml_file}: {error}")
                    all_passed = False
                else:
                    self.logger.debug(f"✅ YAML valid: {yaml_file}")
            else:
                self.warnings.append(f"YAML file not found: {yaml_file}")
        
        if all_passed:
            self.logger.info("✅ YAML syntax: PASSED")
        else:
            self.logger.error("❌ YAML syntax: FAILED")
        
        return all_passed
    
    def test_helm_charts(self) -> bool:
        """Test all Helm charts comprehensively."""
        self.logger.info("⛑️  Testing Helm charts...")
        
        if not self.charts_dir.exists():
            self.errors.append(f"Charts directory not found: {self.charts_dir}")
            return False
        
        # Check if Helm is available
        helm_available, _, _ = self.run_command(["helm", "version"])
        if not helm_available:
            self.warnings.append("Helm CLI not available, skipping advanced tests")
        
        all_passed = True
        
        for chart_name in self.charts:
            chart_passed = self.test_single_chart(chart_name, helm_available)
            if not chart_passed:
                all_passed = False
        
        if all_passed:
            self.logger.info("✅ Helm charts: ALL PASSED")
        else:
            self.logger.error("❌ Helm charts: SOME FAILED")
        
        return all_passed
    
    def test_single_chart(self, chart_name: str, helm_available: bool) -> bool:
        """Test a single Helm chart."""
        self.logger.info(f"  📦 Testing chart: {chart_name}")
        chart_path = self.charts_dir / chart_name
        chart_passed = True
        
        # Test 1: Chart structure
        if not chart_path.exists() or not chart_path.is_dir():
            self.errors.append(f"{chart_name}: Chart directory not found")
            return False
        
        required_files = ["Chart.yaml", "values.yaml"]
        for file_name in required_files:
            file_path = chart_path / file_name
            if not file_path.exists():
                self.errors.append(f"{chart_name}: Missing {file_name}")
                chart_passed = False
            else:
                # Validate YAML syntax
                is_valid, error = self.validate_yaml_file(file_path)
                if not is_valid:
                    self.errors.append(f"{chart_name}/{file_name}: {error}")
                    chart_passed = False
        
        # Test 2: Chart metadata validation
        chart_yaml = chart_path / "Chart.yaml"
        if chart_yaml.exists():
            try:
                with open(chart_yaml, 'r') as f:
                    chart_data = yaml.safe_load(f)
                
                required_fields = ['apiVersion', 'name', 'version']
                for field in required_fields:
                    if field not in chart_data:
                        self.errors.append(f"{chart_name}: Missing {field} in Chart.yaml")
                        chart_passed = False
                
                if chart_data.get('apiVersion') not in ['v1', 'v2']:
                    self.errors.append(f"{chart_name}: Invalid apiVersion")
                    chart_passed = False
                    
            except Exception as e:
                self.errors.append(f"{chart_name}: Error reading Chart.yaml - {e}")
                chart_passed = False
        
        # Test 3: Helm lint (if available)
        if helm_available:
            success, stdout, stderr = self.run_command(["helm", "lint", str(chart_path)])
            if not success:
                self.errors.append(f"{chart_name}: Helm lint failed - {stderr}")
                chart_passed = False
        
        # Test 4: Template rendering (if Helm available)
        if helm_available:
            success, stdout, stderr = self.run_command(["helm", "template", "test", str(chart_path)])
            if not success:
                self.errors.append(f"{chart_name}: Template rendering failed - {stderr}")
                chart_passed = False
        
        if chart_passed:
            self.logger.info(f"    ✅ {chart_name}: PASSED")
        else:
            self.logger.error(f"    ❌ {chart_name}: FAILED")
        
        return chart_passed
    
    def test_security_basics(self) -> bool:
        """Basic security tests."""
        self.logger.info("🔒 Running basic security tests...")
        
        all_passed = True
        
        # Check for common security files
        security_files = [
            ".gitignore",
            "Script/.yamllint.yml"
        ]
        
        for file_name in security_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                self.warnings.append(f"Security-related file not found: {file_name}")
        
        # Check for potential secrets in files (basic check)
        try:
            success, stdout, stderr = self.run_command([
                "grep", "-r", "-i", 
                "--exclude-dir=.git",
                "--exclude-dir=node_modules",
                "password\\|secret\\|api[_-]?key",
                str(self.project_root)
            ])
            if success and stdout.strip():
                self.warnings.append("Potential secrets found in files (manual review needed)")
        except:
            pass  # grep might not be available
        
        self.logger.info("✅ Security basics: COMPLETED")
        return all_passed
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report."""
        total_errors = len(self.errors)
        total_warnings = len(self.warnings)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "overall_status": "PASSED" if total_errors == 0 else "FAILED"
            },
            "errors": self.errors,
            "warnings": self.warnings
        }
        
        return report
    
    def save_report(self, report: Dict[str, Any]) -> str:
        """Save report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"noah_test_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("🧪 N.O.A.H Test Suite Summary")
        print("=" * 60)
        
        summary = report["summary"]
        status = summary["overall_status"]
        
        if status == "PASSED":
            print("🎉 Overall Status: ✅ PASSED")
        else:
            print("💥 Overall Status: ❌ FAILED")
        
        print(f"📊 Errors: {summary['total_errors']}")
        print(f"⚠️  Warnings: {summary['total_warnings']}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        print("=" * 60)
    
    def run_all_tests(self) -> bool:
        """Run all test suites."""
        print("🧪 N.O.A.H Comprehensive Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test suites
        tests = [
            ("Project Structure", self.test_project_structure),
            ("YAML Syntax", self.test_yaml_syntax),
            ("Helm Charts", self.test_helm_charts),
            ("Security Basics", self.test_security_basics)
        ]
        
        all_passed = True
        for test_name, test_func in tests:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                self.errors.append(f"{test_name}: Unexpected error - {e}")
                all_passed = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Generate and save report
        report = self.generate_report()
        report["duration"] = duration
        report_file = self.save_report(report)
        
        # Print summary
        self.print_summary(report)
        print(f"\n📄 Detailed report saved: {report_file}")
        print(f"⏱️  Total duration: {duration:.2f} seconds")
        
        return all_passed


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="N.O.A.H Comprehensive Test Suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--charts-only", action="store_true", help="Run only Helm chart tests")
    parser.add_argument("--structure-only", action="store_true", help="Run only structure tests")
    
    args = parser.parse_args()
    
    # Change to the Test directory
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    suite = NOAHTestSuite(verbose=args.verbose)
    
    if args.charts_only:
        success = suite.test_helm_charts()
    elif args.structure_only:
        success = suite.test_project_structure()
    else:
        success = suite.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
