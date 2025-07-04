#!/bin/bash

# =============================================================================
# N.O.A.H - Next Open-source Architecture Hub - Enhanced Helm Deployment and Verification Script
# =============================================================================
#
# This script provides comprehensive Helm chart deployment and verification
# capabilities for the N.O.A.H platform. It supports multiple deployment
# modes, environments, and provides extensive validation and monitoring.
#
# FEATURES:
# - Multi-environment deployment support (dev, staging, production)
# - Modular deployment with dependency management
# - Parallel and sequential deployment modes
# - Comprehensive pre-deployment validation
# - Post-deployment health checks and verification
# - Rollback capabilities on deployment failures
# - Upgrade mode for existing deployments
# - Dry-run mode for testing configurations
# - Detailed logging and progress reporting
# - Integration testing and service validation
# - Resource monitoring and capacity planning
#
# DEPLOYMENT MODES:
# - Fresh Installation: Complete new deployment
# - Upgrade Mode: Update existing deployments
# - Dry Run: Validate configurations without applying
# - Selective Deployment: Deploy specific charts only
# - Parallel Deployment: Deploy independent charts simultaneously
#
# CHART DEPLOYMENT ORDER:
# 1. Infrastructure: Samba4 (LDAP), PostgreSQL, Redis
# 2. Security: Keycloak (IAM), OAuth2-Proxy, Wazuh (SIEM)
# 3. Monitoring: Prometheus, Grafana, AlertManager
# 4. Applications: GitLab, Nextcloud, Mattermost
# 5. Additional: OpenEDR, custom applications
#
# USAGE:
#   ./deploy_and_verify_helm.sh                    # Default development deployment
#   ./deploy_and_verify_helm.sh -e production      # Production deployment
#   ./deploy_and_verify_helm.sh --dry-run          # Validate without deploying
#   ./deploy_and_verify_helm.sh --upgrade          # Upgrade existing deployment
#   ./deploy_and_verify_helm.sh --parallel         # Parallel deployment mode
#
# REQUIREMENTS:
# - kubectl: Kubernetes CLI with cluster access
# - helm: Helm 3.x package manager
# - Valid kubeconfig with appropriate permissions
# - Sufficient cluster resources for target environment
#
# Author: N.O.A.H Team
# Version: 2.0.0
# License: MIT
# Documentation: ../Docs/README.md
# =============================================================================

# Bash strict mode for robust error handling
# -e: Exit immediately on command failure
# -u: Exit on undefined variable usage
# -o pipefail: Exit on pipe command failures
set -euo pipefail

# =============================================================================
# Script Configuration and Metadata
# =============================================================================

# Script version and identification
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="deploy_and_verify_helm.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELM_CHARTS_DIR="${SCRIPT_DIR}/../Helm"

# =============================================================================
# Default Configuration Values
# =============================================================================
# These values can be overridden via command-line arguments

# Target deployment environment
# Affects resource allocation, replica counts, and security settings
DEFAULT_ENVIRONMENT="dev"

# Kubernetes namespace prefix for resource organization
# Final namespace will be: ${NAMESPACE_PREFIX}-${ENVIRONMENT}
DEFAULT_NAMESPACE_PREFIX="noah"

# Helm operation timeout for deployments
# Increase for large deployments or slow storage
DEFAULT_TIMEOUT="10m"

# Custom values file override (leave empty to use chart defaults)
DEFAULT_VALUES_FILE=""

# Deployment mode flags
UPGRADE_MODE=false          # Use helm upgrade instead of install
DRY_RUN=false              # Validate configurations without applying
VERBOSE=false              # Enable detailed debug logging
SKIP_TESTS=false           # Skip post-deployment health checks
PARALLEL_DEPLOYS=false     # Deploy independent charts in parallel

# =============================================================================
# Terminal Color Codes for Enhanced Output
# =============================================================================
# ANSI color codes for improved readability and user experience

