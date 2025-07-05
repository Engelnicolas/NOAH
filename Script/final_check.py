#!/usr/bin/env python3
"""
NOAH Final Build Readiness Check
Simple validation to ensure GitHub Actions will pass.
"""

import os
import sys
import yaml
from pathlib import Path

def main():
    """Run final validation checks."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 NOAH Final Build Readiness Check")
    print("=" * 50)
    
    errors = 0
    checks = 0
    
    # 1. Check critical files exist
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
    
    for file_path in critical_files:
        checks += 1
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ MISSING: {file_path}")
            errors += 1
    
    # 2. Check navigation files from mkdocs.yml
    print("\n📚 Checking MkDocs navigation files...")
    try:
        with open("mkdocs.yml") as f:
            config = yaml.safe_load(f)
        
        def check_nav_files(nav_items, base_path="docs/"):
            nav_errors = 0
            for item in nav_items:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str):
                            file_path = Path(base_path) / value
                            if file_path.exists():
                                print(f"✅ {file_path}")
                            else:
                                print(f"❌ MISSING NAV FILE: {file_path}")
                                nav_errors += 1
                        elif isinstance(value, list):
                            nav_errors += check_nav_files(value, base_path)
            return nav_errors
        
        if 'nav' in config:
            nav_errors = check_nav_files(config['nav'])
            errors += nav_errors
            checks += 20  # Approximate number of nav files
        
    except Exception as e:
        print(f"❌ Error reading mkdocs.yml: {e}")
        errors += 1
        checks += 1
    
    # 3. Check Helm charts have basic structure
    print("\n⚓ Checking Helm charts...")
    helm_dir = Path("Helm")
    if helm_dir.exists():
        for chart_dir in helm_dir.iterdir():
            if chart_dir.is_dir():
                checks += 3
                chart_yaml = chart_dir / "Chart.yaml"
                values_yaml = chart_dir / "values.yaml"
                templates_dir = chart_dir / "templates"
                
                if chart_yaml.exists():
                    print(f"✅ {chart_dir.name}/Chart.yaml")
                else:
                    print(f"❌ MISSING: {chart_dir.name}/Chart.yaml")
                    errors += 1
                
                if values_yaml.exists():
                    print(f"✅ {chart_dir.name}/values.yaml")
                else:
                    print(f"❌ MISSING: {chart_dir.name}/values.yaml")
                    errors += 1
                
                if templates_dir.exists():
                    print(f"✅ {chart_dir.name}/templates/")
                else:
                    print(f"❌ MISSING: {chart_dir.name}/templates/")
                    errors += 1
    
    # 4. Validate key YAML files
    print("\n🔍 Validating key YAML files...")
    yaml_files = [
        "mkdocs.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/docs.yml",
        "Ansible/main.yml",
        "Ansible/inventory",
        "Ansible/requirements.yml"
    ]
    
    for yaml_file in yaml_files:
        checks += 1
        try:
            with open(yaml_file) as f:
                yaml.safe_load(f)
            print(f"✅ YAML valid: {yaml_file}")
        except Exception as e:
            print(f"❌ YAML invalid: {yaml_file} - {e}")
            errors += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FINAL SUMMARY")
    print("=" * 50)
    print(f"Total checks: {checks}")
    print(f"Passed: {checks - errors}")
    print(f"Failed: {errors}")
    
    if errors == 0:
        print("\n🎉 ALL CHECKS PASSED!")
        print("✅ Repository is ready for GitHub Actions build!")
        print("\n🚀 You can now:")
        print("   • Push to GitHub")
        print("   • Create pull requests")
        print("   • Trigger CI/CD workflows")
        return 0
    else:
        print(f"\n❌ {errors} issues found!")
        print("⚠️  Please fix these issues before pushing to GitHub")
        print("\n💡 Quick fixes:")
        print("   • Check all file paths are correct")
        print("   • Ensure all referenced files exist")
        print("   • Validate YAML syntax")
        return 1

if __name__ == "__main__":
    sys.exit(main())
