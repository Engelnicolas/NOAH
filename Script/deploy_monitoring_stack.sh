#!/bin/bash

# =======================
# OpenInfra - Enhanced Monitoring Stack Deployment Script
# =======================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="deploy_monitoring_stack.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
DEFAULT_ENVIRONMENT="dev"
DEFAULT_NAMESPACE="monitoring"
DEFAULT_PROMETHEUS_RETENTION="15d"
DEFAULT_GRAFANA_PASSWORD="admin"
ENABLE_ALERTMANAGER=true
ENABLE_NODE_EXPORTER=true
ENABLE_KUBE_STATE_METRICS=true
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
${BLUE}OpenInfra - Enhanced Monitoring Stack Deployment v${SCRIPT_VERSION}${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS]

${YELLOW}OPTIONS:${NC}
    -e, --environment ENV        Target environment (dev/staging/prod) [default: ${DEFAULT_ENVIRONMENT}]
    -n, --namespace NAMESPACE    Kubernetes namespace [default: ${DEFAULT_NAMESPACE}]
    -r, --retention DURATION     Prometheus data retention [default: ${DEFAULT_RETENTION}]
    -p, --grafana-password PWD   Grafana admin password [default: ${DEFAULT_GRAFANA_PASSWORD}]
    --no-alertmanager           Disable Alertmanager deployment
    --no-node-exporter          Disable Node Exporter deployment
    --no-kube-state-metrics     Disable Kube State Metrics deployment
    -d, --dry-run               Perform a dry run without making changes
    -v, --verbose               Enable verbose logging
    -h, --help                  Show this help message

${YELLOW}EXAMPLES:${NC}
    $0 --environment prod --retention 30d
    $0 --namespace observability --grafana-password secretpass
    $0 --dry-run --verbose

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
            -r|--retention)
                PROMETHEUS_RETENTION="$2"
                shift 2
                ;;
            -p|--grafana-password)
                GRAFANA_PASSWORD="$2"
                shift 2
                ;;
            --no-alertmanager)
                ENABLE_ALERTMANAGER=false
                shift
                ;;
            --no-node-exporter)
                ENABLE_NODE_EXPORTER=false
                shift
                ;;
            --no-kube-state-metrics)
                ENABLE_KUBE_STATE_METRICS=false
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
    PROMETHEUS_RETENTION="${PROMETHEUS_RETENTION:-$DEFAULT_PROMETHEUS_RETENTION}"
    GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-$DEFAULT_GRAFANA_PASSWORD}"
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

# Create namespace
create_namespace() {
    log "Creating namespace: $NAMESPACE"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would create namespace $NAMESPACE"
        return
    fi
    
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
}

