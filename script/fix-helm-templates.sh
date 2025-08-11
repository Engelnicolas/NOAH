#!/bin/bash

# Fix Helm template files that start with --- followed by conditional blocks
# This script moves the conditional {{- if ... }} above the --- separator

echo "🔧 Fixing Helm template YAML structure issues..."

# Find all template files that start with --- followed by {{- if
find /root/NOAH/helm -name "*.yaml" -path "*/templates/*" | while read file; do
    if head -3 "$file" | grep -q "^---" && head -3 "$file" | grep -q "{{-.*if"; then
        echo "Fixing $file"
        # Create a temporary file
        temp_file=$(mktemp)
        
        # Read the first few lines to identify the pattern
        first_line=$(sed -n '1p' "$file")
        second_line=$(sed -n '2p' "$file")
        
        if [[ "$first_line" == "---" ]] && [[ "$second_line" =~ ^\{\{-.*if ]]; then
            # Move the conditional above the ---
            echo "$second_line" > "$temp_file"
            echo "---" >> "$temp_file"
            tail -n +3 "$file" >> "$temp_file"
            mv "$temp_file" "$file"
            echo "  ✅ Fixed $file"
        else
            rm "$temp_file"
        fi
    fi
done

echo "🔧 Fixing template files with missing conditional wrappers..."

# Add conditional wrappers to templates that don't have them
find /root/NOAH/helm -name "*.yaml" -path "*/templates/*" | while read file; do
    # Skip _helpers.tpl and already processed files
    if [[ $(basename "$file") == "_helpers.tpl" ]] || [[ $(basename "$file") == "*.yaml" ]]; then
        continue
    fi
    
    # Check if file doesn't start with a conditional but contains template syntax
    if ! grep -q "^{{-.*if" "$file" && grep -q "{{" "$file"; then
        # Get the chart name from the path
        chart_name=$(echo "$file" | sed 's|.*/helm/\([^/]*\)/templates/.*|\1|')
        template_name=$(basename "$file" .yaml)
        
        echo "Adding conditional wrapper to $file"
        temp_file=$(mktemp)
        
        # Add a basic conditional wrapper based on common patterns
        case "$template_name" in
            *ingress*)
                echo "{{- if .Values.ingress.enabled }}" > "$temp_file"
                ;;
            *service*)
                echo "{{- if .Values.service.enabled }}" > "$temp_file"
                ;;
            *pvc*|*volume*)
                echo "{{- if .Values.persistence.enabled }}" > "$temp_file"
                ;;
            *hpa*)
                echo "{{- if .Values.autoscaling.enabled }}" > "$temp_file"
                ;;
            *servicemonitor*)
                echo "{{- if .Values.serviceMonitor.enabled }}" > "$temp_file"
                ;;
            *networkpolicy*)
                echo "{{- if .Values.networkPolicy.enabled }}" > "$temp_file"
                ;;
            *poddisruptionbudget*)
                echo "{{- if .Values.podDisruptionBudget.enabled }}" > "$temp_file"
                ;;
            *)
                echo "{{- if .Values.${chart_name}.enabled }}" > "$temp_file"
                ;;
        esac
        
        cat "$file" >> "$temp_file"
        echo "{{- end }}" >> "$temp_file"
        
        mv "$temp_file" "$file"
        echo "  ✅ Added conditional wrapper to $file"
    fi
done

echo "✅ Template fixes completed!"