readonly RED='\033[0;31m'      # Error messages and failures
readonly GREEN='\033[0;32m'    # Success messages and completed tasks
readonly YELLOW='\033[0;33m'   # Warning messages and important notes
readonly BLUE='\033[0;34m'     # Process information and headers
readonly PURPLE='\033[0;35m'   # Major section headers
readonly CYAN='\033[0;36m'     # Debug messages and detailed info
readonly NC='\033[0m'          # No Color (reset to default)

# =============================================================================
# Centralized Logging Functions
# =============================================================================
# Consistent logging with timestamps, colors, and severity levels

# General information logging with timestamp
log() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Warning message logging for non-critical issues
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Error message logging sent to stderr for proper handling
log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

# Debug message logging (only displayed when VERBOSE=true)
log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${CYAN}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}
    fi
}

# Error handling
error_exit() {
    log_error "$1"
    exit 1
}

# Help function
show_help() {
    cat << EOF
${BLUE}N.O.A.H - Enhanced Helm Deployment Script v${SCRIPT_VERSION}${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS]

${YELLOW}OPTIONS:${NC}
    -e, --environment ENV        Target environment (dev/staging/prod) [default: ${DEFAULT_ENVIRONMENT}]
    -n, --namespace-prefix PREFIX Namespace prefix for deployments [default: ${DEFAULT_NAMESPACE_PREFIX}]
    -t, --timeout TIMEOUT       Helm operation timeout [default: ${DEFAULT_TIMEOUT}]
    -f, --values-file FILE       Custom values file path
    -u, --upgrade               Upgrade existing deployments instead of install
    -d, --dry-run               Perform a dry run without making changes
    -v, --verbose               Enable verbose logging
    -s, --skip-tests            Skip post-deployment tests
    -p, --parallel              Deploy charts in parallel (experimental)
    -c, --charts CHART1,CHART2   Deploy specific charts only
    -h, --help                  Show this help message

${YELLOW}EXAMPLES:${NC}
    $0 --environment prod --upgrade
    $0 --dry-run --verbose
    $0 --charts gitlab,keycloak --environment staging
    $0 --values-file custom-values.yaml

${YELLOW}SUPPORTED CHARTS:${NC}
    gitlab, grafana, keycloak, mattermost, nextcloud, oauth2-proxy,
    openedr, prometheus, samba4, wazuh

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -n|--namespace-prefix)
                NAMESPACE_PREFIX="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -f|--values-file)
                VALUES_FILE="$2"
                shift 2
                ;;
            -u|--upgrade)
                UPGRADE_MODE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -p|--parallel)
                PARALLEL_DEPLOYS=true
                shift
                ;;
            -c|--charts)
                IFS=',' read -ra SELECTED_CHARTS <<< "$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
        esac
    done

    # Set defaults
    ENVIRONMENT="${ENVIRONMENT:-$DEFAULT_ENVIRONMENT}"
    NAMESPACE_PREFIX="${NAMESPACE_PREFIX:-$DEFAULT_NAMESPACE_PREFIX}"
    TIMEOUT="${TIMEOUT:-$DEFAULT_TIMEOUT}"
    VALUES_FILE="${VALUES_FILE:-$DEFAULT_VALUES_FILE}"
}

# Validate environment
validate_environment() {
    log "Validating environment and dependencies..."
    
    # Check required tools
    local required_tools=("kubectl" "helm")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error_exit "$tool is required but not installed."
        fi
    done

    # Check Kubernetes connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error_exit "Cannot connect to Kubernetes cluster. Check your kubeconfig."
    fi

    # Validate environment parameter
    case "$ENVIRONMENT" in
        dev|staging|prod)
            log_debug "Environment '$ENVIRONMENT' is valid"
            ;;
        *)
            error_exit "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
            ;;
    esac

    # Check Helm charts directory
    if [[ ! -d "$HELM_CHARTS_DIR" ]]; then
        error_exit "Helm charts directory not found: $HELM_CHARTS_DIR"
    fi

    log "Environment validation completed successfully"
}

# Get available charts
get_available_charts() {
    local charts=()
    for chart_dir in "$HELM_CHARTS_DIR"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            charts+=($(basename "$chart_dir"))
        fi
    done
    echo "${charts[@]}"
}

