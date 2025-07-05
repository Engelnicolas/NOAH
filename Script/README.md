# NOAH Scripts - Unified CLI Interface

This directory contains the simplified, unified script interface for the NOAH infrastructure platform. The scripts have been consolidated into a powerful CLI tool that provides all functionality through a single entry point.

## 🚀 Quick Start

### Main CLI Interface
```bash
# Show all available commands
./noah help

# Validate the entire project
./noah validate

# Fix common issues automatically
./noah fix --verbose

# Check infrastructure status
./noah infra status

# Deploy infrastructure
./noah infra deploy --environment dev
```

## 📋 Unified Scripts Overview

### 1. `noah` - Main CLI Entry Point
**Single command interface for all NOAH operations**

**Usage:**
```bash
./noah COMMAND [OPTIONS]
```

**Available Commands:**
- `validate` - Project validation (YAML, Ansible, Helm, scripts)
- `fix` - Automatically fix common issues
- `infra` - Infrastructure management
- `monitoring` - Monitoring stack management
- `backup` - Backup and restore operations

### 2. `noah-validate` - Unified Validation
**Comprehensive project validation with scope control**

**Features:**
- YAML syntax validation
- Ansible playbook validation  
- Helm chart validation
- Shell script validation
- Project structure validation
- Auto-fix capability

**Usage:**
```bash
./noah validate                    # Validate everything
./noah validate --scope yaml      # Only YAML files
./noah validate --scope helm      # Only Helm charts
./noah validate --fix             # Validate and fix issues
./noah validate --verbose         # Detailed output
```

### 3. `noah-fix.py` - Unified Fix Tool
**Automatically fix common code issues**

**Features:**
- YAML syntax fixing (trailing spaces, indentation)
- Shell script fixing (shebangs, syntax)
- MkDocs configuration validation
- Dry-run mode for safe testing
- File type filtering

**Usage:**
```bash
./noah fix                        # Fix all issues
./noah fix --dry-run             # Show what would be fixed
./noah fix --types yaml          # Only fix YAML files
./noah fix specific-file.yml     # Fix specific file
```

### 4. `noah-infra` - Infrastructure Management
**Complete infrastructure lifecycle management**

**Features:**
- Infrastructure setup with prerequisites
- Helm chart deployment
- Status monitoring and health checks
- Infrastructure teardown
- Environment management (dev/staging/prod)
- Dry-run mode for safe operations

**Usage:**
```bash
./noah infra status                    # Check current status
./noah infra setup --environment dev   # Set up dev environment
./noah infra deploy --verbose          # Deploy with verbose output
./noah infra teardown --dry-run        # Show what would be removed
```

### 5. `noah-monitoring` - Monitoring Management
**Monitoring stack lifecycle management**

**Features:**
- Deploy Prometheus and Grafana
- Monitor stack health and status
- Teardown monitoring components
- Environment-specific deployments

**Usage:**
```bash
./noah monitoring deploy             # Deploy monitoring stack
./noah monitoring status             # Check monitoring status
./noah monitoring teardown           # Remove monitoring stack
```

#### 2. `deploy_and_verify_helm.sh` - Helm Deployment
**Comprehensive Helm chart deployment with verification**

**Features:**
- Parallel and sequential deployment modes
- Environment-specific values file support
- Comprehensive health checks and verification
- Detailed deployment reporting
- Custom values file support
- Upgrade and install modes
- Dry-run capability

**Usage:**
```bash
# Deploy all charts
./deploy_and_verify_helm.sh

# Deploy specific charts
./deploy_and_verify_helm.sh --charts gitlab,keycloak

# Production upgrade with custom values
./deploy_and_verify_helm.sh --environment prod --upgrade --values-file custom.yaml

# Dry run with detailed output
./deploy_and_verify_helm.sh --dry-run --verbose
```

**Options:**
- `-e, --environment ENV`: Target environment
- `-c, --charts CHART1,CHART2`: Deploy specific charts only
- `-u, --upgrade`: Upgrade existing deployments
- `-d, --dry-run`: Perform dry run
- `-v, --verbose`: Enable verbose logging
- `-p, --parallel`: Deploy charts in parallel

#### 3. `uninstall_helm_charts.sh` - Helm Uninstall
**Safe and comprehensive Helm chart removal**

