#!/usr/bin/env python3
"""
NOAH YAML Validation Script
Validates all YAML files in the project for syntax errors.
"""

import os
import sys
import yaml
import glob

def validate_yaml_file(filepath):
    """Validate a single YAML file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

def main():
    """Main validation function."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Find all YAML files
    yaml_patterns = ['**/*.yml', '**/*.yaml']
    yaml_files = []
    
    for pattern in yaml_patterns:
        yaml_files.extend(glob.glob(pattern, recursive=True))
    
    # Remove duplicates and sort
    yaml_files = sorted(set(yaml_files))
    
    print(f"🔍 Validating {len(yaml_files)} YAML files...")
    print()
    
    valid_files = 0
    invalid_files = 0
    
    for filepath in yaml_files:
        if os.path.isfile(filepath):
            is_valid, error = validate_yaml_file(filepath)
            
            if is_valid:
                print(f"✅ {filepath}")
                valid_files += 1
            else:
                print(f"❌ {filepath}")
                print(f"   Error: {error}")
                invalid_files += 1
    
    print()
    print(f"📊 Summary:")
    print(f"   Valid files: {valid_files}")
    print(f"   Invalid files: {invalid_files}")
    print(f"   Total files: {len(yaml_files)}")
    
    if invalid_files == 0:
        print("🎉 All YAML files are valid!")
        return 0
    else:
        print(f"❌ {invalid_files} YAML files have syntax errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
