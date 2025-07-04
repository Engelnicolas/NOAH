#!/bin/bash

# N.O.A.H - Chaos Engineering Tests
# 
# Chaos engineering testing to validate system resilience and failure recovery
# capabilities of the N.O.A.H infrastructure.

set -e

# Configuration
NAMESPACE="noah"
LOG_FILE="/tmp/noah_chaos_tests_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="/tmp/noah_chaos_reports_$(date +%Y%m%d_%H%M%S)"
CHAOS_DURATION="300"  # 5 minutes default
RECOVERY_TIMEOUT="600"  # 10 minutes recovery timeout

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Test results tracking
declare -A CHAOS_RESULTS=()
TOTAL_CHAOS_TESTS=0
PASSED_CHAOS_TESTS=0
FAILED_CHAOS_TESTS=0

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

chaos_info() {
    log "CHAOS" "${PURPLE}$*${NC}"
}

# Test execution wrapper for chaos tests
run_chaos_test() {
    local test_name="$1"
    local test_function="$2"
    
    chaos_info "Starting chaos test: $test_name"
    ((TOTAL_CHAOS_TESTS++))
    
    if $test_function; then
        success "✅ $test_name - RECOVERED"
        CHAOS_RESULTS["$test_name"]="RECOVERED"
        ((PASSED_CHAOS_TESTS++))
        return 0
    else
        error "❌ $test_name - FAILED TO RECOVER"
        CHAOS_RESULTS["$test_name"]="FAILED"
        ((FAILED_CHAOS_TESTS++))
        return 1
    fi
}

# Wait for system to stabilize
wait_for_system_stability() {
    local timeout="${1:-300}"
    local namespace="$2"
    
    info "Waiting for system to stabilize (timeout: ${timeout}s)..."
    
    local end_time=$(($(date +%s) + timeout))
    
    while [[ $(date +%s) -lt $end_time ]]; do
        local pods_not_ready=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | grep -v "Running\|Completed" | wc -l)
        
        if [[ $pods_not_ready -eq 0 ]]; then
            success "System stabilized - all pods are running"
            return 0
        fi
        
        info "Waiting for $pods_not_ready pods to stabilize..."
        sleep 10
    done
    
    error "System failed to stabilize within timeout"
    return 1
}

# Get baseline metrics
get_baseline_metrics() {
    info "Collecting baseline metrics..."
    
    local baseline_file="$REPORT_DIR/baseline_metrics.json"
    mkdir -p "$REPORT_DIR"
    
    # Collect pod status
    kubectl get pods -n "$NAMESPACE" -o json > "$baseline_file.pods"
    
    # Collect service status
    kubectl get services -n "$NAMESPACE" -o json > "$baseline_file.services"
    
    # Collect resource usage if metrics server is available
    if kubectl top nodes &> /dev/null; then
        kubectl top nodes > "$baseline_file.nodes_usage" 2>/dev/null || true
        kubectl top pods -n "$NAMESPACE" > "$baseline_file.pods_usage" 2>/dev/null || true
    fi
    
    success "Baseline metrics collected"
}

# Verify system recovery
verify_system_recovery() {
    local component="$1"
    local timeout="${2:-600}"
    
    info "Verifying recovery of $component (timeout: ${timeout}s)..."
    
    # Wait for pods to be ready
    if ! wait_for_system_stability "$timeout" "$NAMESPACE"; then
        error "$component failed to recover - pods not stabilized"
        return 1
    fi
    
    # Additional component-specific checks
    case "$component" in
        "database")
            # Test database connectivity
            local postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            if [[ -n "$postgres_pod" ]]; then
                if kubectl exec -n "$NAMESPACE" "$postgres_pod" -- pg_isready -U postgres &> /dev/null; then
                    success "Database connectivity verified"
                else
                    error "Database connectivity failed"
                    return 1
                fi
            fi
            ;;
        "web-services")
            # Test web service accessibility
            for service in nextcloud mattermost gitlab; do
                local pod=$(kubectl get pods -n "$NAMESPACE" -l app="$service" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
                if [[ -n "$pod" ]]; then
                    if kubectl exec -n "$NAMESPACE" "$pod" -- curl -s -f http://localhost/ &> /dev/null || \
                       kubectl exec -n "$NAMESPACE" "$pod" -- curl -s -f http://localhost:8080/health &> /dev/null; then
                        info "$service is accessible"
                    else
                        warn "$service may not be fully accessible yet"
                    fi
                fi
            done
            ;;
    esac
    
    success "$component recovery verified"
    return 0
}

