#!/usr/bin/env python3
"""
NOAH Helm Charts Validation Script
Validates all Helm charts for syntax and common issues
"""
import os
import yaml
import sys
from pathlib import Path

def validate_yaml_file(file_path):
    """Validate a YAML file"""
    try:
        with open(file_path, 'r') as f:
            yaml.safe_load(f)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def validate_chart_structure(chart_dir):
    """Validate basic Helm chart structure"""
    issues = []
    
    # Check required files
    required_files = ['Chart.yaml', 'values.yaml']
    for req_file in required_files:
        file_path = chart_dir / req_file
        if not file_path.exists():
            issues.append(f"Missing required file: {req_file}")
        else:
            valid, error = validate_yaml_file(file_path)
            if not valid:
                issues.append(f"{req_file}: {error}")
    
    # Check templates directory
    templates_dir = chart_dir / 'templates'
    if not templates_dir.exists():
        issues.append("Missing templates directory")
    
    return issues

def validate_chart_yaml(chart_dir):
    """Validate Chart.yaml specific requirements"""
    issues = []
    chart_file = chart_dir / 'Chart.yaml'
    
    if not chart_file.exists():
        return ["Missing Chart.yaml"]
    
    try:
        with open(chart_file, 'r') as f:
            chart_data = yaml.safe_load(f)
        
        # Check required fields
        required_fields = ['apiVersion', 'name', 'version', 'description']
        for field in required_fields:
            if field not in chart_data:
                issues.append(f"Chart.yaml missing required field: {field}")
        
        # Check apiVersion is v2
        if chart_data.get('apiVersion') != 'v2':
            issues.append(f"Chart.yaml should use apiVersion: v2, got: {chart_data.get('apiVersion')}")
            
    except Exception as e:
        issues.append(f"Error reading Chart.yaml: {e}")
    
    return issues

def check_template_syntax(templates_dir):
    """Basic check for template files"""
    issues = []
    
    if not templates_dir.exists():
        return ["Templates directory does not exist"]
    
    for template_file in templates_dir.glob('*.yaml'):
        # Check for basic template issues
        try:
            with open(template_file, 'r') as f:
                content = f.read()
                
            # Check for unmatched braces
            open_braces = content.count('{{')
            close_braces = content.count('}}')
            if open_braces != close_braces:
                issues.append(f"{template_file.name}: Unmatched template braces")
                
        except Exception as e:
            issues.append(f"{template_file.name}: Error reading file - {e}")
    
    return issues

def main():
    """Main validation function"""
    helm_dir = Path(__file__).parent / 'Helm'
    
    if not helm_dir.exists():
        print("❌ Helm directory not found")
        sys.exit(1)
    
    print("🔍 NOAH Helm Charts Validation")
    print("=" * 50)
    
    total_charts = 0
    valid_charts = 0
    
    for chart_dir in helm_dir.iterdir():
        if chart_dir.is_dir() and not chart_dir.name.startswith('.'):
            total_charts += 1
            print(f"\n📦 Validating chart: {chart_dir.name}")
            
            all_issues = []
            
            # Basic structure validation
            structure_issues = validate_chart_structure(chart_dir)
            all_issues.extend(structure_issues)
            
            # Chart.yaml validation
            chart_yaml_issues = validate_chart_yaml(chart_dir)
            all_issues.extend(chart_yaml_issues)
            
            # Template syntax validation
            template_issues = check_template_syntax(chart_dir / 'templates')
            all_issues.extend(template_issues)
            
            if all_issues:
                print(f"  ❌ Issues found:")
                for issue in all_issues:
                    print(f"    - {issue}")
            else:
                print(f"  ✅ Valid")
                valid_charts += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Summary:")
    print(f"  Total charts: {total_charts}")
    print(f"  Valid charts: {valid_charts}")
    print(f"  Charts with issues: {total_charts - valid_charts}")
    
    if valid_charts == total_charts:
        print("🎉 All charts are valid!")
        sys.exit(0)
    else:
        print("⚠️  Some charts have issues that need attention")
        sys.exit(1)

if __name__ == "__main__":
    main()
