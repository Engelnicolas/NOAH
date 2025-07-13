#!/bin/bash

# Script to find potential YAML syntax issues with hyphens

echo "🔍 Checking for YAML syntax issues with hyphens..."
echo "=================================================="

# Find all YAML template files and check for potential issues
error_files=()

for file in $(find Helm -name "*.yaml" -path "*/templates/*" | sort); do
    if [[ -f "$file" ]]; then
        echo "Checking: $file"
        
        # Run yamllint with proper configuration and capture output
        yamllint_output=$(yamllint --config-file=Script/.yamllint.yml "$file" 2>&1)
        
        if [[ $? -ne 0 ]]; then
            echo "❌ YAML errors found in $file:"
            echo "$yamllint_output"
            error_files+=("$file")
            echo "---"
        else
            echo "✅ No errors"
        fi
    fi
done

echo
echo "Summary:"
echo "========"
echo "Total files checked: $(find Helm -name "*.yaml" -path "*/templates/*" | wc -l)"
echo "Files with errors: ${#error_files[@]}"

if [[ ${#error_files[@]} -gt 0 ]]; then
    echo
    echo "Files with errors:"
    for file in "${error_files[@]}"; do
        echo "- $file"
    done
fi