# Chaos Test: Pod Deletion
chaos_test_pod_deletion() {
    chaos_info "Chaos Test: Random Pod Deletion"
    
    # Get a random non-critical pod
    local target_pod=$(kubectl get pods -n "$NAMESPACE" --no-headers | grep -v "postgresql\|samba4" | shuf -n 1 | awk '{print $1}')
    
    if [[ -z "$target_pod" ]]; then
        warn "No suitable pods found for deletion test"
        return 0
    fi
    
    chaos_info "Deleting pod: $target_pod"
    kubectl delete pod -n "$NAMESPACE" "$target_pod" &> /dev/null
    
    sleep 30  # Wait for chaos to propagate
    
    # Verify recovery
    if verify_system_recovery "pod-deletion" 300; then
        return 0
    else
        return 1
    fi
}

# Chaos Test: Resource Exhaustion
chaos_test_resource_exhaustion() {
    chaos_info "Chaos Test: Resource Exhaustion"
    
    # Create a resource-intensive pod
    cat << EOF | kubectl apply -f - &> /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: chaos-resource-exhaustion
  namespace: $NAMESPACE
  labels:
    chaos-test: "resource-exhaustion"
spec:
  containers:
  - name: cpu-hog
    image: busybox
    command: ["sh", "-c", "while true; do dd if=/dev/zero of=/dev/null; done"]
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1000m"
        memory: "512Mi"
  restartPolicy: Never
EOF
    
    chaos_info "Resource exhaustion pod created, monitoring for $CHAOS_DURATION seconds..."
    sleep "$CHAOS_DURATION"
    
    # Cleanup chaos pod
    kubectl delete pod -n "$NAMESPACE" chaos-resource-exhaustion &> /dev/null || true
    
    # Verify system recovery
    if verify_system_recovery "resource-exhaustion" 300; then
        return 0
    else
        return 1
    fi
}

# Chaos Test: Network Partition
chaos_test_network_partition() {
    chaos_info "Chaos Test: Network Partition Simulation"
    
    # Create a network policy that blocks traffic
    cat << EOF | kubectl apply -f - &> /dev/null
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: chaos-network-partition
  namespace: $NAMESPACE
spec:
  podSelector:
    matchLabels:
      app: nextcloud
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF
    
    chaos_info "Network partition applied for 60 seconds..."
    sleep 60
    
    # Remove the network policy
    kubectl delete networkpolicy -n "$NAMESPACE" chaos-network-partition &> /dev/null || true
    
    # Verify recovery
    if verify_system_recovery "network-partition" 300; then
        return 0
    else
        return 1
    fi
}

# Chaos Test: Storage Failure Simulation
chaos_test_storage_failure() {
    chaos_info "Chaos Test: Storage Failure Simulation"
    
    # Find a PVC to target
    local target_pvc=$(kubectl get pvc -n "$NAMESPACE" --no-headers | head -1 | awk '{print $1}')
    
    if [[ -z "$target_pvc" ]]; then
        warn "No PVCs found for storage failure test"
        return 0
    fi
    
    # Create a pod that will fill up the storage
    cat << EOF | kubectl apply -f - &> /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: chaos-storage-filler
  namespace: $NAMESPACE
spec:
  containers:
  - name: storage-filler
    image: busybox
    command: ["sh", "-c", "dd if=/dev/zero of=/tmp/bigfile bs=1M count=100 2>/dev/null || true; sleep 300"]
    volumeMounts:
    - name: target-storage
      mountPath: /tmp
  volumes:
  - name: target-storage
    persistentVolumeClaim:
      claimName: $target_pvc
  restartPolicy: Never
EOF
    
    chaos_info "Storage stress test running for 120 seconds..."
    sleep 120
    
    # Cleanup
    kubectl delete pod -n "$NAMESPACE" chaos-storage-filler &> /dev/null || true
    
    # Verify recovery
    if verify_system_recovery "storage-failure" 300; then
        return 0
    else
        return 1
    fi
}

