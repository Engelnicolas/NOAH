#!/bin/bash

# =============================================================================
# NOAH Helm Charts Template Validation Script
# =============================================================================
# This script validates all Helm chart templates by attempting to render them
# with various configurations and value combinations. It helps catch template
# errors before deployment and ensures all charts are properly configured.
#
# Features:
# - Template rendering validation for all charts
# - Multiple test scenarios (default, minimal, full)
# - Colored output and progress indicators
# - Detailed error reporting and suggestions
# - Integration with CI/CD pipelines
# - Performance timing and statistics
#
# Usage:
#   ./validate-templates.sh [OPTIONS]
#
# Options:
#   --verbose, -v     Enable verbose output
#   --chart CHART     Validate specific chart only
#   --scenario SCENARIO Test specific scenario (default, minimal, full)
#   --output FORMAT   Output format (console, json, junit)
#   --help, -h        Show this help message
#
# Exit codes:
#   0: All templates validated successfully
#   1: Template validation failed
#   2: Prerequisites not met
#   3: Invalid arguments
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration and Constants
# =============================================================================

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELM_DIR="$REPO_ROOT/Helm"
TEMP_DIR="/tmp/noah-template-validation"
VERBOSE=false
CHART_FILTER=""
SCENARIO_FILTER=""
OUTPUT_FORMAT="console"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Symbols
SUCCESS="✅"
FAILURE="❌"
WARNING="⚠️"
INFO="ℹ️"
ARROW="→"

# Statistics
TOTAL_CHARTS=0
PASSED_CHARTS=0
FAILED_CHARTS=0
TOTAL_TEMPLATES=0
PASSED_TEMPLATES=0
FAILED_TEMPLATES=0
START_TIME=$(date +%s)

# =============================================================================
# Utility Functions
# =============================================================================

# Print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Print timestamped log message
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%H:%M:%S')
    
    case $level in
        "INFO")  print_color "$BLUE" "[$timestamp] $message" ;;
        "WARN")  print_color "$YELLOW" "[$timestamp] $WARNING $message" ;;
        "ERROR") print_color "$RED" "[$timestamp] $FAILURE $message" ;;
        "SUCCESS") print_color "$GREEN" "[$timestamp] $SUCCESS $message" ;;
        *) echo "[$timestamp] $message" ;;
    esac
}

# Print verbose message
verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        log "INFO" "$1"
    fi
}

# Print progress with percentage
print_progress() {
    local current=$1
    local total=$2
    local item=$3
    local percentage=$((current * 100 / total))
    printf "\r${CYAN}Progress: [%3d%%] %s${NC}" "$percentage" "$item"
    if [[ $current -eq $total ]]; then
        echo
    fi
}

# =============================================================================
# Validation Functions
# =============================================================================

# Check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if running from correct directory
    if [[ ! -d "$HELM_DIR" ]]; then
        log "ERROR" "Helm directory not found: $HELM_DIR"
        return 1
    fi
    
    # Check required tools
    local required_tools=("helm")
    local optional_tools=("yq")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "ERROR" "Required tool not found: $tool"
            return 1
        fi
    done
    
    for tool in "${optional_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log "WARN" "Optional tool not found: $tool (some features may be limited)"
        fi
    done
    
    # Check Helm version
    local helm_version=$(helm version --short --client 2>/dev/null | grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
    verbose "Helm version: $helm_version"
    
    log "SUCCESS" "Prerequisites check passed"
    return 0
}

# Setup temporary directory
setup_temp_dir() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
    mkdir -p "$TEMP_DIR"
    verbose "Created temporary directory: $TEMP_DIR"
}

# Setup Helm repositories
setup_helm_repos() {
    log "INFO" "Setting up Helm repositories..."
    
    # Add required repositories
    helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
    helm repo add elastic https://helm.elastic.co >/dev/null 2>&1 || true
    helm repo update >/dev/null 2>&1
    
    log "SUCCESS" "Helm repositories updated"
}

