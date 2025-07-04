#!/bin/bash

# N.O.A.H - Performance Testing Suite
# 
# Comprehensive performance testing for the N.O.A.H infrastructure including
# load testing, resource monitoring, and performance analysis.

set -e

# Configuration
NAMESPACE="noah"
LOG_FILE="/tmp/noah_performance_tests_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="/tmp/noah_performance_reports_$(date +%Y%m%d_%H%M%S)"
TEST_DURATION="300"  # 5 minutes default
CONCURRENT_USERS="10"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Setup
setup() {
    info "Setting up performance testing environment..."
    
    mkdir -p "$REPORT_DIR"
    
    # Check for required tools
    local tools_available=()
    local tools_missing=()
    
    local required_tools=("kubectl" "curl" "ab" "wrk" "hey")
    
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            tools_available+=("$tool")
        else
            tools_missing+=("$tool")
        fi
    done
    
    info "Available tools: ${tools_available[*]}"
    if [ ${#tools_missing[@]} -gt 0 ]; then
        warn "Missing tools: ${tools_missing[*]}"
        warn "Some performance tests will be skipped"
    fi
    
    success "Performance testing environment ready"
}

# Resource monitoring
monitor_resources() {
    info "=== Resource Monitoring ==="
    
    # Monitor cluster resources
    info "Monitoring cluster resources..."
    
    # Node resource usage
    kubectl top nodes > "$REPORT_DIR/node_resources.txt" 2>/dev/null || warn "Metrics server not available for node metrics"
    
    # Pod resource usage
    kubectl top pods -n "$NAMESPACE" > "$REPORT_DIR/pod_resources.txt" 2>/dev/null || warn "Metrics server not available for pod metrics"
    
    # Get resource requests and limits
    kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].resources.requests.cpu}{"\t"}{.spec.containers[0].resources.requests.memory}{"\t"}{.spec.containers[0].resources.limits.cpu}{"\t"}{.spec.containers[0].resources.limits.memory}{"\n"}{end}' > "$REPORT_DIR/resource_allocation.txt"
    
    # Storage usage
    kubectl get pvc -n "$NAMESPACE" -o custom-columns=NAME:.metadata.name,CAPACITY:.status.capacity.storage,ACCESS:.spec.accessModes > "$REPORT_DIR/storage_usage.txt"
    
    success "Resource monitoring data collected"
}

# Network performance testing
test_network_performance() {
    info "=== Network Performance Testing ==="
    
    # Test internal network latency
    info "Testing internal network latency..."
    
    # Get a running pod for network tests
    local test_pod=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$test_pod" ]; then
        info "Using pod $test_pod for network tests"
        
        # Test DNS resolution performance
        kubectl exec -n "$NAMESPACE" "$test_pod" -- time nslookup kubernetes.default.svc.cluster.local > "$REPORT_DIR/dns_performance.txt" 2>&1 || warn "DNS test failed"
        
        # Test inter-pod connectivity
        local target_services=("samba4" "postgresql" "redis")
        for service in "${target_services[@]}"; do
            kubectl exec -n "$NAMESPACE" "$test_pod" -- ping -c 4 "$service.$NAMESPACE.svc.cluster.local" > "$REPORT_DIR/ping_$service.txt" 2>&1 || warn "Ping test to $service failed"
        done
        
    else
        warn "No running pods found for network testing"
    fi
    
    success "Network performance testing completed"
}

# Application load testing
test_application_load() {
    info "=== Application Load Testing ==="
    
    local services=("nextcloud" "mattermost" "gitlab" "keycloak")
    
    for service in "${services[@]}"; do
        info "Load testing $service..."
        
        local url="https://$service.local"
        
        # Test with Apache Bench (if available)
        if command -v ab &> /dev/null; then
            info "Running Apache Bench test for $service"
            ab -n 100 -c 10 -k -r "$url/" > "$REPORT_DIR/ab_$service.txt" 2>&1 || warn "Apache Bench test failed for $service"
        fi
        
        # Test with wrk (if available)
        if command -v wrk &> /dev/null; then
            info "Running wrk test for $service"
            wrk -t4 -c10 -d30s "$url/" > "$REPORT_DIR/wrk_$service.txt" 2>&1 || warn "wrk test failed for $service"
        fi
        
        # Test with hey (if available)
        if command -v hey &> /dev/null; then
            info "Running hey test for $service"
            hey -n 100 -c 10 "$url/" > "$REPORT_DIR/hey_$service.txt" 2>&1 || warn "hey test failed for $service"
        fi
        
        # Basic curl response time test
        info "Running basic response time test for $service"
        {
            echo "Response time analysis for $service:"
            for i in {1..10}; do
                curl -k -w "@-" -o /dev/null -s "$url/" <<< '%{time_total}\n' 2>/dev/null || echo "failed"
                sleep 1
            done
        } > "$REPORT_DIR/response_time_$service.txt"
        
    done
    
    success "Application load testing completed"
}