**Features:**
- Selective chart uninstallation
- Data preservation options
- Automatic backup creation
- Namespace cleanup
- Force deletion mode
- Comprehensive reporting

**Usage:**
```bash
# Uninstall all charts with data preservation
./uninstall_helm_charts.sh --preserve-data

# Uninstall specific charts
./uninstall_helm_charts.sh --charts gitlab,prometheus --force

# Dry run to see what would be removed
./uninstall_helm_charts.sh --dry-run --verbose
```

### Monitoring Scripts

#### 4. `deploy_monitoring_stack.sh` - Monitoring Deployment
**Production-ready monitoring stack deployment**

**Features:**
- Prometheus with custom configuration
- Grafana with pre-configured dashboards
- Alertmanager integration
- Environment-specific resource allocation
- Custom retention policies
- Security configurations

**Usage:**
```bash
# Deploy monitoring for production
./deploy_monitoring_stack.sh --environment prod --retention 30d

# Custom namespace and password
./deploy_monitoring_stack.sh --namespace observability --grafana-password mypass

# Disable optional components
./deploy_monitoring_stack.sh --no-alertmanager --no-node-exporter
```

#### 5. `teardown_monitoring_stack.sh` - Monitoring Cleanup
**Safe monitoring stack removal**

**Features:**
- Data preservation options
- Configuration backup
- Gradual teardown process
- Comprehensive reporting

**Usage:**
```bash
# Teardown with data preservation
./teardown_monitoring_stack.sh --preserve-data

# Force teardown
./teardown_monitoring_stack.sh --force

# Dry run
./teardown_monitoring_stack.sh --dry-run
```

### Utility Scripts

#### 6. `status_check.sh` - Comprehensive Status Check
**Detailed system and service status monitoring**

**Features:**
- Helm release status
- Kubernetes deployment health
- Resource usage monitoring
- Network information
- Service endpoint discovery
- Multiple output formats (table/json/yaml)

**Usage:**
```bash
# Basic status check
./status_check.sh

# Detailed status with logs for failed services
./status_check.sh --detailed --show-logs

# JSON output for integration
./status_check.sh --format json

# Health check disabled
./status_check.sh --no-health-check
```

#### 7. `backup_restore.sh` - Backup and Restore
**Comprehensive backup and restore solution**

**Features:**
- Helm release backup
- Kubernetes resource backup
- Persistent volume data backup
- Incremental and full backups
- Encryption support
- Cross-environment restore

**Usage:**
```bash
# Create full backup
./backup_restore.sh --action backup --environment prod

# Backup specific charts with secrets
./backup_restore.sh --action backup --charts gitlab,keycloak --include-secrets

# List available backups
./backup_restore.sh --action list

# Restore from backup
./backup_restore.sh --action restore --backup-name backup-20231201-120000
```

#### 8. `validate_charts.sh` - Helm Chart Validation
**Comprehensive Helm chart validation and linting**

**Features:**
- Chart.yaml validation
- Template syntax checking
- Values schema validation
- Security best practices check
- Dependency validation
- Auto-fix common issues

**Usage:**
```bash
# Validate all charts
./validate_charts.sh

# Strict validation with auto-fix
./validate_charts.sh --strict --fix

# Validate specific charts
./validate_charts.sh gitlab keycloak --verbose
```

### Makefile - Unified Interface

The enhanced `Makefile` provides a unified interface for all operations:

**Features:**
- Dependency checking
- Configuration display
- Environment-specific targets
- Comprehensive help system
- Color-coded output

**Usage:**
```bash
# Show all available targets
make help

# Deploy development environment
make dev-deploy

# Deploy production environment
make prod-deploy

# Check deployment status
make status

# Create backup
make backup

# Run validation
make validate
```

## 🔧 Configuration

### Environment Variables

The scripts support the following environment variables:

```bash
# Environment settings
export ENVIRONMENT=prod                    # dev/staging/prod
export NAMESPACE_PREFIX=noah         # Kubernetes namespace prefix
export HELM_TIMEOUT=10m                   # Helm operation timeout

# Backup settings
export BACKUP_LOCATION=/backups           # Backup storage location
export COMPRESS_BACKUP=true               # Enable backup compression
export ENCRYPT_BACKUP=true                # Enable backup encryption

# Monitoring settings
export PROMETHEUS_RETENTION=30d           # Prometheus data retention
export GRAFANA_PASSWORD=admin             # Grafana admin password
```