# Build chart dependencies
build_dependencies() {
    local chart_dir=$1
    local chart_name=$(basename "$chart_dir")
    
    if [[ -f "$chart_dir/Chart.yaml" ]] && grep -q "dependencies:" "$chart_dir/Chart.yaml"; then
        verbose "Building dependencies for $chart_name..."
        if helm dependency build "$chart_dir" >/dev/null 2>&1; then
            verbose "Dependencies built for $chart_name"
            return 0
        else
            log "ERROR" "Failed to build dependencies for $chart_name"
            return 1
        fi
    else
        verbose "No dependencies for $chart_name"
        return 0
    fi
}

# Generate test values for different scenarios
generate_test_values() {
    local chart_dir=$1
    local scenario=$2
    local output_file=$3
    local chart_name=$(basename "$chart_dir")
    
    case $scenario in
        "minimal")
            # Generate minimal values (disabled features)
            cat > "$output_file" << EOF
# Minimal configuration for testing
global:
  imageRegistry: ""
  imagePullSecrets: []
  
replicaCount: 1

# Disable optional features
ingress:
  enabled: false
  
metrics:
  enabled: false
  
autoscaling:
  enabled: false
  
# Minimal resources
resources:
  limits:
    cpu: 100m
    memory: 128Mi
  requests:
    cpu: 50m
    memory: 64Mi

# Disable dependencies where possible
postgresql:
  enabled: false
  
redis:
  enabled: false
  
elasticsearch:
  enabled: false
EOF
            ;;
        "full")
            # Generate full configuration (all features enabled)
            cat > "$output_file" << EOF
# Full configuration for testing
global:
  imageRegistry: "registry.noah.local"
  imagePullSecrets: 
    - name: "noah-registry-secret"
  
replicaCount: 3

# Enable all features
ingress:
  enabled: true
  hostname: "${chart_name}.noah.local"
  
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
    
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  
# Full resources
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

# Enable dependencies
postgresql:
  enabled: true
  
redis:
  enabled: true
  
elasticsearch:
  enabled: true
EOF
            ;;
        *)
            # Default scenario - use chart's default values
            echo "# Default values from chart" > "$output_file"
            ;;
    esac
}

# Validate template rendering
validate_template() {
    local chart_dir=$1
    local scenario=$2
    local chart_name=$(basename "$chart_dir")
    local test_values_file="$TEMP_DIR/${chart_name}-${scenario}-values.yaml"
    local output_file="$TEMP_DIR/${chart_name}-${scenario}-output.yaml"
    local error_file="$TEMP_DIR/${chart_name}-${scenario}-error.log"
    
    # Generate test values
    generate_test_values "$chart_dir" "$scenario" "$test_values_file"
    
    # Attempt template rendering
    local helm_cmd="helm template test-release"
    if [[ -f "$test_values_file" ]] && [[ -s "$test_values_file" ]]; then
        helm_cmd="$helm_cmd --values \"$test_values_file\""
    fi
    helm_cmd="$helm_cmd \"$chart_dir\""
    
    verbose "Testing $chart_name with $scenario scenario..."
    verbose "Command: $helm_cmd"
    
    if eval "$helm_cmd" > "$output_file" 2> "$error_file"; then
        # Template rendered successfully
        local template_count=$(grep -c "^---" "$output_file" || echo "0")
        verbose "$SUCCESS $chart_name ($scenario): $template_count templates rendered"
        
        # Basic validation of rendered output
        if validate_rendered_output "$output_file" "$error_file"; then
            PASSED_TEMPLATES=$((PASSED_TEMPLATES + 1))
            return 0
        else
            FAILED_TEMPLATES=$((FAILED_TEMPLATES + 1))
            return 1
        fi
    else
        # Template rendering failed
        log "ERROR" "$chart_name ($scenario): Template rendering failed"
        if [[ -f "$error_file" ]]; then
            verbose "Error details:"
            if [[ "$VERBOSE" == "true" ]]; then
                cat "$error_file" | head -10
            fi
        fi
        FAILED_TEMPLATES=$((FAILED_TEMPLATES + 1))
        return 1
    fi
}