# Generate Prometheus configuration
generate_prometheus_config() {
    local config_file="prometheus-config.yaml"
    
    log "Generating Prometheus configuration..."
    
    cat > "$config_file" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: $NAMESPACE
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
      external_labels:
        cluster: 'openinfra-$ENVIRONMENT'
        environment: '$ENVIRONMENT'

    rule_files:
      - "/etc/prometheus/rules/*.yml"

    alerting:
      alertmanagers:
        - static_configs:
            - targets:
              - alertmanager:9093

    scrape_configs:
      # Prometheus itself
      - job_name: 'prometheus'
        static_configs:
          - targets: ['localhost:9090']

      # Kubernetes API server
      - job_name: 'kubernetes-apiservers'
        kubernetes_sd_configs:
          - role: endpoints
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
          - source_labels: [__meta_kubernetes_namespace, __meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]
            action: keep
            regex: default;kubernetes;https

      # Kubernetes nodes
      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
          - role: node
        scheme: https
        tls_config:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        bearer_token_file: /var/run/secrets/kubernetes.io/serviceaccount/token
        relabel_configs:
          - action: labelmap
            regex: __meta_kubernetes_node_label_(.+)
          - target_label: __address__
            replacement: kubernetes.default.svc:443
          - source_labels: [__meta_kubernetes_node_name]
            regex: (.+)
            target_label: __metrics_path__
            replacement: /api/v1/nodes/\${1}/proxy/metrics

      # Kubernetes pods
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: \$1:\$2
            target_label: __address__
          - action: labelmap
            regex: __meta_kubernetes_pod_label_(.+)
          - source_labels: [__meta_kubernetes_namespace]
            action: replace
            target_label: kubernetes_namespace
          - source_labels: [__meta_kubernetes_pod_name]
            action: replace
            target_label: kubernetes_pod_name

      # OpenInfra services
      - job_name: 'openinfra-services'
        kubernetes_sd_configs:
          - role: service
        relabel_configs:
          - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scheme]
            action: replace
            target_label: __scheme__
            regex: (https?)
          - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_service_annotation_prometheus_io_port]
            action: replace
            target_label: __address__
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: \$1:\$2
          - action: labelmap
            regex: __meta_kubernetes_service_label_(.+)
          - source_labels: [__meta_kubernetes_namespace]
            action: replace
            target_label: kubernetes_namespace
          - source_labels: [__meta_kubernetes_service_name]
            action: replace
            target_label: kubernetes_service_name
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Generated Prometheus configuration (not applied)"
        rm "$config_file"
        return
    fi
    
    kubectl apply -f "$config_file"
    rm "$config_file"
    
    log "Prometheus configuration created successfully"
}

# Generate alerting rules
generate_alerting_rules() {
    local rules_file="prometheus-rules.yaml"
    
    log "Generating Prometheus alerting rules..."
    
    cat > "$rules_file" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: $NAMESPACE
data:
  openinfra.yml: |
    groups:
    - name: openinfra.rules
      rules:
      - alert: HighErrorRate
        expr: |
          (
            rate(http_requests_total{status=~"5.."}[5m]) /
            rate(http_requests_total[5m])
          ) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ \$value | humanizePercentage }} for {{ \$labels.service }}"

      - alert: PodCrashLooping
        expr: |
          rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod is crash looping"
          description: "Pod {{ \$labels.namespace }}/{{ \$labels.pod }} is restarting frequently"

      - alert: NodeNotReady
        expr: |
          kube_node_status_condition{condition="Ready",status="true"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Node is not ready"
          description: "Node {{ \$labels.node }} has been not ready for more than 2 minutes"

      - alert: DiskSpaceHigh
        expr: |
          (
            node_filesystem_avail_bytes{mountpoint="/"} /
            node_filesystem_size_bytes{mountpoint="/"}
          ) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Disk space is running low"
          description: "Disk space on {{ \$labels.instance }} is {{ \$value | humanizePercentage }} full"

      - alert: MemoryUsageHigh
        expr: |
          (
            (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) /
            node_memory_MemTotal_bytes
          ) > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage on {{ \$labels.instance }} is {{ \$value | humanizePercentage }}"
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Generated alerting rules (not applied)"
        rm "$rules_file"
        return
    fi
    
    kubectl apply -f "$rules_file"
    rm "$rules_file"
    
    log "Prometheus alerting rules created successfully"
}