### Configuration Files

Scripts automatically detect and use environment-specific configuration files:

```
Helm/
├── chart-name/
│   ├── values.yaml              # Default values
│   ├── values-dev.yaml          # Development overrides
│   ├── values-staging.yaml      # Staging overrides
│   └── values-prod.yaml         # Production overrides
```

## 🛡️ Security Features

### Data Protection
- Secrets excluded from backups by default
- Encryption support for sensitive backups
- Secure temporary file handling
- Non-root user execution

### Access Control
- Environment-specific access controls
- Kubernetes RBAC integration
- Service account management
- Network policy enforcement

### Validation
- Input validation and sanitization
- Configuration validation
- Resource limit enforcement
- Security context validation

## 📊 Monitoring and Logging

### Logging Features
- Structured logging with timestamps
- Log level control (INFO/WARN/ERROR/DEBUG)
- Color-coded output for better visibility
- Comprehensive error reporting

### Monitoring Integration
- Prometheus metrics collection
- Grafana dashboard provisioning
- Alertmanager rule configuration
- Health check endpoints

## 🔄 Backup and Recovery

### Backup Types
- **Configuration Backup**: Helm values, ConfigMaps, Secrets
- **Resource Backup**: Kubernetes manifests and definitions
- **Data Backup**: Persistent volume data
- **Full Backup**: Complete system state

### Recovery Features
- Cross-environment restore capability
- Selective restore options
- Backup validation and verification
- Recovery testing procedures

## 🚨 Error Handling

### Robust Error Handling
- Comprehensive error detection
- Graceful failure handling
- Automatic retry mechanisms
- Detailed error reporting

### Recovery Procedures
- Automatic rollback capabilities
- State validation checks
- Recovery documentation
- Emergency procedures

## 📈 Performance Features

### Optimization
- Parallel deployment support
- Resource usage monitoring
- Performance profiling
- Bottleneck identification

### Scalability
- Multi-environment support
- Resource scaling automation
- Load balancing configuration
- Performance tuning

## 🔍 Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix script permissions
   chmod +x Script/*.sh
   ```

2. **Kubernetes Connection Issues**
   ```bash
   # Verify cluster connection
   kubectl cluster-info
   ```

3. **Helm Repository Issues**
   ```bash
   # Update Helm repositories
   helm repo update
   ```

4. **Resource Conflicts**
   ```bash
   # Check existing resources
   ./status_check.sh --detailed
   ```

### Debug Mode

Enable debug mode for detailed troubleshooting:
```bash
# Enable verbose logging for any script
./script_name.sh --verbose

# Enable debug mode
export DEBUG=true
```

## 🎯 Best Practices

### Development Workflow
1. Use `--dry-run` for testing changes
2. Validate charts before deployment
3. Monitor resource usage
4. Create backups before major changes

### Production Deployment
1. Use staging environment for testing
2. Enable all security features
3. Configure monitoring and alerting
4. Document all configurations

### Maintenance
1. Regular backup schedules
2. Resource usage monitoring
3. Security updates
4. Performance optimization

## 📚 Advanced Usage

### Custom Integrations
The scripts can be integrated with CI/CD pipelines:

```yaml
# GitLab CI example
deploy:
  script:
    - ./setup_infra.sh --environment prod
    - ./deploy_and_verify_helm.sh --environment prod --upgrade
    - ./status_check.sh --format json > deployment-status.json
```

### Automation
Set up automated deployments and monitoring:

```bash
# Cron job for automated backups
0 2 * * * /path/to/backup_restore.sh --action backup --environment prod

# Automated health checks
*/5 * * * * /path/to/status_check.sh --no-health-check --format json
```

## 🆘 Support

For issues and support:
1. Check the troubleshooting section
2. Review script logs with `--verbose`
3. Validate configurations with `validate_charts.sh`
4. Use `--dry-run` to test changes safely

## 📝 Change Log

### Version 2.0.0 (Current)
- Complete rewrite of all scripts
- Added comprehensive error handling
- Implemented advanced configuration management
- Added backup and restore functionality
- Enhanced security features
- Improved logging and monitoring
- Added validation and testing capabilities

---

**Note**: This enhanced script section provides production-ready automation for the NOAH platform. All scripts include comprehensive help documentation accessible via the `--help` option.
