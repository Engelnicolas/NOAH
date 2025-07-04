#!/bin/bash

# N.O.A.H - Security Testing Suite
# 
# Comprehensive security testing for the N.O.A.H infrastructure including
# vulnerability scanning, penetration testing, and compliance checks.

set -e

# Configuration
NAMESPACE="noah"
LOG_FILE="/tmp/noah_security_tests_$(date +%Y%m%d_%H%M%S).log"
REPORT_DIR="/tmp/noah_security_reports_$(date +%Y%m%d_%H%M%S)"

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
    info "Setting up security testing environment..."
    
    mkdir -p "$REPORT_DIR"
    
    # Check for required tools
    local required_tools=("kubectl" "nmap" "curl" "openssl")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            warn "$tool is not installed - some tests will be skipped"
        fi
    done
    
    success "Security testing environment ready"
}

# Container security scanning
scan_container_images() {
    info "=== Container Image Security Scanning ==="
    
    # Get all container images in use
    local images=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].spec.containers[*].image}' | tr ' ' '\n' | sort -u)
    
    info "Found container images:"
    echo "$images" | while read -r image; do
        info "  - $image"
    done
    
    # Check for latest tags (security anti-pattern)
    local latest_tags=$(echo "$images" | grep -c ":latest" || echo "0")
    if [ "$latest_tags" -gt 0 ]; then
        warn "Found $latest_tags images using 'latest' tag - this is not recommended for production"
        echo "$images" | grep ":latest" | while read -r image; do
            warn "  - $image"
        done
    else
        success "No images using 'latest' tag"
    fi
    
    # Check for official base images
    local unofficial_images=$(echo "$images" | grep -v -E "(nginx|postgres|redis|alpine|ubuntu|debian)" | wc -l)
    if [ "$unofficial_images" -gt 0 ]; then
        info "Found $unofficial_images custom/unofficial images - ensure they are from trusted sources"
    fi
    
    # Save image list for external scanning
    echo "$images" > "$REPORT_DIR/container_images.txt"
    success "Container image analysis completed"
}

# Network security testing
test_network_security() {
    info "=== Network Security Testing ==="
    
    # Test service exposure
    info "Checking service exposure..."
    
    # Get all services
    kubectl get services -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.type}{" "}{.spec.ports[*].port}{"\n"}{end}' > "$REPORT_DIR/services.txt"
    
    # Check for LoadBalancer services (external exposure)
    local lb_services=$(kubectl get services -n "$NAMESPACE" --field-selector spec.type=LoadBalancer --no-headers | wc -l)
    if [ "$lb_services" -gt 0 ]; then
        warn "Found $lb_services LoadBalancer services - ensure they are intentionally exposed"
        kubectl get services -n "$NAMESPACE" --field-selector spec.type=LoadBalancer
    fi
    
    # Check for NodePort services
    local np_services=$(kubectl get services -n "$NAMESPACE" --field-selector spec.type=NodePort --no-headers | wc -l)
    if [ "$np_services" -gt 0 ]; then
        warn "Found $np_services NodePort services - ensure they are secure"
        kubectl get services -n "$NAMESPACE" --field-selector spec.type=NodePort
    fi
    
    # Test internal network connectivity
    info "Testing internal network connectivity..."
    
    # Check if network policies are in place
    local netpols=$(kubectl get networkpolicy -n "$NAMESPACE" --no-headers | wc -l)
    if [ "$netpols" -eq 0 ]; then
        error "No NetworkPolicies found - network traffic is not restricted"
    else
        success "Found $netpols NetworkPolicies - good security practice"
    fi
    
    success "Network security testing completed"
}

