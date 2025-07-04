#!/bin/bash

# =======================
# NOAH - Comprehensive Status Check Script
# =======================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="status_check.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_ENVIRONMENT="dev"
DEFAULT_NAMESPACE_PREFIX="noah"
SHOW_DETAILED=false
SHOW_LOGS=false
CHECK_HEALTH=true
OUTPUT_FORMAT="table"
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
${BLUE}NOAH - Comprehensive Status Check Script v${SCRIPT_VERSION}${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS]

${YELLOW}OPTIONS:${NC}
    -e, --environment ENV        Target environment (dev/staging/prod) [default: ${DEFAULT_ENVIRONMENT}]
    -n, --namespace-prefix PREFIX Namespace prefix for deployments [default: ${DEFAULT_NAMESPACE_PREFIX}]
    -d, --detailed              Show detailed status information
    -l, --show-logs             Show recent logs for failed components
    --no-health-check           Skip health checks
    -f, --format FORMAT         Output format (table/json/yaml) [default: ${OUTPUT_FORMAT}]
    -v, --verbose               Enable verbose logging
    -h, --help                  Show this help message

${YELLOW}EXAMPLES:${NC}
    $0 --environment prod --detailed
    $0 --format json --no-health-check
    $0 --show-logs --verbose

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
            -d|--detailed)
                SHOW_DETAILED=true
                shift
                ;;
            -l|--show-logs)
                SHOW_LOGS=true
                shift
                ;;
            --no-health-check)
                CHECK_HEALTH=false
                shift
                ;;
            -f|--format)
                OUTPUT_FORMAT="$2"
                shift 2
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
    log_debug "Validating environment and dependencies..."
    
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

    log_debug "Environment validation completed successfully"
}

# Get cluster information
get_cluster_info() {
    echo -e "${BLUE}🏗️  Cluster Information${NC}"
    echo -e "${BLUE}=======================${NC}"
    
    # Kubernetes version
    local k8s_version
    k8s_version=$(kubectl version --short 2>/dev/null | grep 'Server Version' | awk '{print $3}' || echo "Unknown")
    echo -e "Kubernetes Version: ${GREEN}$k8s_version${NC}"
    
    # Current context
    local context
    context=$(kubectl config current-context 2>/dev/null || echo "Unknown")
    echo -e "Current Context: ${CYAN}$context${NC}"
    
    # Cluster nodes
    local node_count
    node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo "0")
    echo -e "Nodes: ${GREEN}$node_count${NC}"
    
    if [[ "$SHOW_DETAILED" == "true" ]]; then
        echo -e "\n${YELLOW}Node Details:${NC}"
        kubectl get nodes -o wide 2>/dev/null || echo "Failed to get node details"
    fi
    
    echo ""
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

# Check Helm release status
check_helm_release() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    local status="Not Installed"
    local revision="N/A"
    local chart_version="N/A"
    local app_version="N/A"
    local last_deployed="N/A"
    
    if helm list -n "$namespace" | grep -q "^$chart"; then
        local helm_status
        helm_status=$(helm status "$chart" -n "$namespace" -o json 2>/dev/null || echo "{}")
        
        if [[ "$helm_status" != "{}" ]]; then
            status=$(echo "$helm_status" | jq -r '.info.status // "Unknown"')
            revision=$(echo "$helm_status" | jq -r '.version // "N/A"')
            chart_version=$(echo "$helm_status" | jq -r '.chart.metadata.version // "N/A"')
            app_version=$(echo "$helm_status" | jq -r '.chart.metadata.appVersion // "N/A"')
            last_deployed=$(echo "$helm_status" | jq -r '.info.last_deployed // "N/A"' | cut -d'T' -f1)
        fi
    fi
    
    echo "$status|$revision|$chart_version|$app_version|$last_deployed"
}

# Check deployment status
check_deployment_status() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    local ready_replicas=0
    local desired_replicas=0
    local available_replicas=0
    local deployment_status="Not Found"
    
    if kubectl get deployment "$chart" -n "$namespace" &>/dev/null; then
        local deployment_info
        deployment_info=$(kubectl get deployment "$chart" -n "$namespace" -o json 2>/dev/null)
        
        if [[ -n "$deployment_info" ]]; then
            ready_replicas=$(echo "$deployment_info" | jq -r '.status.readyReplicas // 0')
            desired_replicas=$(echo "$deployment_info" | jq -r '.spec.replicas // 0')
            available_replicas=$(echo "$deployment_info" | jq -r '.status.availableReplicas // 0')
            
            if [[ $ready_replicas -eq $desired_replicas && $available_replicas -eq $desired_replicas ]]; then
                deployment_status="Ready"
            elif [[ $ready_replicas -gt 0 ]]; then
                deployment_status="Partial"
            else
                deployment_status="Not Ready"
            fi
        fi
    fi
    
    echo "$deployment_status|$ready_replicas/$desired_replicas"
}

