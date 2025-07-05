# N.O.A.H Testing Suite Documentation

## Overview

The N.O.A.H (Next Open-source Architecture Hub) testing suite provides comprehensive validation, security testing, performance testing, and compliance auditing for the entire infrastructure stack. This documentation covers all testing components and their usage.

## Test Suite Components

### 1. Master Test Runner (`run_all_tests.sh`)
- **Purpose**: Orchestrates all testing phases
- **Features**: 
  - Sequential or parallel execution
  - Selective test suite execution
  - Comprehensive reporting
  - Automated cleanup

### 2. Helm Chart Tests (`helm_chart_tests.sh`)
- **Purpose**: Unit testing for Helm charts
- **Coverage**:
  - Chart structure validation
  - Template rendering tests
  - Values schema validation
  - Security policy checks
  - Dependency verification

### 3. Post-Deploy Validation (via `../Script/noah validate`)
- **Purpose**: Infrastructure and service validation
- **Coverage**:
  - Pod health and readiness
  - Service connectivity
  - LDAP integration
  - OIDC authentication
  - Monitoring stack validation
  - Backup system verification

### 4. Integration Tests (`integration_tests.sh`)
- **Purpose**: End-to-end workflow validation
- **Coverage**:
  - Authentication flows
  - Service mesh connectivity
  - Data persistence
  - Cross-service integration
  - SSL/TLS configuration
  - Resource limits compliance

### 5. Security Tests (`security_tests.sh`)
- **Purpose**: Comprehensive security validation
- **Coverage**:
  - Container security scanning
  - Network security policies
  - RBAC configuration
  - TLS/SSL validation
  - Secrets management
  - Pod security standards

### 6. Performance Tests (`performance_tests.sh`)
- **Purpose**: Performance and scalability validation
- **Coverage**:
  - Resource utilization monitoring
  - Network performance testing
  - Application response times
  - Database performance
  - Storage I/O testing
  - Scaling behavior

### 7. Load Tests (`load_tests.sh`)
- **Purpose**: Realistic load testing and capacity planning
- **Coverage**:
  - Web application load testing
  - API load testing
  - Database connection testing
  - Capacity planning scenarios
  - Resource monitoring under load

### 8. Chaos Engineering Tests (`chaos_tests.sh`)
- **Purpose**: System resilience and failure recovery validation
- **Coverage**:
  - Pod deletion scenarios
  - Resource exhaustion testing
  - Network partition simulation
  - Storage failure testing
  - Cascading failure scenarios
  - Recovery time validation

### 9. Compliance Tests (`compliance_tests.sh`)
- **Purpose**: Regulatory and security compliance validation
- **Coverage**:
  - CIS Kubernetes Benchmark
  - GDPR data protection requirements
  - SOC2 security controls
  - NIST Cybersecurity Framework
  - PCI DSS requirements

## Quick Start Guide

### Prerequisites

1. **Required Tools**:
   ```bash
   # Kubernetes access
   kubectl version
   helm version
   
   # Testing tools (auto-installed if missing)
   wrk          # Load testing
   curl         # HTTP testing
   nc           # Network testing
   ```

2. **Cluster Access**:
   - Kubernetes cluster with N.O.A.H deployed
   - kubectl configured with appropriate permissions
   - Access to monitoring namespace (if applicable)

### Running All Tests

```bash
# Run complete test suite
./run_all_tests.sh

# Run with parallel execution (faster)
./run_all_tests.sh --parallel

# Run specific test suite only
./run_all_tests.sh --test-suite security

# Skip specific test categories
./run_all_tests.sh --skip-performance --skip-chaos
```

### Running Individual Test Suites

```bash
# Helm chart validation
./helm_chart_tests.sh

# Post-deployment validation
../Script/noah validate all

# Integration testing
./integration_tests.sh

# Security testing
./security_tests.sh

# Performance testing
./performance_tests.sh

# Load testing
./load_tests.sh

# Chaos engineering
./chaos_tests.sh

# Compliance auditing
./compliance_tests.sh
```

## Test Configuration

### Environment Variables

```bash
# Override default namespace
export NOAH_NAMESPACE="noah-prod"

# Set custom test duration
export TEST_DURATION="600"  # 10 minutes

# Configure load test parameters
export LOAD_TEST_USERS="50"
export LOAD_TEST_DURATION="300"

# Set report directory
export REPORT_DIR="/custom/reports/path"
```

### Configuration Files

Each test script accepts configuration through command-line arguments:

```bash
# Helm chart tests with custom charts directory
./helm_chart_tests.sh --charts-dir /path/to/charts

# Load tests with custom parameters
./load_tests.sh --users 100 --duration 600 --scenario stress

# Security tests with custom scan depth
./security_tests.sh --deep-scan --compliance-mode
```

## Test Reports

### Report Generation

All test scripts generate comprehensive HTML reports including:

