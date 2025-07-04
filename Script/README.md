# OpenInfra - Enhanced Script Section

This directory contains production-ready deployment and automation scripts for the OpenInfra infrastructure platform. All scripts have been completely enhanced with robust error handling, comprehensive logging, configuration management, and advanced operational features.

## 📋 Overview

The enhanced script section provides a complete suite of automation tools for:
- Infrastructure setup and configuration
- Helm chart deployment and management
- Monitoring stack deployment
- Backup and restore operations
- System validation and health checks
- Comprehensive status monitoring

## 🚀 Scripts Overview

### Core Deployment Scripts

#### 1. `setup_infra.sh` - Infrastructure Setup
**Enhanced production-ready infrastructure setup script**

**Features:**
- Multi-OS support (Fedora, Ubuntu, Debian, Arch)
- Multiple Kubernetes cluster types (Minikube, Kind, K3s, existing)
- Comprehensive dependency management
- System requirements validation
- Environment-specific configuration
- Automatic service enablement and configuration

**Usage:**
```bash
# Basic setup
./setup_infra.sh

# Production setup with existing cluster
./setup_infra.sh --environment prod --cluster-type existing

# Development setup with Kind
./setup_infra.sh --environment dev --cluster-type kind --verbose

# Force reinstall all components
./setup_infra.sh --force-reinstall --verbose
```

**Options:**
- `-e, --environment ENV`: Target environment (dev/staging/prod)
- `-c, --cluster-type TYPE`: Cluster type (minikube/kind/k3s/existing)
- `-k, --kube-version VERSION`: Kubernetes version
- `-f, --force-reinstall`: Force reinstall existing components
- `-v, --verbose`: Enable detailed logging

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
export NAMESPACE_PREFIX=openinfra         # Kubernetes namespace prefix
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

**Note**: This enhanced script section provides production-ready automation for the OpenInfra platform. All scripts include comprehensive help documentation accessible via the `--help` option.
