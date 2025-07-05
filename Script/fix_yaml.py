#!/usr/bin/env python3

import os
import glob

def fix_yaml_file(filepath):
    """Fix trailing spaces and ensure newline at end"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Remove trailing spaces from each line
        lines = content.splitlines()
        fixed_lines = [line.rstrip() for line in lines]
        fixed_content = '\n'.join(fixed_lines)
        
        # Ensure file ends with newline if not empty
        if fixed_content and not fixed_content.endswith('\n'):
            fixed_content += '\n'
        
        with open(filepath, 'w') as f:
            f.write(fixed_content)
            
        print(f'Fixed: {filepath}')
        return True
    except Exception as e:
        print(f'Error fixing {filepath}: {e}')
        return False

def main():
    """Main function to process all YAML files"""
    print("Fixing YAML files in NOAH project...")
    
    fixed_count = 0
    
    # Process .yml files
    for file in glob.glob('**/*.yml', recursive=True):
        if '.git' not in file:
            if fix_yaml_file(file):
                fixed_count += 1
    
    # Process .yaml files  
    for file in glob.glob('**/*.yaml', recursive=True):
        if '.git' not in file:
            if fix_yaml_file(file):
                fixed_count += 1
                
    print(f"Processed {fixed_count} YAML files.")

if __name__ == '__main__':
    main()