# Check service status
check_service_status() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    local service_type="N/A"
    local cluster_ip="N/A"
    local external_ip="N/A"
    local ports="N/A"
    
    if kubectl get service "$chart" -n "$namespace" &>/dev/null; then
        local service_info
        service_info=$(kubectl get service "$chart" -n "$namespace" -o json 2>/dev/null)
        
        if [[ -n "$service_info" ]]; then
            service_type=$(echo "$service_info" | jq -r '.spec.type // "N/A"')
            cluster_ip=$(echo "$service_info" | jq -r '.spec.clusterIP // "N/A"')
            
            # Get external IP
            if [[ "$service_type" == "LoadBalancer" ]]; then
                external_ip=$(echo "$service_info" | jq -r '.status.loadBalancer.ingress[0].ip // "Pending"')
            elif [[ "$service_type" == "NodePort" ]]; then
                external_ip="NodePort"
            fi
            
            # Get ports
            ports=$(echo "$service_info" | jq -r '.spec.ports | map("\(.port):\(.targetPort)") | join(",")')
        fi
    fi
    
    echo "$service_type|$cluster_ip|$external_ip|$ports"
}

# Perform health check
perform_health_check() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    if [[ "$CHECK_HEALTH" != "true" ]]; then
        echo "Skipped"
        return
    fi
    
    local health_status="Unknown"
    
    # Check if deployment is ready
    if kubectl get deployment "$chart" -n "$namespace" &>/dev/null; then
        if kubectl rollout status deployment/"$chart" -n "$namespace" --timeout=30s &>/dev/null; then
            health_status="Healthy"
        else
            health_status="Unhealthy"
        fi
    else
        health_status="No Deployment"
    fi
    
    echo "$health_status"
}

# Get pod logs
get_pod_logs() {
    local chart="$1"
    local namespace="${NAMESPACE_PREFIX}-${chart}"
    
    if [[ "$SHOW_LOGS" != "true" ]]; then
        return
    fi
    
    local pods
    pods=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name="$chart" --no-headers 2>/dev/null | awk '{print $1}' || true)
    
    if [[ -n "$pods" ]]; then
        echo -e "\n${YELLOW}Recent logs for $chart:${NC}"
        echo "$pods" | while read -r pod; do
            if [[ -n "$pod" ]]; then
                echo -e "${CYAN}--- Pod: $pod ---${NC}"
                kubectl logs "$pod" -n "$namespace" --tail=10 2>/dev/null || echo "Failed to get logs"
            fi
        done
    fi
}

# Display status table
display_status_table() {
    local charts
    IFS=' ' read -ra charts <<< "$(get_available_charts)"
    
    echo -e "${BLUE}📊 NOAH Services Status${NC}"
    echo -e "${BLUE}=============================${NC}"
    
    # Table header
    printf "%-15s %-12s %-8s %-12s %-10s %-15s %-10s\n" \
        "SERVICE" "HELM_STATUS" "REV" "DEPLOYMENT" "REPLICAS" "SERVICE_TYPE" "HEALTH"
    echo "--------------------------------------------------------------------------------"
    
    for chart in "${charts[@]}"; do
        local helm_info deployment_info service_info health
        
        # Get status information
        helm_info=$(check_helm_release "$chart")
        deployment_info=$(check_deployment_status "$chart")
        service_info=$(check_service_status "$chart")
        health=$(perform_health_check "$chart")
        
        # Parse information
        IFS='|' read -r helm_status revision chart_version app_version last_deployed <<< "$helm_info"
        IFS='|' read -r deployment_status replicas <<< "$deployment_info"
        IFS='|' read -r service_type cluster_ip external_ip ports <<< "$service_info"
        
        # Color coding
        local helm_color="$RED"
        [[ "$helm_status" == "deployed" ]] && helm_color="$GREEN"
        [[ "$helm_status" == "pending-install" || "$helm_status" == "pending-upgrade" ]] && helm_color="$YELLOW"
        
        local deployment_color="$RED"
        [[ "$deployment_status" == "Ready" ]] && deployment_color="$GREEN"
        [[ "$deployment_status" == "Partial" ]] && deployment_color="$YELLOW"
        
        local health_color="$RED"
        [[ "$health" == "Healthy" ]] && health_color="$GREEN"
        [[ "$health" == "Skipped" ]] && health_color="$CYAN"
        
        # Display row
        printf "%-15s ${helm_color}%-12s${NC} %-8s ${deployment_color}%-12s${NC} %-10s %-15s ${health_color}%-10s${NC}\n" \
            "$chart" "$helm_status" "$revision" "$deployment_status" "$replicas" "$service_type" "$health"
        
        # Show detailed information if requested
        if [[ "$SHOW_DETAILED" == "true" ]]; then
            echo "  Chart Version: $chart_version, App Version: $app_version"
            echo "  Last Deployed: $last_deployed"
            echo "  Cluster IP: $cluster_ip, External IP: $external_ip"
            echo "  Ports: $ports"
            echo ""
        fi
        
        # Show logs if requested and service is unhealthy
        if [[ "$SHOW_LOGS" == "true" && ("$deployment_status" != "Ready" || "$health" == "Unhealthy") ]]; then
            get_pod_logs "$chart"
        fi
    done
    
    echo ""
}

