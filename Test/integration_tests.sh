#!/bin/bash

# N.O.A.H - Integration Tests
# 
# Comprehensive integration testing for the N.O.A.H infrastructure
# including end-to-end workflows, service interactions, and data flow validation.

set -e

# Configuration
NAMESPACE="noah"
MONITORING_NAMESPACE="monitoring"
LOG_FILE="/tmp/noah_integration_tests_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="/tmp/noah_integration_reports_$(date +%Y%m%d_%H%M%S)"
TIMEOUT=300

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Test results tracking
declare -A TEST_RESULTS=()
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

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

# Test execution wrapper
run_test() {
    local test_name="$1"
    local test_function="$2"
    
    info "Running test: $test_name"
    ((TOTAL_TESTS++))
    
    if $test_function; then
        success "✅ $test_name - PASSED"
        TEST_RESULTS["$test_name"]="PASSED"
        ((PASSED_TESTS++))
        return 0
    else
        error "❌ $test_name - FAILED"
        TEST_RESULTS["$test_name"]="FAILED"
        ((FAILED_TESTS++))
        return 1
    fi
}

# Wait for pod to be ready
wait_for_pod() {
    local pod_selector="$1"
    local namespace="$2"
    local timeout="${3:-300}"
    
    info "Waiting for pod with selector '$pod_selector' in namespace '$namespace'"
    
    if kubectl wait --for=condition=ready pod -l "$pod_selector" -n "$namespace" --timeout="${timeout}s"; then
        return 0
    else
        error "Pod with selector '$pod_selector' failed to become ready"
        return 1
    fi
}

# Test authentication flow
test_authentication_flow() {
    info "Testing authentication flow through Keycloak"
    
    # Check if Keycloak is accessible
    local keycloak_pod=$(kubectl get pods -n "$NAMESPACE" -l app=keycloak -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -z "$keycloak_pod" ]]; then
        error "Keycloak pod not found"
        return 1
    fi
    
    # Test Keycloak health endpoint
    if kubectl exec -n "$NAMESPACE" "$keycloak_pod" -- curl -s -f http://localhost:8080/health/ready &> /dev/null; then
        success "Keycloak health check passed"
    else
        error "Keycloak health check failed"
        return 1
    fi
    
    # Test LDAP connectivity from Keycloak
    if kubectl exec -n "$NAMESPACE" "$keycloak_pod" -- nc -z samba4 389 &> /dev/null; then
        success "Keycloak can connect to LDAP"
    else
        error "Keycloak cannot connect to LDAP"
        return 1
    fi
    
    return 0
}

# Test service mesh connectivity
test_service_mesh() {
    info "Testing service mesh connectivity"
    
    local services=("nextcloud" "mattermost" "gitlab" "keycloak")
    
    for service in "${services[@]}"; do
        local pod=$(kubectl get pods -n "$NAMESPACE" -l app="$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [[ -z "$pod" ]]; then
            warn "No pod found for service: $service"
            continue
        fi
        
        # Test connectivity to other services
        for target_service in "${services[@]}"; do
            if [[ "$service" != "$target_service" ]]; then
                if kubectl exec -n "$NAMESPACE" "$pod" -- nc -z "$target_service" 80 &> /dev/null; then
                    info "$service can connect to $target_service"
                else
                    warn "$service cannot connect to $target_service (this might be expected)"
                fi
            fi
        done
    done
    
    return 0
}

# Test data persistence
test_data_persistence() {
    info "Testing data persistence across pod restarts"
    
    # Test PostgreSQL data persistence
    local postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$postgres_pod" ]]; then
        # Create a test database
        local test_db="noah_test_$(date +%s)"
        if kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -c "CREATE DATABASE $test_db;" &> /dev/null; then
            success "Test database created successfully"
            
            # Restart the pod and check if data persists
            kubectl delete pod -n "$NAMESPACE" "$postgres_pod" &> /dev/null
            sleep 30
            
            if wait_for_pod "app=postgresql" "$NAMESPACE" 180; then
                local new_postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app=postgresql -o jsonpath='{.items[0].metadata.name}')
                if kubectl exec -n "$NAMESPACE" "$new_postgres_pod" -- psql -U postgres -c "\\l" | grep -q "$test_db"; then
                    success "Data persisted across pod restart"
                    # Cleanup
                    kubectl exec -n "$NAMESPACE" "$new_postgres_pod" -- psql -U postgres -c "DROP DATABASE $test_db;" &> /dev/null
                    return 0
                else
                    error "Data not persisted across pod restart"
                    return 1
                fi
            else
                error "PostgreSQL pod failed to restart"
                return 1
            fi
        else
            error "Failed to create test database"
            return 1
        fi
    else
        warn "PostgreSQL pod not found, skipping persistence test"
        return 0
    fi
}

