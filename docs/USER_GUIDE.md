# N.O.A.H User Guide - Complete Deployment Guide

## 🎯 Overview

This comprehensive guide walks you through deploying the complete N.O.A.H (Next Open-source Architecture Hub) infrastructure platform using the **unified CLI interface** with **enhanced error logging** and **flexible security modes**.

N.O.A.H provides a production-ready, secure, and scalable open-source infrastructure stack with identity management, collaboration tools, monitoring, and security components. The latest version includes comprehensive error logging, root user deployment support, and simplified troubleshooting capabilities.

---

## 🚀 Quick Start (5 Minutes)

### Fastest Path to Running N.O.A.H

```bash
# Clone repository
git clone https://github.com/your-org/noah.git
cd noah

# Validate and fix any issues
./Script/noah validate --fix

# Deploy infrastructure with root security (recommended for compatibility)
./Script/noah infra deploy --security root --verbose

# Monitor deployment progress
./Script/noah-logs tail

# Verify deployment
./Script/noah infra status

# Access your services at:
# - Keycloak: kubectl port-forward svc/keycloak 8080:8080
# - Nextcloud: kubectl port-forward svc/nextcloud 8081:80
# - Mattermost: kubectl port-forward svc/mattermost 8082:8065
# - Grafana: kubectl port-forward svc/grafana 3000:3000
```

---

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, or similar)
- **CPU**: 4 cores
- **RAM**: 16GB
- **Storage**: 100GB available space
- **Network**: Internet access for initial setup

**Production Requirements:**
- **CPU**: 8+ cores
- **RAM**: 32GB+
- **Storage**: 500GB+ SSD storage
- **Network**: Dedicated network with load balancer

### Required Software

**Core Tools:**
```bash
# Check if tools are installed
./Script/noah validate --scope dependencies

# Required tools (auto-checked):
- Docker >= 20.10
- Kubernetes (kubectl) >= 1.24
- Helm >= 3.10
- Python >= 3.8
- Git >= 2.30
- Make
```

**Optional Tools:**
- Terraform >= 1.3 (for infrastructure provisioning)
- Ansible >= 2.12 (for configuration management)

### Quick Tool Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io kubectl helm python3 python3-pip git make

# CentOS/RHEL/Fedora
sudo dnf install -y docker kubectl helm python3 python3-pip git make

# macOS (using Homebrew)
brew install docker kubectl helm python3 git make
```

---

## 🏗️ Installation and Deployment

N.O.A.H now supports simplified deployment with enhanced security modes and comprehensive error logging:

### Security Modes

N.O.A.H supports three security modes:

1. **Root Mode** (`--security root`) - **Recommended**
   - Applications run as root user (UID 0)
   - Maximum compatibility with complex applications like GitLab
   - Required capabilities for full functionality
   - Default mode for simplified deployment

2. **Minimal Mode** (`--security minimal`)
   - Non-root user with limited privileges
   - Reduced resource allocation
   - Basic functionality only

3. **Secure Mode** (`--security secure`)
   - Strict security with non-root users
   - Read-only root filesystem
   - Network policies enabled
   - Production-ready security posture

### Deployment Methods

#### Method 1: Kubernetes Deployment (Default)

**Best for**: All environments with automatic error logging

```bash
# 1. Ensure Kubernetes cluster is available
kubectl cluster-info

# 2. Deploy with root security mode (recommended)
./Script/noah infra deploy --security root --verbose

# 3. Monitor deployment in real-time
./Script/noah-logs tail

# 4. Check status
./Script/noah infra status

# 5. View any errors
./Script/noah-logs errors
```

#### Method 2: Chart-Default Deployment

**Uses each chart's default values.yaml with security overrides**

```bash
# Deploy using chart defaults with root security
./Script/noah infra deploy --use-chart-defaults --security root

