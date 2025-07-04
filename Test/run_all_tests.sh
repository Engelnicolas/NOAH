#!/bin/bash

# N.O.A.H - Comprehensive Test Runner
# 
# This script orchestrates all testing phases for the N.O.A.H infrastructure
# including unit tests, integration tests, security tests, and performance tests.

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="/tmp/noah_test_reports_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${REPORTS_DIR}/master_test_log.log"

# Test configuration
SKIP_UNIT_TESTS=false
SKIP_INTEGRATION_TESTS=false
SKIP_SECURITY_TESTS=false
SKIP_PERFORMANCE_TESTS=false
SKIP_CLEANUP=false
PARALLEL_EXECUTION=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
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

title() {
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${PURPLE}$*${NC}"
    echo -e "${PURPLE}════════════════════════════════════════════════════════════════════════════════${NC}"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

N.O.A.H Comprehensive Test Runner

OPTIONS:
    -h, --help                  Show this help message
    -u, --skip-unit             Skip Helm chart unit tests
    -i, --skip-integration      Skip integration/deployment tests
    -s, --skip-security         Skip security tests
    -p, --skip-performance      Skip performance tests
    -c, --skip-cleanup          Skip cleanup after tests
    -P, --parallel              Run compatible tests in parallel
    --reports-dir DIR           Custom reports directory
    --test-suite SUITE          Run specific test suite only (unit|integration|security|performance)

EXAMPLES:
    $0                          # Run all tests
    $0 --skip-performance       # Run all except performance tests
    $0 --test-suite security    # Run only security tests
    $0 --parallel               # Run tests in parallel where possible

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -u|--skip-unit)
                SKIP_UNIT_TESTS=true
                shift
                ;;
            -i|--skip-integration)
                SKIP_INTEGRATION_TESTS=true
                shift
                ;;
            -s|--skip-security)
                SKIP_SECURITY_TESTS=true
                shift
                ;;
            -p|--skip-performance)
                SKIP_PERFORMANCE_TESTS=true
                shift
                ;;
            -c|--skip-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            -P|--parallel)
                PARALLEL_EXECUTION=true
                shift
                ;;
            --reports-dir)
                REPORTS_DIR="$2"
                LOG_FILE="${REPORTS_DIR}/master_test_log.log"
                shift 2
                ;;
            --test-suite)
                case $2 in
                    unit)
                        SKIP_INTEGRATION_TESTS=true
                        SKIP_SECURITY_TESTS=true
                        SKIP_PERFORMANCE_TESTS=true
                        ;;
                    integration)
                        SKIP_UNIT_TESTS=true
                        SKIP_SECURITY_TESTS=true
                        SKIP_PERFORMANCE_TESTS=true
                        ;;
                    security)
                        SKIP_UNIT_TESTS=true
                        SKIP_INTEGRATION_TESTS=true
                        SKIP_PERFORMANCE_TESTS=true
                        ;;
                    performance)
                        SKIP_UNIT_TESTS=true
                        SKIP_INTEGRATION_TESTS=true
                        SKIP_SECURITY_TESTS=true
                        ;;
                    *)
                        error "Invalid test suite: $2"
                        usage
                        exit 1
                        ;;
                esac
                shift 2
                ;;
            *)
                error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Setup function
setup() {
    title "N.O.A.H Comprehensive Test Suite - Setup"
    
    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    
    info "Test reports will be saved to: $REPORTS_DIR"
    info "Master log file: $LOG_FILE"
    
    # Check prerequisites
    info "Checking prerequisites..."
    
    local missing_tools=()
    
    if ! command -v kubectl &> /dev/null; then
        missing_tools+=("kubectl")
    fi
    
    if ! command -v helm &> /dev/null; then
        missing_tools+=("helm")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing_tools[*]}"
        error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        error "Please ensure kubectl is configured correctly"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Run unit tests
run_unit_tests() {
    if [[ "$SKIP_UNIT_TESTS" == "true" ]]; then
        warn "Skipping unit tests"
        return 0
    fi
    
    title "Running Helm Chart Unit Tests"
    
    local test_script="${SCRIPT_DIR}/helm_chart_tests.sh"
    if [[ ! -f "$test_script" ]]; then
        error "Unit test script not found: $test_script"
        return 1
    fi
    
    info "Starting Helm chart unit tests..."
    if bash "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        success "Unit tests completed successfully"
        return 0
    else
        error "Unit tests failed"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    if [[ "$SKIP_INTEGRATION_TESTS" == "true" ]]; then
        warn "Skipping integration tests"
        return 0
    fi
    
    title "Running Integration Tests"
    
    local test_script="${SCRIPT_DIR}/post_deploy_validate.sh"
    if [[ ! -f "$test_script" ]]; then
        error "Integration test script not found: $test_script"
        return 1
    fi
    
    info "Starting post-deployment validation tests..."
    if bash "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        success "Integration tests completed successfully"
        return 0
    else
        error "Integration tests failed"
        return 1
    fi
}

# Run security tests
run_security_tests() {
    if [[ "$SKIP_SECURITY_TESTS" == "true" ]]; then
        warn "Skipping security tests"
        return 0
    fi
    
    title "Running Security Tests"
    
    local test_script="${SCRIPT_DIR}/security_tests.sh"
    if [[ ! -f "$test_script" ]]; then
        error "Security test script not found: $test_script"
        return 1
    fi
    
    info "Starting security validation tests..."
    if bash "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        success "Security tests completed successfully"
        return 0
    else
        error "Security tests failed"
        return 1
    fi
}

