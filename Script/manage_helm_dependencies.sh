#!/bin/bash

# Helm Dependencies Management Script
# Manages Helm chart dependencies for the NOAH project

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if helm is installed
check_helm() {
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install Helm 3.8+ first."
        echo ""
        echo "Install Helm:"
        echo "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
        echo "Or visit: https://helm.sh/docs/intro/install/"
        exit 1
    fi
    
    local helm_version
    helm_version=$(helm version --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
    log_info "Using Helm $helm_version"
}

# Function to add Bitnami repository
add_repositories() {
    log_info "Adding required Helm repositories..."
    
    if helm repo list | grep -q bitnami; then
        log_success "Bitnami repository already added"
    else
        helm repo add bitnami https://charts.bitnami.com/bitnami
        log_success "Added Bitnami repository"
    fi
    
    helm repo update
    log_success "Updated repository indexes"
}

# Function to update dependencies for a chart
update_chart_dependencies() {
    local chart_dir="$1"
    local chart_name
    chart_name=$(basename "$chart_dir")
    
    log_info "Updating dependencies for $chart_name..."
    
    if [ ! -f "$chart_dir/Chart.yaml" ]; then
        log_error "Chart.yaml not found in $chart_dir"
        return 1
    fi
    
    # Check if chart has dependencies
    if ! grep -q "dependencies:" "$chart_dir/Chart.yaml"; then
        log_warning "No dependencies defined in $chart_name/Chart.yaml"
        return 0
    fi
    
    cd "$chart_dir"
    
    # Update dependencies
    if helm dependency update; then
        log_success "Dependencies updated for $chart_name"
        
        # Verify dependencies were downloaded
        if [ -d "charts" ] && [ "$(ls -A charts 2>/dev/null)" ]; then
            log_success "Dependency charts downloaded to $chart_name/charts/"
            ls -la charts/
        else
            log_warning "No dependency charts found in $chart_name/charts/"
        fi
        
        # Lint the chart with dependencies
        if helm lint .; then
            log_success "Chart $chart_name passes lint with dependencies"
        else
            log_error "Chart $chart_name failed lint check"
        fi
        
    else
        log_error "Failed to update dependencies for $chart_name"
        return 1
    fi
    
    cd - > /dev/null
}

# Main function
main() {
    echo "🚀 NOAH Helm Dependencies Manager"
    echo "================================="
    echo ""
    
    # Check if helm is installed
    check_helm
    
    # Add required repositories
    add_repositories
    
    echo ""
    log_info "Processing Helm charts..."
    
    # Find all Helm charts
    local charts_found=0
    
    for chart_dir in Helm/*/; do
        if [ -d "$chart_dir" ] && [ -f "$chart_dir/Chart.yaml" ]; then
            charts_found=1
            echo ""
            update_chart_dependencies "$chart_dir"
        fi
    done
    
    if [ $charts_found -eq 0 ]; then
        log_warning "No Helm charts found in Helm/ directory"
        exit 1
    fi
    
    echo ""
    log_success "Helm dependencies management completed!"
    echo ""
    log_info "Next steps:"
    echo "1. Test your charts: helm template <release-name> <chart-directory>"
    echo "2. Validate charts: helm lint <chart-directory>"
    echo "3. Install charts: helm install <release-name> <chart-directory>"
}

# Help function
show_help() {
    echo "NOAH Helm Dependencies Manager"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help     Show this help message"
    echo "  -c, --chart    Update dependencies for specific chart"
    echo ""
    echo "Examples:"
    echo "  $0                    # Update all chart dependencies"
    echo "  $0 -c gitlab          # Update only GitLab chart dependencies"
    echo ""
    echo "This script will:"
    echo "1. Check if Helm is installed"
    echo "2. Add required Helm repositories (Bitnami)"
    echo "3. Update dependencies for all charts"
    echo "4. Verify dependencies were downloaded"
    echo "5. Run lint checks on charts"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--chart)
            if [ -n "${2:-}" ]; then
                SPECIFIC_CHART="$2"
                shift 2
            else
                log_error "Chart name required after -c/--chart"
                exit 1
            fi
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function or specific chart
if [ -n "${SPECIFIC_CHART:-}" ]; then
    echo "🚀 NOAH Helm Dependencies Manager - $SPECIFIC_CHART"
    echo "============================================="
    echo ""
    
    check_helm
    add_repositories
    
    if [ -d "Helm/$SPECIFIC_CHART" ]; then
        update_chart_dependencies "Helm/$SPECIFIC_CHART"
    else
        log_error "Chart directory Helm/$SPECIFIC_CHART not found"
        exit 1
    fi
else
    main
fi
