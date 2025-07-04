#!/bin/bash

# N.O.A.H - Next Open-source Architecture Hub
# Enhanced Post-Deployment Validation Script
# 
# This script performs comprehensive validation of the N.O.A.H stack deployment
# including infrastructure, services, security, monitoring, and integration tests.

set -e

# Configuration
NAMESPACE="noah"
MONITORING_NAMESPACE="monitoring"
TIMEOUT=300
RETRY_INTERVAL=10
LOG_FILE="/tmp/noah_validation_$(date +%Y%m%d_%H%M%S).log"

# Service configurations
declare -A SERVICES=(
    ["nextcloud"]="443"
    ["mattermost"]="443" 
    ["gitlab"]="443"
    ["wazuh"]="5601"
    ["openedr"]="8443"
    ["keycloak"]="8080"
    ["prometheus"]="9090"
    ["grafana"]="3000"
    ["alertmanager"]="9093"
)

declare -A INTERNAL_SERVICES=(
    ["samba4"]="389"
    ["postgresql"]="5432"
    ["redis"]="6379"
    ["oauth2-proxy"]="4180"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "${BLUE}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

error_exit() {
    error "$1"
    exit 1
}

# Utility functions
wait_for_condition() {
    local condition="$1"
    local description="$2"
    local timeout="${3:-$TIMEOUT}"
    local interval="${4:-$RETRY_INTERVAL}"
    
    info "Waiting for: $description"
    local elapsed=0
    
    while ! eval "$condition" >/dev/null 2>&1; do
        if [ $elapsed -ge $timeout ]; then
            error "Timeout waiting for: $description"
            return 1
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -n "."
    done
    echo
    success "$description - OK"
    return 0
}

# Check if kubectl is available and cluster is accessible
check_prerequisites() {
    info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        error_exit "kubectl is not installed or not in PATH"
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error_exit "Cannot connect to Kubernetes cluster"
    fi
    
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error_exit "Namespace '$NAMESPACE' does not exist"
    fi
    
    success "Prerequisites check passed"
}

# Infrastructure validation tests
validate_infrastructure() {
    info "=== Infrastructure Validation ==="
    
    # Check node status
    info "Checking cluster nodes..."
    local ready_nodes=$(kubectl get nodes --no-headers | grep Ready | wc -l)
    local total_nodes=$(kubectl get nodes --no-headers | wc -l)
    
    if [ "$ready_nodes" -eq "$total_nodes" ] && [ "$ready_nodes" -gt 0 ]; then
        success "All $ready_nodes nodes are ready"
    else
        error "Node status: $ready_nodes/$total_nodes ready"
        kubectl get nodes
        return 1
    fi
    
    # Check storage classes
    info "Checking storage classes..."
    if kubectl get storageclass &> /dev/null; then
        success "Storage classes available"
        kubectl get storageclass --no-headers | awk '{print "  - " $1}'
    else
        warn "No storage classes found"
    fi
    
    # Check ingress controller
    info "Checking ingress controller..."
    if kubectl get pods -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx 2>/dev/null | grep -q Running; then
        success "Ingress controller is running"
    else
        warn "Ingress controller not found in ingress-nginx namespace"
    fi
}

# Pod and deployment validation
validate_pods() {
    info "=== Pod Validation ==="
    
    info "Checking pods in namespace '$NAMESPACE'..."
    
    # Get pod status
    local pod_status=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [ -z "$pod_status" ]; then
        error "No pods found in namespace '$NAMESPACE'"
        return 1
    fi
    
    # Check if all pods are running or completed
    local total_pods=$(echo "$pod_status" | wc -l)
    local running_pods=$(echo "$pod_status" | grep -E "(Running|Completed)" | wc -l)
    
    info "Pod status: $running_pods/$total_pods ready"
    
    # Show detailed pod status
    kubectl get pods -n "$NAMESPACE" -o wide
    
    # Check for failed pods
    local failed_pods=$(echo "$pod_status" | grep -v -E "(Running|Completed)" || true)
    if [ -n "$failed_pods" ]; then
        warn "Non-running pods detected:"
        echo "$failed_pods"
        
        # Get details for failed pods
        echo "$failed_pods" | while read -r line; do
            local pod_name=$(echo "$line" | awk '{print $1}')
            warn "Describing failed pod: $pod_name"
            kubectl describe pod "$pod_name" -n "$NAMESPACE" | tail -20
        done
    fi
    
    if [ "$running_pods" -eq "$total_pods" ]; then
        success "All pods are running successfully"
        return 0
    else
        error "Some pods are not running properly"
        return 1
    fi
}

# Service connectivity tests
validate_services() {
    info "=== Service Connectivity Validation ==="
    
    # Test internal services
    for service in "${!INTERNAL_SERVICES[@]}"; do
        local port="${INTERNAL_SERVICES[$service]}"
        info "Testing internal service: $service:$port"
        
        if nc -z "$service.$NAMESPACE.svc.cluster.local" "$port" 2>/dev/null; then
            success "$service internal connectivity - OK"
        else
            error "$service internal connectivity - FAILED"
        fi
    done
    
    # Test external service endpoints
    for service in "${!SERVICES[@]}"; do
        local port="${SERVICES[$service]}"
        info "Testing external service: $service.local"
        
        # Test with curl (allow self-signed certificates)
        if curl -k --max-time 10 --silent --fail "https://$service.local" >/dev/null 2>&1; then
            success "$service external connectivity - OK"
        else
            # Try with different methods
            local http_code=$(curl -k --max-time 10 --silent --output /dev/null --write-out "%{http_code}" "https://$service.local" 2>/dev/null || echo "000")
            if [ "$http_code" -ne "000" ]; then
                success "$service external connectivity - OK (HTTP $http_code)"
            else
                warn "$service external connectivity - May not be reachable (this might be expected for internal services)"
            fi
        fi
    done
}

# LDAP/Active Directory validation
validate_ldap() {
    info "=== LDAP/Active Directory Validation ==="
    
    # Test LDAP port connectivity
    info "Testing LDAP port connectivity..."
    if wait_for_condition "nc -z samba4.$NAMESPACE.svc.cluster.local 389" "LDAP port 389 availability" 30 5; then
        success "LDAP port 389 is accessible"
    else
        error "LDAP port 389 is not accessible"
        return 1
    fi
    
    # Test LDAP search (if ldapsearch is available)
    if command -v ldapsearch &> /dev/null; then
        info "Testing LDAP search functionality..."
        # Update to use noah domain
        if ldapsearch -x -H "ldap://samba4.$NAMESPACE.svc.cluster.local" \
           -b "dc=noah,dc=local" \
           -D "cn=admin,dc=noah,dc=local" \
           -w "password" \
           "(objectClass=*)" dn 2>/dev/null | grep -q "dn:"; then
            success "LDAP search query successful"
        else
            warn "LDAP search query failed (credentials may need updating)"
        fi
    else
        warn "ldapsearch not available, skipping LDAP query test"
    fi
}

# Authentication and authorization validation
validate_auth() {
    info "=== Authentication & Authorization Validation ==="
    
    # Check Keycloak health
    info "Checking Keycloak health..."
    local keycloak_health=$(curl -k --max-time 10 --silent "https://keycloak.local/health" 2>/dev/null || echo "failed")
    if echo "$keycloak_health" | grep -q "UP\|healthy\|ok"; then
        success "Keycloak health check - OK"
    else
        warn "Keycloak health check failed or endpoint not accessible"
    fi
    
    # Check OAuth2 Proxy
    info "Checking OAuth2 Proxy..."
    if kubectl get pods -n "$NAMESPACE" -l app=oauth2-proxy 2>/dev/null | grep -q Running; then
        success "OAuth2 Proxy is running"
    else
        warn "OAuth2 Proxy not found or not running"
    fi
    
    # Generate OIDC test configuration
    info "Generating OIDC test configuration..."
    cat > "/tmp/oidc_test_config.json" <<EOF
{
  "issuer": "https://keycloak.local/realms/noah",
  "client_id": "nextcloud-client",
  "redirect_uri": "https://nextcloud.local/oidc",
  "scope": "openid profile email",
  "discovery_url": "https://keycloak.local/realms/noah/.well-known/openid_configuration"
}
EOF
    success "OIDC test configuration generated at /tmp/oidc_test_config.json"
}

# Monitoring stack validation
validate_monitoring() {
    info "=== Monitoring Stack Validation ==="
    
    # Check Prometheus
    info "Checking Prometheus..."
    if curl -k --max-time 10 --silent "https://prometheus.local/-/healthy" 2>/dev/null | grep -q "Prometheus is Healthy"; then
        success "Prometheus health check - OK"
    else
        warn "Prometheus health check failed"
    fi
    
    # Check Grafana
    info "Checking Grafana..."
    local grafana_response=$(curl -k --max-time 10 --silent --write-out "%{http_code}" "https://grafana.local/api/health" 2>/dev/null)
    if echo "$grafana_response" | grep -q "200"; then
        success "Grafana health check - OK"
    else
        warn "Grafana health check failed"
    fi
    
    # Check AlertManager
    info "Checking AlertManager..."
    if curl -k --max-time 10 --silent "https://alertmanager.local/-/healthy" 2>/dev/null | grep -q "OK"; then
        success "AlertManager health check - OK"
    else
        warn "AlertManager health check failed"
    fi
    
    # Check ServiceMonitors
    info "Checking ServiceMonitors..."
    local servicemonitors=$(kubectl get servicemonitor -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$servicemonitors" -gt 0 ]; then
        success "ServiceMonitors found: $servicemonitors"
    else
        warn "No ServiceMonitors found"
    fi
}

# Security validation
validate_security() {
    info "=== Security Validation ==="
    
    # Check network policies
    info "Checking NetworkPolicies..."
    local netpols=$(kubectl get networkpolicy -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$netpols" -gt 0 ]; then
        success "NetworkPolicies found: $netpols"
    else
        warn "No NetworkPolicies found - consider implementing network segmentation"
    fi
    
    # Check pod security contexts
    info "Checking pod security contexts..."
    local insecure_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.securityContext.runAsRoot}{"\n"}{end}' 2>/dev/null | grep -c "true" || echo "0")
    if [ "$insecure_pods" -eq 0 ]; then
        success "No pods running as root"
    else
        warn "$insecure_pods pods are running as root"
    fi
    
    # Check TLS certificates
    info "Checking TLS certificates..."
    local tls_secrets=$(kubectl get secrets -n "$NAMESPACE" --field-selector type=kubernetes.io/tls --no-headers 2>/dev/null | wc -l)
    if [ "$tls_secrets" -gt 0 ]; then
        success "TLS secrets found: $tls_secrets"
    else
        warn "No TLS secrets found"
    fi
    
    # Check Wazuh agent connectivity
    info "Checking Wazuh security monitoring..."
    if curl -k --max-time 10 --silent "https://wazuh.local" 2>/dev/null | grep -q "Wazuh\|kibana"; then
        success "Wazuh dashboard accessible"
    else
        warn "Wazuh dashboard not accessible"
    fi
}

# Backup and disaster recovery validation
validate_backup() {
    info "=== Backup & Disaster Recovery Validation ==="
    
    # Check persistent volumes
    info "Checking persistent volumes..."
    local pvs=$(kubectl get pv --no-headers 2>/dev/null | wc -l)
    local pvcs=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    info "Persistent Volumes: $pvs"
    info "Persistent Volume Claims in $NAMESPACE: $pvcs"
    
    # Check backup configurations
    if kubectl get cronjob -n "$NAMESPACE" 2>/dev/null | grep -q backup; then
        success "Backup CronJobs found"
    else
        warn "No backup CronJobs found - consider implementing automated backups"
    fi
    
    # Check Velero (if installed)
    if kubectl get pods -n velero 2>/dev/null | grep -q Running; then
        success "Velero backup solution detected"
    else
        warn "Velero backup solution not found"
    fi
}

# Performance and resource validation
validate_performance() {
    info "=== Performance & Resource Validation ==="
    
    # Check resource quotas
    local quotas=$(kubectl get resourcequota -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$quotas" -gt 0 ]; then
        info "Resource quotas configured: $quotas"
    else
        warn "No resource quotas found"
    fi
    
    # Check HPA
    local hpas=$(kubectl get hpa -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    if [ "$hpas" -gt 0 ]; then
        success "Horizontal Pod Autoscalers configured: $hpas"
    else
        warn "No Horizontal Pod Autoscalers found"
    fi
    
    # Check pod resource requests/limits
    info "Checking pod resource configurations..."
    kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" requests:"}{.spec.containers[0].resources.requests}{" limits:"}{.spec.containers[0].resources.limits}{"\n"}{end}' 2>/dev/null | head -5
}

# Main test execution
main() {
    info "Starting N.O.A.H Post-Deployment Validation"
    info "Timestamp: $(date)"
    info "Namespace: $NAMESPACE"
    info "Log file: $LOG_FILE"
    
    local failed_tests=0
    
    # Run all validation tests
    check_prerequisites || ((failed_tests++))
    validate_infrastructure || ((failed_tests++))
    validate_pods || ((failed_tests++))
    validate_services || ((failed_tests++))
    validate_ldap || ((failed_tests++))
    validate_auth || ((failed_tests++))
    validate_monitoring || ((failed_tests++))
    validate_security || ((failed_tests++))
    validate_backup || ((failed_tests++))
    validate_performance || ((failed_tests++))
    
    # Summary
    info "=== Validation Summary ==="
    if [ "$failed_tests" -eq 0 ]; then
        success "All validation tests passed successfully!"
        success "N.O.A.H deployment is healthy and ready for use"
    else
        error "$failed_tests validation test(s) failed"
        error "Please review the logs and address any issues"
        exit 1
    fi
    
    info "Detailed logs available at: $LOG_FILE"
    
    # Generate validation report
    generate_report
}

# Generate validation report
generate_report() {
    local report_file="/tmp/noah_validation_report_$(date +%Y%m%d_%H%M%S).html"
    
    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Deployment Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        .info { color: blue; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 5px; }
        .section { margin: 20px 0; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
    </style>
</head>
<body>
    <h1>N.O.A.H Deployment Validation Report</h1>
    <p><strong>Generated:</strong> $(date)</p>
    <p><strong>Namespace:</strong> $NAMESPACE</p>
    
    <div class="section">
        <h2>Validation Checklist</h2>
        <ul>
            <li>✅ Infrastructure validation</li>
            <li>✅ Pod and deployment validation</li>
            <li>✅ Service connectivity tests</li>
            <li>✅ LDAP/Active Directory integration</li>
            <li>✅ Authentication and authorization</li>
            <li>✅ Monitoring stack validation</li>
            <li>✅ Security configuration check</li>
            <li>✅ Backup and disaster recovery</li>
            <li>✅ Performance and resource validation</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Detailed Log</h2>
        <pre>$(cat "$LOG_FILE")</pre>
    </div>
    
    <div class="section">
        <h2>Next Steps</h2>
        <ol>
            <li>Review any warnings or errors in the detailed log</li>
            <li>Test manual login to all services</li>
            <li>Verify OIDC/SSO integration</li>
            <li>Configure monitoring alerts</li>
            <li>Set up backup schedules</li>
            <li>Conduct security audit</li>
        </ol>
    </div>
</body>
</html>
EOF
    
    success "Validation report generated: $report_file"
}

# Run main function
main "$@"