# Authentication and authorization testing
test_auth_security() {
    info "=== Authentication & Authorization Security Testing ==="
    
    # Check RBAC configuration
    info "Checking RBAC configuration..."
    
    # Check for overly permissive ClusterRoles
    kubectl get clusterroles -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.rules[*].verbs[*]}{"\n"}{end}' | grep -E "\*|\bget\b.*\blist\b.*\bwatch\b.*\bcreate\b.*\bupdate\b.*\bpatch\b.*\bdelete\b" > "$REPORT_DIR/permissive_clusterroles.txt" || true
    
    if [ -s "$REPORT_DIR/permissive_clusterroles.txt" ]; then
        warn "Found potentially overly permissive ClusterRoles:"
        head -5 "$REPORT_DIR/permissive_clusterroles.txt"
    fi
    
    # Check service accounts
    local sa_count=$(kubectl get serviceaccounts -n "$NAMESPACE" --no-headers | wc -l)
    info "Found $sa_count service accounts in namespace $NAMESPACE"
    
    # Check for service accounts with cluster-admin privileges
    kubectl get clusterrolebindings -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.subjects[*].name}{"\n"}{end}' | grep -v "^system:" > "$REPORT_DIR/cluster_admin_users.txt" || true
    
    if [ -s "$REPORT_DIR/cluster_admin_users.txt" ]; then
        warn "Found non-system users with cluster-admin privileges:"
        cat "$REPORT_DIR/cluster_admin_users.txt"
    fi
    
    # Test Keycloak security
    info "Testing Keycloak security configuration..."
    
    # Check if Keycloak admin console is protected
    local keycloak_admin=$(curl -k -s -o /dev/null -w "%{http_code}" "https://keycloak.local/admin" 2>/dev/null || echo "000")
    if [ "$keycloak_admin" = "200" ]; then
        warn "Keycloak admin console appears to be accessible without authentication"
    elif [ "$keycloak_admin" = "401" ] || [ "$keycloak_admin" = "302" ]; then
        success "Keycloak admin console is properly protected"
    fi
    
    success "Authentication and authorization testing completed"
}

# TLS/SSL security testing
test_tls_security() {
    info "=== TLS/SSL Security Testing ==="
    
    # Get all ingress resources
    kubectl get ingress -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.spec.rules[*].host}{"\n"}{end}' > "$REPORT_DIR/ingress_hosts.txt"
    
    while read -r host; do
        if [ -n "$host" ]; then
            info "Testing TLS configuration for: $host"
            
            # Test TLS certificate
            if command -v openssl &> /dev/null; then
                local cert_info=$(echo | timeout 10 openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "failed")
                
                if [ "$cert_info" != "failed" ]; then
                    success "TLS certificate found for $host"
                    echo "$cert_info" >> "$REPORT_DIR/tls_certificates.txt"
                    
                    # Check certificate expiration
                    local not_after=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
                    if [ -n "$not_after" ]; then
                        local exp_date=$(date -d "$not_after" +%s 2>/dev/null || echo "0")
                        local current_date=$(date +%s)
                        local days_left=$(( (exp_date - current_date) / 86400 ))
                        
                        if [ "$days_left" -lt 30 ]; then
                            warn "Certificate for $host expires in $days_left days"
                        else
                            info "Certificate for $host expires in $days_left days"
                        fi
                    fi
                else
                    warn "Could not retrieve TLS certificate for $host"
                fi
                
                # Test TLS configuration
                local tls_result=$(timeout 10 nmap --script ssl-enum-ciphers -p 443 "$host" 2>/dev/null | grep -E "(TLSv1\.|SSLv)" || echo "")
                if echo "$tls_result" | grep -q "SSLv\|TLSv1\.0\|TLSv1\.1"; then
                    warn "Weak TLS/SSL protocols detected for $host"
                    echo "$tls_result" >> "$REPORT_DIR/weak_tls.txt"
                else
                    success "Strong TLS configuration for $host"
                fi
            fi
        fi
    done < "$REPORT_DIR/ingress_hosts.txt"
    
    success "TLS/SSL security testing completed"
}

# Pod security testing
test_pod_security() {
    info "=== Pod Security Testing ==="
    
    # Check pod security contexts
    info "Checking pod security contexts..."
    
    kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" runAsUser:"}{.spec.securityContext.runAsUser}{" runAsNonRoot:"}{.spec.securityContext.runAsNonRoot}{" readOnlyRootFilesystem:"}{.spec.containers[0].securityContext.readOnlyRootFilesystem}{"\n"}{end}' > "$REPORT_DIR/pod_security_contexts.txt"
    
    # Check for pods running as root
    local root_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.securityContext.runAsUser}{"\n"}{end}' | grep -c " 0$" || echo "0")
    if [ "$root_pods" -gt 0 ]; then
        warn "Found $root_pods pods running as root user"
    else
        success "No pods running as root user"
    fi
    
    # Check for privileged containers
    local privileged_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{range .spec.containers[*]}{$.metadata.name}{" "}{.securityContext.privileged}{"\n"}{end}{end}' | grep -c "true$" || echo "0")
    if [ "$privileged_pods" -gt 0 ]; then
        error "Found $privileged_pods privileged containers"
    else
        success "No privileged containers found"
    fi
    
    # Check for containers with capabilities
    kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{range .spec.containers[*]}{$.metadata.name}{" capabilities:"}{.securityContext.capabilities}{"\n"}{end}{end}' | grep -v "capabilities:$" > "$REPORT_DIR/container_capabilities.txt" || true
    
    if [ -s "$REPORT_DIR/container_capabilities.txt" ]; then
        warn "Found containers with additional capabilities:"
        head -5 "$REPORT_DIR/container_capabilities.txt"
    fi
    
    # Check for host network usage
    local host_network_pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.hostNetwork}{"\n"}{end}' | grep -c "true$" || echo "0")
    if [ "$host_network_pods" -gt 0 ]; then
        warn "Found $host_network_pods pods using host network"
    else
        success "No pods using host network"
    fi
    
    success "Pod security testing completed"
}

