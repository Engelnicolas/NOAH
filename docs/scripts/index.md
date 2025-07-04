# Scripts Documentation

This section contains documentation for the automation scripts included in the N.O.A.H project.

## Overview

The Script directory contains essential automation tools for:
- **Infrastructure Setup** - Initial system configuration
- **Deployment Management** - Service rollout and lifecycle
- **Monitoring Stack** - Observability platform management
- **Backup & Recovery** - Data protection and disaster recovery
- **Validation & Testing** - Quality assurance and compliance

## Available Scripts

### Core Infrastructure
- **`setup_infra.sh`** - Master infrastructure setup script
- **`status_check.sh`** - System health and status validation
- **`backup_restore.sh`** - Backup and recovery operations

### Helm Management
- **`deploy_and_verify_helm.sh`** - Helm chart deployment with validation
- **`uninstall_helm_charts.sh`** - Clean chart removal
- **`validate_charts.sh`** - Chart linting and testing

### Monitoring Stack
- **`deploy_monitoring_stack.sh`** - Prometheus/Grafana deployment
- **`teardown_monitoring_stack.sh`** - Clean monitoring removal

## Script Categories

### 🚀 Deployment Scripts

#### setup_infra.sh
Master infrastructure deployment script that orchestrates the complete platform setup.

**Usage:**
```bash
./setup_infra.sh [options]
```

**Options:**
- `--environment [dev|staging|prod]` - Target environment
- `--dry-run` - Validate without executing
- `--verbose` - Enable detailed logging
- `--skip-validation` - Skip pre-deployment checks

#### deploy_and_verify_helm.sh
Deploy Helm charts with comprehensive validation and rollback support.

**Usage:**
```bash
./deploy_and_verify_helm.sh [chart-name] [options]
```

### 📊 Monitoring Scripts

#### deploy_monitoring_stack.sh
Deploy complete observability stack including Prometheus, Grafana, and alerting rules.

**Features:**
- Automated metric collection setup
- Custom dashboard deployment
- Alert rule configuration
- Service discovery configuration

#### status_check.sh
Comprehensive system health validation script.

**Checks:**
- Service availability
- Resource utilization
- Network connectivity
- Security compliance
- Backup status

### 🛠️ Management Scripts

#### validate_charts.sh
Comprehensive Helm chart validation and testing.

**Validations:**
- Chart syntax and structure
- Template rendering
- Dependency resolution
- Security scanning
- Best practices compliance

#### backup_restore.sh
Data protection and disaster recovery operations.

**Operations:**
- Database backups
- Configuration exports
- Volume snapshots
- Recovery procedures
- Backup verification

## Usage Guidelines

### Prerequisites
- Bash 4.0+ with common utilities
- kubectl configured and accessible
- Helm 3.8+ installed
- Appropriate cluster access permissions

### Environment Variables
Set these variables before running scripts:

```bash
export KUBECONFIG=/path/to/kubeconfig
export NOAH_NAMESPACE=noah-prod
export NOAH_DOMAIN=noah.example.com
```

### Logging and Debugging
All scripts support standardized logging:

```bash
# Enable verbose mode
export NOAH_VERBOSE=true

# Set log level
export NOAH_LOG_LEVEL=debug

# Custom log directory
export NOAH_LOG_DIR=/var/log/noah
```

### Error Handling
Scripts implement comprehensive error handling:
- Automatic rollback on failures
- Detailed error reporting
- Recovery suggestions
- Exit code standards

## Development Guidelines

### Script Standards
- Use bash shebang: `#!/bin/bash`
- Enable strict mode: `set -euo pipefail`
- Include usage documentation
- Implement proper error handling

### Function Structure
```bash
#!/bin/bash
set -euo pipefail

# Function documentation
function deploy_service() {
    local service_name="$1"
    local namespace="${2:-default}"
    
    echo "Deploying $service_name to $namespace..."
    # Implementation
}
```

### Error Handling
```bash
# Exit on error with cleanup
trap cleanup EXIT ERR

function cleanup() {
    if [[ $? -ne 0 ]]; then
        echo "Error occurred, cleaning up..."
        # Cleanup operations
    fi
}
```

### Testing
- Include unit tests where applicable
- Test with shellcheck for syntax validation
- Validate in different environments
- Document test procedures

## Quick Reference

### Common Operations
```bash
# Full infrastructure deployment
./setup_infra.sh --environment prod

# Health check
./status_check.sh --verbose

# Chart validation
./validate_charts.sh --all

# Backup creation
./backup_restore.sh backup --target all

# Monitoring deployment
./deploy_monitoring_stack.sh --with-alerts
```

### Troubleshooting
- Check script logs in `/var/log/noah/`
- Verify environment variables
- Validate cluster connectivity
- Review QUICK_REFERENCE.md for common issues

For detailed script documentation, see the individual script files and their inline documentation.
