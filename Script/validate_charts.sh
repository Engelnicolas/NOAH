#!/bin/bash

# =======================
# NOAH - Helm Charts Validation Script
# =======================

set -euo pipefail

# Script metadata
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="validate_charts.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
HELM_CHARTS_DIR="${SCRIPT_DIR}/../Helm"
STRICT_MODE=false
FIX_ISSUES=false
VERBOSE=false

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Counters
TOTAL_CHARTS=0
VALID_CHARTS=0
CHARTS_WITH_WARNINGS=0
CHARTS_WITH_ERRORS=0

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
        echo -e "${CYAN}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

error_exit() {
    log_error "$1"
    exit 1
}

# Help function
show_help() {
    cat << EOF
${BLUE}NOAH - Helm Charts Validation Script v${SCRIPT_VERSION}${NC}

${YELLOW}USAGE:${NC}
    $0 [OPTIONS] [CHART_NAMES...]

${YELLOW}OPTIONS:${NC}
    -d, --charts-dir DIR         Helm charts directory [default: ${HELM_CHARTS_DIR}]
    -s, --strict                 Enable strict validation mode
    -f, --fix                    Attempt to fix common issues automatically
    -v, --verbose                Enable verbose logging
    -h, --help                   Show this help message

${YELLOW}EXAMPLES:${NC}
    $0                           Validate all charts
    $0 gitlab keycloak          Validate specific charts
    $0 --strict --verbose       Strict validation with detailed output
    $0 --fix                    Auto-fix common issues

${YELLOW}VALIDATION CHECKS:${NC}
    - Chart.yaml structure and required fields
    - Template syntax and Kubernetes resource validity
    - Values schema compliance
    - Dependency consistency
    - Security best practices
    - Resource limits and requests
    - Label and annotation standards

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--charts-dir)
                HELM_CHARTS_DIR="$2"
                shift 2
                ;;
            -s|--strict)
                STRICT_MODE=true
                shift
                ;;
            -f|--fix)
                FIX_ISSUES=true
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
            -*)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
            *)
                SELECTED_CHARTS+=("$1")
                shift
                ;;
        esac
    done
}