# Secrets and configuration security
test_secrets_security() {
    info "=== Secrets and Configuration Security Testing ==="
    
    # Check for secrets
    local secrets_count=$(kubectl get secrets -n "$NAMESPACE" --no-headers | wc -l)
    info "Found $secrets_count secrets in namespace $NAMESPACE"
    
    # Check for default service account token auto-mount
    local auto_mount_sa=$(kubectl get serviceaccounts -n "$NAMESPACE" -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.automountServiceAccountToken}{"\n"}{end}' | grep -c "true$" || echo "0")
    if [ "$auto_mount_sa" -gt 0 ]; then
        warn "Found $auto_mount_sa service accounts with auto-mounted tokens"
    fi
    
    # Check ConfigMaps for sensitive data patterns
    info "Scanning ConfigMaps for potential secrets..."
    kubectl get configmaps -n "$NAMESPACE" -o yaml | grep -iE "(password|secret|key|token|credential)" > "$REPORT_DIR/configmap_secrets.txt" || true
    
    if [ -s "$REPORT_DIR/configmap_secrets.txt" ]; then
        warn "Found potential secrets in ConfigMaps:"
        head -5 "$REPORT_DIR/configmap_secrets.txt"
    fi
    
    # Check for hardcoded secrets in pod environment variables
    kubectl get pods -n "$NAMESPACE" -o jsonpath='{range .items[*]}{range .spec.containers[*]}{range .env[*]}{.name}{": "}{.value}{"\n"}{end}{end}{end}' | grep -iE "(password|secret|key|token)" > "$REPORT_DIR/env_secrets.txt" || true
    
    if [ -s "$REPORT_DIR/env_secrets.txt" ]; then
        warn "Found potential secrets in environment variables:"
        head -5 "$REPORT_DIR/env_secrets.txt"
    fi
    
    success "Secrets and configuration security testing completed"
}

# Compliance checks
compliance_checks() {
    info "=== Compliance Checks ==="
    
    # CIS Kubernetes Benchmark checks
    info "Running CIS Kubernetes Benchmark checks..."
    
    # Check if Pod Security Standards are enforced
    local pss_labels=$(kubectl get namespace "$NAMESPACE" -o jsonpath='{.metadata.labels}' | grep -E "pod-security" || echo "")
    if [ -n "$pss_labels" ]; then
        success "Pod Security Standards labels found on namespace"
        echo "$pss_labels" >> "$REPORT_DIR/pss_config.txt"
    else
        warn "No Pod Security Standards labels found on namespace"
    fi
    
    # Check for admission controllers
    info "Checking admission controllers configuration..."
    # This would require cluster-admin access to check
    
    # Check for resource quotas and limits
    local resource_quotas=$(kubectl get resourcequota -n "$NAMESPACE" --no-headers | wc -l)
    if [ "$resource_quotas" -gt 0 ]; then
        success "Resource quotas configured"
    else
        warn "No resource quotas found - consider implementing to prevent resource exhaustion"
    fi
    
    # Check for limit ranges
    local limit_ranges=$(kubectl get limitrange -n "$NAMESPACE" --no-headers | wc -l)
    if [ "$limit_ranges" -gt 0 ]; then
        success "Limit ranges configured"
    else
        warn "No limit ranges found"
    fi
    
    success "Compliance checks completed"
}

