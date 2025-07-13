#!/bin/bash

# Script to check which Helm template files need the --- document marker

echo "Checking Helm template files for missing --- document markers..."
echo "================================================================"

missing_marker_files=()

# Find all YAML template files
for file in $(find Helm -name "*.yaml" -path "*/templates/*" | sort); do
    if [[ -f "$file" ]]; then
        # Read the first line
        first_line=$(head -n1 "$file")
        
        # Check if first line starts with ---
        if [[ "$first_line" != "---" ]]; then
            missing_marker_files+=("$file")
            echo "❌ $file - First line: $first_line"
        else
            echo "✅ $file"
        fi
    fi
done

echo ""
echo "Summary:"
echo "========"
echo "Total files checked: $(find Helm -name "*.yaml" -path "*/templates/*" | wc -l)"
echo "Files missing --- marker: ${#missing_marker_files[@]}"

if [[ ${#missing_marker_files[@]} -gt 0 ]]; then
    echo ""
    echo "Files that need fixing:"
    echo "======================"
    for file in "${missing_marker_files[@]}"; do
        echo "- $file"
    done
fi