# Deploy with minimal security
./Script/noah infra deploy --use-chart-defaults --security minimal
```

#### Method 3: Traditional Ansible Deployment

**Best for**: Existing VM infrastructure

```bash
# Configure inventory
cd Ansible
cp inventory/example inventory/custom
vim inventory/custom/hosts

# Deploy with Ansible
ansible-playbook -i inventory/custom main.yml
```

---

## 🔧 Configuration and Values

## 🔧 Configuration and Values

### Security Context Configuration

N.O.A.H now includes flexible security context management:

```yaml
# Root user configuration (values-root.yaml)
securityContext:
  runAsUser: 0
  runAsGroup: 0
  fsGroup: 0
  readOnlyRootFilesystem: false
  allowPrivilegeEscalation: true

# Secure configuration (values-secure.yaml)
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

### Built-in Values Files

```
Helm/values/
├── values-root.yaml      # Root user deployment (default)
├── values-minimal.yaml   # Minimal resources, basic security
├── values-secure.yaml    # High security, production-ready
├── values-gitlab.yaml    # GitLab-specific optimizations
└── Chart-specific values.yaml in each chart directory
```

### Custom Configuration

You can override any setting using command-line parameters:

```bash
# Deploy with custom security settings
./Script/noah infra deploy \
  --set securityContext.runAsUser=1001 \
  --set securityContext.runAsGroup=1001

# Deploy with specific chart configuration
helm upgrade --install gitlab ./Helm/gitlab \
  --namespace noah \
  --set gitlab.rootPassword=mysecretpassword
```

---

## 🚀 Step-by-Step Deployment

### Step 1: Repository Setup

```bash
# Clone the repository
git clone https://github.com/your-org/noah.git
cd noah

# Make scripts executable
chmod +x Script/noah*

# Validate project structure
./Script/noah validate
```

### Step 2: Environment Preparation

```bash
# Check system dependencies
./Script/noah validate --scope dependencies

# Fix any validation issues
./Script/noah fix --dry-run  # Preview fixes
./Script/noah fix            # Apply fixes

# Verify readiness
./Script/noah infra status
```

### Step 3: Infrastructure Deployment

#### Quick Deployment (Recommended)

```bash
# Deploy with root security mode for maximum compatibility
./Script/noah infra deploy --security root --verbose

# Monitor deployment progress in real-time
./Script/noah-logs tail

# Check final status
./Script/noah infra status
```

#### Advanced Deployment Options

```bash
# Deploy with chart defaults
./Script/noah infra deploy --use-chart-defaults --security root

# Deploy with external values file
./Script/noah infra deploy --security minimal

# Dry run to see what would be deployed
./Script/noah infra deploy --dry-run --verbose
```

### Step 4: Service Access

#### Port Forwarding (Development)

```bash
# Access GitLab
kubectl port-forward svc/gitlab-gitlab-simple 8080:80 -n noah
# Access: http://localhost:8080 (root/noah123)

# Access Keycloak
kubectl port-forward svc/keycloak 8081:8080 -n noah
# Access: http://localhost:8081/admin (admin/admin)

# Access Nextcloud
kubectl port-forward svc/nextcloud 8082:80 -n noah
# Access: http://localhost:8082 (admin/changeme)

# Access Grafana
kubectl port-forward svc/grafana 3000:3000 -n noah
# Access: http://localhost:3000 (admin/prom-operator)
```

#### Service Configuration

```bash
# List all services
kubectl get services -n noah

# Get service details
kubectl describe service gitlab-gitlab-simple -n noah

# Check service endpoints
kubectl get endpoints -n noah
```

---

## 📊 Enhanced Logging and Troubleshooting

### Comprehensive Error Logging

N.O.A.H now includes advanced error logging and analysis:

```bash
# View deployment logs in real-time
./Script/noah-logs tail

# Check recent error logs
./Script/noah-logs errors

# View latest deployment log
./Script/noah-logs latest

# Show log summary and disk usage
./Script/noah-logs summary

# Clean old logs (keeps last 10 deployments, 20 errors)
./Script/noah-logs clean
```

