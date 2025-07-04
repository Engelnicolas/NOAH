#!/bin/bash

# Script to fix YAML linting issues
# Fixes: trailing spaces, missing newlines, and optionally long lines

set -euo pipefail

echo "🔧 Fixing YAML linting issues..."

# Find all YAML files
yaml_files=$(find . -name "*.yml" -o -name "*.yaml" | grep -v node_modules | grep -v .git)

echo "Found $(echo "$yaml_files" | wc -l) YAML files to process"

fixed_count=0
for file in $yaml_files; do
    echo "Processing: $file"
    
    # Check if file has issues
    has_trailing_spaces=$(grep -l '[[:space:]]$' "$file" 2>/dev/null || true)
    has_no_final_newline=$(test "$(tail -c1 "$file" | wc -l)" -eq 0 && echo "true" || echo "false")
    
    if [[ -n "$has_trailing_spaces" ]] || [[ "$has_no_final_newline" == "true" ]]; then
        echo "  ⚠️  Fixing issues in $file"
        
        # Remove trailing spaces
        sed -i 's/[[:space:]]*$//' "$file"
        
        # Ensure file ends with newline
        if [[ "$has_no_final_newline" == "true" ]]; then
            echo "" >> "$file"
        fi
        
        ((fixed_count++))
        echo "  ✅ Fixed $file"
    else
        echo "  ✓ $file is clean"
    fi
done

echo ""
echo "🎉 YAML linting fix complete!"
echo "📊 Fixed $fixed_count files"
echo ""
echo "Running yamllint to verify fixes..."

# Check if yamllint is available
if command -v yamllint >/dev/null 2>&1; then
    echo "Running yamllint on fixed files..."
    yamllint . || echo "⚠️  Some yamllint issues remain (may need manual review)"
else
    echo "ℹ️  yamllint not installed. Install with: pip install yamllint"
fi

echo "✅ YAML fix script completed"
