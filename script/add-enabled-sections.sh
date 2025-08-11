#!/bin/bash

# Script to add missing chartname.enabled sections to Helm values.yaml files

echo "Adding missing enabled sections to Helm charts..."

# Function to add enabled section if missing
add_enabled_section() {
    local chart_name="$1"
    local values_file="/root/NOAH/helm/$chart_name/values.yaml"
    
    if [[ -f "$values_file" ]]; then
        # Check if the chart.enabled pattern exists
        if ! grep -q "^$chart_name:" "$values_file"; then
            echo "Adding $chart_name.enabled to $values_file"
            # Add the enabled section at the beginning after any comments
            sed -i '/^# /!s/^/# Enable\/disable '"$chart_name"' deployment\n'"$chart_name"':\n  enabled: true\n\n&/' "$values_file"
        else
            echo "$chart_name.enabled already exists in $values_file"
        fi
    else
        echo "Warning: $values_file not found"
    fi
}

# Charts that need the pattern based on grep results
charts=("prometheus" "mattermost" "samba4" "nextcloud" "gitlab" "openedr")

for chart in "${charts[@]}"; do
    add_enabled_section "$chart"
done

echo "Completed adding enabled sections"