# Run performance tests
run_performance_tests() {
    if [[ "$SKIP_PERFORMANCE_TESTS" == "true" ]]; then
        warn "Skipping performance tests"
        return 0
    fi
    
    title "Running Performance Tests"
    
    local test_script="${SCRIPT_DIR}/performance_tests.sh"
    if [[ ! -f "$test_script" ]]; then
        error "Performance test script not found: $test_script"
        return 1
    fi
    
    info "Starting performance validation tests..."
    if bash "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        success "Performance tests completed successfully"
        return 0
    else
        error "Performance tests failed"
        return 1
    fi
}

# Run tests in parallel
run_parallel_tests() {
    title "Running Tests in Parallel Mode"
    
    local pids=()
    local results=()
    
    # Run unit and security tests in parallel (they don't interfere)
    if [[ "$SKIP_UNIT_TESTS" != "true" ]]; then
        info "Starting unit tests in background..."
        run_unit_tests &
        pids+=($!)
        results+=("unit")
    fi
    
    if [[ "$SKIP_SECURITY_TESTS" != "true" ]]; then
        info "Starting security tests in background..."
        run_security_tests &
        pids+=($!)
        results+=("security")
    fi
    
    # Wait for parallel tests to complete
    local parallel_success=true
    for i in "${!pids[@]}"; do
        local pid=${pids[$i]}
        local test_name=${results[$i]}
        
        if wait $pid; then
            success "$test_name tests completed successfully"
        else
            error "$test_name tests failed"
            parallel_success=false
        fi
    done
    
    # Run sequential tests
    if [[ "$SKIP_INTEGRATION_TESTS" != "true" ]]; then
        if ! run_integration_tests; then
            parallel_success=false
        fi
    fi
    
    if [[ "$SKIP_PERFORMANCE_TESTS" != "true" ]]; then
        if ! run_performance_tests; then
            parallel_success=false
        fi
    fi
    
    return $([[ "$parallel_success" == "true" ]] && echo 0 || echo 1)
}

# Generate final report
generate_report() {
    title "Generating Test Report"
    
    local report_file="${REPORTS_DIR}/test_summary.html"
    local start_time=$(date -d "$(head -1 "$LOG_FILE" | cut -d' ' -f1-2)" +%s 2>/dev/null || echo "0")
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
        .info { color: #17a2b8; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>N.O.A.H - Test Execution Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Duration:</strong> ${duration} seconds</p>
        <p><strong>Reports Directory:</strong> $REPORTS_DIR</p>
    </div>
    
    <div class="test-section">
        <h2>Test Configuration</h2>
        <ul>
            <li>Unit Tests: $([[ "$SKIP_UNIT_TESTS" == "true" ]] && echo "Skipped" || echo "Executed")</li>
            <li>Integration Tests: $([[ "$SKIP_INTEGRATION_TESTS" == "true" ]] && echo "Skipped" || echo "Executed")</li>
            <li>Security Tests: $([[ "$SKIP_SECURITY_TESTS" == "true" ]] && echo "Skipped" || echo "Executed")</li>
            <li>Performance Tests: $([[ "$SKIP_PERFORMANCE_TESTS" == "true" ]] && echo "Skipped" || echo "Executed")</li>
            <li>Parallel Execution: $([[ "$PARALLEL_EXECUTION" == "true" ]] && echo "Enabled" || echo "Sequential")</li>
        </ul>
    </div>
    
    <div class="test-section">
        <h2>Test Results Summary</h2>
        <p>Detailed logs are available in the individual test report files.</p>
        <p>Master log file: <code>$LOG_FILE</code></p>
    </div>
    
    <div class="test-section">
        <h2>Recent Log Entries</h2>
        <pre>$(tail -50 "$LOG_FILE" 2>/dev/null || echo "No log entries found")</pre>
    </div>
</body>
</html>
EOF
    
    info "Test report generated: $report_file"
}

# Cleanup function
cleanup() {
    if [[ "$SKIP_CLEANUP" == "true" ]]; then
        warn "Skipping cleanup"
        return 0
    fi
    
    title "Cleanup"
    
    info "Cleaning up test resources..."
    
    # Clean up any test namespaces
    if kubectl get namespace noah-test &> /dev/null; then
        info "Removing test namespace..."
        kubectl delete namespace noah-test --ignore-not-found=true
    fi
    
    # Clean up any temporary files older than 1 day
    find /tmp -name "noah_*" -type f -mtime +1 -delete 2>/dev/null || true
    
    success "Cleanup completed"
}

# Main execution function
main() {
    local overall_success=true
    
    # Setup
    setup
    
    # Record start time
    local start_time=$(date)
    info "Test execution started at: $start_time"
    
    # Run tests
    if [[ "$PARALLEL_EXECUTION" == "true" ]]; then
        if ! run_parallel_tests; then
            overall_success=false
        fi
    else
        # Sequential execution
        if ! run_unit_tests; then
            overall_success=false
        fi
        
        if ! run_integration_tests; then
            overall_success=false
        fi
        
        if ! run_security_tests; then
            overall_success=false
        fi
        
        if ! run_performance_tests; then
            overall_success=false
        fi
    fi
    
    # Generate report
    generate_report
    
    # Cleanup
    cleanup
    
    # Final status
    local end_time=$(date)
    info "Test execution completed at: $end_time"
    
    if [[ "$overall_success" == "true" ]]; then
        title "✅ All Tests Passed Successfully!"
        success "N.O.A.H infrastructure validation completed successfully"
        success "Reports available in: $REPORTS_DIR"
        exit 0
    else
        title "❌ Some Tests Failed"
        error "N.O.A.H infrastructure validation completed with errors"
        error "Check the reports in: $REPORTS_DIR"
        exit 1
    fi
}

# Trap for cleanup on exit
trap cleanup EXIT

# Parse arguments and run main
parse_args "$@"
main