### Log Structure

**Deployment Logs**: `logs/deployments/deployment_YYYYMMDD_HHMMSS.log`
- Complete deployment session
- All commands and results
- Timestamped entries

**Error Logs**: `logs/errors/CHARTNAME_error_YYYYMMDD_HHMMSS.log`
- Detailed error reports
- Helm error output
- Chart configuration
- Kubernetes status
- Troubleshooting information

### Error Log Contents

Each error log includes:
```
=== DEPLOYMENT ERROR REPORT ===
Chart: gitlab
Timestamp: Mon Jul 14 10:12:57 UTC 2025
Namespace: noah
Security Mode: root
Use Chart Defaults: true
Helm Timeout: 600s

=== ERROR OUTPUT ===
[Complete Helm error output]

=== CHART INFORMATION ===
[Chart.yaml and values.yaml contents]

=== KUBERNETES STATUS ===
[Current pods, events, and cluster state]
```

### Common Issues and Solutions

#### Permission Errors
```bash
# If you see permission denied errors:
./Script/noah infra deploy --security root

# For more security, use minimal mode:
./Script/noah infra deploy --security minimal
```

#### Storage Issues
```bash
# Check persistent volumes
kubectl get pv,pvc -n noah

# Describe storage issues
kubectl describe pvc -n noah

# Check available storage classes
kubectl get storageclass
```

#### Network Issues
```bash
# Test pod connectivity
kubectl exec -it deployment/gitlab-gitlab-simple -n noah -- ping google.com

# Check DNS resolution
kubectl exec -it deployment/gitlab-gitlab-simple -n noah -- nslookup keycloak.noah.svc.cluster.local

# View network policies
kubectl get networkpolicy -n noah
```

#### Timeout Issues
```bash
# Increase timeout for slow deployments
./Script/noah infra deploy --timeout 1200s --security root

# Check pod startup progress
kubectl get pods -n noah -w

# View pod logs
kubectl logs -f deployment/gitlab-gitlab-simple -n noah
```

---

## 🧪 Testing and Validation

### Comprehensive Testing Suite

```bash
# Run complete test suite
cd Test
make test

# Run specific test types
make test-python    # Structure, YAML, Helm validation
make test-shell     # Dependencies, integration, security

# Check test dependencies
make check-deps

# Validate specific components
./Script/noah validate --scope yaml
./Script/noah validate --scope security
./Script/noah validate --scope dependencies
```

### Deployment Validation

```bash
# Validate deployment success
./Script/noah infra status

# Check all pods are running
kubectl get pods -n noah

# Verify services are accessible
kubectl get services -n noah

# Test connectivity between services
kubectl exec -it deployment/gitlab-gitlab-simple -n noah -- wget -qO- http://keycloak:8080/health
```

---

## 🎛️ Service Management

### Individual Service Management

```bash
# Restart specific service
kubectl rollout restart deployment/gitlab-gitlab-simple -n noah

# Scale services
kubectl scale deployment/nextcloud --replicas=3 -n noah

# Update service configuration
helm upgrade gitlab ./Helm/gitlab --namespace noah --set gitlab.rootPassword=newpassword

# Check deployment status
kubectl rollout status deployment/gitlab-gitlab-simple -n noah
```

### Bulk Operations

```bash
# Update all services
./Script/noah infra deploy --security root

# Check status of all services
./Script/noah infra status

# View all logs
./Script/noah-logs deployments

# Restart all services
kubectl rollout restart deployment -n noah
```

### Resource Management

```bash
# Check resource usage
kubectl top pods -n noah
kubectl top nodes

# View resource requests and limits
kubectl describe pods -n noah | grep -A 5 "Requests\|Limits"

# Scale based on resource usage
kubectl scale deployment/gitlab-gitlab-simple --replicas=2 -n noah
```

---

## 🔐 Security Configuration