# Chaos Test: Database Connection Exhaustion
chaos_test_database_exhaustion() {
    chaos_info "Chaos Test: Database Connection Exhaustion"
    
    local postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$postgres_pod" ]]; then
        warn "PostgreSQL pod not found, skipping database exhaustion test"
        return 0
    fi
    
    # Create multiple connections to exhaust the connection pool
    for i in {1..20}; do
        kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -c "SELECT pg_sleep(30);" &> /dev/null &
    done
    
    chaos_info "Database connection exhaustion test running for 60 seconds..."
    sleep 60
    
    # Kill background processes
    pkill -f "kubectl exec.*psql" 2>/dev/null || true
    
    # Verify recovery
    if verify_system_recovery "database" 300; then
        return 0
    else
        return 1
    fi
}

# Chaos Test: Cascading Failure
chaos_test_cascading_failure() {
    chaos_info "Chaos Test: Cascading Failure Simulation"
    
    # Delete multiple pods simultaneously
    local pods_to_delete=($(kubectl get pods -n "$NAMESPACE" --no-headers | grep -v "postgresql\|samba4" | head -3 | awk '{print $1}'))
    
    for pod in "${pods_to_delete[@]}"; do
        if [[ -n "$pod" ]]; then
            chaos_info "Deleting pod: $pod"
            kubectl delete pod -n "$NAMESPACE" "$pod" &> /dev/null &
        fi
    done
    
    # Wait for deletions to complete
    wait
    
    chaos_info "Cascading failure initiated, waiting for recovery..."
    sleep 60
    
    # Verify recovery
    if verify_system_recovery "cascading-failure" 600; then
        return 0
    else
        return 1
    fi
}

# Chaos Test: Memory Pressure
chaos_test_memory_pressure() {
    chaos_info "Chaos Test: Memory Pressure"
    
    # Create a memory-intensive pod
    cat << EOF | kubectl apply -f - &> /dev/null
apiVersion: v1
kind: Pod
metadata:
  name: chaos-memory-pressure
  namespace: $NAMESPACE
spec:
  containers:
  - name: memory-hog
    image: busybox
    command: ["sh", "-c", "mkdir /tmp/memory; mount -t tmpfs -o size=400M tmpfs /tmp/memory; dd if=/dev/zero of=/tmp/memory/bigfile bs=1M count=300 2>/dev/null; sleep 300"]
    resources:
      requests:
        memory: "256Mi"
      limits:
        memory: "512Mi"
  restartPolicy: Never
EOF
    
    chaos_info "Memory pressure test running for 180 seconds..."
    sleep 180
    
    # Cleanup
    kubectl delete pod -n "$NAMESPACE" chaos-memory-pressure &> /dev/null || true
    
    # Verify recovery
    if verify_system_recovery "memory-pressure" 300; then
        return 0
    else
        return 1
    fi
}

# Setup
setup() {
    info "Setting up chaos engineering test environment..."
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
    
    # Get baseline metrics
    get_baseline_metrics
    
    # Ensure system is stable before starting chaos tests
    if ! wait_for_system_stability 300 "$NAMESPACE"; then
        error "System is not stable before starting chaos tests"
        exit 1
    fi
    
    success "Chaos engineering setup completed"
}