# Install Prometheus
install_prometheus() {
    log "Installing Prometheus..."
    
    # Add Helm repository
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Prepare Prometheus values
    local values_args="--set server.retention=$PROMETHEUS_RETENTION"
    values_args="$values_args --set server.global.external_labels.environment=$ENVIRONMENT"
    values_args="$values_args --set server.global.external_labels.cluster=openinfra-$ENVIRONMENT"
    
    if [[ "$ENABLE_ALERTMANAGER" == "false" ]]; then
        values_args="$values_args --set alertmanager.enabled=false"
    fi
    
    if [[ "$ENABLE_NODE_EXPORTER" == "false" ]]; then
        values_args="$values_args --set nodeExporter.enabled=false"
    fi
    
    if [[ "$ENABLE_KUBE_STATE_METRICS" == "false" ]]; then
        values_args="$values_args --set kubeStateMetrics.enabled=false"
    fi
    
    # Environment-specific configurations
    case "$ENVIRONMENT" in
        dev)
            values_args="$values_args --set server.resources.requests.memory=512Mi"
            values_args="$values_args --set server.resources.requests.cpu=250m"
            ;;
        staging)
            values_args="$values_args --set server.resources.requests.memory=1Gi"
            values_args="$values_args --set server.resources.requests.cpu=500m"
            ;;
        prod)
            values_args="$values_args --set server.resources.requests.memory=2Gi"
            values_args="$values_args --set server.resources.requests.cpu=1000m"
            values_args="$values_args --set server.replicaCount=2"
            ;;
    esac
    
    local helm_cmd="helm upgrade --install prometheus prometheus-community/prometheus"
    helm_cmd="$helm_cmd --namespace $NAMESPACE"
    helm_cmd="$helm_cmd --create-namespace"
    helm_cmd="$helm_cmd $values_args"
    helm_cmd="$helm_cmd --wait --timeout=10m"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        helm_cmd="$helm_cmd --dry-run"
        log "DRY RUN: $helm_cmd"
        return
    fi
    
    log_debug "Executing: $helm_cmd"
    
    if eval "$helm_cmd"; then
        log "✅ Prometheus installed successfully"
    else
        error_exit "❌ Failed to install Prometheus"
    fi
}

# Install Grafana
install_grafana() {
    log "Installing Grafana..."
    
    # Add Helm repository
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Generate Grafana datasource configuration
    local datasource_config='
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server:80
      access: proxy
      isDefault: true
      editable: true
    - name: Loki
      type: loki
      url: http://loki:3100
      access: proxy
      editable: true
'
    
    # Generate dashboard providers configuration
    local dashboard_providers='
dashboardProviders:
  dashboardproviders.yaml:
    apiVersion: 1
    providers:
    - name: default
      orgId: 1
      folder: ""
      type: file
      disableDeletion: true
      updateIntervalSeconds: 10
      allowUiUpdates: false
      options:
        path: /var/lib/grafana/dashboards/default
'
    
    # Prepare Grafana values
    local values_args="--set adminPassword=$GRAFANA_PASSWORD"
    values_args="$values_args --set service.type=ClusterIP"
    values_args="$values_args --set persistence.enabled=true"
    values_args="$values_args --set persistence.size=10Gi"
    
    # Environment-specific configurations
    case "$ENVIRONMENT" in
        dev)
            values_args="$values_args --set resources.requests.memory=256Mi"
            values_args="$values_args --set resources.requests.cpu=100m"
            ;;
        staging|prod)
            values_args="$values_args --set resources.requests.memory=512Mi"
            values_args="$values_args --set resources.requests.cpu=250m"
            values_args="$values_args --set replicas=2"
            ;;
    esac
    
    local helm_cmd="helm upgrade --install grafana grafana/grafana"
    helm_cmd="$helm_cmd --namespace $NAMESPACE"
    helm_cmd="$helm_cmd $values_args"
    helm_cmd="$helm_cmd --wait --timeout=10m"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        helm_cmd="$helm_cmd --dry-run"
        log "DRY RUN: $helm_cmd"
        return
    fi
    
    log_debug "Executing: $helm_cmd"
    
    if eval "$helm_cmd"; then
        log "✅ Grafana installed successfully"
    else
        error_exit "❌ Failed to install Grafana"
    fi
}

# Wait for deployments
wait_for_deployments() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would wait for deployments"
        return
    fi
    
    log "Waiting for deployments to be ready..."
    
    local deployments=("prometheus-server" "grafana")
    
    if [[ "$ENABLE_ALERTMANAGER" == "true" ]]; then
        deployments+=("prometheus-alertmanager")
    fi
    
    for deployment in "${deployments[@]}"; do
        log "Waiting for $deployment..."
        if kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=300s; then
            log "✅ $deployment is ready"
        else
            log_warn "⚠️ $deployment rollout timed out"
        fi
    done
}

