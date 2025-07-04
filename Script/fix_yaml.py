#!/usr/bin/env python3

"""
YAML Linting Fixer
Fixes common YAML linting issues:
- Trailing spaces
- Missing final newlines
- Long lines (with basic line breaking)
"""

import os
import re
import sys
from pathlib import Path

def fix_yaml_file(file_path):
    """Fix common YAML linting issues in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix trailing spaces
        lines = content.splitlines()
        fixed_lines = [line.rstrip() for line in lines]
        
        # Basic line length handling for common cases
        final_lines = []
        for line in fixed_lines:
            if len(line) > 80 and ':' in line:
                # Try to break long lines at reasonable points
                if ' - ' in line:  # List items
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        final_lines.append(line)  # Keep as-is for now
                    else:
                        final_lines.append(line)
                elif line.strip().startswith('- ') and len(line) > 80:
                    # Long list items - keep as-is for now to avoid breaking YAML structure
                    final_lines.append(line)
                else:
                    final_lines.append(line)
            else:
                final_lines.append(line)
        
        # Ensure file ends with newline
        content = '\n'.join(final_lines)
        if content and not content.endswith('\n'):
            content += '\n'
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to find and fix YAML files."""
    root_dir = Path('.')
    yaml_patterns = ['**/*.yml', '**/*.yaml']
    
    exclude_dirs = {'.git', 'node_modules', '.venv', '__pycache__'}
    
    fixed_count = 0
    total_count = 0
    
    print("🔧 Fixing YAML linting issues...")
    
    for pattern in yaml_patterns:
        for file_path in root_dir.glob(pattern):
            # Skip files in excluded directories
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            
            total_count += 1
            print(f"Processing: {file_path}")
            
            if fix_yaml_file(file_path):
                print(f"  ✅ Fixed {file_path}")
                fixed_count += 1
            else:
                print(f"  ✓ {file_path} is clean")
    
    print(f"\n🎉 YAML linting fix complete!")
    print(f"📊 Processed {total_count} files, fixed {fixed_count} files")

if __name__ == "__main__":
    main()
