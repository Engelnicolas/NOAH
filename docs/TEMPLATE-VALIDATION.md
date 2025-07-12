# NOAH Helm Charts Template Validation

This document describes the template validation tools and processes for NOAH Helm charts.

## Overview

Template validation ensures that all Helm charts can be properly rendered and deployed. The validation process includes:

- **Template Rendering**: Verifying that templates can be rendered without errors
- **Scenario Testing**: Testing charts with different configurations (minimal, default, full)
- **Dependency Validation**: Ensuring all chart dependencies are properly resolved
- **YAML Syntax**: Validating generated YAML is syntactically correct
- **Resource Validation**: Checking that rendered resources are valid Kubernetes objects

## Validation Scripts

### 1. Quick Template Test (`quick-template-test.sh`)

A simple, fast validation script that tests basic template rendering for all charts.

**Usage:**
```bash
./Script/quick-template-test.sh
```

**Features:**
- ✅ Fast execution (completes in seconds)
- ✅ Tests all charts with their default values
- ✅ Handles library charts (skips them)
- ✅ Colored output with clear results
- ✅ Dependency building included

**Example Output:**
```
🚀 Quick Template Validation
============================

Setting up Helm repositories...
✅ Repositories updated

Found 11 charts to validate

Testing gitlab... ✅ Passed
Testing grafana... ✅ Passed
Testing keycloak... ✅ Passed
Testing mattermost... ✅ Passed
Testing nextcloud... ✅ Passed
Testing noah-common... ⚠️  Skipped (library chart)
Testing oauth2-proxy... ✅ Passed
Testing openedr... ✅ Passed
Testing prometheus... ✅ Passed
Testing samba4... ✅ Passed
Testing wazuh... ✅ Passed

📊 Summary:
  ✅ Passed: 10
  ❌ Failed: 0
  📊 Total:  11
  📈 Success Rate: 90%

🎉 All templates validated successfully!
```

### 2. Advanced Template Validation (`validate-templates.sh`)

A comprehensive validation script that tests multiple scenarios and provides detailed reporting.

**Usage:**
```bash
# Basic validation
./Script/validate-templates.sh

# Verbose output
./Script/validate-templates.sh --verbose

# Test specific chart
./Script/validate-templates.sh --chart mattermost

# Test specific scenario
./Script/validate-templates.sh --scenario minimal

# Generate JSON report
./Script/validate-templates.sh --output json
```

**Features:**
- ✅ Multiple test scenarios (default, minimal, full)
- ✅ Detailed error reporting and suggestions
- ✅ Performance timing and statistics
- ✅ JSON and JUnit XML output formats
- ✅ Integration with CI/CD pipelines
- ✅ Comprehensive resource validation

**Scenarios:**

**Default Scenario:**
- Uses chart's default values
- Tests standard configuration

**Minimal Scenario:**
- Disables optional features
- Minimal resource allocation
- Tests basic functionality

**Full Scenario:**
- Enables all features
- Maximum resource allocation
- Tests complete functionality

## Makefile Integration

The validation scripts are integrated into the Makefile for easy access:

```bash
# Quick template test
make quick-template-test

# Advanced template validation
make template-validate

# Full validation (includes templates)
make validate

# Show all available targets
make help
```

## CI/CD Integration

### GitHub Actions

The template validation is integrated into the GitHub Actions workflow:

```yaml
- name: Template Validation
  run: |
    cd Helm
    make quick-template-test
```

### Local Development

For local development, use the quick template test:

```bash
# Before committing changes
make quick-template-test

# For detailed validation
make template-validate
```

## Troubleshooting

### Common Issues

1. **Dependency Build Failures**
   ```
   Testing chart... ❌ (dependency build failed)
   ```
   
   **Solution:** Ensure Helm repositories are properly configured:
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm repo add elastic https://helm.elastic.co
   helm repo update
   ```

2. **Template Rendering Errors**
   ```
   Error: template: chart/templates/deployment.yaml:42:23: executing "chart/templates/deployment.yaml" at <.Values.missing.value>: nil pointer evaluating interface {}.value
   ```
   
   **Solution:** Check that all referenced values exist in values.yaml or provide default values:
   ```yaml
   # In template
   {{ .Values.missing.value | default "default-value" }}
   ```

3. **Library Chart Errors**
   ```
   Error: library charts are not installable
   ```
   
   **Solution:** Library charts are automatically skipped in the validation scripts.

### Debug Mode

For debugging template issues, use Helm's debug mode:

```bash
# Debug specific chart
helm template test-release Helm/mattermost --debug --dry-run

# Debug with custom values
helm template test-release Helm/mattermost --debug --dry-run --values custom-values.yaml
```

## Chart Development Guidelines

### Template Best Practices

1. **Use Default Values**
   ```yaml
   # Good
   {{ .Values.service.port | default 8080 }}
   
   # Bad
   {{ .Values.service.port }}
   ```

2. **Conditional Rendering**
   ```yaml
   # Good
   {{- if .Values.ingress.enabled }}
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   # ...
   {{- end }}
   ```

3. **Value Validation**
   ```yaml
   # Good
   {{- if not .Values.database.password }}
   {{- fail "Database password is required" }}
   {{- end }}
   ```

### Testing Your Templates

1. **Local Testing**
   ```bash
   # Test your chart
   helm template test-release ./my-chart --dry-run
   
   # Test with different values
   helm template test-release ./my-chart --dry-run --values test-values.yaml
   ```

2. **Integration Testing**
   ```bash
   # Run quick validation
   make quick-template-test
   
   # Run comprehensive validation
   make template-validate
   ```

## Validation Rules

### Required Elements

All charts must have:
- ✅ Valid `Chart.yaml` file
- ✅ At least one template that renders valid Kubernetes resources
- ✅ Proper value defaults for all required fields
- ✅ No template rendering errors

### Recommended Elements

Charts should have:
- ✅ Comprehensive `values.yaml` with comments
- ✅ Proper label and selector consistency
- ✅ Resource limits and requests
- ✅ Probes for health checking
- ✅ Security contexts

### Validation Checks

1. **Syntax Validation**
   - YAML syntax correctness
   - Helm template syntax

2. **Value Validation**
   - Required values presence
   - Default value appropriateness
   - Value type consistency

3. **Resource Validation**
   - Valid Kubernetes API versions
   - Proper resource specifications
   - Label and selector consistency

4. **Security Validation**
   - Security contexts defined
   - Non-root user execution
   - Resource limits specified

## Performance Optimization

### Quick Validation

For development speed, use the quick template test:
```bash
make quick-template-test  # ~10 seconds
```

### Comprehensive Validation

For thorough testing, use the advanced validation:
```bash
make template-validate    # ~2-5 minutes
```

### CI/CD Optimization

In CI/CD pipelines:
- Use quick validation for pull requests
- Use comprehensive validation for main branch
- Cache Helm repositories and dependencies

## Integration Examples

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: helm-template-validation
        name: Helm Template Validation
        entry: make quick-template-test
        language: system
        files: ^Helm/.*\.(yaml|yml)$
        pass_filenames: false
```

### GitHub Actions

```yaml
# .github/workflows/helm-validation.yml
name: Helm Validation
on: [push, pull_request]
jobs:
  template-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Helm
        uses: azure/setup-helm@v3
      - name: Template Validation
        run: |
          cd Helm
          make quick-template-test
```

## Conclusion

The template validation system ensures that all NOAH Helm charts are reliable, deployable, and maintain high quality standards. Use the quick template test for daily development and the comprehensive validation for release preparation.

For questions or issues, please refer to the troubleshooting section or create an issue in the repository.