# Validate environment
validate_environment() {
    log_debug "Validating environment and dependencies..."
    
    # Check required tools
    local required_tools=("helm" "yq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error_exit "$tool is required but not installed."
        fi
    done

    # Check charts directory
    if [[ ! -d "$HELM_CHARTS_DIR" ]]; then
        error_exit "Helm charts directory not found: $HELM_CHARTS_DIR"
    fi

    log_debug "Environment validation completed successfully"
}

# Get available charts
get_available_charts() {
    local charts=()
    
    for chart_dir in "$HELM_CHARTS_DIR"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            charts+=($(basename "$chart_dir"))
        fi
    done
    
    echo "${charts[@]}"
}

# Validate Chart.yaml
validate_chart_yaml() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    local chart_file="$chart_dir/Chart.yaml"
    local issues=()
    
    log_debug "Validating Chart.yaml for $chart"
    
    if [[ ! -f "$chart_file" ]]; then
        issues+=("Chart.yaml file not found")
        return 1
    fi
    
    # Check required fields
    local required_fields=("apiVersion" "name" "version" "description")
    for field in "${required_fields[@]}"; do
        if ! yq eval ".$field" "$chart_file" &>/dev/null || [[ "$(yq eval ".$field" "$chart_file")" == "null" ]]; then
            issues+=("Missing required field: $field")
        fi
    done
    
    # Check API version
    local api_version
    api_version=$(yq eval ".apiVersion" "$chart_file" 2>/dev/null || echo "")
    if [[ "$api_version" != "v2" ]]; then
        issues+=("API version should be 'v2', found: '$api_version'")
    fi
    
    # Check chart name matches directory
    local chart_name
    chart_name=$(yq eval ".name" "$chart_file" 2>/dev/null || echo "")
    if [[ "$chart_name" != "$chart" ]]; then
        issues+=("Chart name '$chart_name' doesn't match directory name '$chart'")
    fi
    
    # Check version format
    local version
    version=$(yq eval ".version" "$chart_file" 2>/dev/null || echo "")
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        issues+=("Version should follow semantic versioning (x.y.z), found: '$version'")
    fi
    
    # Strict mode checks
    if [[ "$STRICT_MODE" == "true" ]]; then
        # Check optional but recommended fields
        local recommended_fields=("type" "appVersion" "keywords" "maintainers")
        for field in "${recommended_fields[@]}"; do
            if ! yq eval ".$field" "$chart_file" &>/dev/null || [[ "$(yq eval ".$field" "$chart_file")" == "null" ]]; then
                issues+=("Missing recommended field: $field")
            fi
        done
        
        # Check description length
        local description
        description=$(yq eval ".description" "$chart_file" 2>/dev/null || echo "")
        if [[ ${#description} -lt 10 ]]; then
            issues+=("Description is too short (minimum 10 characters)")
        fi
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo "Chart.yaml issues:"
        printf '  - %s\n' "${issues[@]}"
        return 1
    fi
    
    return 0
}

# Validate values.yaml
validate_values_yaml() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    local values_file="$chart_dir/values.yaml"
    local issues=()
    
    log_debug "Validating values.yaml for $chart"
    
    if [[ ! -f "$values_file" ]]; then
        issues+=("values.yaml file not found")
        return 1
    fi
    
    # Check YAML syntax
    if ! yq eval '.' "$values_file" &>/dev/null; then
        issues+=("Invalid YAML syntax in values.yaml")
        return 1
    fi
    
    # Check for common required sections
    local recommended_sections=("image" "service" "resources")
    for section in "${recommended_sections[@]}"; do
        if ! yq eval ".$section" "$values_file" &>/dev/null || [[ "$(yq eval ".$section" "$values_file")" == "null" ]]; then
            if [[ "$STRICT_MODE" == "true" ]]; then
                issues+=("Missing recommended section: $section")
            fi
        fi
    done
    
    # Check resource limits are defined
    if yq eval ".resources" "$values_file" &>/dev/null && [[ "$(yq eval ".resources" "$values_file")" != "null" ]]; then
        if ! yq eval ".resources.limits" "$values_file" &>/dev/null || [[ "$(yq eval ".resources.limits" "$values_file")" == "null" ]]; then
            if [[ "$STRICT_MODE" == "true" ]]; then
                issues+=("Resource limits not defined")
            fi
        fi
    fi
    
    # Check security context
    if ! yq eval ".securityContext" "$values_file" &>/dev/null || [[ "$(yq eval ".securityContext" "$values_file")" == "null" ]]; then
        if [[ "$STRICT_MODE" == "true" ]]; then
            issues+=("Security context not defined")
        fi
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo "values.yaml issues:"
        printf '  - %s\n' "${issues[@]}"
        return 1
    fi
    
    return 0
}

# Validate templates
validate_templates() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    local templates_dir="$chart_dir/templates"
    local issues=()
    
    log_debug "Validating templates for $chart"
    
    if [[ ! -d "$templates_dir" ]]; then
        issues+=("templates directory not found")
        return 1
    fi
    
    # Check for required templates
    local required_templates=("deployment.yaml" "service.yaml")
    for template in "${required_templates[@]}"; do
        if [[ ! -f "$templates_dir/$template" ]]; then
            issues+=("Missing required template: $template")
        fi
    done
    
    # Check template syntax using helm lint
    local helm_lint_output
    if helm_lint_output=$(helm lint "$chart_dir" 2>&1); then
        log_debug "Helm lint passed for $chart"
    else
        issues+=("Helm lint failed:")
        while IFS= read -r line; do
            issues+=("  $line")
        done <<< "$helm_lint_output"
    fi
    
    # Check for Kubernetes resource validation
    if command -v kubectl &> /dev/null; then
        local dry_run_output
        if dry_run_output=$(helm template "$chart" "$chart_dir" 2>&1 | kubectl apply --dry-run=client -f - 2>&1); then
            log_debug "Kubernetes validation passed for $chart"
        else
            issues+=("Kubernetes validation failed:")
            while IFS= read -r line; do
                issues+=("  $line")
            done <<< "$dry_run_output"
        fi
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo "Template issues:"
        printf '  - %s\n' "${issues[@]}"
        return 1
    fi
    
    return 0
}

# Validate dependencies
validate_dependencies() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    local chart_file="$chart_dir/Chart.yaml"
    local issues=()
    
    log_debug "Validating dependencies for $chart"
    
    # Check if dependencies are defined
    if yq eval ".dependencies" "$chart_file" &>/dev/null && [[ "$(yq eval ".dependencies" "$chart_file")" != "null" ]]; then
        local dependencies
        dependencies=$(yq eval ".dependencies[].name" "$chart_file" 2>/dev/null || true)
        
        if [[ -n "$dependencies" ]]; then
            # Check if Chart.lock exists
            if [[ ! -f "$chart_dir/Chart.lock" ]]; then
                issues+=("Chart.lock file missing (run 'helm dependency update')")
            fi
            
            # Check if charts directory exists
            if [[ ! -d "$chart_dir/charts" ]]; then
                issues+=("charts directory missing (run 'helm dependency update')")
            fi
        fi
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo "Dependency issues:"
        printf '  - %s\n' "${issues[@]}"
        return 1
    fi
    
    return 0
}

