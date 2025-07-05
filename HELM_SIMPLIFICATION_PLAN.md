# NOAH Helm Charts Simplification Plan

## Overview
The current Helm charts in the NOAH project are comprehensive but overly complex with extensive configurations that make them difficult to maintain and use. This document outlines a simplification strategy to modernize and streamline the Helm repository.

## Current Issues Identified

### 1. Configuration Complexity
- **Values files are too large**: 400-800+ lines per chart
- **Excessive documentation**: More comments than actual configuration
- **Over-parameterization**: Too many configuration options creating complexity
- **Redundant configurations**: Similar patterns repeated across charts

### 2. Template Complexity
- **Duplicate helper functions**: Similar `_helpers.tpl` patterns across all charts
- **Over-engineering**: Complex conditional logic in templates
- **Inconsistent naming**: Different patterns across charts
- **Missing standardization**: No common template library

### 3. Structure Issues
- **Chart dependencies**: Complex interdependencies between charts
- **Resource management**: Inconsistent resource definitions
- **Security policies**: Scattered security configurations
- **Monitoring setup**: Complex ServiceMonitor configurations

## Simplification Strategy

### Phase 1: Common Template Library
Create a shared library chart with common templates and helpers:

```
Helm/
├── noah-common/           # New: Shared library chart
│   ├── Chart.yaml
│   └── templates/
│       ├── _helpers.tpl   # Common helper functions
│       ├── _labels.tpl    # Standard label templates
│       ├── _security.tpl  # Security context templates
│       └── _monitoring.tpl # ServiceMonitor templates
└── [existing charts]/
```

### Phase 2: Simplified Values Structure
Reduce values.yaml complexity:

**Before** (400+ lines):
```yaml
# Extensive documentation
# Multiple environment configurations
# Redundant settings
# Complex nested structures
```

**After** (50-100 lines):
```yaml
# Essential configuration only
# Environment-specific overrides in separate files
# Sensible defaults
# Simplified structure
```

### Phase 3: Chart Consolidation
Group related charts into umbrella charts:

```
Helm/
├── noah-common/              # Shared templates
├── noah-core/               # Core infrastructure (Keycloak, Samba4)
├── noah-collaboration/      # Collaboration (GitLab, Nextcloud, Mattermost)
├── noah-security/          # Security stack (Wazuh, OpenEDR)
├── noah-monitoring/        # Monitoring (Prometheus, Grafana)
└── noah-proxy/             # Networking (OAuth2-Proxy, Ingress)
```

### Phase 4: Environment-Specific Values
Create environment-specific value files:

```
values/
├── values-dev.yaml         # Development overrides
├── values-staging.yaml     # Staging overrides
├── values-prod.yaml        # Production overrides
└── values-minimal.yaml     # Minimal installation
```

## Implementation Steps

### Step 1: Create Common Library Chart
### Step 2: Simplify Individual Charts  
### Step 3: Create Umbrella Charts
### Step 4: Update Documentation
### Step 5: Update CLI and Automation

## Expected Benefits

1. **Reduced Complexity**: 80% reduction in configuration lines
2. **Better Maintainability**: Shared templates reduce duplication
3. **Easier Deployment**: Simplified values and umbrella charts
4. **Consistent Patterns**: Standardized approach across all charts
5. **Faster Development**: Reusable components speed up new charts

## Success Metrics

- Values file size reduced from 400+ to <100 lines per chart
- Template duplication reduced by 70%
- Deployment time reduced by 50%
- Documentation clarity improved
- User adoption increased