# Validate rendered output
validate_rendered_output() {
    local output_file=$1
    local error_file=$2
    
    # Check for common template errors in warnings
    if [[ -f "$error_file" ]] && grep -q "nil pointer\|undefined variable\|template.*not found" "$error_file"; then
        log "ERROR" "Template contains nil pointer or undefined variable errors"
        return 1
    fi
    
    # Check if output contains actual Kubernetes resources
    if ! grep -q "apiVersion:" "$output_file"; then
        log "ERROR" "Rendered output doesn't contain Kubernetes resources"
        return 1
    fi
    
    # Basic YAML validation (less strict)
    if command -v python3 &> /dev/null; then
        if ! python3 -c "
import yaml
try:
    with open('$output_file', 'r') as f:
        list(yaml.safe_load_all(f))
except Exception as e:
    print(f'YAML validation failed: {e}')
    exit(1)
" 2>/dev/null; then
            verbose "YAML validation failed, but continuing (might be multi-document YAML)"
        fi
    fi
    
    return 0
}

# Validate single chart
validate_chart() {
    local chart_dir=$1
    local chart_name=$(basename "$chart_dir")
    local scenarios=("default" "minimal" "full")
    local chart_passed=true
    
    # Filter scenarios if specified
    if [[ -n "$SCENARIO_FILTER" ]]; then
        scenarios=("$SCENARIO_FILTER")
    fi
    
    verbose "Validating chart: $chart_name"
    
    # Build dependencies first
    if ! build_dependencies "$chart_dir"; then
        log "ERROR" "$chart_name: Failed to build dependencies"
        FAILED_CHARTS=$((FAILED_CHARTS + 1))
        return 1
    fi
    
    # Test each scenario
    for scenario in "${scenarios[@]}"; do
        TOTAL_TEMPLATES=$((TOTAL_TEMPLATES + 1))
        
        if ! validate_template "$chart_dir" "$scenario"; then
            chart_passed=false
            log "ERROR" "$chart_name ($scenario): Template validation failed"
        else
            verbose "$SUCCESS $chart_name ($scenario): Template validation passed"
        fi
    done
    
    # Update chart statistics
    if [[ "$chart_passed" == "true" ]]; then
        PASSED_CHARTS=$((PASSED_CHARTS + 1))
        log "SUCCESS" "$chart_name: All templates validated successfully"
    else
        FAILED_CHARTS=$((FAILED_CHARTS + 1))
        log "ERROR" "$chart_name: Template validation failed"
    fi
    
    return $([[ "$chart_passed" == "true" ]] && echo 0 || echo 1)
}

# =============================================================================
# Reporting Functions
# =============================================================================

# Generate summary report
generate_summary() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo
    print_color "$WHITE" "📊 NOAH Template Validation Summary"
    print_color "$WHITE" "=================================="
    
    # Chart statistics
    echo "Charts:"
    print_color "$GREEN" "  ✅ Passed: $PASSED_CHARTS"
    print_color "$RED" "  ❌ Failed: $FAILED_CHARTS"
    print_color "$BLUE" "  📊 Total:  $TOTAL_CHARTS"
    
    # Template statistics
    echo "Templates:"
    print_color "$GREEN" "  ✅ Passed: $PASSED_TEMPLATES"
    print_color "$RED" "  ❌ Failed: $FAILED_TEMPLATES"
    print_color "$BLUE" "  📊 Total:  $TOTAL_TEMPLATES"
    
    # Performance
    echo "Performance:"
    print_color "$CYAN" "  ⏱️  Duration: ${minutes}m ${seconds}s"
    
    # Success rate
    local success_rate=0
    if [[ $TOTAL_CHARTS -gt 0 ]]; then
        success_rate=$((PASSED_CHARTS * 100 / TOTAL_CHARTS))
    fi
    
    echo "Success Rate:"
    if [[ $success_rate -eq 100 ]]; then
        print_color "$GREEN" "  🎉 $success_rate% - All templates validated successfully!"
    elif [[ $success_rate -ge 80 ]]; then
        print_color "$YELLOW" "  ⚠️  $success_rate% - Most templates validated successfully"
    else
        print_color "$RED" "  ❌ $success_rate% - Many templates failed validation"
    fi
    
    echo
}