# Application-specific security tests
test_application_security() {
    info "=== Application-Specific Security Testing ==="
    
    # Test Nextcloud security headers
    info "Testing Nextcloud security headers..."
    local nextcloud_headers=$(curl -k -s -I "https://nextcloud.local" 2>/dev/null || echo "")
    
    if echo "$nextcloud_headers" | grep -qi "X-Frame-Options"; then
        success "Nextcloud has X-Frame-Options header"
    else
        warn "Nextcloud missing X-Frame-Options header"
    fi
    
    if echo "$nextcloud_headers" | grep -qi "X-Content-Type-Options"; then
        success "Nextcloud has X-Content-Type-Options header"
    else
        warn "Nextcloud missing X-Content-Type-Options header"
    fi
    
    # Test GitLab security
    info "Testing GitLab security configuration..."
    local gitlab_headers=$(curl -k -s -I "https://gitlab.local" 2>/dev/null || echo "")
    
    if echo "$gitlab_headers" | grep -qi "Strict-Transport-Security"; then
        success "GitLab has HSTS header"
    else
        warn "GitLab missing HSTS header"
    fi
    
    # Test Wazuh dashboard access
    info "Testing Wazuh dashboard security..."
    local wazuh_response=$(curl -k -s -o /dev/null -w "%{http_code}" "https://wazuh.local" 2>/dev/null || echo "000")
    if [ "$wazuh_response" = "401" ] || [ "$wazuh_response" = "302" ]; then
        success "Wazuh dashboard requires authentication"
    else
        warn "Wazuh dashboard may be accessible without authentication"
    fi
    
    success "Application-specific security testing completed"
}

# Generate security report
generate_report() {
    info "Generating comprehensive security report..."
    
    local report_file="$REPORT_DIR/security_report.html"
    
    cat > "$report_file" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>N.O.A.H Security Assessment Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .critical { background-color: #ffe6e6; }
        .medium { background-color: #fff3cd; }
        .low { background-color: #e6f3ff; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 5px; font-size: 12px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>N.O.A.H Security Assessment Report</h1>
    <p><strong>Generated:</strong> $(date)</p>
    <p><strong>Namespace:</strong> $NAMESPACE</p>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <p>This report provides a comprehensive security assessment of the N.O.A.H deployment.</p>
        <h3>Key Findings:</h3>
        <ul>
            <li>Container security configuration</li>
            <li>Network security policies</li>
            <li>Authentication and authorization setup</li>
            <li>TLS/SSL configuration</li>
            <li>Pod security contexts</li>
            <li>Secrets management</li>
            <li>Compliance status</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Detailed Findings</h2>
        <h3>Container Images</h3>
        <pre>$(cat "$REPORT_DIR/container_images.txt" 2>/dev/null || echo "No data available")</pre>
        
        <h3>Service Exposure</h3>
        <pre>$(cat "$REPORT_DIR/services.txt" 2>/dev/null || echo "No data available")</pre>
        
        <h3>Pod Security Contexts</h3>
        <pre>$(cat "$REPORT_DIR/pod_security_contexts.txt" 2>/dev/null || echo "No data available")</pre>
        
        <h3>TLS Certificates</h3>
        <pre>$(cat "$REPORT_DIR/tls_certificates.txt" 2>/dev/null || echo "No data available")</pre>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <ol>
            <li><strong>High Priority:</strong>
                <ul>
                    <li>Implement NetworkPolicies for network segmentation</li>
                    <li>Ensure all containers run with non-root security contexts</li>
                    <li>Remove any privileged containers</li>
                    <li>Implement Pod Security Standards</li>
                </ul>
            </li>
            <li><strong>Medium Priority:</strong>
                <ul>
                    <li>Configure resource quotas and limits</li>
                    <li>Implement proper secrets management</li>
                    <li>Enable admission controllers</li>
                    <li>Regular certificate rotation</li>
                </ul>
            </li>
            <li><strong>Low Priority:</strong>
                <ul>
                    <li>Security headers optimization</li>
                    <li>Regular security scanning</li>
                    <li>Audit logging configuration</li>
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
    
    success "Security report generated: $report_file"
}

# Main function
main() {
    info "Starting N.O.A.H Security Testing Suite"
    info "Namespace: $NAMESPACE"
    info "Report directory: $REPORT_DIR"
    info "Log file: $LOG_FILE"
    
    setup
    
    # Run security tests
    scan_container_images
    test_network_security
    test_auth_security
    test_tls_security
    test_pod_security
    test_secrets_security
    compliance_checks
    test_application_security
    
    # Generate comprehensive report
    generate_report
    
    success "Security testing completed"
    info "Reports available in: $REPORT_DIR"
    info "Main report: $REPORT_DIR/security_report.html"
}

# Run main function
main "$@"