# Check security best practices
validate_security() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    local values_file="$chart_dir/values.yaml"
    local issues=()
    
    log_debug "Validating security for $chart"
    
    if [[ ! -f "$values_file" ]]; then
        return 0
    fi
    
    # Check if running as root is disabled
    if yq eval ".securityContext.runAsNonRoot" "$values_file" &>/dev/null; then
        local run_as_non_root
        run_as_non_root=$(yq eval ".securityContext.runAsNonRoot" "$values_file" 2>/dev/null || echo "false")
        if [[ "$run_as_non_root" != "true" ]]; then
            issues+=("Consider setting securityContext.runAsNonRoot: true")
        fi
    else
        if [[ "$STRICT_MODE" == "true" ]]; then
            issues+=("securityContext.runAsNonRoot not defined")
        fi
    fi
    
    # Check if readOnlyRootFilesystem is enabled
    if yq eval ".securityContext.readOnlyRootFilesystem" "$values_file" &>/dev/null; then
        local read_only_root
        read_only_root=$(yq eval ".securityContext.readOnlyRootFilesystem" "$values_file" 2>/dev/null || echo "false")
        if [[ "$read_only_root" != "true" ]]; then
            if [[ "$STRICT_MODE" == "true" ]]; then
                issues+=("Consider setting securityContext.readOnlyRootFilesystem: true")
            fi
        fi
    fi
    
    # Check for allowPrivilegeEscalation
    if yq eval ".securityContext.allowPrivilegeEscalation" "$values_file" &>/dev/null; then
        local allow_privilege_escalation
        allow_privilege_escalation=$(yq eval ".securityContext.allowPrivilegeEscalation" "$values_file" 2>/dev/null || echo "true")
        if [[ "$allow_privilege_escalation" == "true" ]]; then
            issues+=("Consider setting securityContext.allowPrivilegeEscalation: false")
        fi
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo "Security issues:"
        printf '  - %s\n' "${issues[@]}"
        return 1
    fi
    
    return 0
}

