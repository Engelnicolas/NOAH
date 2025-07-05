#!/usr/bin/env python3

"""
NOAH - Unified Fix Script
=========================
Combines: fix_yaml.py, validate_yaml.py, validate_build.py, final_check.py
Purpose: Single script for fixing and validating code issues
"""

import os
import sys
import yaml
import glob
import subprocess
import argparse
from pathlib import Path
import re


class NoahFixer:
    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.errors_found = 0
        
    def log(self, message, level="INFO"):
        colors = {
            "INFO": "\033[0;34m",
            "SUCCESS": "\033[0;32m", 
            "WARNING": "\033[0;33m",
            "ERROR": "\033[0;31m",
            "NC": "\033[0m"
        }
        if self.verbose or level in ["SUCCESS", "ERROR"]:
            print(f"{colors.get(level, '')}{level}: {message}{colors['NC']}")
    
    def fix_yaml_syntax(self, file_path):
        """Fix common YAML syntax issues"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Fix trailing spaces
            content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
            
            # Fix missing newline at end of file
            if content and not content.endswith('\n'):
                content += '\n'
            
            # Add document start if missing (for .yml files that don't start with ---)
            if not content.startswith('---') and not content.startswith('#'):
                content = '---\n' + content
            
            # Fix indentation issues and line length
            lines = content.split('\n')
            fixed_lines = []
            for line in lines:
                # Replace tabs with spaces
                line = line.replace('\t', '  ')
                
                # Fix common indentation patterns
                if line.strip().startswith('- name:'):
                    # Ensure task items are properly indented
                    if not line.startswith('  - name:') and not line.startswith('- name:'):
                        line = re.sub(r'^(\s*)- name:', r'\1- name:', line)
                
                # Fix line length issues by breaking long lines
                if len(line) > 80 and ':' in line and not line.strip().startswith('#'):
                    # Try to break long lines at appropriate points
                    if 'ansible.builtin.' in line or 'community.' in line:
                        # Module lines
                        match = re.match(r'^(\s+)(\w+):\s*(.+)$', line)
                        if match:
                            indent, key, value = match.groups()
                            if len(value) > 60:
                                line = f"{indent}{key}: >\n{indent}  {value}"
                
                fixed_lines.append(line)
            content = '\n'.join(fixed_lines)
            
            # Try to parse YAML to ensure validity (skip Helm templates)
            if not ('{{' in content and '}}' in content):
                try:
                    yaml.safe_load(content)
                except yaml.YAMLError as e:
                    self.log(f"YAML syntax error in {file_path}: {e}", "ERROR")
                    self.errors_found += 1
                    return
            
            if content != original_content:
                if not self.dry_run:
                    with open(file_path, 'w') as f:
                        f.write(content)
                self.log(f"Fixed YAML syntax in {file_path}", "SUCCESS")
                self.fixes_applied += 1
            else:
                self.log(f"YAML file is already valid: {file_path}", "INFO")
                
        except Exception as e:
            self.log(f"Error processing {file_path}: {e}", "ERROR")
            self.errors_found += 1
    
    def fix_shell_scripts(self, file_path):
        """Fix common shell script issues"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Fix trailing spaces
            content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
            
            # Fix missing newline at end of file
            if content and not content.endswith('\n'):
                content += '\n'
            
            # Check if script has shebang
            if not content.startswith('#!'):
                content = '#!/bin/bash\n\n' + content
                self.log(f"Added shebang to {file_path}", "WARNING")
            
            # Test shell syntax
            if self.test_shell_syntax(file_path, content):
                if content != original_content:
                    if not self.dry_run:
                        with open(file_path, 'w') as f:
                            f.write(content)
                    self.log(f"Fixed shell script: {file_path}", "SUCCESS")
                    self.fixes_applied += 1
            else:
                self.log(f"Shell syntax error in {file_path}", "ERROR")
                self.errors_found += 1
                
        except Exception as e:
            self.log(f"Error processing {file_path}: {e}", "ERROR")
            self.errors_found += 1
    
    def test_shell_syntax(self, file_path, content=None):
        """Test shell script syntax"""
        try:
            if content:
                # Write to temp file for syntax check
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                    f.write(content)
                    temp_path = f.name
                result = subprocess.run(['bash', '-n', temp_path], 
                                      capture_output=True, text=True)
                os.unlink(temp_path)
            else:
                result = subprocess.run(['bash', '-n', file_path], 
                                      capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def validate_mkdocs(self):
        """Validate MkDocs configuration"""
        mkdocs_file = "mkdocs.yml"
        if not os.path.exists(mkdocs_file):
            self.log("mkdocs.yml not found", "WARNING")
            return
        
        try:
            with open(mkdocs_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check for required navigation files
            nav = config.get('nav', [])
            missing_files = []
            
            def check_nav_item(item, base_path="docs"):
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str):
                            file_path = os.path.join(base_path, value)
                            if not os.path.exists(file_path):
                                missing_files.append(file_path)
                        elif isinstance(value, list):
                            for sub_item in value:
                                check_nav_item(sub_item, base_path)
                elif isinstance(item, str):
                    file_path = os.path.join(base_path, item)
                    if not os.path.exists(file_path):
                        missing_files.append(file_path)
            
            for item in nav:
                check_nav_item(item)
            
            if missing_files:
                self.log(f"Missing MkDocs navigation files: {missing_files}", "ERROR")
                self.errors_found += len(missing_files)
            else:
                self.log("MkDocs configuration is valid", "SUCCESS")
                
        except Exception as e:
            self.log(f"Error validating MkDocs: {e}", "ERROR")
            self.errors_found += 1
    
    def process_files(self, file_pattern="", file_types=None):
        """Process files based on pattern and types"""
        if file_types is None:
            file_types = ['yaml', 'shell', 'mkdocs']
        
        processed = 0
        
        if 'yaml' in file_types:
            yaml_patterns = [
                "**/*.yml",
                "**/*.yaml",
                "Ansible/inventory"
            ]
            
            for pattern in yaml_patterns:
                for file_path in glob.glob(pattern, recursive=True):
                    if '.git' not in file_path and 'charts/' not in file_path:
                        self.log(f"Processing YAML: {file_path}", "INFO")
                        self.fix_yaml_syntax(file_path)
                        processed += 1
        
        if 'shell' in file_types:
            for file_path in glob.glob("**/*.sh", recursive=True):
                if '.git' not in file_path:
                    self.log(f"Processing shell script: {file_path}", "INFO")
                    self.fix_shell_scripts(file_path)
                    processed += 1
        
        if 'mkdocs' in file_types:
            self.validate_mkdocs()
        
        # Process specific file if provided
        if file_pattern and os.path.exists(file_pattern):
            if file_pattern.endswith(('.yml', '.yaml')):
                self.fix_yaml_syntax(file_pattern)
            elif file_pattern.endswith('.sh'):
                self.fix_shell_scripts(file_pattern)
            processed += 1
        
        return processed


def main():
    parser = argparse.ArgumentParser(description='NOAH Unified Fix Script')
    parser.add_argument('file', nargs='?', help='Specific file to fix')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('-n', '--dry-run', action='store_true',
                       help='Show what would be fixed without making changes')
    parser.add_argument('-t', '--types', nargs='+', 
                       choices=['yaml', 'shell', 'mkdocs'],
                       default=['yaml', 'shell', 'mkdocs'],
                       help='File types to process')
    
    args = parser.parse_args()
    
    fixer = NoahFixer(verbose=args.verbose, dry_run=args.dry_run)
    
    print("🔧 NOAH Unified Fix Script")
    print("=========================")
    print(f"Dry run: {args.dry_run}")
    print(f"File types: {args.types}")
    print()
    
    processed = fixer.process_files(args.file or "", args.types)
    
    print()
    print("📊 Fix Summary")
    print("==============")
    print(f"Files processed: {processed}")
    print(f"Fixes applied: {fixer.fixes_applied}")
    print(f"Errors found: {fixer.errors_found}")
    
    if fixer.errors_found > 0:
        print(f"\n💥 {fixer.errors_found} errors found!")
        sys.exit(1)
    elif fixer.fixes_applied > 0:
        print(f"\n🎉 Successfully applied {fixer.fixes_applied} fixes!")
    else:
        print("\n✅ No issues found!")


if __name__ == "__main__":
    main()
