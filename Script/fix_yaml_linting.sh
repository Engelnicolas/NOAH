#!/bin/bash

# Script to fix common YAML linting issues
# - Remove trailing spaces
# - Ensure files end with newline

echo "Fixing YAML files in NOAH project..."

# Function to fix a single file
fix_yaml_file() {
    local file="$1"
    echo "Processing: $file"
    
    # Remove trailing spaces
    sed -i 's/[[:space:]]*$//' "$file"
    
    # Ensure file ends with newline (only if it's not empty)
    if [ -s "$file" ]; then
        # Check if file ends with newline
        if [ "$(tail -c1 "$file" | wc -l)" -eq 0 ]; then
            echo "" >> "$file"
        fi
    fi
}

# Find and fix all YAML files
find . -name "*.yml" -o -name "*.yaml" | while read -r file; do
    # Skip hidden directories like .git
    if [[ "$file" != *"/.git/"* ]]; then
        fix_yaml_file "$file"
    fi
done

echo "YAML files have been processed."