# Database performance testing
test_database_performance() {
    info "=== Database Performance Testing ==="
    
    # Test PostgreSQL performance
    info "Testing PostgreSQL performance..."
    
    local postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app=postgresql --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$postgres_pod" ]; then
        info "Testing PostgreSQL connection and basic operations"
        
        # Test connection time
        kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -c "SELECT NOW();" > "$REPORT_DIR/postgres_connection.txt" 2>&1 || warn "PostgreSQL connection test failed"
        
        # Test simple query performance
        kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -c "EXPLAIN ANALYZE SELECT 1;" > "$REPORT_DIR/postgres_query_performance.txt" 2>&1 || warn "PostgreSQL query test failed"
        
    else
        warn "PostgreSQL pod not found"
    fi
    
    # Test Redis performance
    info "Testing Redis performance..."
    
    local redis_pod=$(kubectl get pods -n "$NAMESPACE" -l app=redis --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$redis_pod" ]; then
        info "Testing Redis operations"
        
        # Test Redis ping
        kubectl exec -n "$NAMESPACE" "$redis_pod" -- redis-cli ping > "$REPORT_DIR/redis_ping.txt" 2>&1 || warn "Redis ping test failed"
        
        # Test Redis benchmark (if available)
        kubectl exec -n "$NAMESPACE" "$redis_pod" -- redis-cli --latency-history -h localhost -p 6379 > "$REPORT_DIR/redis_latency.txt" 2>&1 &
        local redis_pid=$!
        sleep 30
        kill $redis_pid 2>/dev/null || true
        
    else
        warn "Redis pod not found"
    fi
    
    success "Database performance testing completed"
}

# Storage performance testing
test_storage_performance() {
    info "=== Storage Performance Testing ==="
    
    # Create a test pod for storage performance testing
    local test_pod_yaml=$(cat <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: storage-perf-test
  namespace: $NAMESPACE
spec:
  containers:
  - name: test
    image: busybox
    command: ["sleep", "3600"]
    volumeMounts:
    - name: test-volume
      mountPath: /test
  volumes:
  - name: test-volume
    emptyDir: {}
  restartPolicy: Never
EOF
)
    
    echo "$test_pod_yaml" | kubectl apply -f - 2>/dev/null || warn "Could not create storage test pod"
    
    # Wait for pod to be ready
    kubectl wait --for=condition=Ready pod/storage-perf-test -n "$NAMESPACE" --timeout=60s 2>/dev/null || {
        warn "Storage test pod not ready, skipping storage tests"
        kubectl delete pod storage-perf-test -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null
        return
    }
    
    info "Running storage performance tests..."
    
    # Test write performance
    kubectl exec -n "$NAMESPACE" storage-perf-test -- dd if=/dev/zero of=/test/testfile bs=1M count=100 2>&1 | tee "$REPORT_DIR/storage_write_performance.txt" || warn "Storage write test failed"
    
    # Test read performance
    kubectl exec -n "$NAMESPACE" storage-perf-test -- dd if=/test/testfile of=/dev/null bs=1M 2>&1 | tee "$REPORT_DIR/storage_read_performance.txt" || warn "Storage read test failed"
    
    # Cleanup
    kubectl delete pod storage-perf-test -n "$NAMESPACE" --ignore-not-found=true 2>/dev/null
    
    success "Storage performance testing completed"
}

# Monitoring stack performance
test_monitoring_performance() {
    info "=== Monitoring Stack Performance Testing ==="
    
    # Test Prometheus query performance
    info "Testing Prometheus query performance..."
    
    local prometheus_queries=(
        "up"
        "rate(container_cpu_usage_seconds_total[5m])"
        "container_memory_usage_bytes"
        "kube_pod_status_phase"
    )
    
    for query in "${prometheus_queries[@]}"; do
        local start_time=$(date +%s.%N)
        curl -k -s -G "https://prometheus.local/api/v1/query" --data-urlencode "query=$query" > "/tmp/prom_query_result.json" 2>/dev/null
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "unknown")
        
        echo "Query: $query, Duration: ${duration}s" >> "$REPORT_DIR/prometheus_query_performance.txt"
    done
    
    # Test Grafana dashboard load time
    info "Testing Grafana dashboard performance..."
    
    local start_time=$(date +%s.%N)
    curl -k -s "https://grafana.local/api/health" > /dev/null 2>&1
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "unknown")
    
    echo "Grafana health endpoint response time: ${duration}s" > "$REPORT_DIR/grafana_performance.txt"
    
    success "Monitoring stack performance testing completed"
}