### Enhanced Security Context Management

N.O.A.H now supports flexible security contexts with automatic privilege management:

#### Root User Mode (Default)
```yaml
securityContext:
  runAsUser: 0
  runAsGroup: 0
  fsGroup: 0
  allowPrivilegeEscalation: true
  capabilities:
    add:
      - CHOWN
      - DAC_OVERRIDE
      - FOWNER
      - SETGID
      - SETUID
```

#### Secure User Mode
```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

### Identity and Access Management

#### Keycloak Setup

1. **Access Keycloak Admin Console**:
   ```bash
   kubectl port-forward svc/keycloak 8080:8080 -n noah
   # Navigate to: http://localhost:8080/admin
   # Default: admin/admin (change immediately)
   ```

2. **Create Realm for N.O.A.H**:
   - Create new realm: `noah`
   - Configure realm settings
   - Import pre-configured clients

3. **Configure OIDC Clients**:
   ```bash
   # Clients are auto-configured for:
   - Nextcloud (nextcloud-oidc)
   - Mattermost (mattermost-oidc)
   - Grafana (grafana-oidc)
   - GitLab (gitlab-oidc)
   ```

#### Samba4 Active Directory

```bash
# Check AD status
kubectl exec -it deployment/samba4 -- samba-tool domain level show -n noah

# Create users
kubectl exec -it deployment/samba4 -- samba-tool user create john.doe -n noah

# Add to groups
kubectl exec -it deployment/samba4 -- samba-tool group addmembers "Domain Users" john.doe -n noah
```

### Network Security

```bash
# Apply network policies (if enabled)
kubectl apply -f Helm/network-policies/ -n noah

# Configure firewall rules (if using VMs)
cd Ansible
ansible-playbook -i inventory/prod -t ufw main.yml

# Enable VPN access
ansible-playbook -i inventory/prod -t openvpn main.yml
```

---

## 📊 Monitoring and Observability

### Enhanced Monitoring with Root Privileges

```bash
# Deploy monitoring stack
./Script/noah monitoring deploy

# Access Grafana with port forwarding
kubectl port-forward svc/grafana 3000:3000 -n noah
# Default: admin/prom-operator

# View Prometheus metrics
kubectl port-forward svc/prometheus 9090:9090 -n noah
```

### Pre-configured Dashboards

- **Infrastructure Overview**: Node metrics, resource usage
- **Kubernetes Cluster**: Pod status, deployments, services
- **Application Performance**: Service response times, errors
- **Security Dashboard**: Authentication events, threats
- **Business Metrics**: User activity, service usage

### Monitoring with Enhanced Logging

```bash
# Monitor deployment progress
./Script/noah-logs tail

# Check monitoring service status
kubectl get pods -l app.kubernetes.io/name=prometheus -n noah

# View monitoring logs
kubectl logs -f deployment/prometheus-server -n noah
```

---

## 💾 Backup and Recovery

### Enhanced Backup with Error Tracking

```bash
# Setup backup with logging
./Script/noah backup setup --schedule daily --log-errors

# Manual backup with error tracking
./Script/noah backup create --full

# List backups with status
./Script/noah backup list --with-logs

# View backup error logs
./Script/noah-logs errors | grep backup
```

### Recovery Procedures

```bash
# Restore from backup with logging
./Script/noah backup restore --backup-name backup-2024-01-15

# Partial restore with error tracking
./Script/noah backup restore --service nextcloud --backup-name backup-2024-01-15

# Disaster recovery with full logging
./Script/noah infra teardown
./Script/noah backup restore --full --backup-name backup-2024-01-15 --verbose
```

---

## 🌍 Multi-Environment Management

### Enhanced Environment Support

```bash
# Deploy to different environments with appropriate security
./Script/noah infra deploy --security root --namespace noah-dev
./Script/noah infra deploy --security secure --namespace noah-prod

# Environment-specific logging
./Script/noah-logs summary | grep -E "(noah-dev|noah-prod)"

