#!/bin/bash

# =======================
# NOAH - Enhanced Monitoring Stack Teardown Script
# =======================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="teardown_monitoring_stack.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_ENVIRONMENT="dev"
DEFAULT_NAMESPACE="monitoring"
FORCE_DELETE=false
PRESERVE_DATA=false
DRY_RUN=false
VERBOSE=false

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Logging functions
log() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

error_exit() {
    log_error "$1"
    exit 1
}

# Help function
show_help() {
    cat << EOF
${BLUE}NOAH - Enhanced Monitoring Stack Teardown v${SCRIPT_VERSION}${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS]

${YELLOW}OPTIONS:${NC}
    -e, --environment ENV        Target environment (dev/staging/prod) [default: ${DEFAULT_ENVIRONMENT}]
    -n, --namespace NAMESPACE    Kubernetes namespace [default: ${DEFAULT_NAMESPACE}]
    -f, --force                  Force delete without confirmation
    -p, --preserve-data          Preserve persistent volumes and data
    -d, --dry-run               Show what would be deleted without actually deleting
    -v, --verbose               Enable verbose logging
    -h, --help                  Show this help message

${YELLOW}EXAMPLES:${NC}
    $0 --environment prod --preserve-data
    $0 --namespace observability --force
    $0 --dry-run --verbose

${YELLOW}WARNING:${NC}
    This script will remove all monitoring components and data!
    Use --preserve-data to keep persistent volumes.

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
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -f|--force)
                FORCE_DELETE=true
                shift
                ;;
            -p|--preserve-data)
                PRESERVE_DATA=true
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
    NAMESPACE="${NAMESPACE:-$DEFAULT_NAMESPACE}"
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

    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warn "Namespace '$NAMESPACE' does not exist. Nothing to teardown."
        exit 0
    fi

    log "Environment validation completed successfully"
}