# Resource scaling tests
test_scaling_performance() {
    info "=== Scaling Performance Testing ==="
    
    # Test horizontal pod autoscaler performance (if configured)
    local hpas=$(kubectl get hpa -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [ -n "$hpas" ]; then
        info "Testing HPA scaling performance..."
        
        echo "$hpas" > "$REPORT_DIR/hpa_status.txt"
        
        # Monitor HPA metrics
        kubectl get hpa -n "$NAMESPACE" -o yaml > "$REPORT_DIR/hpa_detailed.yaml" 2>/dev/null
        
    else
        warn "No HPAs found for scaling tests"
    fi
    
    # Test manual scaling
    info "Testing manual scaling performance..."
    
    local deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -n "$deployments" ]; then
        local original_replicas=$(kubectl get deployment "$deployments" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null)
        
        info "Testing scaling of deployment: $deployments"
        
        # Scale up
        local start_time=$(date +%s)
        kubectl scale deployment "$deployments" --replicas=3 -n "$NAMESPACE" 2>/dev/null
        kubectl rollout status deployment/"$deployments" -n "$NAMESPACE" --timeout=300s 2>/dev/null
        local scale_up_time=$(($(date +%s) - start_time))
        
        # Scale back to original
        kubectl scale deployment "$deployments" --replicas="$original_replicas" -n "$NAMESPACE" 2>/dev/null
        kubectl rollout status deployment/"$deployments" -n "$NAMESPACE" --timeout=300s 2>/dev/null
        
        echo "Scale up time for $deployments: ${scale_up_time}s" > "$REPORT_DIR/scaling_performance.txt"
        
    else
        warn "No deployments found for scaling tests"
    fi
    
    success "Scaling performance testing completed"
}