# Generate HTML report
generate_chaos_report() {
    local report_file="$REPORT_DIR/chaos_test_report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Chaos Engineering Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .warning-box { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .summary { background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .test-result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .recovered { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .failed { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .stats { display: flex; justify-content: space-around; text-align: center; }
        .stat-box { background: white; padding: 15px; border-radius: 5px; min-width: 100px; }
        .chaos-icon { font-size: 2em; }
    </style>
</head>
<body>
    <div class="header">
        <h1><span class="chaos-icon">🔥</span> N.O.A.H Chaos Engineering Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Namespace:</strong> $NAMESPACE</p>
        <p><strong>Test Duration:</strong> $CHAOS_DURATION seconds per test</p>
    </div>
    
    <div class="warning-box">
        <h3>⚠️ Chaos Engineering Notice</h3>
        <p>This report contains results from intentional system failures and stress tests designed to validate system resilience and recovery capabilities.</p>
    </div>
    
    <div class="summary">
        <h2>Chaos Test Summary</h2>
        <div class="stats">
            <div class="stat-box">
                <h3>$TOTAL_CHAOS_TESTS</h3>
                <p>Chaos Tests</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #28a745;">$PASSED_CHAOS_TESTS</h3>
                <p>Recovered</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #dc3545;">$FAILED_CHAOS_TESTS</h3>
                <p>Failed to Recover</p>
            </div>
            <div class="stat-box">
                <h3>$(( (PASSED_CHAOS_TESTS * 100) / (TOTAL_CHAOS_TESTS > 0 ? TOTAL_CHAOS_TESTS : 1) ))%</h3>
                <p>Recovery Rate</p>
            </div>
        </div>
    </div>
    
    <div class="test-results">
        <h2>Chaos Test Results</h2>
EOF

    for test_name in "${!CHAOS_RESULTS[@]}"; do
        local result="${CHAOS_RESULTS[$test_name]}"
        local css_class="recovered"
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
        <h2>Recommendations</h2>
        <ul>
            <li>Review failed recovery scenarios and implement improvements</li>
            <li>Consider implementing circuit breakers for better failure isolation</li>
            <li>Evaluate resource limits and scaling policies based on stress test results</li>
            <li>Schedule regular chaos engineering exercises</li>
        </ul>
    </div>
    
    <div class="summary">
        <h2>Recent Log Entries</h2>
        <pre>$(tail -50 "$LOG_FILE" 2>/dev/null || echo "No log entries found")</pre>
    </div>
</body>
</html>
EOF

    success "Chaos engineering report generated: $report_file"
}

# Cleanup function
cleanup() {
    info "Cleaning up chaos test resources..."
    
    # Remove any chaos test pods
    kubectl delete pods -n "$NAMESPACE" -l chaos-test --ignore-not-found=true &> /dev/null || true
    
    # Remove any chaos network policies
    kubectl delete networkpolicy -n "$NAMESPACE" chaos-network-partition --ignore-not-found=true &> /dev/null || true
    
    # Kill any background processes
    pkill -f "kubectl exec.*psql" 2>/dev/null || true
    
    success "Cleanup completed"
}

# Main execution
main() {
    setup
    
    warn "⚠️  CAUTION: Starting chaos engineering tests - this will intentionally disrupt services!"
    info "Starting N.O.A.H chaos engineering tests..."
    
    # Run chaos tests
    run_chaos_test "Pod Deletion" chaos_test_pod_deletion
    run_chaos_test "Resource Exhaustion" chaos_test_resource_exhaustion
    run_chaos_test "Network Partition" chaos_test_network_partition
    run_chaos_test "Storage Failure" chaos_test_storage_failure
    run_chaos_test "Database Exhaustion" chaos_test_database_exhaustion
    run_chaos_test "Memory Pressure" chaos_test_memory_pressure
    run_chaos_test "Cascading Failure" chaos_test_cascading_failure
    
    # Generate report
    generate_chaos_report
    
    # Cleanup
    cleanup
    
    # Final summary
    info "Chaos engineering testing completed"
    info "Total chaos tests: $TOTAL_CHAOS_TESTS"
    info "Recovered: $PASSED_CHAOS_TESTS"
    info "Failed to recover: $FAILED_CHAOS_TESTS"
    
    if [[ $FAILED_CHAOS_TESTS -eq 0 ]]; then
        success "All systems recovered from chaos tests! 🎉"
        exit 0
    else
        warn "Some systems failed to recover from chaos. Review the report for details."
        exit 1
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"
