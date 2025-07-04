#!/bin/bash

# =======================
# OpenInfra - Enhanced Helm Charts Uninstall Script
# =======================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="uninstall_helm_charts.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_ENVIRONMENT="dev"
DEFAULT_NAMESPACE_PREFIX="openinfra"
FORCE_DELETE=false
PRESERVE_DATA=false
DELETE_NAMESPACES=false
DRY_RUN=false
VERBOSE=false

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
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
        echo -e "${CYAN}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

error_exit() {
    log_error "$1"
    exit 1
}

# Help function
show_help() {
    cat << EOF
${BLUE}OpenInfra - Enhanced Helm Charts Uninstall Script v${SCRIPT_VERSION}${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS]

${YELLOW}OPTIONS:${NC}
    -e, --environment ENV        Target environment (dev/staging/prod) [default: ${DEFAULT_ENVIRONMENT}]
    -n, --namespace-prefix PREFIX Namespace prefix for deployments [default: ${DEFAULT_NAMESPACE_PREFIX}]
    -c, --charts CHART1,CHART2   Uninstall specific charts only
    -f, --force                  Force delete without confirmation
    -p, --preserve-data          Preserve persistent volumes and data
    --delete-namespaces         Delete namespaces after uninstalling charts
    -d, --dry-run               Show what would be deleted without actually deleting
    -v, --verbose               Enable verbose logging
    -h, --help                  Show this help message

${YELLOW}EXAMPLES:${NC}
    $0 --environment prod --preserve-data
    $0 --charts gitlab,keycloak --force
    $0 --dry-run --verbose --delete-namespaces

${YELLOW}SUPPORTED CHARTS:${NC}
    gitlab, grafana, keycloak, mattermost, nextcloud, oauth2-proxy,
    openedr, prometheus, samba4, wazuh

${YELLOW}WARNING:${NC}
    This script will remove all specified charts and their data!
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
            -n|--namespace-prefix)
                NAMESPACE_PREFIX="$2"
                shift 2
                ;;
            -c|--charts)
                IFS=',' read -ra SELECTED_CHARTS <<< "$2"
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
            --delete-namespaces)
                DELETE_NAMESPACES=true
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
    NAMESPACE_PREFIX="${NAMESPACE_PREFIX:-$DEFAULT_NAMESPACE_PREFIX}"
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

    log "Environment validation completed successfully"
}