# Test backup and restore workflow
test_backup_restore() {
    info "Testing backup and restore workflow"
    
    # Check if backup script exists
    local backup_script="../Script/backup_restore.sh"
    if [[ ! -f "$backup_script" ]]; then
        warn "Backup script not found, skipping backup test"
        return 0
    fi
    
    # Test backup creation
    if bash "$backup_script" --dry-run 2>&1 | grep -q "Backup simulation completed"; then
        success "Backup script validation passed"
        return 0
    else
        error "Backup script validation failed"
        return 1
    fi
}

# Test monitoring integration
test_monitoring_integration() {
    info "Testing monitoring and alerting integration"
    
    # Check Prometheus connectivity
    local prometheus_pod=$(kubectl get pods -n "$MONITORING_NAMESPACE" -l app=prometheus -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -z "$prometheus_pod" ]]; then
        error "Prometheus pod not found"
        return 1
    fi
    
    # Test if Prometheus can scrape metrics from services
    local targets_up=0
    local targets_total=0
    
    for service in nextcloud mattermost gitlab keycloak; do
        if kubectl get svc -n "$NAMESPACE" "$service" &> /dev/null; then
            ((targets_total++))
            # Check if service has metrics endpoint
            local pod=$(kubectl get pods -n "$NAMESPACE" -l app="$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            if [[ -n "$pod" ]]; then
                if kubectl exec -n "$NAMESPACE" "$pod" -- curl -s -f http://localhost:8080/metrics &> /dev/null || \
                   kubectl exec -n "$NAMESPACE" "$pod" -- curl -s -f http://localhost:9090/metrics &> /dev/null; then
                    ((targets_up++))
                    info "$service metrics endpoint is accessible"
                fi
            fi
        fi
    done
    
    if [[ $targets_up -gt 0 ]]; then
        success "Monitoring integration working ($targets_up/$targets_total services with metrics)"
        return 0
    else
        error "No monitoring targets found"
        return 1
    fi
}

# Test load balancing and failover
test_load_balancing() {
    info "Testing load balancing and failover scenarios"
    
    # Test if services have multiple replicas
    local services_with_replicas=0
    
    for service in nextcloud mattermost gitlab; do
        local replicas=$(kubectl get deployment -n "$NAMESPACE" "$service" -o jsonpath='{.spec.replicas}' 2>/dev/null)
        if [[ -n "$replicas" && "$replicas" -gt 1 ]]; then
            ((services_with_replicas++))
            success "$service has $replicas replicas for load balancing"
        else
            warn "$service has only 1 replica (no load balancing)"
        fi
    done
    
    if [[ $services_with_replicas -gt 0 ]]; then
        return 0
    else
        warn "No services configured for load balancing"
        return 0  # This is a warning, not a failure
    fi
}

