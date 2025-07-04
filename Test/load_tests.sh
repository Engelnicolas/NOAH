#!/bin/bash

# N.O.A.H - Load Testing Suite
# 
# Comprehensive load testing for the N.O.A.H infrastructure
# including realistic user scenarios, stress testing, and capacity planning.

set -e

# Configuration
NAMESPACE="noah"
LOG_FILE="/tmp/noah_load_tests_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="/tmp/noah_load_reports_$(date +%Y%m%d_%H%M%S)"

# Load test parameters
DEFAULT_USERS="10"
DEFAULT_DURATION="300"
DEFAULT_RAMP_TIME="60"
STRESS_MULTIPLIER="5"

# Test scenarios
declare -A LOAD_SCENARIOS=(
    ["light_load"]="5,180,30"      # users,duration,ramp
    ["normal_load"]="20,300,60"
    ["heavy_load"]="50,600,120"
    ["stress_load"]="100,900,180"
    ["spike_load"]="200,300,30"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Test results tracking
declare -A LOAD_RESULTS=()
declare -A PERFORMANCE_METRICS=()
TOTAL_LOAD_TESTS=0
PASSED_LOAD_TESTS=0
FAILED_LOAD_TESTS=0

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

load_info() {
    log "LOAD" "${PURPLE}$*${NC}"
}

# Test execution wrapper for load tests
run_load_test() {
    local test_name="$1"
    local test_function="$2"
    local scenario_params="$3"
    
    load_info "Running load test: $test_name"
    ((TOTAL_LOAD_TESTS++))
    
    if $test_function "$scenario_params"; then
        success "✅ $test_name - PASSED"
        LOAD_RESULTS["$test_name"]="PASSED"
        ((PASSED_LOAD_TESTS++))
        return 0
    else
        error "❌ $test_name - FAILED"
        LOAD_RESULTS["$test_name"]="FAILED"
        ((FAILED_LOAD_TESTS++))
        return 1
    fi
}

# Install load testing tools if needed
install_load_tools() {
    info "Checking load testing tools..."
    
    # Check for wrk (web load testing)
    if ! command -v wrk &> /dev/null; then
        info "Installing wrk load testing tool..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y wrk
        elif command -v yum &> /dev/null; then
            sudo yum install -y wrk
        else
            warn "Could not install wrk automatically. Please install manually."
            return 1
        fi
    fi
    
    # Check for curl (for API testing)
    if ! command -v curl &> /dev/null; then
        error "curl is required but not installed"
        return 1
    fi
    
    success "Load testing tools are available"
    return 0
}

# Get service URLs
get_service_urls() {
    declare -gA SERVICE_URLS
    
    # Get ingress IPs/hostnames
    local ingresses=$(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [[ -n "$ingresses" ]]; then
        while IFS= read -r ingress_line; do
            local ingress_name=$(echo "$ingress_line" | awk '{print $1}')
            local hosts=$(kubectl get ingress -n "$NAMESPACE" "$ingress_name" -o jsonpath='{.spec.rules[*].host}' 2>/dev/null)
            local address=$(kubectl get ingress -n "$NAMESPACE" "$ingress_name" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
            
            if [[ -z "$address" ]]; then
                address=$(kubectl get ingress -n "$NAMESPACE" "$ingress_name" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
            fi
            
            if [[ -n "$hosts" && -n "$address" ]]; then
                for host in $hosts; do
                    SERVICE_URLS["$host"]="https://$address"
                done
            fi
        done <<< "$ingresses"
    fi
    
    # If no ingress, try NodePort services
    if [[ ${#SERVICE_URLS[@]} -eq 0 ]]; then
        local node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}' 2>/dev/null)
        if [[ -z "$node_ip" ]]; then
            node_ip=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}' 2>/dev/null)
        fi
        
        if [[ -n "$node_ip" ]]; then
            local services=$(kubectl get svc -n "$NAMESPACE" --no-headers 2>/dev/null | grep NodePort)
            while IFS= read -r svc_line; do
                local svc_name=$(echo "$svc_line" | awk '{print $1}')
                local node_port=$(kubectl get svc -n "$NAMESPACE" "$svc_name" -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
                
                if [[ -n "$node_port" ]]; then
                    SERVICE_URLS["$svc_name"]="http://$node_ip:$node_port"
                fi
            done <<< "$services"
        fi
    fi
    
    # Fallback to port-forward URLs
    if [[ ${#SERVICE_URLS[@]} -eq 0 ]]; then
        SERVICE_URLS["nextcloud"]="http://localhost:8080"
        SERVICE_URLS["mattermost"]="http://localhost:8081"
        SERVICE_URLS["gitlab"]="http://localhost:8082"
        warn "No external access detected, using port-forward URLs"
    fi
    
    info "Detected service URLs:"
    for service in "${!SERVICE_URLS[@]}"; do
        info "  $service: ${SERVICE_URLS[$service]}"
    done
}

# Generate load test script for wrk
generate_wrk_script() {
    local script_file="$1"
    local scenario="$2"
    
    cat > "$script_file" << 'EOF'
-- Realistic user behavior simulation
local counter = 1
local threads = {}

function setup(thread)
    thread:set("id", counter)
    table.insert(threads, thread)
    counter = counter + 1
end

function init(args)
    requests = 0
    responses = 0
    
    -- User agents for realistic simulation
    user_agents = {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }
    
    -- Simulate different user paths
    paths = {
        "/",
        "/login",
        "/dashboard",
        "/profile",
        "/settings"
    }
end

function request()
    requests = requests + 1
    local path = paths[math.random(#paths)]
    local ua = user_agents[math.random(#user_agents)]
    
    wrk.headers["User-Agent"] = ua
    wrk.headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    
    return wrk.format("GET", path)
end

function response(status, headers, body)
    responses = responses + 1
end

function done(summary, latency, requests)
    io.write("------------------------------\n")
    io.write(string.format("Requests:      %d\n", summary.requests))
    io.write(string.format("Responses:     %d\n", responses))
    io.write(string.format("Duration:      %.2fs\n", summary.duration / 1000000))
    io.write(string.format("Requests/sec:  %.2f\n", summary.requests / (summary.duration / 1000000)))
    io.write(string.format("Transfer/sec:  %s\n", summary.bytes / (summary.duration / 1000000)))
    io.write("------------------------------\n")
end
EOF
}

# Run web application load test
run_web_load_test() {
    local params="$1"
    local users=$(echo "$params" | cut -d',' -f1)
    local duration=$(echo "$params" | cut -d',' -f2)
    local ramp_time=$(echo "$params" | cut -d',' -f3)
    
    load_info "Running web load test: $users users, ${duration}s duration, ${ramp_time}s ramp"
    
    local test_passed=true
    local script_file="$REPORT_DIR/load_test.lua"
    generate_wrk_script "$script_file" "web"
    
    # Test each available service
    for service in "${!SERVICE_URLS[@]}"; do
        local url="${SERVICE_URLS[$service]}"
        local output_file="$REPORT_DIR/${service}_load_test.txt"
        
        load_info "Testing $service at $url"
        
        # Run wrk load test
        if timeout $((duration + 60)) wrk -t"$users" -c"$users" -d"${duration}s" \
            --script="$script_file" --timeout=10s "$url" > "$output_file" 2>&1; then
            
            # Parse results
            local requests_per_sec=$(grep "Requests/sec:" "$output_file" | awk '{print $2}' | head -1)
            local avg_latency=$(grep "Latency" "$output_file" | awk '{print $2}' | head -1)
            
            if [[ -n "$requests_per_sec" && $(echo "$requests_per_sec > 0" | bc 2>/dev/null) ]]; then
                PERFORMANCE_METRICS["${service}_rps"]="$requests_per_sec"
                PERFORMANCE_METRICS["${service}_latency"]="$avg_latency"
                success "$service: ${requests_per_sec} req/s, ${avg_latency} avg latency"
            else
                error "$service load test failed or produced no traffic"
                test_passed=false
            fi
        else
            error "$service load test timed out or failed"
            test_passed=false
        fi
    done
    
    return $([[ "$test_passed" == "true" ]] && echo 0 || echo 1)
}

# Run API load test
run_api_load_test() {
    local params="$1"
    local users=$(echo "$params" | cut -d',' -f1)
    local duration=$(echo "$params" | cut -d',' -f2)
    
    load_info "Running API load test: $users concurrent users, ${duration}s duration"
    
    local test_passed=true
    local pids=()
    
    # Start concurrent API test workers
    for ((i=1; i<=users; i++)); do
        {
            local worker_requests=0
            local worker_errors=0
            local start_time=$(date +%s)
            local end_time=$((start_time + duration))
            
            while [[ $(date +%s) -lt $end_time ]]; do
                for service in "${!SERVICE_URLS[@]}"; do
                    local url="${SERVICE_URLS[$service]}"
                    
                    # Test basic connectivity
                    if curl -s -f -m 5 --max-redirs 5 "$url" > /dev/null 2>&1; then
                        ((worker_requests++))
                    else
                        ((worker_errors++))
                    fi
                    
                    # Add some realistic delay between requests
                    sleep 0.5
                done
            done
            
            echo "Worker $i: $worker_requests requests, $worker_errors errors" >> "$REPORT_DIR/api_workers.log"
        } &
        pids+=($!)
    done
    
    # Wait for all workers to complete
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # Analyze results
    if [[ -f "$REPORT_DIR/api_workers.log" ]]; then
        local total_requests=$(awk '{sum+=$3} END {print sum}' "$REPORT_DIR/api_workers.log")
        local total_errors=$(awk '{sum+=$5} END {print sum}' "$REPORT_DIR/api_workers.log")
        local error_rate=$((total_errors * 100 / (total_requests > 0 ? total_requests : 1)))
        
        PERFORMANCE_METRICS["api_total_requests"]="$total_requests"
        PERFORMANCE_METRICS["api_error_rate"]="$error_rate"
        
        if [[ $error_rate -le 5 ]]; then
            success "API load test: $total_requests requests, ${error_rate}% error rate"
        else
            error "API load test: High error rate ${error_rate}%"
            test_passed=false
        fi
    else
        error "API load test failed to generate results"
        test_passed=false
    fi
    
    return $([[ "$test_passed" == "true" ]] && echo 0 || echo 1)
}

# Run database load test
run_database_load_test() {
    local params="$1"
    local users=$(echo "$params" | cut -d',' -f1)
    local duration=$(echo "$params" | cut -d',' -f2)
    
    load_info "Running database load test: $users connections, ${duration}s duration"
    
    local postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$postgres_pod" ]]; then
        warn "PostgreSQL pod not found, skipping database load test"
        return 0
    fi
    
    local test_passed=true
    local pids=()
    
    # Create test database for load testing
    kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -c "CREATE DATABASE loadtest;" 2>/dev/null || true
    
    # Start concurrent database workers
    for ((i=1; i<=users; i++)); do
        {
            local worker_queries=0
            local worker_errors=0
            local start_time=$(date +%s)
            local end_time=$((start_time + duration))
            
            while [[ $(date +%s) -lt $end_time ]]; do
                # Simple read query
                if kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -d loadtest -c "SELECT current_timestamp;" > /dev/null 2>&1; then
                    ((worker_queries++))
                else
                    ((worker_errors++))
                fi
                
                sleep 1
            done
            
            echo "DB Worker $i: $worker_queries queries, $worker_errors errors" >> "$REPORT_DIR/db_workers.log"
        } &
        pids+=($!)
    done
    
    # Wait for all workers
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    # Cleanup test database
    kubectl exec -n "$NAMESPACE" "$postgres_pod" -- psql -U postgres -c "DROP DATABASE IF EXISTS loadtest;" 2>/dev/null || true
    
    # Analyze results
    if [[ -f "$REPORT_DIR/db_workers.log" ]]; then
        local total_queries=$(awk '{sum+=$4} END {print sum}' "$REPORT_DIR/db_workers.log")
        local total_errors=$(awk '{sum+=$6} END {print sum}' "$REPORT_DIR/db_workers.log")
        local error_rate=$((total_errors * 100 / (total_queries > 0 ? total_queries : 1)))
        
        PERFORMANCE_METRICS["db_total_queries"]="$total_queries"
        PERFORMANCE_METRICS["db_error_rate"]="$error_rate"
        
        if [[ $error_rate -le 2 ]]; then
            success "Database load test: $total_queries queries, ${error_rate}% error rate"
        else
            error "Database load test: High error rate ${error_rate}%"
            test_passed=false
        fi
    else
        error "Database load test failed to generate results"
        test_passed=false
    fi
    
    return $([[ "$test_passed" == "true" ]] && echo 0 || echo 1)
}

# Monitor resource usage during tests
monitor_resources() {
    local duration="$1"
    local output_file="$REPORT_DIR/resource_monitor.log"
    
    load_info "Monitoring resource usage for ${duration}s..."
    
    {
        echo "timestamp,cpu_usage,memory_usage,pod_count"
        local end_time=$(($(date +%s) + duration))
        
        while [[ $(date +%s) -lt $end_time ]]; do
            local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            local cpu_usage="0"
            local memory_usage="0"
            local pod_count=$(kubectl get pods -n "$NAMESPACE" --no-headers | grep Running | wc -l)
            
            # Get resource usage if metrics server is available
            if kubectl top pods -n "$NAMESPACE" &> /dev/null; then
                cpu_usage=$(kubectl top pods -n "$NAMESPACE" --no-headers | awk '{sum+=$2} END {print sum}' 2>/dev/null || echo "0")
                memory_usage=$(kubectl top pods -n "$NAMESPACE" --no-headers | awk '{sum+=$3} END {print sum}' 2>/dev/null || echo "0")
            fi
            
            echo "$timestamp,$cpu_usage,$memory_usage,$pod_count"
            sleep 10
        done
    } > "$output_file" &
    
    local monitor_pid=$!
    return 0
}

# Run capacity planning test
run_capacity_test() {
    local params="$1"
    
    load_info "Running capacity planning test"
    
    # Start with baseline metrics
    local baseline_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | grep Running | wc -l)
    
    # Gradually increase load and monitor
    local test_passed=true
    local max_stable_load=0
    
    for load_level in 5 10 20 30 50; do
        load_info "Testing capacity at $load_level concurrent users..."
        
        # Start monitoring
        monitor_resources 120 &
        local monitor_pid=$!
        
        # Run load test for 2 minutes
        if run_web_load_test "$load_level,120,30"; then
            max_stable_load=$load_level
            success "System stable at $load_level users"
        else
            error "System unstable at $load_level users"
            test_passed=false
            break
        fi
        
        # Stop monitoring
        kill $monitor_pid 2>/dev/null || true
        
        # Wait for system to stabilize
        sleep 30
    done
    
    PERFORMANCE_METRICS["max_stable_load"]="$max_stable_load"
    
    return $([[ "$test_passed" == "true" ]] && echo 0 || echo 1)
}

# Setup
setup() {
    info "Setting up load testing environment..."
    mkdir -p "$REPORT_DIR"
    
    # Install tools
    if ! install_load_tools; then
        error "Failed to setup load testing tools"
        exit 1
    fi
    
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
    
    # Get service URLs
    get_service_urls
    
    if [[ ${#SERVICE_URLS[@]} -eq 0 ]]; then
        error "No services found for load testing"
        exit 1
    fi
    
    success "Load testing setup completed"
}

# Generate load test report
generate_load_report() {
    local report_file="$REPORT_DIR/load_test_report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Load Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary { background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .test-result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .passed { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .failed { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric-box { background: white; padding: 15px; border: 1px solid #ddd; border-radius: 5px; text-align: center; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .stats { display: flex; justify-content: space-around; text-align: center; }
        .stat-box { background: white; padding: 15px; border-radius: 5px; min-width: 100px; }
        .load-icon { font-size: 2em; }
    </style>
</head>
<body>
    <div class="header">
        <h1><span class="load-icon">⚡</span> N.O.A.H Load Test Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Namespace:</strong> $NAMESPACE</p>
        <p><strong>Services Tested:</strong> ${!SERVICE_URLS[*]}</p>
    </div>
    
    <div class="summary">
        <h2>Load Test Summary</h2>
        <div class="stats">
            <div class="stat-box">
                <h3>$TOTAL_LOAD_TESTS</h3>
                <p>Total Tests</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #28a745;">$PASSED_LOAD_TESTS</h3>
                <p>Passed</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #dc3545;">$FAILED_LOAD_TESTS</h3>
                <p>Failed</p>
            </div>
            <div class="stat-box">
                <h3>$(( (PASSED_LOAD_TESTS * 100) / (TOTAL_LOAD_TESTS > 0 ? TOTAL_LOAD_TESTS : 1) ))%</h3>
                <p>Success Rate</p>
            </div>
        </div>
    </div>
    
    <div class="summary">
        <h2>Performance Metrics</h2>
        <div class="metrics">
EOF

    # Add performance metrics
    for metric in "${!PERFORMANCE_METRICS[@]}"; do
        local value="${PERFORMANCE_METRICS[$metric]}"
        echo "            <div class=\"metric-box\">" >> "$report_file"
        echo "                <h4>$metric</h4>" >> "$report_file"
        echo "                <p><strong>$value</strong></p>" >> "$report_file"
        echo "            </div>" >> "$report_file"
    done

    cat >> "$report_file" << EOF
        </div>
    </div>
    
    <div class="test-results">
        <h2>Test Results</h2>
EOF

    for test_name in "${!LOAD_RESULTS[@]}"; do
        local result="${LOAD_RESULTS[$test_name]}"
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
        <h2>Recommendations</h2>
        <ul>
            <li>Review failed tests and investigate performance bottlenecks</li>
            <li>Consider scaling resources based on capacity test results</li>
            <li>Implement performance monitoring and alerting</li>
            <li>Plan for peak load scenarios based on test results</li>
            <li>Schedule regular load testing as part of CI/CD pipeline</li>
        </ul>
    </div>
    
    <div class="summary">
        <h2>Test Logs</h2>
        <pre>$(tail -100 "$LOG_FILE" 2>/dev/null || echo "No log entries found")</pre>
    </div>
</body>
</html>
EOF

    success "Load test report generated: $report_file"
}

# Main execution
main() {
    setup
    
    info "Starting N.O.A.H load testing suite..."
    
    # Run different load test scenarios
    run_load_test "Light Load Web Test" run_web_load_test "${LOAD_SCENARIOS[light_load]}"
    run_load_test "Normal Load Web Test" run_web_load_test "${LOAD_SCENARIOS[normal_load]}"
    run_load_test "API Load Test" run_api_load_test "${LOAD_SCENARIOS[normal_load]}"
    run_load_test "Database Load Test" run_database_load_test "${LOAD_SCENARIOS[normal_load]}"
    run_load_test "Heavy Load Test" run_web_load_test "${LOAD_SCENARIOS[heavy_load]}"
    run_load_test "Capacity Planning Test" run_capacity_test "${LOAD_SCENARIOS[stress_load]}"
    
    # Generate report
    generate_load_report
    
    # Final summary
    info "Load testing completed"
    info "Total tests: $TOTAL_LOAD_TESTS"
    info "Passed: $PASSED_LOAD_TESTS"
    info "Failed: $FAILED_LOAD_TESTS"
    
    if [[ $FAILED_LOAD_TESTS -eq 0 ]]; then
        success "All load tests passed! 🎉"
        exit 0
    else
        warn "Some load tests failed. Review the report for details."
        exit 1
    fi
}

# Run main function
main "$@"