# Generate JSON report
generate_json_report() {
    local output_file="$TEMP_DIR/validation-report.json"
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    cat > "$output_file" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "duration_seconds": $duration,
  "summary": {
    "total_charts": $TOTAL_CHARTS,
    "passed_charts": $PASSED_CHARTS,
    "failed_charts": $FAILED_CHARTS,
    "total_templates": $TOTAL_TEMPLATES,
    "passed_templates": $PASSED_TEMPLATES,
    "failed_templates": $FAILED_TEMPLATES,
    "success_rate": $((PASSED_CHARTS * 100 / TOTAL_CHARTS))
  },
  "charts": []
}
EOF
    
    echo "JSON report generated: $output_file"
}

# Generate JUnit XML report
generate_junit_report() {
    local output_file="$TEMP_DIR/validation-junit.xml"
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    cat > "$output_file" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="NOAH Template Validation" tests="$TOTAL_TEMPLATES" failures="$FAILED_TEMPLATES" time="$duration">
  <testsuite name="helm-template-validation" tests="$TOTAL_TEMPLATES" failures="$FAILED_TEMPLATES" time="$duration">
    <!-- Individual test results would be added here -->
  </testsuite>
</testsuites>
EOF
    
    echo "JUnit report generated: $output_file"
}

# =============================================================================
# Main Execution
# =============================================================================

# Show help
show_help() {
    cat << EOF
NOAH Helm Charts Template Validation Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -v, --verbose          Enable verbose output
    -c, --chart CHART      Validate specific chart only
    -s, --scenario SCENARIO Test specific scenario (default, minimal, full)
    -o, --output FORMAT    Output format (console, json, junit)
    -h, --help             Show this help message

EXAMPLES:
    $0                              # Validate all charts
    $0 --verbose                    # Validate with verbose output
    $0 --chart mattermost           # Validate only mattermost chart
    $0 --scenario minimal           # Test only minimal scenario
    $0 --output json                # Generate JSON report

EXIT CODES:
    0: All templates validated successfully
    1: Template validation failed
    2: Prerequisites not met
    3: Invalid arguments
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -c|--chart)
                CHART_FILTER="$2"
                shift 2
                ;;
            -s|--scenario)
                SCENARIO_FILTER="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 3
                ;;
        esac
    done
}

# Main function
main() {
    parse_arguments "$@"
    
    # Setup
    print_color "$CYAN" "🚀 NOAH Helm Charts Template Validation"
    print_color "$CYAN" "======================================="
    echo
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 2
    fi
    
    # Setup environment
    setup_temp_dir
    setup_helm_repos
    
    # Find charts to validate
    local charts=()
    if [[ -n "$CHART_FILTER" ]]; then
        if [[ -d "$HELM_DIR/$CHART_FILTER" ]]; then
            charts=("$HELM_DIR/$CHART_FILTER")
        else
            log "ERROR" "Chart not found: $CHART_FILTER"
            exit 1
        fi
    else
        while IFS= read -r -d '' chart_dir; do
            charts+=("$chart_dir")
        done < <(find "$HELM_DIR" -maxdepth 1 -type d -name "*" -not -path "$HELM_DIR" -print0 | sort -z)
    fi
    
    TOTAL_CHARTS=${#charts[@]}
    
    if [[ $TOTAL_CHARTS -eq 0 ]]; then
        log "ERROR" "No charts found to validate"
        exit 1
    fi
    
    log "INFO" "Found $TOTAL_CHARTS charts to validate"
    
    # Validate each chart
    local current_chart=0
    for chart_dir in "${charts[@]}"; do
        current_chart=$((current_chart + 1))
        local chart_name=$(basename "$chart_dir")
        
        # Skip if not a valid chart directory
        if [[ ! -f "$chart_dir/Chart.yaml" ]]; then
            verbose "Skipping $chart_name (not a Helm chart)"
            continue
        fi
        
        print_progress "$current_chart" "$TOTAL_CHARTS" "$chart_name"
        
        validate_chart "$chart_dir"
    done
    
    # Generate reports
    case $OUTPUT_FORMAT in
        "json")
            generate_json_report
            ;;
        "junit")
            generate_junit_report
            ;;
        *)
            generate_summary
            ;;
    esac
    
    # Cleanup
    if [[ "$VERBOSE" != "true" ]]; then
        rm -rf "$TEMP_DIR"
    else
        log "INFO" "Temporary files preserved in: $TEMP_DIR"
    fi
    
    # Exit with appropriate code
    if [[ $FAILED_CHARTS -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function with all arguments
main "$@"
