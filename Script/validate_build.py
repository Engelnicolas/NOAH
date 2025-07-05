#!/usr/bin/env python3
"""
NOAH Build Validation Script
Comprehensive validation for GitHub Actions readiness.
"""

import os
import sys
import yaml
import glob
import subprocess
from pathlib import Path

class BuildValidator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def log_error(self, message):
        self.errors.append(message)
        print(f"❌ {message}")
        
    def log_warning(self, message):
        self.warnings.append(message)
        print(f"⚠️  {message}")
        
    def log_success(self, message):
        self.successes.append(message)
        print(f"✅ {message}")
        
    def validate_yaml_file(self, filepath):
        """Validate a single YAML file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.log_error(f"YAML error in {filepath}: {e}")
            return False
        except Exception as e:
            self.log_error(f"Error reading {filepath}: {e}")
            return False
    
    def check_file_exists(self, filepath):
        """Check if a file exists."""
        full_path = self.project_root / filepath
        if full_path.exists():
            self.log_success(f"File exists: {filepath}")
            return True
        else:
            self.log_error(f"Missing file: {filepath}")
            return False
    
    def check_yaml_files(self):
        """Validate all YAML files."""
        print("\n🔍 Validating YAML files...")
        
        yaml_files = []
        for pattern in ['**/*.yml', '**/*.yaml']:
            yaml_files.extend(self.project_root.glob(pattern))
        
        valid_count = 0
        for yaml_file in yaml_files:
            if yaml_file.is_file():
                if self.validate_yaml_file(yaml_file):
                    valid_count += 1
        
        print(f"📊 Validated {valid_count}/{len(yaml_files)} YAML files")
        return len(self.errors) == 0
    
    def check_critical_files(self):
        """Check that all critical files exist."""
        print("\n📁 Checking critical files...")
        
        critical_files = [
            "mkdocs.yml",
            "LICENSE",
            "CONTRIBUTING.md", 
            "README.md",
            "docs/index.md",
            "docs/LICENSE.md",
            "docs/USER_GUIDE.md",
            "docs/charts/index.md",
            "docs/ansible/index.md",
            "docs/scripts/index.md",
            ".github/workflows/ci.yml",
            ".github/workflows/docs.yml",
            ".github/workflows/release.yml",
            ".github/workflows/dependencies.yml",
            "Ansible/main.yml",
            "Ansible/inventory",
            "Ansible/ansible.cfg",
            "Ansible/requirements.yml",
            "Ansible/vars/global.yml"
        ]
        
        all_exist = True
        for file_path in critical_files:
            if not self.check_file_exists(file_path):
                all_exist = False
        
        return all_exist
    
    def check_helm_charts(self):
        """Check Helm chart structure."""
        print("\n⚓ Checking Helm charts...")
        
        helm_dir = self.project_root / "Helm"
        if not helm_dir.exists():
            self.log_error("Helm directory does not exist")
            return False
        
        chart_dirs = [d for d in helm_dir.iterdir() if d.is_dir()]
        valid_charts = 0
        
        for chart_dir in chart_dirs:
            chart_yaml = chart_dir / "Chart.yaml"
            values_yaml = chart_dir / "values.yaml"
            templates_dir = chart_dir / "templates"
            
            if chart_yaml.exists() and values_yaml.exists() and templates_dir.exists():
                # Validate Chart.yaml
                if self.validate_yaml_file(chart_yaml):
                    # Validate values.yaml
                    if self.validate_yaml_file(values_yaml):
                        self.log_success(f"Helm chart valid: {chart_dir.name}")
                        valid_charts += 1
                    else:
                        self.log_error(f"Invalid values.yaml in {chart_dir.name}")
                else:
                    self.log_error(f"Invalid Chart.yaml in {chart_dir.name}")
            else:
                missing = []
                if not chart_yaml.exists():
                    missing.append("Chart.yaml")
                if not values_yaml.exists():
                    missing.append("values.yaml")
                if not templates_dir.exists():
                    missing.append("templates/")
                
                self.log_error(f"Helm chart {chart_dir.name} missing: {', '.join(missing)}")
        
        print(f"📊 Valid Helm charts: {valid_charts}/{len(chart_dirs)}")
        return valid_charts == len(chart_dirs)
    
    def check_script_permissions(self):
        """Check that scripts are executable."""
        print("\n🔧 Checking script permissions...")
        
        script_dirs = ["Script", "Test"]
        executable_count = 0
        total_scripts = 0
        
        for script_dir in script_dirs:
            script_path = self.project_root / script_dir
            if script_path.exists():
                for script_file in script_path.glob("*.sh"):
                    total_scripts += 1
                    if os.access(script_file, os.X_OK):
                        executable_count += 1
                    else:
                        self.log_warning(f"Script not executable: {script_file.name}")
                        # Fix the permission
                        try:
                            script_file.chmod(0o755)
                            self.log_success(f"Fixed permissions: {script_file.name}")
                            executable_count += 1
                        except Exception as e:
                            self.log_error(f"Could not fix permissions for {script_file.name}: {e}")
        
        print(f"📊 Executable scripts: {executable_count}/{total_scripts}")
        return True
    
    def check_mkdocs_config(self):
        """Validate MkDocs configuration."""
        print("\n📚 Checking MkDocs configuration...")
        
        mkdocs_yml = self.project_root / "mkdocs.yml"
        if not mkdocs_yml.exists():
            self.log_error("mkdocs.yml does not exist")
            return False
        
        if not self.validate_yaml_file(mkdocs_yml):
            return False
        
        # Check if referenced navigation files exist
        try:
            with open(mkdocs_yml, 'r') as f:
                config = yaml.safe_load(f)
            
            if 'nav' in config:
                missing_files = []
                self._check_nav_files(config['nav'], self.project_root / 'docs', missing_files)
                
                if missing_files:
                    for missing_file in missing_files:
                        self.log_error(f"Missing navigation file: {missing_file}")
                    return False
                else:
                    self.log_success("All MkDocs navigation files exist")
                    return True
            else:
                self.log_warning("No navigation defined in mkdocs.yml")
                return True
                
        except Exception as e:
            self.log_error(f"Error checking MkDocs navigation: {e}")
            return False
    
    def _check_nav_files(self, nav, docs_dir, missing_files):
        """Recursively check navigation files."""
        for item in nav:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, str):
                        file_path = docs_dir / value
                        if not file_path.exists():
                            missing_files.append(str(file_path.relative_to(self.project_root)))
                    elif isinstance(value, list):
                        self._check_nav_files(value, docs_dir, missing_files)
    
    def run_validation(self):
        """Run all validation checks."""
        print("🚀 Starting NOAH Build Validation")
        print("=" * 50)
        
        # Run all checks
        yaml_ok = self.check_yaml_files()
        files_ok = self.check_critical_files()
        helm_ok = self.check_helm_charts()
        scripts_ok = self.check_script_permissions()
        mkdocs_ok = self.check_mkdocs_config()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        print()
        
        if self.errors:
            print("❌ VALIDATION FAILED")
            print("\nErrors to fix:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  • {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
            print()
            print("💡 Quick fixes:")
            print("  • Run: ./Script/fix_build_issues.sh")
            print("  • Check file permissions: chmod +x Script/*.sh Test/*.sh")
            print("  • Validate YAML syntax manually")
            return False
        else:
            print("🎉 ALL VALIDATIONS PASSED!")
            print("\n✅ Your repository is ready for GitHub Actions build!")
            if self.warnings:
                print(f"\n⚠️  Note: {len(self.warnings)} warnings were found but won't prevent builds")
            return True

def main():
    validator = BuildValidator()
    success = validator.run_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