# Get available charts
get_available_charts() {
    local charts=()
    local helm_charts_dir="$SCRIPT_DIR/../Helm"
    
    if [[ -d "$helm_charts_dir" ]]; then
        for chart_dir in "$helm_charts_dir"/*; do
            if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
                charts+=($(basename "$chart_dir"))
            fi
        done
    else
        # Default charts if directory structure not available
        charts=("gitlab" "grafana" "keycloak" "mattermost" "nextcloud" "oauth2-proxy" "openedr" "prometheus" "samba4" "wazuh")
    fi
    
    echo "${charts[@]}"
}

# Get installed releases
get_installed_releases() {
    local installed_releases=()
    
    # Get all Helm releases across all namespaces
    local releases
    releases=$(helm list --all-namespaces -q 2>/dev/null || true)
    
    if [[ -n "$releases" ]]; then
        while IFS= read -r release; do
            if [[ -n "$release" ]]; then
                installed_releases+=("$release")
            fi
        done <<< "$releases"
    fi
    
    echo "${installed_releases[@]}"
}

# Check if chart is installed
is_chart_installed() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    if helm list -n "$namespace" | grep -q "^$chart"; then
        return 0
    else
        return 1
    fi
}

# Confirm deletion
confirm_deletion() {
    if [[ "$FORCE_DELETE" == "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    local charts_to_delete=()
    if [[ -n "${SELECTED_CHARTS:-}" ]]; then
        charts_to_delete=("${SELECTED_CHARTS[@]}")
    else
        IFS=' ' read -ra charts_to_delete <<< "$(get_available_charts)"
    fi
    
    echo -e "${YELLOW}⚠️  WARNING: This will uninstall the following OpenInfra charts:${NC}"
    for chart in "${charts_to_delete[@]}"; do
        local namespace="${NAMESPACE_PREFIX}-${chart}"
        if is_chart_installed "$chart"; then
            echo -e "  ${RED}✓${NC} $chart (namespace: $namespace)"
        else
            echo -e "  ${YELLOW}-${NC} $chart (not installed)"
        fi
    done
    
    echo ""
    echo -e "${YELLOW}Environment: $ENVIRONMENT${NC}"
    echo -e "${YELLOW}Namespace Prefix: $NAMESPACE_PREFIX${NC}"
    
    if [[ "$PRESERVE_DATA" == "false" ]]; then
        echo -e "${RED}⚠️  All application data will be permanently lost!${NC}"
    else
        echo -e "${BLUE}ℹ️  Persistent volumes will be preserved${NC}"
    fi
    
    if [[ "$DELETE_NAMESPACES" == "true" ]]; then
        echo -e "${YELLOW}⚠️  Namespaces will be deleted after chart removal${NC}"
    fi
    
    echo ""
    read -p "Are you sure you want to proceed? (type 'yes' to confirm): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log "Uninstallation cancelled by user"
        exit 0
    fi
}

# Create backup
create_backup() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would create backup"
        return
    fi
    
    local backup_dir="openinfra-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    log "Creating backup in: $backup_dir"
    
    local charts_to_backup=()
    if [[ -n "${SELECTED_CHARTS:-}" ]]; then
        charts_to_backup=("${SELECTED_CHARTS[@]}")
    else
        IFS=' ' read -ra charts_to_backup <<< "$(get_available_charts)"
    fi
    
    for chart in "${charts_to_backup[@]}"; do
        local namespace="${NAMESPACE_PREFIX}-${chart}"
        
        if ! is_chart_installed "$chart"; then
            log_debug "Chart $chart not installed, skipping backup"
            continue
        fi
        
        log_debug "Backing up $chart..."
        
        local chart_backup_dir="$backup_dir/$chart"
        mkdir -p "$chart_backup_dir"
        
        # Backup Helm release values
        helm get values "$chart" -n "$namespace" > "$chart_backup_dir/values.yaml" 2>/dev/null || true
        
        # Backup ConfigMaps
        kubectl get configmap -n "$namespace" -o yaml > "$chart_backup_dir/configmaps.yaml" 2>/dev/null || true
        
        # Backup Secrets (without sensitive data)
        kubectl get secret -n "$namespace" -o yaml | \
            sed 's/data:/data: {}/' > "$chart_backup_dir/secrets.yaml" 2>/dev/null || true
        
        # Backup PVCs info
        kubectl get pvc -n "$namespace" -o yaml > "$chart_backup_dir/pvcs.yaml" 2>/dev/null || true
        
        # Backup custom resources
        kubectl get all -n "$namespace" -o yaml > "$chart_backup_dir/resources.yaml" 2>/dev/null || true
    done
    
    log "Backup completed: $backup_dir"
}

# Handle persistent volumes for a chart
handle_persistent_volumes() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    local pvcs
    pvcs=$(kubectl get pvc -n "$namespace" -o name 2>/dev/null || true)
    
    if [[ -z "$pvcs" ]]; then
        log_debug "No persistent volumes found for $chart"
        return
    fi
    
    if [[ "$PRESERVE_DATA" == "true" ]]; then
        log "Preserving persistent volumes for $chart"
        
        if [[ "$DRY_RUN" == "false" ]]; then
            # Add labels to PVCs for identification
            echo "$pvcs" | while read -r pvc; do
                if [[ -n "$pvc" ]]; then
                    kubectl label "$pvc" -n "$namespace" preserved-by=openinfra-uninstall chart="$chart" --overwrite 2>/dev/null || true
                fi
            done
        fi
        
        log_debug "Persistent volumes for $chart have been labeled for preservation"
        return
    fi
    
    log "Deleting persistent volumes for $chart..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would delete persistent volumes for $chart"
        echo "$pvcs" | while read -r pvc; do
            [[ -n "$pvc" ]] && log_debug "  - $pvc"
        done
        return
    fi
    
    echo "$pvcs" | while read -r pvc; do
        if [[ -n "$pvc" ]]; then
            log_debug "Deleting $pvc..."
            kubectl delete "$pvc" -n "$namespace" 2>/dev/null || log_warn "Failed to delete $pvc"
        fi
    done
}

# Uninstall single chart
uninstall_chart() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    log "Processing chart: $chart"
    
    # Check if chart is installed
    if ! is_chart_installed "$chart"; then
        log_warn "Chart '$chart' is not installed or not found in namespace '$namespace'"
        return 1
    fi
    
    # Handle persistent volumes before uninstallation
    handle_persistent_volumes "$chart"
    
    # Uninstall Helm release
    log "Uninstalling Helm release '$chart' from namespace '$namespace'..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would uninstall Helm release '$chart' from namespace '$namespace'"
        return 0
    fi
    
    local helm_cmd="helm uninstall $chart --namespace $namespace --timeout 10m"
    
    log_debug "Executing: $helm_cmd"
    
    if eval "$helm_cmd"; then
        log "✅ Successfully uninstalled $chart"
        
        # Wait for pods to terminate
        log_debug "Waiting for pods to terminate in namespace $namespace..."
        local max_wait=120
        local wait_time=0
        
        while [[ $wait_time -lt $max_wait ]]; do
            local pod_count
            pod_count=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | wc -l)
            
            if [[ $pod_count -eq 0 ]]; then
                log_debug "All pods terminated for $chart"
                break
            fi
            
            sleep 5
            ((wait_time += 5))
        done
        
        return 0
    else
        log_error "❌ Failed to uninstall $chart"
        return 1
    fi
}

# Delete namespace if empty
delete_namespace_if_empty() {
    local namespace="$1"
    local chart="$2"
    
    if [[ "$DELETE_NAMESPACES" != "true" ]]; then
        log_debug "Namespace deletion disabled, keeping $namespace"
        return
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would check if namespace '$namespace' should be deleted"
        return
    fi
    
    # Check if namespace exists
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        log_debug "Namespace '$namespace' does not exist"
        return
    fi
    
    # Check if namespace has other resources (excluding preserved PVCs)
    local resource_count
    if [[ "$PRESERVE_DATA" == "true" ]]; then
        # Count resources excluding preserved PVCs
        resource_count=$(kubectl get all -n "$namespace" --no-headers 2>/dev/null | wc -l)
        local preserved_pvc_count
        preserved_pvc_count=$(kubectl get pvc -n "$namespace" -l preserved-by=openinfra-uninstall --no-headers 2>/dev/null | wc -l)
        
        # If only preserved PVCs remain, we can consider the namespace "empty" for our purposes
        if [[ $resource_count -eq 0 && $preserved_pvc_count -gt 0 ]]; then
            log "Namespace '$namespace' contains only preserved PVCs, not deleting"
            return
        fi
    else
        resource_count=$(kubectl get all -n "$namespace" --no-headers 2>/dev/null | wc -l)
    fi
    
    if [[ $resource_count -gt 0 ]]; then
        log_debug "Namespace '$namespace' contains other resources, not deleting"
        return
    fi
    
    log "Deleting empty namespace: $namespace"
    
    if kubectl delete namespace "$namespace" --timeout=60s; then
        log "✅ Namespace '$namespace' deleted successfully"
    else
        log_warn "⚠️ Failed to delete namespace '$namespace'"
    fi
}

# Generate uninstall report
generate_uninstall_report() {
    local report_file="openinfra-uninstall-$(date +%Y%m%d-%H%M%S).log"
    local successful_uninstalls=("$@")
    
    {
        echo "OpenInfra Helm Charts Uninstall Report"
        echo "=========================================="
        echo "Timestamp: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Namespace Prefix: $NAMESPACE_PREFIX"
        echo "Preserve Data: $PRESERVE_DATA"
        echo "Delete Namespaces: $DELETE_NAMESPACES"
        echo "Force Delete: $FORCE_DELETE"
        echo "Dry Run: $DRY_RUN"
        echo ""
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "DRY RUN: No actual changes were made"
            echo ""
            echo "Charts that would be uninstalled:"
            local charts_to_process=()
            if [[ -n "${SELECTED_CHARTS:-}" ]]; then
                charts_to_process=("${SELECTED_CHARTS[@]}")
            else
                IFS=' ' read -ra charts_to_process <<< "$(get_available_charts)"
            fi
            
            for chart in "${charts_to_process[@]}"; do
                if is_chart_installed "$chart"; then
                    echo "✓ $chart (currently installed)"
                else
                    echo "- $chart (not installed)"
                fi
            done
        else
            echo "Uninstallation Summary:"
            echo "======================"
            
            if [[ ${#successful_uninstalls[@]} -gt 0 ]]; then
                echo "Successfully uninstalled (${#successful_uninstalls[@]}):"
                for chart in "${successful_uninstalls[@]}"; do
                    echo "✅ $chart"
                done
            else
                echo "No charts were uninstalled"
            fi
            
            echo ""
            if [[ "$PRESERVE_DATA" == "true" ]]; then
                echo "Data Preservation: Enabled"
                echo "Persistent volumes have been preserved and labeled"
                
                # List preserved PVCs
                local preserved_pvcs
                preserved_pvcs=$(kubectl get pvc --all-namespaces -l preserved-by=openinfra-uninstall --no-headers 2>/dev/null || true)
                if [[ -n "$preserved_pvcs" ]]; then
                    echo ""
                    echo "Preserved Persistent Volumes:"
                    echo "$preserved_pvcs"
                fi
            else
                echo "Data Preservation: Disabled"
                echo "All application data has been deleted"
            fi
        fi
        
    } | tee "$report_file"
    
    log "Uninstall report saved to: $report_file"
}

# Display post-uninstall information
display_post_uninstall_info() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return
    fi
    
    echo -e "\n${BLUE}📋 Post-Uninstall Information${NC}"
    echo -e "${BLUE}==============================${NC}"
    
    # Check for remaining Helm releases
    local remaining_releases
    remaining_releases=$(helm list --all-namespaces | grep -E "(${NAMESPACE_PREFIX}-|openinfra)" || true)
    
    if [[ -n "$remaining_releases" ]]; then
        echo -e "${YELLOW}Remaining OpenInfra Helm releases:${NC}"
        echo "$remaining_releases"
    else
        echo -e "${GREEN}✅ No OpenInfra Helm releases remaining${NC}"
    fi
    
    # Check for remaining namespaces
    local remaining_namespaces
    remaining_namespaces=$(kubectl get namespaces | grep -E "(${NAMESPACE_PREFIX}-|openinfra)" || true)
    
    if [[ -n "$remaining_namespaces" ]]; then
        echo -e "\n${YELLOW}Remaining OpenInfra namespaces:${NC}"
        echo "$remaining_namespaces"
    fi
    
    # Show preserved PVCs if any
    if [[ "$PRESERVE_DATA" == "true" ]]; then
        local preserved_pvcs
        preserved_pvcs=$(kubectl get pvc --all-namespaces -l preserved-by=openinfra-uninstall --no-headers 2>/dev/null || true)
        
        if [[ -n "$preserved_pvcs" ]]; then
            echo -e "\n${BLUE}💾 Preserved Persistent Volumes:${NC}"
            echo "$preserved_pvcs"
            echo -e "\n${YELLOW}To restore data, you can remove the 'preserved-by' label and redeploy the charts.${NC}"
        fi
    fi
}

# Main function
main() {
    echo -e "${BLUE}🧹 OpenInfra - Enhanced Helm Charts Uninstall v${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate environment
    validate_environment
    
    # Confirm deletion
    confirm_deletion
    
    # Create backup
    create_backup
    
    # Get charts to uninstall
    local charts_to_uninstall=()
    if [[ -n "${SELECTED_CHARTS:-}" ]]; then
        charts_to_uninstall=("${SELECTED_CHARTS[@]}")
        log "Uninstalling selected charts: ${charts_to_uninstall[*]}"
    else
        IFS=' ' read -ra charts_to_uninstall <<< "$(get_available_charts)"
        log "Uninstalling all available charts: ${charts_to_uninstall[*]}"
    fi
    
    # Track successful uninstalls
    local successful_uninstalls=()
    local failed_uninstalls=()
    
    # Uninstall charts
    log "Starting chart uninstallation process..."
    
    for chart in "${charts_to_uninstall[@]}"; do
        if uninstall_chart "$chart"; then
            successful_uninstalls+=("$chart")
            
            # Handle namespace deletion
            local namespace="${NAMESPACE_PREFIX}-${chart}"
            delete_namespace_if_empty "$namespace" "$chart"
        else
            failed_uninstalls+=("$chart")
        fi
    done
    
    # Generate summary
    echo -e "\n${BLUE}📊 Uninstallation Summary${NC}"
    echo -e "${BLUE}==========================${NC}"
    
    if [[ ${#successful_uninstalls[@]} -gt 0 ]]; then
        echo -e "${GREEN}✅ Successfully uninstalled (${#successful_uninstalls[@]}):${NC}"
        printf '   %s\n' "${successful_uninstalls[@]}"
    fi
    
    if [[ ${#failed_uninstalls[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Failed uninstalls (${#failed_uninstalls[@]}):${NC}"
        printf '   %s\n' "${failed_uninstalls[@]}"
    fi
    
    # Display post-uninstall information
    display_post_uninstall_info
    
    # Generate uninstall report
    generate_uninstall_report "${successful_uninstalls[@]}"
    
    # Final status
    if [[ ${#failed_uninstalls[@]} -eq 0 ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo -e "\n${GREEN}🎯 Dry run completed successfully!${NC}"
            echo -e "${BLUE}Use the same command without --dry-run to perform the actual uninstallation.${NC}"
        else
            echo -e "\n${GREEN}🎉 All charts uninstalled successfully!${NC}"
        fi
        exit 0
    else
        echo -e "\n${YELLOW}⚠️ Uninstallation completed with some failures.${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"