# Display access information
display_access_info() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "DRY RUN: Would display access information"
        return
    fi
    
    echo -e "\n${BLUE}📊 Monitoring Stack Access Information${NC}"
    echo -e "${BLUE}=======================================${NC}"
    
    # Prometheus
    echo -e "${GREEN}Prometheus:${NC}"
    echo "  - Service: prometheus-server.$NAMESPACE.svc.cluster.local"
    echo "  - Port Forward: kubectl port-forward -n $NAMESPACE svc/prometheus-server 9090:80"
    echo "  - Local URL: http://localhost:9090"
    
    # Grafana
    echo -e "\n${GREEN}Grafana:${NC}"
    echo "  - Service: grafana.$NAMESPACE.svc.cluster.local"
    echo "  - Port Forward: kubectl port-forward -n $NAMESPACE svc/grafana 3000:80"
    echo "  - Local URL: http://localhost:3000"
    echo "  - Username: admin"
    echo "  - Password: $GRAFANA_PASSWORD"
    
    # Alertmanager (if enabled)
    if [[ "$ENABLE_ALERTMANAGER" == "true" ]]; then
        echo -e "\n${GREEN}Alertmanager:${NC}"
        echo "  - Service: prometheus-alertmanager.$NAMESPACE.svc.cluster.local"
        echo "  - Port Forward: kubectl port-forward -n $NAMESPACE svc/prometheus-alertmanager 9093:80"
        echo "  - Local URL: http://localhost:9093"
    fi
    
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Access Grafana and import dashboards"
    echo "2. Configure alerting rules in Prometheus"
    echo "3. Set up notification channels in Grafana"
    echo "4. Monitor your OpenInfra services"
}

# Generate summary report
generate_summary() {
    local report_file="monitoring-deployment-$(date +%Y%m%d-%H%M%S).log"
    
    {
        echo "OpenInfra Monitoring Stack Deployment Report"
        echo "==============================================="
        echo "Timestamp: $(date)"
        echo "Environment: $ENVIRONMENT"
        echo "Namespace: $NAMESPACE"
        echo "Prometheus Retention: $PROMETHEUS_RETENTION"
        echo ""
        echo "Components Deployed:"
        echo "- Prometheus Server: ✅"
        echo "- Grafana: ✅"
        echo "- Alertmanager: $(if [[ "$ENABLE_ALERTMANAGER" == "true" ]]; then echo "✅"; else echo "❌ (disabled)"; fi)"
        echo "- Node Exporter: $(if [[ "$ENABLE_NODE_EXPORTER" == "true" ]]; then echo "✅"; else echo "❌ (disabled)"; fi)"
        echo "- Kube State Metrics: $(if [[ "$ENABLE_KUBE_STATE_METRICS" == "true" ]]; then echo "✅"; else echo "❌ (disabled)"; fi)"
        echo ""
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "Kubernetes Resources:"
            echo "====================="
            kubectl get pods,svc,pvc -n "$NAMESPACE" 2>/dev/null || echo "Failed to get resources"
        else
            echo "DRY RUN: No resources were actually created"
        fi
    } | tee "$report_file"
    
    log "Summary report saved to: $report_file"
}

# Main function
main() {
    echo -e "${BLUE}📊 OpenInfra - Enhanced Monitoring Stack Deployment v${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate environment
    validate_environment
    
    # Create namespace
    create_namespace
    
    # Generate configurations
    generate_prometheus_config
    generate_alerting_rules
    
    # Install components
    install_prometheus
    install_grafana
    
    # Wait for deployments
    wait_for_deployments
    
    # Display access information
    display_access_info
    
    # Generate summary
    generate_summary
    
    # Success message
    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "\n${GREEN}🎯 Dry run completed successfully!${NC}"
    else
        echo -e "\n${GREEN}🎉 Monitoring stack deployed successfully!${NC}"
    fi
}

# Execute main function
main "$@"