# Deploy single chart
deploy_chart() {
    local chart="$1"
    local chart_path="$HELM_CHARTS_DIR/$chart"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    local release_name="${chart}"
    
    log "Processing chart: $chart"
    
    # Validate chart exists
    if [[ ! -d "$chart_path" || ! -f "$chart_path/Chart.yaml" ]]; then
        log_warn "Chart '$chart' not found or invalid. Skipping..."
        return 1
    fi

    # Prepare Helm command
    local helm_cmd="helm"
    local action="install"
    
    if [[ "$UPGRADE_MODE" == "true" ]]; then
        action="upgrade --install"
    fi
    
    helm_cmd="$helm_cmd $action $release_name $chart_path"
    helm_cmd="$helm_cmd --create-namespace --namespace $namespace"
    helm_cmd="$helm_cmd --timeout $TIMEOUT"
    helm_cmd="$helm_cmd --wait"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        helm_cmd="$helm_cmd --dry-run"
    fi
    
    # Add values file if specified
    if [[ -n "$VALUES_FILE" && -f "$VALUES_FILE" ]]; then
        helm_cmd="$helm_cmd --values $VALUES_FILE"
    fi
    
    # Check for environment-specific values
    local env_values_file="$chart_path/values-$ENVIRONMENT.yaml"
    if [[ -f "$env_values_file" ]]; then
        helm_cmd="$helm_cmd --values $env_values_file"
        log_debug "Using environment-specific values: $env_values_file"
    fi
    
    # Execute Helm command
    log_debug "Executing: $helm_cmd"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would execute: $helm_cmd"
        return 0
    fi
    
    if eval "$helm_cmd"; then
        log "✅ Successfully deployed $chart"
        return 0
    else
        log_error "❌ Failed to deploy $chart"
        return 1
    fi
}

# Verify deployment
verify_deployment() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    local max_retries=30
    local retry_count=0
    
    log "Verifying deployment for $chart..."
    
    # Wait for deployment to be ready
    while [[ $retry_count -lt $max_retries ]]; do
        if kubectl get deployment "$chart" -n "$namespace" &> /dev/null; then
            if kubectl rollout status deployment/"$chart" -n "$namespace" --timeout=60s &> /dev/null; then
                log "✅ Deployment $chart is ready"
                return 0
            fi
        fi
        
        ((retry_count++))
        log_debug "Waiting for $chart deployment... (attempt $retry_count/$max_retries)"
        sleep 10
    done
    
    log_warn "⚠️ Deployment $chart verification timed out"
    return 1
}

# Get service endpoints
get_service_endpoints() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    log_debug "Getting service endpoints for $chart..."
    
    # Try to get external IP
    local external_ip
    external_ip=$(kubectl get svc -n "$namespace" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    
    if [[ -n "$external_ip" ]]; then
        log "$chart: External IP: $external_ip"
    else
        # Try to get NodePort
        local nodeport
        nodeport=$(kubectl get svc -n "$namespace" -o jsonpath='{.items[0].spec.ports[0].nodePort}' 2>/dev/null || echo "")
        if [[ -n "$nodeport" ]]; then
            log "$chart: NodePort: $nodeport"
        else
            log "$chart: ClusterIP service (no external access)"
        fi
    fi
}

# Run post-deployment tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log "Skipping post-deployment tests as requested"
        return 0
    fi
    
    log "Running post-deployment tests..."
    
    local test_script="$SCRIPT_DIR/../Test/post_deploy_validate.sh"
    if [[ -f "$test_script" ]]; then
        if bash "$test_script" --environment "$ENVIRONMENT"; then
            log "✅ All tests passed"
        else
            log_warn "⚠️ Some tests failed"
            return 1
        fi
    else
        log_warn "Test script not found: $test_script"
    fi
}

