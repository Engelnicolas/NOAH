#!/bin/bash

# N.O.A.H - Compliance and Audit Tests
# 
# Comprehensive compliance testing for security standards including
# GDPR, SOC2, CIS Kubernetes Benchmark, and other regulatory requirements.

set -e

# Configuration
NAMESPACE="noah"
LOG_FILE="/tmp/noah_compliance_tests_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="/tmp/noah_compliance_reports_$(date +%Y%m%d_%H%M%S)"

# Compliance frameworks to test
COMPLIANCE_FRAMEWORKS=(
    "CIS_KUBERNETES"
    "GDPR_DATA_PROTECTION"
    "SOC2_SECURITY"
    "NIST_CYBERSECURITY"
    "PCI_DSS"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Test results tracking
declare -A COMPLIANCE_RESULTS=()
declare -A FRAMEWORK_SCORES=()
TOTAL_COMPLIANCE_TESTS=0
PASSED_COMPLIANCE_TESTS=0
FAILED_COMPLIANCE_TESTS=0

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

compliance_info() {
    log "COMPLIANCE" "${PURPLE}$*${NC}"
}

# Test execution wrapper for compliance tests
run_compliance_test() {
    local test_name="$1"
    local test_function="$2"
    local framework="$3"
    
    compliance_info "Running compliance test: $test_name [$framework]"
    ((TOTAL_COMPLIANCE_TESTS++))
    
    if $test_function; then
        success "✅ $test_name - COMPLIANT"
        COMPLIANCE_RESULTS["$test_name"]="COMPLIANT"
        ((PASSED_COMPLIANCE_TESTS++))
        
        # Update framework score
        if [[ -n "${FRAMEWORK_SCORES[$framework]}" ]]; then
            FRAMEWORK_SCORES["$framework"]=$((${FRAMEWORK_SCORES[$framework]} + 1))
        else
            FRAMEWORK_SCORES["$framework"]=1
        fi
        return 0
    else
        error "❌ $test_name - NON-COMPLIANT"
        COMPLIANCE_RESULTS["$test_name"]="NON-COMPLIANT"
        ((FAILED_COMPLIANCE_TESTS++))
        return 1
    fi
}

# CIS Kubernetes Benchmark Tests
test_cis_rbac_enabled() {
    info "Testing CIS 1.2.6: Ensure that the --authorization-mode argument includes RBAC"
    
    # Check if RBAC is enabled in the cluster
    if kubectl auth can-i create pods --as=system:anonymous 2>/dev/null; then
        error "Anonymous users have excessive permissions"
        return 1
    fi
    
    # Check if RBAC resources exist
    local rbac_roles=$(kubectl get clusterroles --no-headers 2>/dev/null | wc -l)
    local rbac_bindings=$(kubectl get clusterrolebindings --no-headers 2>/dev/null | wc -l)
    
    if [[ $rbac_roles -gt 0 && $rbac_bindings -gt 0 ]]; then
        success "RBAC is properly configured ($rbac_roles roles, $rbac_bindings bindings)"
        return 0
    else
        error "RBAC not properly configured"
        return 1
    fi
}

test_cis_pod_security_standards() {
    info "Testing CIS 5.1: Pod Security Standards"
    
    local non_compliant_pods=0
    local total_pods=0
    
    # Check pods for security context
    while IFS= read -r pod_line; do
        local pod_name=$(echo "$pod_line" | awk '{print $1}')
        ((total_pods++))
        
        # Check if pod runs as non-root
        local runs_as_root=$(kubectl get pod -n "$NAMESPACE" "$pod_name" -o jsonpath='{.spec.securityContext.runAsNonRoot}' 2>/dev/null)
        local container_root=$(kubectl get pod -n "$NAMESPACE" "$pod_name" -o jsonpath='{.spec.containers[*].securityContext.runAsNonRoot}' 2>/dev/null)
        
        if [[ "$runs_as_root" != "true" && "$container_root" != *"true"* ]]; then
            ((non_compliant_pods++))
            warn "Pod $pod_name may be running as root"
        fi
        
    done < <(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    local compliance_rate=$((((total_pods - non_compliant_pods) * 100) / (total_pods > 0 ? total_pods : 1)))
    
    if [[ $compliance_rate -ge 80 ]]; then
        success "Pod security compliance: $compliance_rate% ($((total_pods - non_compliant_pods))/$total_pods pods compliant)"
        return 0
    else
        error "Pod security compliance too low: $compliance_rate%"
        return 1
    fi
}

test_cis_network_policies() {
    info "Testing CIS 5.3: Network Policies"
    
    local network_policies=$(kubectl get networkpolicies -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    if [[ $network_policies -gt 0 ]]; then
        success "Network policies are configured ($network_policies policies found)"
        return 0
    else
        warn "No network policies found - network traffic is not restricted"
        return 1
    fi
}

test_cis_secrets_management() {
    info "Testing CIS 5.4: Secrets Management"
    
    local secrets_as_files=0
    local secrets_as_env=0
    local total_secrets=0
    
    # Check how secrets are mounted
    while IFS= read -r pod_line; do
        local pod_name=$(echo "$pod_line" | awk '{print $1}')
        
        # Check for secret volume mounts (preferred)
        local volume_secrets=$(kubectl get pod -n "$NAMESPACE" "$pod_name" -o jsonpath='{.spec.volumes[?(@.secret)].secret.secretName}' 2>/dev/null)
        if [[ -n "$volume_secrets" ]]; then
            ((secrets_as_files++))
        fi
        
        # Check for secrets as environment variables (less secure)
        local env_secrets=$(kubectl get pod -n "$NAMESPACE" "$pod_name" -o jsonpath='{.spec.containers[*].env[?(@.valueFrom.secretKeyRef)].valueFrom.secretKeyRef.name}' 2>/dev/null)
        if [[ -n "$env_secrets" ]]; then
            ((secrets_as_env++))
        fi
        
        if [[ -n "$volume_secrets" || -n "$env_secrets" ]]; then
            ((total_secrets++))
        fi
        
    done < <(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [[ $total_secrets -gt 0 ]]; then
        local file_ratio=$((secrets_as_files * 100 / total_secrets))
        info "Secrets management: $secrets_as_files as files, $secrets_as_env as env vars"
        
        if [[ $file_ratio -ge 70 ]]; then
            success "Good secrets management practices (${file_ratio}% as files)"
            return 0
        else
            warn "Consider mounting more secrets as files instead of environment variables"
            return 1
        fi
    else
        info "No secrets found in pod configurations"
        return 0
    fi
}

# GDPR Data Protection Tests
test_gdpr_data_encryption() {
    info "Testing GDPR: Data Encryption at Rest and in Transit"
    
    local encryption_compliant=true
    
    # Check for TLS in ingresses
    local tls_ingresses=0
    local total_ingresses=0
    
    while IFS= read -r ingress_line; do
        local ingress_name=$(echo "$ingress_line" | awk '{print $1}')
        ((total_ingresses++))
        
        if kubectl get ingress -n "$NAMESPACE" "$ingress_name" -o yaml | grep -q "tls:"; then
            ((tls_ingresses++))
        fi
    done < <(kubectl get ingress -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [[ $total_ingresses -gt 0 ]]; then
        local tls_ratio=$((tls_ingresses * 100 / total_ingresses))
        info "TLS configuration: $tls_ingresses/$total_ingresses ingresses have TLS"
        
        if [[ $tls_ratio -lt 100 ]]; then
            encryption_compliant=false
            warn "Not all ingresses have TLS configured"
        fi
    fi
    
    # Check for encrypted storage classes
    local encrypted_storage=false
    while IFS= read -r sc_line; do
        local sc_name=$(echo "$sc_line" | awk '{print $1}')
        if kubectl get storageclass "$sc_name" -o yaml | grep -q "encrypted"; then
            encrypted_storage=true
            break
        fi
    done < <(kubectl get storageclass --no-headers 2>/dev/null)
    
    if [[ "$encrypted_storage" == "true" ]]; then
        success "Encrypted storage classes found"
    else
        warn "No encrypted storage classes detected"
        encryption_compliant=false
    fi
    
    if [[ "$encryption_compliant" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

test_gdpr_data_retention() {
    info "Testing GDPR: Data Retention Policies"
    
    # Check for backup retention policies
    local backup_configs=$(kubectl get configmaps -n "$NAMESPACE" --no-headers | grep -i backup | wc -l)
    
    # Check for log retention in monitoring
    local log_retention_configured=false
    if kubectl get configmaps -n monitoring --no-headers 2>/dev/null | grep -q prometheus; then
        log_retention_configured=true
    fi
    
    if [[ $backup_configs -gt 0 || "$log_retention_configured" == "true" ]]; then
        success "Data retention policies appear to be configured"
        return 0
    else
        warn "Data retention policies not clearly configured"
        return 1
    fi
}

test_gdpr_access_controls() {
    info "Testing GDPR: Access Controls and Data Subject Rights"
    
    # Check for proper RBAC configuration
    local admin_users=$(kubectl get clusterrolebindings -o yaml | grep -c "cluster-admin" 2>/dev/null)
    local total_users=$(kubectl get clusterrolebindings -o yaml | grep -c "subjects:" 2>/dev/null)
    
    if [[ $total_users -gt 0 ]]; then
        local admin_ratio=$((admin_users * 100 / total_users))
        
        if [[ $admin_ratio -le 20 ]]; then
            success "Principle of least privilege appears to be followed (${admin_ratio}% admin users)"
            return 0
        else
            warn "Too many users have admin privileges (${admin_ratio}%)"
            return 1
        fi
    else
        warn "Cannot determine user access patterns"
        return 1
    fi
}

# SOC2 Security Tests
test_soc2_access_monitoring() {
    info "Testing SOC2: Access Monitoring and Logging"
    
    # Check for audit logging
    local audit_logs_enabled=false
    
    # Check if monitoring namespace exists and has logging components
    if kubectl get namespace monitoring &> /dev/null; then
        local logging_pods=$(kubectl get pods -n monitoring --no-headers | grep -E "(grafana|prometheus|loki|elasticsearch)" | wc -l)
        
        if [[ $logging_pods -gt 0 ]]; then
            audit_logs_enabled=true
            success "Monitoring and logging infrastructure detected ($logging_pods components)"
        fi
    fi
    
    # Check for service mesh or ingress logging
    local ingress_logging=$(kubectl get configmaps -A --no-headers | grep -i "nginx\|traefik\|istio" | wc -l)
    
    if [[ "$audit_logs_enabled" == "true" || $ingress_logging -gt 0 ]]; then
        return 0
    else
        error "Insufficient access monitoring and logging"
        return 1
    fi
}

test_soc2_change_management() {
    info "Testing SOC2: Change Management Controls"
    
    # Check for resource annotations indicating change management
    local annotated_resources=0
    local total_resources=0
    
    for resource_type in deployment statefulset daemonset; do
        while IFS= read -r resource_line; do
            local resource_name=$(echo "$resource_line" | awk '{print $1}')
            ((total_resources++))
            
            # Check for annotations indicating change management
            local annotations=$(kubectl get "$resource_type" -n "$NAMESPACE" "$resource_name" -o jsonpath='{.metadata.annotations}' 2>/dev/null)
            if [[ "$annotations" == *"version"* || "$annotations" == *"revision"* || "$annotations" == *"deployment"* ]]; then
                ((annotated_resources++))
            fi
        done < <(kubectl get "$resource_type" -n "$NAMESPACE" --no-headers 2>/dev/null)
    done
    
    if [[ $total_resources -gt 0 ]]; then
        local annotation_ratio=$((annotated_resources * 100 / total_resources))
        
        if [[ $annotation_ratio -ge 50 ]]; then
            success "Change management practices detected (${annotation_ratio}% resources have tracking annotations)"
            return 0
        else
            warn "Limited change management tracking (${annotation_ratio}% resources have annotations)"
            return 1
        fi
    else
        warn "No deployable resources found"
        return 0
    fi
}

# NIST Cybersecurity Framework Tests
test_nist_identify() {
    info "Testing NIST: Identify - Asset Management"
    
    # Check for proper labeling and documentation
    local labeled_resources=0
    local total_resources=0
    
    for resource_type in pod service deployment; do
        while IFS= read -r resource_line; do
            local resource_name=$(echo "$resource_line" | awk '{print $1}')
            ((total_resources++))
            
            # Check for proper labels
            local labels=$(kubectl get "$resource_type" -n "$NAMESPACE" "$resource_name" -o jsonpath='{.metadata.labels}' 2>/dev/null)
            if [[ "$labels" == *"app"* && "$labels" == *"version"* ]]; then
                ((labeled_resources++))
            fi
        done < <(kubectl get "$resource_type" -n "$NAMESPACE" --no-headers 2>/dev/null)
    done
    
    if [[ $total_resources -gt 0 ]]; then
        local labeling_ratio=$((labeled_resources * 100 / total_resources))
        
        if [[ $labeling_ratio -ge 80 ]]; then
            success "Good asset identification practices (${labeling_ratio}% resources properly labeled)"
            return 0
        else
            warn "Asset identification needs improvement (${labeling_ratio}% resources properly labeled)"
            return 1
        fi
    else
        return 0
    fi
}

test_nist_protect() {
    info "Testing NIST: Protect - Access Control and Data Security"
    
    # Check for security contexts
    local secure_pods=0
    local total_pods=0
    
    while IFS= read -r pod_line; do
        local pod_name=$(echo "$pod_line" | awk '{print $1}')
        ((total_pods++))
        
        # Check for security context
        local security_context=$(kubectl get pod -n "$NAMESPACE" "$pod_name" -o jsonpath='{.spec.securityContext}' 2>/dev/null)
        local container_security=$(kubectl get pod -n "$NAMESPACE" "$pod_name" -o jsonpath='{.spec.containers[*].securityContext}' 2>/dev/null)
        
        if [[ -n "$security_context" || -n "$container_security" ]]; then
            ((secure_pods++))
        fi
    done < <(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [[ $total_pods -gt 0 ]]; then
        local security_ratio=$((secure_pods * 100 / total_pods))
        
        if [[ $security_ratio -ge 70 ]]; then
            success "Good protection controls (${security_ratio}% pods have security contexts)"
            return 0
        else
            warn "Protection controls need improvement (${security_ratio}% pods have security contexts)"
            return 1
        fi
    else
        return 0
    fi
}

# PCI DSS Tests (if applicable)
test_pci_network_segmentation() {
    info "Testing PCI DSS: Network Segmentation"
    
    # Check for network policies that segment traffic
    local network_policies=$(kubectl get networkpolicies -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
    
    # Check for multiple namespaces (segmentation)
    local namespaces=$(kubectl get namespaces --no-headers | grep -v "kube-\|default" | wc -l)
    
    if [[ $network_policies -gt 0 && $namespaces -gt 1 ]]; then
        success "Network segmentation controls detected ($network_policies policies, $namespaces namespaces)"
        return 0
    else
        warn "Limited network segmentation (consider implementing network policies)"
        return 1
    fi
}

test_pci_data_protection() {
    info "Testing PCI DSS: Cardholder Data Protection"
    
    # Check for secrets and their protection
    local secrets=$(kubectl get secrets -n "$NAMESPACE" --no-headers | grep -v "default-token" | wc -l)
    
    # Check for encrypted storage
    local encrypted_pvcs=0
    local total_pvcs=0
    
    while IFS= read -r pvc_line; do
        local pvc_name=$(echo "$pvc_line" | awk '{print $1}')
        ((total_pvcs++))
        
        # Check if PVC uses encrypted storage class
        local storage_class=$(kubectl get pvc -n "$NAMESPACE" "$pvc_name" -o jsonpath='{.spec.storageClassName}' 2>/dev/null)
        if kubectl get storageclass "$storage_class" -o yaml 2>/dev/null | grep -q "encrypted"; then
            ((encrypted_pvcs++))
        fi
    done < <(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    local encryption_ratio=100
    if [[ $total_pvcs -gt 0 ]]; then
        encryption_ratio=$((encrypted_pvcs * 100 / total_pvcs))
    fi
    
    if [[ $secrets -gt 0 && $encryption_ratio -ge 80 ]]; then
        success "Data protection measures detected ($secrets secrets, ${encryption_ratio}% encrypted storage)"
        return 0
    else
        warn "Data protection may need enhancement"
        return 1
    fi
}

# Setup
setup() {
    info "Setting up compliance testing environment..."
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
    
    success "Compliance testing setup completed"
}

# Generate compliance report
generate_compliance_report() {
    local report_file="$REPORT_DIR/compliance_audit_report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Compliance Audit Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .compliance-notice { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .summary { background: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .framework { margin: 20px 0; padding: 15px; border: 2px solid #ddd; border-radius: 5px; }
        .test-result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .compliant { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .non-compliant { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .stats { display: flex; justify-content: space-around; text-align: center; }
        .stat-box { background: white; padding: 15px; border-radius: 5px; min-width: 100px; }
        .framework-score { text-align: center; font-weight: bold; font-size: 1.2em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ N.O.A.H Compliance Audit Report</h1>
        <p><strong>Generated:</strong> $(date)</p>
        <p><strong>Namespace:</strong> $NAMESPACE</p>
        <p><strong>Audit Scope:</strong> ${COMPLIANCE_FRAMEWORKS[*]}</p>
    </div>
    
    <div class="compliance-notice">
        <h3>📋 Compliance Notice</h3>
        <p>This audit report provides automated compliance testing results. Manual review and additional testing may be required for full compliance certification.</p>
    </div>
    
    <div class="summary">
        <h2>Overall Compliance Summary</h2>
        <div class="stats">
            <div class="stat-box">
                <h3>$TOTAL_COMPLIANCE_TESTS</h3>
                <p>Total Tests</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #28a745;">$PASSED_COMPLIANCE_TESTS</h3>
                <p>Compliant</p>
            </div>
            <div class="stat-box">
                <h3 style="color: #dc3545;">$FAILED_COMPLIANCE_TESTS</h3>
                <p>Non-Compliant</p>
            </div>
            <div class="stat-box">
                <h3>$(( (PASSED_COMPLIANCE_TESTS * 100) / (TOTAL_COMPLIANCE_TESTS > 0 ? TOTAL_COMPLIANCE_TESTS : 1) ))%</h3>
                <p>Compliance Rate</p>
            </div>
        </div>
    </div>
    
    <div class="frameworks">
        <h2>Framework Compliance Scores</h2>
EOF

    # Add framework scores
    for framework in "${COMPLIANCE_FRAMEWORKS[@]}"; do
        local score="${FRAMEWORK_SCORES[$framework]:-0}"
        echo "        <div class=\"framework\">" >> "$report_file"
        echo "            <h3>$framework</h3>" >> "$report_file"
        echo "            <div class=\"framework-score\">Score: $score tests passed</div>" >> "$report_file"
        echo "        </div>" >> "$report_file"
    done

    cat >> "$report_file" << EOF
    </div>
    
    <div class="test-results">
        <h2>Detailed Test Results</h2>
EOF

    for test_name in "${!COMPLIANCE_RESULTS[@]}"; do
        local result="${COMPLIANCE_RESULTS[$test_name]}"
        local css_class="compliant"
        local icon="✅"
        
        if [[ "$result" == "NON-COMPLIANT" ]]; then
            css_class="non-compliant"
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
            <li>Address all non-compliant items identified in this audit</li>
            <li>Implement regular compliance monitoring and testing</li>
            <li>Conduct manual security reviews for critical controls</li>
            <li>Maintain documentation for compliance evidence</li>
            <li>Review and update security policies regularly</li>
        </ul>
    </div>
    
    <div class="summary">
        <h2>Audit Log</h2>
        <pre>$(tail -100 "$LOG_FILE" 2>/dev/null || echo "No log entries found")</pre>
    </div>
</body>
</html>
EOF

    success "Compliance audit report generated: $report_file"
}

# Main execution
main() {
    setup
    
    info "Starting N.O.A.H compliance and audit testing..."
    
    # CIS Kubernetes Benchmark tests
    run_compliance_test "RBAC Authorization" test_cis_rbac_enabled "CIS_KUBERNETES"
    run_compliance_test "Pod Security Standards" test_cis_pod_security_standards "CIS_KUBERNETES"
    run_compliance_test "Network Policies" test_cis_network_policies "CIS_KUBERNETES"
    run_compliance_test "Secrets Management" test_cis_secrets_management "CIS_KUBERNETES"
    
    # GDPR tests
    run_compliance_test "Data Encryption" test_gdpr_data_encryption "GDPR_DATA_PROTECTION"
    run_compliance_test "Data Retention" test_gdpr_data_retention "GDPR_DATA_PROTECTION"
    run_compliance_test "Access Controls" test_gdpr_access_controls "GDPR_DATA_PROTECTION"
    
    # SOC2 tests
    run_compliance_test "Access Monitoring" test_soc2_access_monitoring "SOC2_SECURITY"
    run_compliance_test "Change Management" test_soc2_change_management "SOC2_SECURITY"
    
    # NIST tests
    run_compliance_test "Asset Identification" test_nist_identify "NIST_CYBERSECURITY"
    run_compliance_test "Protection Controls" test_nist_protect "NIST_CYBERSECURITY"
    
    # PCI DSS tests
    run_compliance_test "Network Segmentation" test_pci_network_segmentation "PCI_DSS"
    run_compliance_test "Data Protection" test_pci_data_protection "PCI_DSS"
    
    # Generate report
    generate_compliance_report
    
    # Final summary
    info "Compliance testing completed"
    info "Total tests: $TOTAL_COMPLIANCE_TESTS"
    info "Compliant: $PASSED_COMPLIANCE_TESTS"
    info "Non-compliant: $FAILED_COMPLIANCE_TESTS"
    
    if [[ $FAILED_COMPLIANCE_TESTS -eq 0 ]]; then
        success "All compliance tests passed! 🎉"
        exit 0
    else
        warn "Some compliance tests failed. Review the audit report for details."
        exit 1
    fi
}

# Run main function
main "$@"