# Promote between environments
./Script/noah infra deploy --security root --namespace noah-staging
./Script/noah validate --namespace noah-staging
./Script/noah infra deploy --security secure --namespace noah-prod
```

### Configuration Management

```bash
# Security mode configurations
./Script/noah infra deploy --security root     # Maximum compatibility
./Script/noah infra deploy --security minimal  # Basic functionality
./Script/noah infra deploy --security secure   # Production security

# Custom security settings
./Script/noah infra deploy \
  --set securityContext.runAsUser=1001 \
  --set securityContext.runAsGroup=1001 \
  --namespace noah-custom
```

---

## 🔧 Advanced Customization

### Adding New Services with Proper Security

1. **Create Helm Chart with Security Context**:
   ```bash
   cd Helm
   helm create myservice
   
   # Add security context to templates/deployment.yaml
   securityContext:
     {{- include "noah.podSecurityContext" . | nindent 8 }}
   containers:
   - name: myservice
     securityContext:
       {{- include "noah.securityContext" . | nindent 10 }}
   ```

2. **Configure Integration with Error Logging**:
   ```yaml
   # Add to values.yaml
   myservice:
     enabled: true
     securityContext:
       runAsUser: 0  # or 1000 for non-root
       runAsGroup: 0
       allowPrivilegeEscalation: true
     oidc:
       client_id: "myservice-oidc"
       realm: "noah"
   ```

3. **Deploy with Monitoring**:
   ```bash
   ./Script/noah infra deploy --verbose
   ./Script/noah-logs tail | grep myservice
   ```

### Custom Security Configurations

```bash
# Create custom security profile
cat > custom-security.yaml << 'EOF'
securityContext:
  runAsUser: 2000
  runAsGroup: 2000
  fsGroup: 2000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE
EOF

# Deploy with custom security
helm upgrade myservice ./Helm/myservice \
  --namespace noah \
  -f custom-security.yaml
```

---

## 🆘 Advanced Troubleshooting

### Using Enhanced Error Logging

#### Comprehensive Error Analysis

```bash
# View all deployment errors
./Script/noah-logs errors

# Analyze specific chart errors
cat logs/errors/gitlab_error_*.log

# Search for specific error patterns
grep -r "permission denied" logs/errors/

# View error trends
ls -la logs/errors/ | grep $(date +%Y%m%d)
```

#### Real-time Monitoring

```bash
# Monitor deployment in real-time
./Script/noah-logs tail

# Follow specific service logs
kubectl logs -f deployment/gitlab-gitlab-simple -n noah

# Watch pod status changes
kubectl get pods -n noah -w
```

#### Common Issues with Solutions

##### Security Context Issues
```bash
# Error: container has runAsNonRoot and image will run as root
# Solution: Use root security mode
./Script/noah infra deploy --security root

# Error: operation not permitted
# Solution: Add required capabilities
helm upgrade service ./Helm/service \
  --set securityContext.capabilities.add="{CHOWN,DAC_OVERRIDE}"
```

##### Storage Permission Issues
```bash
# Error: permission denied on volume mount
# Solution: Set proper fsGroup
helm upgrade service ./Helm/service \
  --set securityContext.fsGroup=0

# Check volume permissions
kubectl exec -it deployment/service -n noah -- ls -la /data
```

##### Network and DNS Issues
```bash
# Test DNS resolution
kubectl exec -it deployment/gitlab-gitlab-simple -n noah -- nslookup keycloak.noah.svc.cluster.local

# Check service connectivity
kubectl exec -it deployment/gitlab-gitlab-simple -n noah -- telnet keycloak 8080

# Verify network policies
kubectl get networkpolicy -n noah
kubectl describe networkpolicy -n noah
```

##### Resource and Performance Issues
```bash
# Check resource constraints
kubectl describe pod -n noah | grep -A 5 "Limits:\|Requests:"