# Generate performance report
generate_performance_report() {
    info "Generating performance report..."
    
    local report_file="$REPORT_DIR/performance_report.html"
    
    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Performance Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .good { background-color: #e6f3e6; }
        .warning { background-color: #fff3cd; }
        .poor { background-color: #ffe6e6; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 5px; font-size: 12px; overflow-x: auto; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .metric { display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 5px; min-width: 150px; }
    </style>
</head>
<body>
    <h1>N.O.A.H Performance Test Report</h1>
    <p><strong>Generated:</strong> $(date)</p>
    <p><strong>Test Duration:</strong> $TEST_DURATION seconds</p>
    <p><strong>Namespace:</strong> $NAMESPACE</p>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <p>This report provides a comprehensive performance analysis of the N.O.A.H deployment.</p>
        
        <div class="metric">
            <h4>Cluster Health</h4>
            <p>$(kubectl get nodes --no-headers | grep Ready | wc -l) / $(kubectl get nodes --no-headers | wc -l) nodes ready</p>
        </div>
        
        <div class="metric">
            <h4>Pod Status</h4>
            <p>$(kubectl get pods -n "$NAMESPACE" --no-headers | grep Running | wc -l) / $(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l) pods running</p>
        </div>
        
        <div class="metric">
            <h4>Storage</h4>
            <p>$(kubectl get pvc -n "$NAMESPACE" --no-headers | wc -l) persistent volume claims</p>
        </div>
    </div>
    
    <div class="section">
        <h2>Resource Utilization</h2>
        <h3>Node Resources</h3>
        <pre>$(cat "$REPORT_DIR/node_resources.txt" 2>/dev/null || echo "Data not available")</pre>
        
        <h3>Pod Resources</h3>
        <pre>$(cat "$REPORT_DIR/pod_resources.txt" 2>/dev/null || echo "Data not available")</pre>
        
        <h3>Resource Allocation</h3>
        <pre>$(cat "$REPORT_DIR/resource_allocation.txt" 2>/dev/null || echo "Data not available")</pre>
    </div>
    
    <div class="section">
        <h2>Application Performance</h2>
        <h3>Response Time Analysis</h3>
EOF
    
    # Add response time data for each service
    for service in nextcloud mattermost gitlab keycloak; do
        if [ -f "$REPORT_DIR/response_time_$service.txt" ]; then
            cat >> "$report_file" <<EOF
        <h4>$service</h4>
        <pre>$(cat "$REPORT_DIR/response_time_$service.txt")</pre>
EOF
        fi
    done
    
    cat >> "$report_file" <<EOF
    </div>
    
    <div class="section">
        <h2>Load Testing Results</h2>
EOF
    
    # Add load testing results
    for tool in ab wrk hey; do
        for service in nextcloud mattermost gitlab keycloak; do
            if [ -f "$REPORT_DIR/${tool}_$service.txt" ]; then
                cat >> "$report_file" <<EOF
        <h3>$tool - $service</h3>
        <pre>$(cat "$REPORT_DIR/${tool}_$service.txt")</pre>
EOF
            fi
        done
    done
    
    cat >> "$report_file" <<EOF
    </div>
    
    <div class="section">
        <h2>Database Performance</h2>
        <h3>PostgreSQL</h3>
        <pre>$(cat "$REPORT_DIR/postgres_connection.txt" 2>/dev/null || echo "Data not available")</pre>
        
        <h3>Redis</h3>
        <pre>$(cat "$REPORT_DIR/redis_ping.txt" 2>/dev/null || echo "Data not available")</pre>
    </div>
    
    <div class="section">
        <h2>Storage Performance</h2>
        <h3>Write Performance</h3>
        <pre>$(cat "$REPORT_DIR/storage_write_performance.txt" 2>/dev/null || echo "Data not available")</pre>
        
        <h3>Read Performance</h3>
        <pre>$(cat "$REPORT_DIR/storage_read_performance.txt" 2>/dev/null || echo "Data not available")</pre>
    </div>
    
    <div class="section">
        <h2>Monitoring Performance</h2>
        <h3>Prometheus Query Performance</h3>
        <pre>$(cat "$REPORT_DIR/prometheus_query_performance.txt" 2>/dev/null || echo "Data not available")</pre>
        
        <h3>Grafana Performance</h3>
        <pre>$(cat "$REPORT_DIR/grafana_performance.txt" 2>/dev/null || echo "Data not available")</pre>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <ol>
            <li><strong>Resource Optimization:</strong>
                <ul>
                    <li>Review resource requests and limits based on actual usage</li>
                    <li>Consider implementing Vertical Pod Autoscaling</li>
                    <li>Monitor and adjust storage allocation</li>
                </ul>
            </li>
            <li><strong>Performance Tuning:</strong>
                <ul>
                    <li>Optimize database configurations</li>
                    <li>Implement caching strategies</li>
                    <li>Consider CDN for static content</li>
                </ul>
            </li>
            <li><strong>Scaling Strategy:</strong>
                <ul>
                    <li>Configure Horizontal Pod Autoscaling</li>
                    <li>Implement cluster autoscaling</li>
                    <li>Plan for traffic spikes</li>
                </ul>
            </li>
        </ol>
    </div>
    
    <div class="section">
        <h2>Detailed Logs</h2>
        <pre>$(cat "$LOG_FILE" 2>/dev/null || echo "No logs available")</pre>
    </div>
</body>
</html>
EOF
    
    success "Performance report generated: $report_file"
}

# Main function
main() {
    info "Starting N.O.A.H Performance Testing Suite"
    info "Namespace: $NAMESPACE"
    info "Test duration: $TEST_DURATION seconds"
    info "Report directory: $REPORT_DIR"
    info "Log file: $LOG_FILE"
    
    setup
    
    # Run performance tests
    monitor_resources
    test_network_performance
    test_application_load
    test_database_performance
    test_storage_performance
    test_monitoring_performance
    test_scaling_performance
    
    # Generate comprehensive report
    generate_performance_report
    
    success "Performance testing completed"
    info "Reports available in: $REPORT_DIR"
    info "Main report: $REPORT_DIR/performance_report.html"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--duration)
            TEST_DURATION="$2"
            shift 2
            ;;
        -c|--concurrent)
            CONCURRENT_USERS="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -d, --duration SECONDS    Test duration (default: 300)"
            echo "  -c, --concurrent USERS    Concurrent users (default: 10)"
            echo "  -n, --namespace NAME      Kubernetes namespace (default: noah)"
            echo "  -h, --help                Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
