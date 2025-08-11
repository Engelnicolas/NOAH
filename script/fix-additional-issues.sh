#!/bin/bash

# Fix additional Helm and workflow issues

echo "🔧 Fixing additional template and configuration issues..."

# Fix the kebab-case file name issue in the Install Linux Act Docker script
if [ -f "/root/NOAH/script/Install_Linux_Act_Docker.sh" ]; then
    echo "📝 Creating Install Linux Act Docker script..."
    cat > "/root/NOAH/script/Install_Linux_Act_Docker.sh" << 'EOF'
#!/bin/bash

# Install Act (GitHub Actions locally) via Docker
# This script sets up Act to run GitHub Actions workflows locally using Docker

set -euo pipefail

echo "🚀 Installing Act for GitHub Actions local execution..."

# Function to ensure act Docker image exists
ensure_act_docker() {
    if ! docker images | grep -q "local/act"; then
        echo "Building act Docker image..."
        docker build -t local/act - <<DOCKERFILE
FROM golang:alpine
RUN apk add --no-cache git docker-cli
RUN go install github.com/nektos/act@latest
ENTRYPOINT ["/go/bin/act"]
DOCKERFILE
    else
        echo "Act Docker image already exists."
    fi
}

# Create act function in shell profile
setup_act_function() {
    local profile_file="$HOME/.bashrc"
    
    # Check if function already exists
    if grep -q "^act()" "$profile_file" 2>/dev/null; then
        echo "Act function already exists in $profile_file"
        return 0
    fi
    
    echo "Adding act function to $profile_file..."
    cat >> "$profile_file" << 'SHELL_FUNC'

# Act function for running GitHub Actions locally
act() {
    ensure_act_docker
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$PWD:$PWD" \
        -w "$PWD" \
        local/act "$@"
}

# Function to ensure act Docker image exists
ensure_act_docker() {
    if ! docker images | grep -q "local/act"; then
        echo "Building act Docker image..."
        docker build -t local/act - <<DOCKERFILE
FROM golang:alpine
RUN apk add --no-cache git docker-cli
RUN go install github.com/nektos/act@latest
ENTRYPOINT ["/go/bin/act"]
DOCKERFILE
    fi
}
SHELL_FUNC
}

main() {
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        echo "❌ Error: Docker is not installed or not in PATH"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Error: Docker is not running"
        echo "Please start Docker and try again"
        exit 1
    fi
    
    # Build the act Docker image
    ensure_act_docker
    
    # Set up the shell function
    setup_act_function
    
    echo "✅ Act installation completed!"
    echo ""
    echo "To use act, either:"
    echo "  1. Source your profile: source ~/.bashrc"
    echo "  2. Open a new terminal"
    echo ""
    echo "Then you can run: act --list"
    echo ""
    echo "For the current session, you can also source the Act via Docker script:"
    echo "  source \"$(dirname "$0")/# Act via Docker.sh\""
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
EOF
    chmod +x "/root/NOAH/script/Install_Linux_Act_Docker.sh"
    echo "  ✅ Created Install_Linux_Act_Docker.sh"
fi

# Fix secret template files that have unescaped template syntax
echo "🔐 Fixing secret template files..."
find /root/NOAH/helm -name "*secret*.yaml" -path "*/templates/*" | while read file; do
    if grep -q "{{.*}}" "$file" && ! grep -q "{{-.*if" "$file"; then
        echo "Adding conditional wrapper to secret file: $file"
        temp_file=$(mktemp)
        chart_name=$(echo "$file" | sed 's|.*/helm/\([^/]*\)/templates/.*|\1|')
        echo "{{- if .Values.${chart_name}.enabled }}" > "$temp_file"
        cat "$file" >> "$temp_file"
        echo "{{- end }}" >> "$temp_file"
        mv "$temp_file" "$file"
        echo "  ✅ Fixed $file"
    fi
done

echo "📊 Creating values.yaml defaults for missing configurations..."

# Function to add default values for features used in templates
add_default_values() {
    local values_file="$1"
    local chart_name="$2"
    
    if [ -f "$values_file" ]; then
        # Check if the chart is enabled by default
        if ! grep -q "enabled:" "$values_file"; then
            echo "# Default chart configuration" >> "$values_file"
            echo "${chart_name}:" >> "$values_file"
            echo "  enabled: true" >> "$values_file"
            echo "" >> "$values_file"
        fi
        
        # Add common service configuration if missing
        if ! grep -q "service:" "$values_file"; then
            cat >> "$values_file" << 'VALUES'
# Service configuration
service:
  enabled: true
  type: ClusterIP
  port: 80

# Ingress configuration  
ingress:
  enabled: false
  annotations: {}
  hosts: []
  tls: []

# Persistence configuration
persistence:
  enabled: false
  size: 10Gi
  storageClass: ""

# Pod disruption budget
podDisruptionBudget:
  enabled: false
  maxUnavailable: 1

# Horizontal Pod Autoscaler
autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

# Service Monitor for Prometheus
serviceMonitor:
  enabled: false

# Network Policy
networkPolicy:
  enabled: false

VALUES
        echo "  ✅ Added default values to $values_file"
        fi
    fi
}

# Add default values to charts that are missing them
for chart_dir in /root/NOAH/helm/*/; do
    if [ -d "$chart_dir" ]; then
        chart_name=$(basename "$chart_dir")
        values_file="$chart_dir/values.yaml"
        
        if [ "$chart_name" != "noah-common" ]; then
            add_default_values "$values_file" "$chart_name"
        fi
    fi
done

echo "🎯 Creating GitHub Actions platform configuration..."

# Create act configuration with proper platform mapping
mkdir -p /root/.config/act
cat > /root/.config/act/actrc << 'ACTRC'
# Act configuration for NOAH project
# Use large runner image for full compatibility

# Platform mappings
-P ubuntu-latest=catthehacker/ubuntu:act-latest
-P ubuntu-22.04=catthehacker/ubuntu:act-22.04
-P ubuntu-20.04=catthehacker/ubuntu:act-20.04

# Default secrets (override with .secrets file in project)
-s GITHUB_TOKEN=placeholder
ACTRC

echo "  ✅ Created Act configuration in ~/.config/act/actrc"

echo "✅ Additional fixes completed!"
echo ""
echo "Summary of fixes applied:"
echo "  📝 Created Install_Linux_Act_Docker.sh script"
echo "  🔐 Fixed secret template conditionals"
echo "  📊 Added default values.yaml configurations"
echo "  🎯 Created Act platform configuration"
echo ""
echo "You can now run:"
echo "  act --list                 # List available workflows"
echo "  act push                   # Run CI workflow"
echo "  act workflow_dispatch     # Run deployment workflow"