# View resource usage
kubectl top pods -n noah
kubectl top nodes

# Scale if needed
kubectl scale deployment/service --replicas=2 -n noah
```

### Debug Mode and Verbose Logging

```bash
# Enable maximum verbosity
./Script/noah infra deploy --verbose --security root

# Debug specific chart deployment
helm install service ./Helm/service \
  --namespace noah \
  --debug \
  --dry-run

# Check Helm release status
helm status service -n noah

# View Helm history
helm history service -n noah
```

### Log Analysis and Cleanup

```bash
# Analyze log patterns
./Script/noah-logs summary

# Clean old logs to save space
./Script/noah-logs clean

# Archive important error logs
mkdir -p archive/$(date +%Y%m)
cp logs/errors/*.log archive/$(date +%Y%m)/

# Monitor disk usage
du -sh logs/
```

---

## 📈 Performance Optimization

### Resource Optimization with Enhanced Monitoring

```bash
# Check resource usage with logging
kubectl top nodes | tee logs/resource-usage-$(date +%Y%m%d).log
kubectl top pods -n noah | tee -a logs/resource-usage-$(date +%Y%m%d).log

# Optimize resource requests/limits for root user deployments
helm upgrade gitlab ./Helm/gitlab \
  --namespace noah \
  --set resources.requests.memory=2Gi \
  --set resources.limits.memory=4Gi \
  --set securityContext.runAsUser=0
```

### Scaling with Security Context Considerations

```bash
# Horizontal scaling (root user compatible)
kubectl scale deployment/gitlab-gitlab-simple --replicas=3 -n noah

# Vertical scaling with proper security context
kubectl patch deployment gitlab-gitlab-simple -n noah -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "gitlab",
            "resources": {
              "requests": {"cpu": "1000m", "memory": "4Gi"},
              "limits": {"cpu": "2000m", "memory": "8Gi"}
            }
          }
        ]
      }
    }
  }
}'

# Auto-scaling with security context awareness
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gitlab-hpa
  namespace: noah
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gitlab-gitlab-simple
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF
```

---

## 🚀 Production Deployment Checklist

### Enhanced Pre-Deployment Checklist

- [ ] **System Requirements**: Verify hardware and software requirements
- [ ] **Security Mode Selection**: Choose appropriate security mode (root/secure)
- [ ] **Logging Setup**: Ensure log directories have sufficient space
- [ ] **Network Planning**: Configure DNS, load balancers, firewall rules
- [ ] **Storage Planning**: Configure persistent storage classes with proper permissions
- [ ] **Security Review**: Review security policies and root user requirements
- [ ] **Backup Strategy**: Configure backup locations and schedules

### Enhanced Deployment Process

- [ ] **Pre-deployment Validation**:
  ```bash
  ./Script/noah validate --scope all
  ./Script/noah-logs clean  # Clean old logs
  ```

- [ ] **Deploy Infrastructure with Logging**:
  ```bash
  ./Script/noah infra deploy --security root --verbose
  ./Script/noah-logs tail &  # Monitor in background
  ```

- [ ] **Enable Monitoring with Proper Security**:
  ```bash
  ./Script/noah monitoring deploy --security root
  ```

- [ ] **Configure Backups with Error Tracking**:
  ```bash
  ./Script/noah backup setup --log-errors
  ```

- [ ] **Security Hardening**: Apply security policies while maintaining functionality

### Enhanced Post-Deployment Checklist

- [ ] **Validation Testing with Logging**:
  ```bash
  cd Test && make test 2>&1 | tee logs/post-deployment-test.log
  ```

- [ ] **Performance Testing**: Load test critical services with monitoring
- [ ] **Security Audit**: Vulnerability scanning and penetration testing
- [ ] **Log Analysis**: Review deployment and error logs
  ```bash
  ./Script/noah-logs summary
  ./Script/noah-logs errors
  ```

- [ ] **Documentation**: Update runbooks and operational procedures
- [ ] **Team Training**: Train operations team on new logging and troubleshooting features

### Ongoing Operations with Enhanced Monitoring

- [ ] **Daily Log Review**:
  ```bash
  ./Script/noah-logs errors | grep $(date +%Y%m%d)
  ./Script/noah-logs summary
  ```

- [ ] **Weekly Log Cleanup**:
  ```bash
  ./Script/noah-logs clean
  ```

- [ ] **Monthly Security Review**: Regular security patches and updates
- [ ] **Performance Monitoring**: Track and optimize resource usage
- [ ] **Capacity Planning**: Monitor growth and plan for scaling

---

## 📚 Additional Resources

### Enhanced Documentation

- **[README.md](../README.md)**: Project overview and quick start
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Contributing guidelines
- **[Test README](../Test/README.md)**: Testing suite documentation
- **[Script README](../Script/README.md)**: CLI tools documentation
- **[Logging Guide](../docs/LOGGING.md)**: Comprehensive logging documentation

### Log Management

```bash
# View logging documentation
./Script/noah-logs help

# Monitor log disk usage
du -sh logs/

# Archive old logs
tar -czf logs-archive-$(date +%Y%m).tar.gz logs/
```

### Security Context Examples

```yaml
# Example: GitLab with root user (maximum compatibility)
securityContext:
  runAsUser: 0
  runAsGroup: 0
  allowPrivilegeEscalation: true
  capabilities:
    add: ["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"]

# Example: Nextcloud with restricted privileges
securityContext:
  runAsUser: 33  # www-data user
  runAsGroup: 33
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
    add: ["CHOWN", "FOWNER"]
```

### Troubleshooting Quick Reference

```bash
# Quick health check
./Script/noah infra status

# View recent errors
./Script/noah-logs errors | tail -5

# Check specific service
kubectl describe deployment/gitlab-gitlab-simple -n noah

# Security context debugging
kubectl get pod -n noah -o yaml | grep -A 10 securityContext

# Network troubleshooting
kubectl exec -it deployment/gitlab-gitlab-simple -n noah -- netstat -tlnp
```

### Community and Support

- **GitHub Repository**: [https://github.com/your-org/noah](https://github.com/your-org/noah)
- **Issue Tracker**: Report bugs and request features
- **Discussions**: Community Q&A and knowledge sharing
- **Wiki**: Additional documentation and tutorials
- **Security Issues**: security@noah-project.org

### Getting Support

1. **Check Documentation**:
   ```bash
   ./Script/noah help
   ./Script/noah-logs help
   ```

2. **Review Logs**:
   ```bash
   ./Script/noah-logs latest
   ./Script/noah-logs errors
   ```

3. **Run Diagnostics**:
   ```bash
   ./Script/noah validate --verbose
   cd Test && make test
   ```

4. **Community Resources**:
   - Search existing issues
   - Check troubleshooting guides
   - Join community discussions

---

**🎉 Congratulations! You now have a complete N.O.A.H infrastructure deployment with enhanced logging, flexible security contexts, and comprehensive troubleshooting capabilities.**

For ongoing support and advanced configurations, please refer to the comprehensive logging system, the additional documentation in the `docs/` directory, or reach out to the community through GitHub Issues and Discussions.

## Quick Command Reference

```bash
# Essential Commands
./Script/noah infra deploy --security root --verbose    # Deploy with root security
./Script/noah infra status                             # Check deployment status
./Script/noah-logs tail                                # Monitor deployments
./Script/noah-logs errors                              # View error logs
./Script/noah-logs summary                             # Log overview
./Script/noah validate                                 # Validate configuration

# Troubleshooting
kubectl get pods -n noah                              # Check pod status
kubectl logs -f deployment/gitlab-gitlab-simple -n noah  # View service logs
kubectl describe deployment/SERVICE -n noah           # Debug deployment issues
./Script/noah-logs clean                              # Clean old logs
```