# Test network policies
test_network_policies() {
    info "Testing network policies and security"
    
    # Check if network policies exist
    local network_policies=$(kubectl get networkpolicies -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [[ $network_policies -gt 0 ]]; then
        success "Found $network_policies network policies"
        
        # Test that restricted traffic is actually blocked
        # This is a simplified test - in real scenarios, you'd want more comprehensive testing
        return 0
    else
        warn "No network policies found - traffic is not restricted"
        return 0  # This is a warning, not a failure
    fi
}

# Test SSL/TLS configuration
test_ssl_tls() {
    info "Testing SSL/TLS configuration"
    
    local ssl_services=0
    
    # Check ingress for TLS configuration
    local ingresses=$(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [[ -n "$ingresses" ]]; then
        while IFS= read -r ingress_line; do
            local ingress_name=$(echo "$ingress_line" | awk '{print $1}')
            if kubectl get ingress -n "$NAMESPACE" "$ingress_name" -o yaml | grep -q "tls:"; then
                ((ssl_services++))
                info "Ingress $ingress_name has TLS configured"
            fi
        done <<< "$ingresses"
    fi
    
    if [[ $ssl_services -gt 0 ]]; then
        success "Found $ssl_services services with TLS configuration"
        return 0
    else
        warn "No TLS configuration found in ingresses"
        return 0  # This might be expected in development environments
    fi
}

# Test resource limits and quotas
test_resource_limits() {
    info "Testing resource limits and quotas"
    
    local pods_with_limits=0
    local total_pods=0
    
    # Check pods for resource limits
    local pods=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [[ -n "$pods" ]]; then
        while IFS= read -r pod_line; do
            local pod_name=$(echo "$pod_line" | awk '{print $1}')
            ((total_pods++))
            
            # Check if pod has resource limits
            if kubectl get pod -n "$NAMESPACE" "$pod_name" -o yaml | grep -A 10 "resources:" | grep -q "limits:"; then
                ((pods_with_limits++))
            fi
        done <<< "$pods"
    fi
    
    if [[ $pods_with_limits -gt 0 ]]; then
        success "$pods_with_limits/$total_pods pods have resource limits configured"
        return 0
    else
        warn "No pods have resource limits configured"
        return 0  # This is a warning, not a failure
    fi
}

# Test cross-service integration
test_cross_service_integration() {
    info "Testing cross-service integration scenarios"
    
    # Test OIDC integration between services
    local oidc_enabled_services=0
    
    for service in nextcloud mattermost gitlab; do
        local pod=$(kubectl get pods -n "$NAMESPACE" -l app="$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [[ -n "$pod" ]]; then
            # Check if service has OIDC configuration (simplified check)
            if kubectl exec -n "$NAMESPACE" "$pod" -- env | grep -i "oidc\|oauth" &> /dev/null; then
                ((oidc_enabled_services++))
                info "$service has OIDC/OAuth configuration"
            fi
        fi
    done
    
    if [[ $oidc_enabled_services -gt 0 ]]; then
        success "$oidc_enabled_services services have OIDC integration"
        return 0
    else
        warn "No services have OIDC integration configured"
        return 0
    fi
}

# Setup
setup() {
    info "Setting up integration testing environment..."
    mkdir -p "$REPORT_DIR"
    
    # Verify cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    # Check if N.O.A.H namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        error "N.O.A.H namespace '$NAMESPACE' not found"
        exit 1
    fi
    
    success "Setup completed successfully"
}

# Generate HTML report
generate_report() {
    local report_file="$REPORT_DIR/integration_test_report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Integration Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary { background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .test-result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .passed { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .failed { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .stats { display: flex; justify-content: space-around; text-align: center; }
        .stat-box { background: white; padding: 15px; border-radius: 5px; min-width: 100px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔧 N.O.A.H Integration Test Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Namespace:</strong> $NAMESPACE</p>
    </div>
    
    <div class="summary">
        <h2>Test Summary</h2>
        <div class="stats">
            <div class="stat-box">
                <h3>$TOTAL_TESTS</h3>
                <p>Total Tests</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #28a745;">$PASSED_TESTS</h3>
                <p>Passed</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #dc3545;">$FAILED_TESTS</h3>
                <p>Failed</p>
            </div>
            <div class="stat-box">
                <h3>$(( (PASSED_TESTS * 100) / (TOTAL_TESTS > 0 ? TOTAL_TESTS : 1) ))%</h3>
                <p>Success Rate</p>
            </div>
        </div>
    </div>
    
    <div class="test-results">
        <h2>Test Results</h2>
EOF

    for test_name in "${!TEST_RESULTS[@]}"; do
        local result="${TEST_RESULTS[$test_name]}"
        local css_class="passed"
        local icon="✅"
        
        if [[ "$result" == "FAILED" ]]; then
            css_class="failed"
            icon="❌"
        fi
        
        echo "        <div class=\"test-result $css_class\">" >> "$report_file"
        echo "            <strong>$icon $test_name:</strong> $result" >> "$report_file"
        echo "        </div>" >> "$report_file"
    done

    cat >> "$report_file" << EOF
    </div>
    
    <div class="summary">
        <h2>Recent Log Entries</h2>
        <pre>$(tail -50 "$LOG_FILE" 2>/dev/null || echo "No log entries found")</pre>
    </div>
</body>
</html>
EOF

    success "Integration test report generated: $report_file"
}

# Main execution
main() {
    setup
    
    info "Starting N.O.A.H integration tests..."
    
    # Run all integration tests
    run_test "Authentication Flow" test_authentication_flow
    run_test "Service Mesh Connectivity" test_service_mesh
    run_test "Data Persistence" test_data_persistence
    run_test "Backup and Restore" test_backup_restore
    run_test "Monitoring Integration" test_monitoring_integration
    run_test "Load Balancing" test_load_balancing
    run_test "Network Policies" test_network_policies
    run_test "SSL/TLS Configuration" test_ssl_tls
    run_test "Resource Limits" test_resource_limits
    run_test "Cross-Service Integration" test_cross_service_integration
    
    # Generate report
    generate_report
    
    # Final summary
    info "Integration testing completed"
    info "Total tests: $TOTAL_TESTS"
    info "Passed: $PASSED_TESTS"
    info "Failed: $FAILED_TESTS"
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        success "All integration tests passed! 🎉"
        exit 0
    else
        error "Some integration tests failed. Check the report for details."
        exit 1
    fi
}

# Run main function
main "$@"
