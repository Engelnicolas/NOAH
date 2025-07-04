#!/usr/bin/env python3
"""
NOAH Shell Scripts Validation Tool
Validates all shell scripts for syntax and common issues
"""
import os
import subprocess
import sys
from pathlib import Path
import re

def check_bash_syntax(script_path):
    """Check bash syntax using bash -n"""
    try:
        result = subprocess.run(['bash', '-n', str(script_path)], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True, "Syntax OK"
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, f"Error checking syntax: {e}"

def check_common_issues(script_path):
    """Check for common shell script issues"""
    issues = []
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [f"Cannot read file: {e}"]
    
    # Check shebang
    if not content.startswith('#!'):
        issues.append("Missing shebang line")
    elif not content.startswith('#!/bin/bash') and not content.startswith('#!/usr/bin/env bash'):
        if content.startswith('#!/bin/sh'):
            issues.append("Using /bin/sh instead of bash - may cause compatibility issues")
    
    # Check for unquoted variables
    unquoted_vars = re.findall(r'\$[A-Za-z_][A-Za-z0-9_]*(?![}"])', content)
    if unquoted_vars:
        # Filter common safe cases
        safe_vars = {'$?', '$!', '$$', '$#', '$@', '$*'}
        unsafe_vars = [var for var in set(unquoted_vars) if var not in safe_vars]
        if unsafe_vars:
            issues.append(f"Potentially unquoted variables: {', '.join(unsafe_vars[:5])}")
    
    # Check for set -e or set -euo pipefail
    has_error_handling = any(
        re.search(r'set\s+-[euo]*e', line) or 
        re.search(r'set\s+-euo\s+pipefail', line)
        for line in lines[:20]  # Check first 20 lines
    )
    if not has_error_handling:
        issues.append("Missing 'set -e' or 'set -euo pipefail' for error handling")
    
    # Check for dangerous patterns
    dangerous_patterns = [
        (r'rm\s+-rf\s+\$', "Potentially dangerous 'rm -rf $var' without quotes"),
        (r'eval\s+\$', "Use of eval with variable - potential security risk"),
        (r'`[^`]*`', "Use of backticks instead of $() - deprecated syntax"),
    ]
    
    for pattern, message in dangerous_patterns:
        if re.search(pattern, content):
            issues.append(message)
    
    # Check for TODO/FIXME comments
    todo_count = len(re.findall(r'#.*(?:TODO|FIXME|XXX)', content, re.IGNORECASE))
    if todo_count > 0:
        issues.append(f"Contains {todo_count} TODO/FIXME comments")
    
    # Check file permissions (should be executable)
    if not os.access(script_path, os.X_OK):
        issues.append("File is not executable")
    
    return issues

def check_script_structure(script_path):
    """Check script structure and best practices"""
    issues = []
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return [f"Cannot read file: {e}"]
    
    # Check for function definitions
    has_functions = bool(re.search(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(\s*\)\s*\{', content, re.MULTILINE))
    
    # Check for main function or script logic organization
    has_main = bool(re.search(r'^\s*main\s*\(\s*\)', content, re.MULTILINE))
    
    # Check script length
    line_count = len([line for line in lines if line.strip()])
    if line_count > 500:
        issues.append(f"Script is quite long ({line_count} lines) - consider splitting into functions or modules")
    
    # Check for proper variable declarations
    local_vars = re.findall(r'local\s+[a-zA-Z_][a-zA-Z0-9_]*', content)
    global_assignments = re.findall(r'^[a-zA-Z_][a-zA-Z0-9_]*=', content, re.MULTILINE)
    
    if has_functions and not local_vars and global_assignments:
        issues.append("Functions found but no 'local' variable declarations - may cause variable conflicts")
    
    # Check for hardcoded paths
    hardcoded_paths = re.findall(r'(?:/usr/|/opt/|/home/)[a-zA-Z0-9_/.-]+', content)
    if hardcoded_paths:
        # Filter out common system paths
        suspicious_paths = [p for p in set(hardcoded_paths) if '/usr/bin/' not in p and '/usr/sbin/' not in p]
        if suspicious_paths:
            issues.append(f"Hardcoded paths found: {', '.join(suspicious_paths[:3])}")
    
    return issues

def validate_script(script_path):
    """Comprehensive script validation"""
    print(f"\n📝 Validating: {script_path.name}")
    
    all_issues = []
    
    # 1. Check bash syntax
    syntax_ok, syntax_msg = check_bash_syntax(script_path)
    if not syntax_ok:
        print(f"  ❌ Syntax Error: {syntax_msg}")
        return False
    else:
        print(f"  ✅ Syntax: {syntax_msg}")
    
    # 2. Check common issues
    common_issues = check_common_issues(script_path)
    all_issues.extend(common_issues)
    
    # 3. Check structure
    structure_issues = check_script_structure(script_path)
    all_issues.extend(structure_issues)
    
    # Report issues
    if all_issues:
        print(f"  ⚠️  Issues found:")
        for issue in all_issues:
            print(f"    - {issue}")
        return False
    else:
        print(f"  ✅ No issues found")
        return True

def main():
    """Main validation function"""
    script_dir = Path(__file__).parent / 'Script'
    
    if not script_dir.exists():
        print("❌ Script directory not found")
        sys.exit(1)
    
    print("🔍 NOAH Shell Scripts Validation")
    print("=" * 50)
    
    # Find all shell scripts
    shell_scripts = list(script_dir.glob('*.sh'))
    
    if not shell_scripts:
        print("❌ No shell scripts found")
        sys.exit(1)
    
    print(f"Found {len(shell_scripts)} shell scripts to validate")
    
    valid_scripts = 0
    total_scripts = len(shell_scripts)
    
    for script in sorted(shell_scripts):
        if validate_script(script):
            valid_scripts += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Summary:")
    print(f"  Total scripts: {total_scripts}")
    print(f"  Valid scripts: {valid_scripts}")
    print(f"  Scripts with issues: {total_scripts - valid_scripts}")
    
    if valid_scripts == total_scripts:
        print("🎉 All scripts passed validation!")
        return 0
    else:
        print("⚠️  Some scripts have issues that should be addressed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
