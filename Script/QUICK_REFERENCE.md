# NOAH - Quick Reference Guide

## 🚀 Quick Start Commands

### Main CLI Interface
```bash
# Show all available commands
./noah help

# Check project status
./noah validate

# Fix common issues
./noah fix --verbose
```

### Infrastructure Management
```bash
# Check infrastructure status
./noah infra status

# Setup development environment
./noah infra setup --environment dev

# Deploy to development
./noah infra deploy --environment dev --verbose

# Deploy to production
./noah infra deploy --environment prod

# Teardown (with safety check)
./noah infra teardown --dry-run
./noah infra teardown --environment dev
```

### Validation and Fixing
```bash
# Validate everything
./noah validate

# Validate specific components
./noah validate --scope yaml
./noah validate --scope ansible
./noah validate --scope helm
./noah validate --scope scripts

# Fix issues automatically
./noah fix
./noah fix --dry-run              # See what would be fixed
./noah fix --types yaml          # Only fix YAML files
./noah fix specific-file.yml     # Fix specific file
```

### Monitoring Stack
```bash
# Deploy monitoring (Prometheus + Grafana)
./noah monitoring deploy

# Check monitoring status
./noah monitoring status

# Remove monitoring stack
./noah monitoring teardown
```
# Deploy monitoring stack
make monitoring-up

# Check system status
make status

# Detailed status check
./status_check.sh --detailed --show-logs
```

### Backup & Restore
```bash
# Create backup
make backup

# List backups
./backup_restore.sh --action list

# Restore from backup
./backup_restore.sh --action restore --backup-name backup-name
```

### Maintenance
```bash
# Validate all charts
make validate

# Clean environment
make clean

# Update deployments
make helm-upgrade
```

## 🎯 Common Workflows

### 1. Initial Development Environment Setup
```bash
# 1. Setup infrastructure
./setup_infra.sh --environment dev --cluster-type minikube

# 2. Deploy services
./deploy_and_verify_helm.sh --environment dev

# 3. Deploy monitoring
./deploy_monitoring_stack.sh --environment dev

# 4. Check status
./status_check.sh --detailed
```

### 2. Production Deployment
```bash
# 1. Validate charts
./validate_charts.sh --strict

# 2. Create backup (if updating existing)
./backup_restore.sh --action backup --environment prod

# 3. Deploy/upgrade services
./deploy_and_verify_helm.sh --environment prod --upgrade

# 4. Deploy monitoring
./deploy_monitoring_stack.sh --environment prod --retention 30d

# 5. Verify deployment
./status_check.sh --environment prod --detailed
```

### 3. Disaster Recovery
```bash
# 1. List available backups
./backup_restore.sh --action list

# 2. Restore from backup
./backup_restore.sh --action restore --backup-name backup-20231201

# 3. Verify restoration
./status_check.sh --detailed

# 4. Test services
make test
```

## 📊 Monitoring Access

### Service URLs (Port Forward)
```bash
# Grafana
kubectl port-forward -n monitoring svc/grafana 3000:80
# Access: http://localhost:3000 (admin/admin)

# Prometheus
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Access: http://localhost:9090

# Application services
kubectl port-forward -n noah-gitlab svc/gitlab 8080:80
```

### Service Discovery
```bash
# Get all service endpoints
./status_check.sh --format json | jq '.services[].external_ip'

# Get specific service info
kubectl get svc --all-namespaces | grep LoadBalancer
```

## 🔧 Configuration Reference

### Environment Variables
```bash
# Core settings
export ENVIRONMENT=prod
export NAMESPACE_PREFIX=noah
export HELM_TIMEOUT=10m

# Backup settings
export BACKUP_LOCATION=/backups
export COMPRESS_BACKUP=true

# Monitoring settings
export PROMETHEUS_RETENTION=30d
export GRAFANA_PASSWORD=secure-password
```

### Make Targets
```bash
make help              # Show all available targets
make check-deps        # Check dependencies
make show-config       # Display current configuration
make dev-deploy        # Deploy development environment
make staging-deploy    # Deploy staging environment
make prod-deploy       # Deploy production environment
make status            # Show deployment status
make backup            # Create backup
make restore           # Restore from backup
make clean             # Clean all resources
```

## 🛠️ Troubleshooting

### Common Issues

**Permission Denied**
```bash
chmod +x Script/*.sh
```

**Kubernetes Connection**
```bash
kubectl cluster-info
kubectl config current-context
```

**Helm Issues**
```bash
helm repo update
helm list --all-namespaces
```

**Resource Conflicts**
```bash
./status_check.sh --show-logs
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Debug Mode
```bash
# Enable verbose logging
./script_name.sh --verbose

# Dry run mode
./script_name.sh --dry-run

# Debug environment variable
export DEBUG=true
```

## 🔍 Health Checks

### Quick Health Check
```bash
# Basic status
./status_check.sh

# Detailed with logs
./status_check.sh --detailed --show-logs

# JSON output for automation
./status_check.sh --format json
```

### Resource Monitoring
```bash
# Node resources
kubectl top nodes

# Pod resources
kubectl top pods --all-namespaces

# Storage usage
kubectl get pvc --all-namespaces
```

## 📋 Maintenance Tasks

### Regular Maintenance
```bash
# Weekly backup
./backup_restore.sh --action backup --environment prod

# Chart validation
./validate_charts.sh --strict

# Resource cleanup
kubectl delete pods --field-selector status.phase=Succeeded --all-namespaces

# Log rotation
kubectl logs --previous deployment/app -n namespace
```

### Updates and Upgrades
```bash
# Update Helm repositories
helm repo update

# Upgrade deployments
./deploy_and_verify_helm.sh --upgrade --environment prod

# Validate after update
./validate_charts.sh && ./status_check.sh --detailed
```

## 🚨 Emergency Procedures

### Service Down
```bash
# Check status
./status_check.sh --show-logs

# Restart deployment
kubectl rollout restart deployment/service-name -n namespace

# Scale deployment
kubectl scale deployment/service-name --replicas=3 -n namespace
```

### Data Loss
```bash
# List backups
./backup_restore.sh --action list

# Restore specific service
./backup_restore.sh --action restore --charts service-name --backup-name backup-name
```

### Complete Failure
```bash
# Full restore
./backup_restore.sh --action restore --backup-name latest-backup

# Redeploy monitoring
./deploy_monitoring_stack.sh --environment prod

# Verify restoration
./status_check.sh --detailed
```

## 📱 Mobile/Remote Access

### Port Forwarding
```bash
# Forward all services (background)
kubectl port-forward -n monitoring svc/grafana 3000:80 &
kubectl port-forward -n noah-gitlab svc/gitlab 8080:80 &
```

### Ingress Access
```bash
# Check ingress configurations
kubectl get ingress --all-namespaces

# Get ingress IPs
kubectl get ingress --all-namespaces -o wide
```

## 🎯 Performance Optimization

### Resource Tuning
```bash
# Check resource usage
./status_check.sh --detailed

# Update resource limits
# Edit values files and redeploy
./deploy_and_verify_helm.sh --upgrade
```

### Scaling
```bash
# Manual scaling
kubectl scale deployment/app --replicas=5 -n namespace

# Auto-scaling (if HPA configured)
kubectl get hpa --all-namespaces
```

---

**💡 Tip**: Use `make help` for the most up-to-date list of available commands and options.