- **Executive Summary**: High-level test results and metrics
- **Detailed Results**: Individual test outcomes with explanations
- **Performance Metrics**: Quantitative measurements and benchmarks
- **Compliance Status**: Regulatory compliance assessments
- **Recommendations**: Actionable insights for improvements
- **Raw Logs**: Complete test execution logs

### Report Locations

```bash
# Default report locations
/tmp/noah_test_reports_YYYYMMDD_HHMMSS/
├── master_test_log.log              # Combined log file
├── test_summary.html                # Overall summary
├── helm_chart_report.html           # Helm chart results
├── integration_test_report.html     # Integration test results
├── security_test_report.html        # Security scan results
├── performance_test_report.html     # Performance metrics
├── load_test_report.html           # Load test results
├── chaos_test_report.html          # Chaos engineering results
└── compliance_audit_report.html    # Compliance audit results
```

## Test Scenarios

### Development Environment Testing

```bash
# Quick validation for development
./run_all_tests.sh --skip-performance --skip-chaos --skip-load

# Focus on functionality
./integration_tests.sh
./security_tests.sh --basic-scan
```

### Staging Environment Testing

```bash
# Comprehensive testing before production
./run_all_tests.sh --parallel

# Include load testing
./load_tests.sh --scenario normal_load

# Validate security
./security_tests.sh --compliance-mode
```

### Production Environment Testing

```bash
# Non-disruptive testing only
../Script/noah validate all
./security_tests.sh --read-only
./compliance_tests.sh

# Scheduled maintenance window
./chaos_tests.sh --controlled-chaos
./load_tests.sh --capacity-planning
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: N.O.A.H Test Suite
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Kubernetes
      uses: helm/kind-action@v1.2.0
      
    - name: Deploy N.O.A.H
      run: |
        cd Script
        ./setup_infra.sh
        
    - name: Run Test Suite
      run: |
        cd Test
        ./run_all_tests.sh --skip-chaos --skip-load
        
    - name: Upload Reports
      uses: actions/upload-artifact@v2
      with:
        name: test-reports
        path: /tmp/noah_test_reports_*
```

### GitLab CI Example

```yaml
stages:
  - deploy
  - test
  - report

test_suite:
  stage: test
  script:
    - cd Test
    - ./run_all_tests.sh --parallel --test-suite integration
  artifacts:
    reports:
      junit: /tmp/noah_test_reports_*/junit.xml
    paths:
      - /tmp/noah_test_reports_*
  only:
    - main
    - merge_requests
```

## Troubleshooting

### Common Issues

1. **Permission Errors**:
   ```bash
   # Ensure proper kubectl permissions
   kubectl auth can-i create pods
   kubectl auth can-i get secrets
   ```

2. **Network Connectivity**:
   ```bash
   # Check cluster connectivity
   kubectl cluster-info
   kubectl get nodes
   ```

3. **Missing Dependencies**:
   ```bash
   # Install required tools
   sudo apt-get install wrk curl netcat-openbsd
   ```

4. **Resource Constraints**:
   ```bash
   # Check cluster resources
   kubectl top nodes
   kubectl describe nodes
   ```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Run with debug output
NOAH_DEBUG=true ./run_all_tests.sh

# Check individual test logs
tail -f /tmp/noah_*_tests_*.log
```

### Test Customization

Create custom test configurations:

```bash
# Custom test configuration
cat > custom_test_config.sh << EOF
NAMESPACE="noah-custom"
TIMEOUT=600
SKIP_PERFORMANCE_TESTS=true
ENABLE_DEEP_SECURITY_SCAN=true
EOF

# Source configuration
source custom_test_config.sh
./run_all_tests.sh
```

## Best Practices

### Test Execution

1. **Environment Preparation**:
   - Ensure cluster stability before testing
   - Verify all services are running
   - Check resource availability

2. **Test Scheduling**:
   - Run non-disruptive tests regularly
   - Schedule chaos tests during maintenance windows
   - Perform load tests in staging environments

3. **Result Analysis**:
   - Review all generated reports
   - Track performance trends over time
   - Address security findings promptly

### Continuous Improvement

1. **Test Coverage**:
   - Regularly review and update test scenarios
   - Add tests for new features and services
   - Validate real-world usage patterns

2. **Performance Baselines**:
   - Establish performance benchmarks
   - Monitor degradation over time
   - Set alerts for critical metrics

3. **Security Posture**:
   - Run security tests with each deployment
   - Keep compliance frameworks updated
   - Regular vulnerability assessments

## Support and Contribution

### Getting Help

- Review test logs for detailed error information
- Check the troubleshooting section above
- Consult the N.O.A.H documentation in `docs/`

### Contributing

- Add new test scenarios for additional coverage
- Improve existing test reliability and accuracy
- Enhance reporting and visualization
- Update documentation for new features

---

For more information about the N.O.A.H project, see the main documentation in the `docs/` directory.