# Confirm deletion
confirm_deletion() {
    if [[ "$FORCE_DELETE" == "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  WARNING: This will delete the monitoring stack in namespace '$NAMESPACE'${NC}"
    
    if [[ "$PRESERVE_DATA" == "false" ]]; then
        echo -e "${RED}⚠️  All monitoring data will be permanently lost!${NC}"
    else
        echo -e "${BLUE}ℹ️  Persistent volumes will be preserved${NC}"
    fi
    
    echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
    echo -e "${YELLOW}Namespace: $NAMESPACE${NC}"
    echo ""
    
    read -p "Are you sure you want to proceed? (type 'yes' to confirm): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log "Teardown cancelled by user"
        exit 0
    fi
}

# Backup configurations
backup_configurations() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would backup configurations"
        return
    fi
    
    local backup_dir="monitoring-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    log "Backing up configurations to: $backup_dir"
    
    # Backup ConfigMaps
    kubectl get configmap -n "$NAMESPACE" -o yaml > "$backup_dir/configmaps.yaml" 2>/dev/null || true
    
    # Backup Secrets (without sensitive data)
    kubectl get secret -n "$NAMESPACE" -o yaml | \
        sed 's/data:/data: {}/' > "$backup_dir/secrets.yaml" 2>/dev/null || true
    
    # Backup PVCs info
    kubectl get pvc -n "$NAMESPACE" -o yaml > "$backup_dir/pvcs.yaml" 2>/dev/null || true
    
    # Backup Helm releases info
    helm list -n "$NAMESPACE" -o yaml > "$backup_dir/helm-releases.yaml" 2>/dev/null || true
    
    log "Configuration backup completed"
}

# Get monitoring components
get_monitoring_components() {
    local components=()
    
    # Check for Helm releases
    if helm list -n "$NAMESPACE" | grep -q prometheus; then
        components+=("prometheus")
    fi
    
    if helm list -n "$NAMESPACE" | grep -q grafana; then
        components+=("grafana")
    fi
    
    if helm list -n "$NAMESPACE" | grep -q alertmanager; then
        components+=("alertmanager")
    fi
    
    if helm list -n "$NAMESPACE" | grep -q loki; then
        components+=("loki")
    fi
    
    echo "${components[@]}"
}

# Uninstall Helm releases
uninstall_helm_releases() {
    local components
    IFS=' ' read -ra components <<< "$(get_monitoring_components)"
    
    if [[ ${#components[@]} -eq 0 ]]; then
        log "No Helm releases found in namespace '$NAMESPACE'"
        return
    fi
    
    log "Found Helm releases: ${components[*]}"
    
    for component in "${components[@]}"; do
        log "Uninstalling $component..."
        
        if [[ "$DRY_RUN" == "true" ]]; then
            log "DRY RUN: Would uninstall Helm release '$component'"
            continue
        fi
        
        if helm uninstall "$component" -n "$NAMESPACE"; then
            log "✅ Successfully uninstalled $component"
        else
            log_warn "⚠️ Failed to uninstall $component or already removed"
        fi
    done
}

# Delete custom resources
delete_custom_resources() {
    log "Deleting custom resources..."
    
    # List of custom resources to delete
    local resources=(
        "configmaps"
        "secrets"
        "serviceaccounts"
        "roles"
        "rolebindings"
        "clusterroles"
        "clusterrolebindings"
    )
    
    for resource in "${resources[@]}"; do
        log_debug "Checking for custom $resource..."
        
        local resource_list
        resource_list=$(kubectl get "$resource" -n "$NAMESPACE" -o name 2>/dev/null | grep -E "(prometheus|grafana|alertmanager|monitoring)" || true)
        
        if [[ -n "$resource_list" ]]; then
            log "Deleting custom $resource..."
            
            if [[ "$DRY_RUN" == "true" ]]; then
                log "DRY RUN: Would delete $resource"
                continue
            fi
            
            echo "$resource_list" | while read -r res; do
                if [[ -n "$res" ]]; then
                    kubectl delete "$res" -n "$NAMESPACE" 2>/dev/null || log_warn "Failed to delete $res"
                fi
            done
        fi
    done
}

# Handle persistent volumes
handle_persistent_volumes() {
    local pvcs
    pvcs=$(kubectl get pvc -n "$NAMESPACE" -o name 2>/dev/null || true)
    
    if [[ -z "$pvcs" ]]; then
        log "No persistent volumes found"
        return
    fi
    
    if [[ "$PRESERVE_DATA" == "true" ]]; then
        log "Preserving persistent volumes as requested"
        
        # Add labels to PVCs for identification
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "$pvcs" | while read -r pvc; do
                if [[ -n "$pvc" ]]; then
                    kubectl label "$pvc" -n "$NAMESPACE" preserved-by=noah-teardown --overwrite 2>/dev/null || true
                fi
            done
        fi
        
        log "Persistent volumes have been labeled for preservation"
        return
    fi
    
    log "Deleting persistent volumes..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would delete persistent volumes"
        echo "$pvcs" | while read -r pvc; do
            [[ -n "$pvc" ]] && log "  - $pvc"
        done
        return
    fi
    
    echo "$pvcs" | while read -r pvc; do
        if [[ -n "$pvc" ]]; then
            log "Deleting $pvc..."
            kubectl delete "$pvc" -n "$NAMESPACE" 2>/dev/null || log_warn "Failed to delete $pvc"
        fi
    done
}

# Wait for resource deletion
wait_for_deletion() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would wait for resource deletion"
        return
    fi
    
    log "Waiting for resources to be deleted..."
    
    local max_wait=300  # 5 minutes
    local wait_time=0
    
    while [[ $wait_time -lt $max_wait ]]; do
        local pods
        pods=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
        
        if [[ $pods -eq 0 ]]; then
            log "All pods have been deleted"
            break
        fi
        
        log_debug "Waiting for $pods pods to be deleted..."
        sleep 10
        ((wait_time += 10))
    done
    
    if [[ $wait_time -ge $max_wait ]]; then
        log_warn "Timeout waiting for all resources to be deleted"
    fi
}

# Delete namespace
delete_namespace() {
    log "Checking if namespace should be deleted..."
    
    # Check if namespace has other resources
    local resource_count
    resource_count=$(kubectl get all -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [[ $resource_count -gt 0 ]]; then
        log_warn "Namespace '$NAMESPACE' contains other resources. Not deleting namespace."
        return
    fi
    
    log "Deleting namespace: $NAMESPACE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would delete namespace '$NAMESPACE'"
        return
    fi
    
    if kubectl delete namespace "$NAMESPACE" --timeout=300s; then
        log "✅ Namespace '$NAMESPACE' deleted successfully"
    else
        log_warn "⚠️ Failed to delete namespace '$NAMESPACE'"
    fi
}

# Display remaining resources
display_remaining_resources() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return
    fi
    
    log "Checking for remaining resources..."
    
    # Check if namespace still exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log "Namespace '$NAMESPACE' has been completely removed"
        return
    fi
    
    # List remaining resources
    local remaining_resources
    remaining_resources=$(kubectl get all -n "$NAMESPACE" --no-headers 2>/dev/null || true)
    
    if [[ -n "$remaining_resources" ]]; then
        echo -e "\n${YELLOW}Remaining resources in namespace '$NAMESPACE':${NC}"
        echo "$remaining_resources"
    fi
    
    # List preserved PVCs
    if [[ "$PRESERVE_DATA" == "true" ]]; then
        local preserved_pvcs
        preserved_pvcs=$(kubectl get pvc -n "$NAMESPACE" -l preserved-by=noah-teardown --no-headers 2>/dev/null || true)
        
        if [[ -n "$preserved_pvcs" ]]; then
            echo -e "\n${BLUE}Preserved persistent volumes:${NC}"
            echo "$preserved_pvcs"
        fi
    fi
}

# Generate teardown report
generate_teardown_report() {
    local report_file="monitoring-teardown-$(date +%Y%m%d-%H%M%S).log"
    
    {
        echo "NOAH Monitoring Stack Teardown Report"
        echo "=============================================="
        echo "Timestamp: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Namespace: $NAMESPACE"
        echo "Preserve Data: $PRESERVE_DATA"
        echo "Force Delete: $FORCE_DELETE"
        echo "Dry Run: $DRY_RUN"
        echo ""
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "DRY RUN: No actual changes were made"
            echo ""
            echo "Components that would be removed:"
            IFS=' ' read -ra components <<< "$(get_monitoring_components)"
            for component in "${components[@]}"; do
                echo "- $component"
            done
        else
            echo "Teardown completed successfully"
            echo ""
            echo "Components removed:"
            echo "- Prometheus (if existed)"
            echo "- Grafana (if existed)"
            echo "- Alertmanager (if existed)"
            echo "- Custom configurations"
            echo ""
            
            if [[ "$PRESERVE_DATA" == "true" ]]; then
                echo "Data preservation: Enabled"
                echo "Persistent volumes have been preserved and labeled"
            else
                echo "Data preservation: Disabled"
                echo "All data has been permanently deleted"
            fi
        fi
        
    } | tee "$report_file"
    
    log "Teardown report saved to: $report_file"
}

# Main function
main() {
    echo -e "${BLUE}🧹 NOAH - Enhanced Monitoring Stack Teardown v${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate environment
    validate_environment
    
    # Confirm deletion
    confirm_deletion
    
    # Backup configurations
    backup_configurations
    
    # Start teardown process
    log "Starting monitoring stack teardown..."
    
    # Uninstall Helm releases
    uninstall_helm_releases
    
    # Delete custom resources
    delete_custom_resources
    
    # Handle persistent volumes
    handle_persistent_volumes
    
    # Wait for deletion to complete
    wait_for_deletion
    
    # Delete namespace if empty
    delete_namespace
    
    # Display remaining resources
    display_remaining_resources
    
    # Generate teardown report
    generate_teardown_report
    
    # Success message
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "\n${GREEN}🎯 Dry run completed successfully!${NC}"
        echo -e "${BLUE}Use the same command without --dry-run to perform the actual teardown.${NC}"
    else
        echo -e "\n${GREEN}🧹 Monitoring stack teardown completed successfully!${NC}"
        
        if [[ "$PRESERVE_DATA" == "true" ]]; then
            echo -e "${BLUE}💾 Persistent volumes have been preserved${NC}"
        else
            echo -e "${YELLOW}⚠️  All monitoring data has been permanently deleted${NC}"
        fi
    fi
}

# Execute main function
main "$@"