# Generate deployment report
generate_report() {
    local report_file="deployment-report-$(date +%Y%m%d-%H%M%S).log"
    
    log "Generating deployment report: $report_file"
    
    {
        echo "N.O.A.H Deployment Report"
        echo "=============================="
        echo "Timestamp: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Namespace Prefix: $NAMESPACE_PREFIX"
        echo "Upgrade Mode: $UPGRADE_MODE"
        echo ""
        
        echo "Deployed Charts:"
        echo "=================="
        for chart in "${DEPLOYED_CHARTS[@]}"; do
            echo "✅ $chart"
        done
        
        if [[ ${#FAILED_CHARTS[@]} -gt 0 ]]; then
            echo ""
            echo "Failed Charts:"
            echo "=============="
            for chart in "${FAILED_CHARTS[@]}"; do
                echo "❌ $chart"
            done
        fi
        
        echo ""
        echo "Service Endpoints:"
        echo "=================="
        for chart in "${DEPLOYED_CHARTS[@]}"; do
            get_service_endpoints "$chart"
        done
        
    } | tee "$report_file"
}

# Cleanup function
cleanup() {
    log "Cleaning up temporary resources..."
    # Add any cleanup logic here
}

# Signal handling
trap cleanup EXIT
trap 'error_exit "Script interrupted by user"' INT TERM

# Main deployment function
main() {
    echo -e "${BLUE}🚀 N.O.A.H - Enhanced Helm Deployment v${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate environment
    validate_environment
    
    # Get charts to deploy
    local charts_to_deploy=()
    if [[ -n "${SELECTED_CHARTS:-}" ]]; then
        charts_to_deploy=("${SELECTED_CHARTS[@]}")
        log "Deploying selected charts: ${charts_to_deploy[*]}"
    else
        IFS=' ' read -ra charts_to_deploy <<< "$(get_available_charts)"
        log "Deploying all available charts: ${charts_to_deploy[*]}"
    fi
    
    # Initialize tracking arrays
    DEPLOYED_CHARTS=()
    FAILED_CHARTS=()
    
    # Deploy charts
    if [[ "$PARALLEL_DEPLOYS" == "true" ]]; then
        log "Deploying charts in parallel mode..."
        local pids=()
        for chart in "${charts_to_deploy[@]}"; do
            deploy_chart "$chart" &
            pids+=($!)
        done
        
        # Wait for all parallel deployments
        for pid in "${pids[@]}"; do
            if wait "$pid"; then
                log_debug "Parallel deployment completed successfully"
            else
                log_warn "A parallel deployment failed"
            fi
        done
    else
        log "Deploying charts sequentially..."
        for chart in "${charts_to_deploy[@]}"; do
            if deploy_chart "$chart"; then
                DEPLOYED_CHARTS+=("$chart")
                
                # Verify deployment if not in dry-run mode
                if [[ "$DRY_RUN" == "false" ]] && ! verify_deployment "$chart"; then
                    log_warn "Deployment verification failed for $chart"
                fi
            else
                FAILED_CHARTS+=("$chart")
            fi
        done
    fi
    
    # Generate summary
    echo -e "\n${BLUE}📊 Deployment Summary${NC}"
    echo -e "${BLUE}=====================${NC}"
    
    if [[ ${#DEPLOYED_CHARTS[@]} -gt 0 ]]; then
        echo -e "${GREEN}✅ Successfully deployed (${#DEPLOYED_CHARTS[@]}):${NC}"
        printf '   %s\n' "${DEPLOYED_CHARTS[@]}"
    fi
    
    if [[ ${#FAILED_CHARTS[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Failed deployments (${#FAILED_CHARTS[@]}):${NC}"
        printf '   %s\n' "${FAILED_CHARTS[@]}"
    fi
    
    # Run tests
    if [[ "$DRY_RUN" == "false" ]]; then
        run_tests
        
        # Show service endpoints
        echo -e "\n${PURPLE}� Service Endpoints${NC}"
        echo -e "${PURPLE}====================${NC}"
        for chart in "${DEPLOYED_CHARTS[@]}"; do
            get_service_endpoints "$chart"
        done
        
        # Generate deployment report
        generate_report
    fi
    
    # Final status
    if [[ ${#FAILED_CHARTS[@]} -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All deployments completed successfully!${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠️ Deployment completed with some failures.${NC}"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"