# Fix common issues
fix_chart_issues() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    
    if [[ "$FIX_ISSUES" != "true" ]]; then
        return
    fi
    
    log_debug "Attempting to fix issues for $chart"
    
    # Update dependencies if Chart.yaml has dependencies but Chart.lock is missing
    local chart_file="$chart_dir/Chart.yaml"
    if yq eval ".dependencies" "$chart_file" &>/dev/null && [[ "$(yq eval ".dependencies" "$chart_file")" != "null" ]]; then
        if [[ ! -f "$chart_dir/Chart.lock" ]]; then
            log_debug "Updating dependencies for $chart"
            (cd "$chart_dir" && helm dependency update)
        fi
    fi
    
    # Add missing _helpers.tpl if it doesn't exist
    local helpers_file="$chart_dir/templates/_helpers.tpl"
    if [[ ! -f "$helpers_file" ]]; then
        log_debug "Creating _helpers.tpl for $chart"
        cat > "$helpers_file" << 'EOF'
{{/*
Expand the name of the chart.
*/}}
{{- define "CHART_NAME.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "CHART_NAME.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "CHART_NAME.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "CHART_NAME.labels" -}}
helm.sh/chart: {{ include "CHART_NAME.chart" . }}
{{ include "CHART_NAME.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "CHART_NAME.selectorLabels" -}}
app.kubernetes.io/name: {{ include "CHART_NAME.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
EOF
        # Replace CHART_NAME with actual chart name
        sed -i "s/CHART_NAME/$chart/g" "$helpers_file"
    fi
}

# Validate single chart
validate_chart() {
    local chart="$1"
    local chart_dir="$HELM_CHARTS_DIR/$chart"
    local has_errors=false
    local has_warnings=false
    
    echo -e "\n${BLUE}🔍 Validating chart: $chart${NC}"
    echo -e "${BLUE}$(printf '=%.0s' {1..50})${NC}"
    
    # Check if chart directory exists
    if [[ ! -d "$chart_dir" ]]; then
        echo -e "${RED}❌ Chart directory not found: $chart_dir${NC}"
        return 1
    fi
    
    # Fix issues before validation if requested
    fix_chart_issues "$chart"
    
    # Validate Chart.yaml
    if validate_chart_yaml "$chart"; then
        echo -e "${GREEN}✅ Chart.yaml validation passed${NC}"
    else
        echo -e "${RED}❌ Chart.yaml validation failed${NC}"
        has_errors=true
    fi
    
    # Validate values.yaml
    if validate_values_yaml "$chart"; then
        echo -e "${GREEN}✅ values.yaml validation passed${NC}"
    else
        if [[ "$STRICT_MODE" == "true" ]]; then
            echo -e "${RED}❌ values.yaml validation failed${NC}"
            has_errors=true
        else
            echo -e "${YELLOW}⚠️ values.yaml validation warnings${NC}"
            has_warnings=true
        fi
    fi
    
    # Validate templates
    if validate_templates "$chart"; then
        echo -e "${GREEN}✅ Templates validation passed${NC}"
    else
        echo -e "${RED}❌ Templates validation failed${NC}"
        has_errors=true
    fi
    
    # Validate dependencies
    if validate_dependencies "$chart"; then
        echo -e "${GREEN}✅ Dependencies validation passed${NC}"
    else
        echo -e "${YELLOW}⚠️ Dependencies validation warnings${NC}"
        has_warnings=true
    fi
    
    # Validate security
    if validate_security "$chart"; then
        echo -e "${GREEN}✅ Security validation passed${NC}"
    else
        if [[ "$STRICT_MODE" == "true" ]]; then
            echo -e "${RED}❌ Security validation failed${NC}"
            has_errors=true
        else
            echo -e "${YELLOW}⚠️ Security validation warnings${NC}"
            has_warnings=true
        fi
    fi
    
    # Determine result
    if [[ "$has_errors" == "true" ]]; then
        echo -e "${RED}❌ Chart validation failed: $chart${NC}"
        return 1
    elif [[ "$has_warnings" == "true" ]]; then
        echo -e "${YELLOW}⚠️ Chart validation passed with warnings: $chart${NC}"
        ((CHARTS_WITH_WARNINGS++))
        return 0
    else
        echo -e "${GREEN}✅ Chart validation passed: $chart${NC}"
        ((VALID_CHARTS++))
        return 0
    fi
}

# Generate validation report
generate_validation_report() {
    local report_file="helm-validation-$(date +%Y%m%d-%H%M%S).log"
    
    {
        echo "NOAH Helm Charts Validation Report"
        echo "==========================================="
        echo "Generated: $(date)"
        echo "Validation Mode: $(if [[ "$STRICT_MODE" == "true" ]]; then echo "Strict"; else echo "Standard"; fi)"
        echo "Auto-fix: $(if [[ "$FIX_ISSUES" == "true" ]]; then echo "Enabled"; else echo "Disabled"; fi)"
        echo ""
        echo "Summary:"
        echo "  Total Charts: $TOTAL_CHARTS"
        echo "  Valid Charts: $VALID_CHARTS"
        echo "  Charts with Warnings: $CHARTS_WITH_WARNINGS"
        echo "  Charts with Errors: $CHARTS_WITH_ERRORS"
        echo ""
        echo "Success Rate: $(( (VALID_CHARTS + CHARTS_WITH_WARNINGS) * 100 / TOTAL_CHARTS ))%"
        
    } | tee "$report_file"
    
    log "Validation report saved to: $report_file"
}

# Display summary
display_summary() {
    echo -e "\n${PURPLE}📊 Validation Summary${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' {1..50})${NC}"
    echo -e "Total Charts: ${BLUE}$TOTAL_CHARTS${NC}"
    echo -e "Valid Charts: ${GREEN}$VALID_CHARTS${NC}"
    echo -e "Charts with Warnings: ${YELLOW}$CHARTS_WITH_WARNINGS${NC}"
    echo -e "Charts with Errors: ${RED}$CHARTS_WITH_ERRORS${NC}"
    echo ""
    
    local success_rate=$(( (VALID_CHARTS + CHARTS_WITH_WARNINGS) * 100 / TOTAL_CHARTS ))
    if [[ $success_rate -eq 100 ]]; then
        echo -e "Success Rate: ${GREEN}${success_rate}%${NC}"
    elif [[ $success_rate -ge 80 ]]; then
        echo -e "Success Rate: ${YELLOW}${success_rate}%${NC}"
    else
        echo -e "Success Rate: ${RED}${success_rate}%${NC}"
    fi
}

# Main function
main() {
    echo -e "${BLUE}🔍 NOAH - Helm Charts Validation v${SCRIPT_VERSION}${NC}"
    echo -e "${BLUE}================================================================${NC}"
    
    # Parse arguments
    parse_args "$@"
    
    # Validate environment
    validate_environment
    
    # Get charts to validate
    local charts_to_validate=()
    if [[ -n "${SELECTED_CHARTS:-}" ]]; then
        charts_to_validate=("${SELECTED_CHARTS[@]}")
        log "Validating selected charts: ${charts_to_validate[*]}"
    else
        IFS=' ' read -ra charts_to_validate <<< "$(get_available_charts)"
        log "Validating all available charts: ${charts_to_validate[*]}"
    fi
    
    if [[ ${#charts_to_validate[@]} -eq 0 ]]; then
        log_warn "No charts found to validate"
        exit 0
    fi
    
    TOTAL_CHARTS=${#charts_to_validate[@]}
    
    # Validate each chart
    local failed_charts=()
    for chart in "${charts_to_validate[@]}"; do
        if ! validate_chart "$chart"; then
            failed_charts+=("$chart")
            ((CHARTS_WITH_ERRORS++))
        fi
    done
    
    # Display summary
    display_summary
    
    # Generate report
    generate_validation_report
    
    # Exit with appropriate code
    if [[ ${#failed_charts[@]} -eq 0 ]]; then
        log_success "All charts validated successfully!"
        exit 0
    else
        log_error "Validation failed for charts: ${failed_charts[*]}"
        exit 1
    fi
}

# Initialize arrays
SELECTED_CHARTS=()

# Execute main function
main "$@"