# Display status in JSON format
display_status_json() {
    local charts
    IFS=' ' read -ra charts <<< "$(get_available_charts)"
    
    local json_output='{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","environment":"'$ENVIRONMENT'","services":['
    
    local first=true
    for chart in "${charts[@]}"; do
        [[ "$first" == "false" ]] && json_output+=","
        first=false
        
        local helm_info deployment_info service_info health
        helm_info=$(check_helm_release "$chart")
        deployment_info=$(check_deployment_status "$chart")
        service_info=$(check_service_status "$chart")
        health=$(perform_health_check "$chart")
        
        # Parse information
        IFS='|' read -r helm_status revision chart_version app_version last_deployed <<< "$helm_info"
        IFS='|' read -r deployment_status replicas <<< "$deployment_info"
        IFS='|' read -r service_type cluster_ip external_ip ports <<< "$service_info"
        
        json_output+='{
            "name":"'$chart'",
            "helm_status":"'$helm_status'",
            "revision":"'$revision'",
            "chart_version":"'$chart_version'",
            "app_version":"'$app_version'",
            "last_deployed":"'$last_deployed'",
            "deployment_status":"'$deployment_status'",
            "replicas":"'$replicas'",
            "service_type":"'$service_type'",
            "cluster_ip":"'$cluster_ip'",
            "external_ip":"'$external_ip'",
            "ports":"'$ports'",
            "health":"'$health'"
        }'
    done
    
    json_output+=']}'
    
    echo "$json_output" | jq '.' 2>/dev/null || echo "$json_output"
}

# Display resource usage summary
display_resource_summary() {
    echo -e "${PURPLE}🔧 Resource Usage Summary${NC}"
    echo -e "${PURPLE}==========================${NC}"
    
    # CPU and Memory usage
    echo -e "${YELLOW}Node Resource Usage:${NC}"
    kubectl top nodes 2>/dev/null || echo "Metrics not available (metrics-server required)"
    
    echo -e "\n${YELLOW}Pod Resource Usage (Top 10):${NC}"
    kubectl top pods --all-namespaces --sort-by=cpu 2>/dev/null | head -11 || echo "Metrics not available"
    
    # Storage usage
    echo -e "\n${YELLOW}Persistent Volume Claims:${NC}"
    kubectl get pvc --all-namespaces -o custom-columns="NAMESPACE:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase,VOLUME:.spec.volumeName,CAPACITY:.status.capacity.storage,STORAGECLASS:.spec.storageClassName" 2>/dev/null || echo "No PVCs found"
    
    echo ""
}

# Display network information
display_network_info() {
    echo -e "${CYAN}🌐 Network Information${NC}"
    echo -e "${CYAN}======================${NC}"
    
    # Services with external access
    echo -e "${YELLOW}Services with External Access:${NC}"
    kubectl get services --all-namespaces --field-selector spec.type=LoadBalancer,NodePort -o wide 2>/dev/null || echo "No external services found"
    
    echo -e "\n${YELLOW}Ingress Resources:${NC}"
    kubectl get ingress --all-namespaces -o wide 2>/dev/null || echo "No ingress resources found"
    
    echo ""
}

# Generate status report
generate_status_report() {
    local report_file="noah-status-$(date +%Y%m%d-%H%M%S).log"
    
    {
        echo "NOAH Status Report"
        echo "=========================="
        echo "Generated: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Namespace Prefix: $NAMESPACE_PREFIX"
        echo ""
        
        # Cluster information
        get_cluster_info
        
        # Services status
        display_status_table
        
        if [[ "$SHOW_DETAILED" == "true" ]]; then
            # Resource usage
            display_resource_summary
            
            # Network information
            display_network_info
        fi
        
    } | tee "$report_file"
    
    log "Status report saved to: $report_file"
}

# Main function
main() {
    echo -e "${BLUE}📋 NOAH - Comprehensive Status Check v${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate environment
    validate_environment
    
    # Display cluster information
    get_cluster_info
    
    # Display status based on format
    case "$OUTPUT_FORMAT" in
        table)
            display_status_table
            ;;
        json)
            display_status_json
            ;;
        yaml)
            display_status_json | yq eval -P 2>/dev/null || display_status_json
            ;;
        *)
            error_exit "Unsupported output format: $OUTPUT_FORMAT"
            ;;
    esac
    
    # Show additional information if detailed mode
    if [[ "$SHOW_DETAILED" == "true" && "$OUTPUT_FORMAT" == "table" ]]; then
        display_resource_summary
        display_network_info
    fi
    
    # Generate report if not JSON/YAML output
    if [[ "$OUTPUT_FORMAT" == "table" ]]; then
        generate_status_report > /dev/null
    fi
    
    log "Status check completed successfully"
}

# Execute main function
main "$@"
