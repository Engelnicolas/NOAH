# N.O.A.H User Guide - Complete Deployment Guide

## 🎯 Overview

This comprehensive guide walks you through deploying the complete N.O.A.H (Next Open-source Architecture Hub) infrastructure platform using the **unified CLI interface** and **simplified tooling**.

N.O.A.H provides a production-ready, secure, and scalable open-source infrastructure stack with identity management, collaboration tools, monitoring, and security components.

---

## 🚀 Quick Start (5 Minutes)

### Fastest Path to Running N.O.A.H

```bash
# Clone repository
git clone https://github.com/your-org/noah.git
cd noah

# Validate and fix any issues
./Script/noah validate --fix

# Deploy infrastructure (development environment)
./Script/noah infra deploy --environment dev

# Verify deployment
./Script/noah infra status

# Access your services at:
# - Keycloak: https://auth.your-domain.com
# - Nextcloud: https://cloud.your-domain.com  
# - Mattermost: https://chat.your-domain.com
# - Grafana: https://monitoring.your-domain.com
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

## 🏗️ Installation Methods

N.O.A.H supports multiple deployment methods depending on your infrastructure and requirements:

### Method 1: Kubernetes Deployment (Recommended)

**Best for**: Production environments, scalable deployments

```bash
# 1. Ensure Kubernetes cluster is available
kubectl cluster-info

# 2. Deploy N.O.A.H infrastructure
./Script/noah infra deploy --environment prod --values-file custom-values.yaml

# 3. Monitor deployment
./Script/noah infra status --watch
```

### Method 2: Docker Compose (Development)

**Best for**: Local development, testing, single-node deployments

```bash
# 1. Generate Docker Compose files
./Script/noah infra setup --mode docker-compose

# 2. Deploy services
docker-compose up -d

# 3. Check status
docker-compose ps
```

### Method 3: Ansible + VMs (Traditional)

**Best for**: Existing VM infrastructure, hybrid deployments

```bash
# 1. Configure inventory
cd Ansible
cp inventory/example inventory/custom
vim inventory/custom/hosts

# 2. Deploy with Ansible
ansible-playbook -i inventory/custom main.yml

# 3. Validate deployment
ansible-playbook -i inventory/custom test_deployment.yml
```

---

## 🔧 Configuration

### Environment Configuration

N.O.A.H supports multiple environments with automatic configuration:

```bash
# Development (minimal resources)
./Script/noah infra deploy --environment dev

# Staging (production-like)
./Script/noah infra deploy --environment staging

# Production (full features, high availability)
./Script/noah infra deploy --environment prod
```

### Environment-Specific Values

```
Helm/values/
├── values-dev.yaml      # Development configuration
├── values-staging.yaml  # Staging configuration
├── values-prod.yaml     # Production configuration
└── values-minimal.yaml  # Minimal installation
```

### Custom Configuration

Create custom values files for specific deployments:

```yaml
# custom-values.yaml
global:
  domain: "your-company.com"
  environment: "production"
  
keycloak:
  adminUser: "admin"
  database:
    type: "postgresql"
    host: "postgres.internal"
    
nextcloud:
  storage:
    size: "500Gi"
    class: "fast-ssd"
    
monitoring:
  prometheus:
    retention: "90d"
  grafana:
    plugins:
      - grafana-piechart-panel
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

#### For Development Environment

```bash
# Deploy with minimal resources
./Script/noah infra deploy --environment dev

# Monitor deployment progress
watch './Script/noah infra status'

# Access services (URLs will be displayed)
./Script/noah infra status --urls
```

#### For Production Environment

```bash
# Deploy with production configuration
./Script/noah infra deploy --environment prod --values-file production-values.yaml

# Enable monitoring
./Script/noah monitoring deploy

# Setup backup strategy
./Script/noah backup setup --schedule daily
```

### Step 4: Service Configuration

#### Identity and Access Management

```bash
# Configure Keycloak SSO
kubectl port-forward svc/keycloak 8080:8080
# Access: http://localhost:8080/admin (admin/admin)

# Create users and groups
# Import OIDC clients for integrated services
```

#### Collaboration Services

```bash
# Configure Nextcloud
kubectl port-forward svc/nextcloud 8081:80
# Access: http://localhost:8081 (admin/changeme)

# Configure Mattermost
kubectl port-forward svc/mattermost 8082:8065
# Access: http://localhost:8082
```

### Step 5: Monitoring and Security

```bash
# Access Grafana dashboards
kubectl port-forward svc/grafana 3000:3000
# Access: http://localhost:3000 (admin/prom-operator)

# Check security status
./Script/noah validate --scope security

# View monitoring overview
./Script/noah monitoring status
```

---

## 🧪 Testing and Validation

N.O.A.H includes a **simplified, comprehensive testing suite** for validation:

### Quick Validation

```bash
# Run complete test suite
cd Test
make test

# Run specific test types
make test-python    # Structure, YAML, Helm validation
make test-shell     # Dependencies, integration, security

# Check test dependencies
make check-deps
```

### Detailed Testing Options

```bash
# Python test suite with options
cd Test
python3 noah_test.py -v              # Verbose output
python3 noah_test.py --charts-only   # Helm charts only
python3 noah_test.py --structure-only # Structure validation

# Shell test suite with options
./unified_tests.sh                   # All tests
./unified_tests.sh --deps-only       # Dependencies only
./unified_tests.sh --helm-only       # Helm chart tests
./unified_tests.sh --security-only   # Security validation
```

### Continuous Testing

```bash
# Set up pre-commit testing
git config core.hooksPath .githooks

# Enable automatic validation
echo "make test" > .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

---

## 🎛️ Service Management

### Individual Service Management

```bash
# Restart specific service
kubectl rollout restart deployment/keycloak

# Scale services
kubectl scale deployment/nextcloud --replicas=3

# Update service configuration
helm upgrade keycloak ./Helm/keycloak --values custom-values.yaml
```

### Bulk Operations

```bash
# Update all services
./Script/noah infra upgrade --environment prod

# Backup all data
./Script/noah backup create --full

# Health check all services
./Script/noah infra status --detailed
```

### Troubleshooting

```bash
# Check deployment issues
kubectl get events --sort-by=.metadata.creationTimestamp

# View service logs
kubectl logs -f deployment/keycloak

# Debug networking
kubectl exec -it pod/debug-pod -- nslookup keycloak

# Validate configuration
./Script/noah validate --verbose
```

---

## 🔐 Security Configuration

### Identity and Access Management

#### Keycloak Setup

1. **Access Keycloak Admin Console**:
   ```bash
   kubectl port-forward svc/keycloak 8080:8080
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
   - Wazuh (wazuh-oidc)
   ```

#### Samba4 Active Directory

```bash
# Check AD status
kubectl exec -it deployment/samba4 -- samba-tool domain level show

# Create users
kubectl exec -it deployment/samba4 -- samba-tool user create john.doe

# Add to groups
kubectl exec -it deployment/samba4 -- samba-tool group addmembers "Domain Users" john.doe
```

### Network Security

```bash
# Apply network policies
kubectl apply -f Helm/network-policies/

# Configure firewall rules (if using VMs)
cd Ansible
ansible-playbook -i inventory/prod -t ufw main.yml

# Enable VPN access
ansible-playbook -i inventory/prod -t openvpn main.yml
```

### Security Monitoring

```bash
# Check Wazuh SIEM
kubectl port-forward svc/wazuh 5601:5601
# Access: http://localhost:5601 (admin/SecretPassword)

# Monitor OpenEDR
kubectl logs -f deployment/openedr

# Security audit
./Script/noah validate --scope security
```

---

## 📊 Monitoring and Observability

### Prometheus and Grafana Setup

```bash
# Deploy monitoring stack
./Script/noah monitoring deploy

# Access Grafana
kubectl port-forward svc/grafana 3000:3000
# Default: admin/prom-operator

# View metrics
kubectl port-forward svc/prometheus 9090:9090
```

### Pre-configured Dashboards

- **Infrastructure Overview**: Node metrics, resource usage
- **Kubernetes Cluster**: Pod status, deployments, services
- **Application Performance**: Service response times, errors
- **Security Dashboard**: Authentication events, threats
- **Business Metrics**: User activity, service usage

### Alerting

```bash
# Configure Alertmanager
kubectl edit configmap alertmanager-config

# Test alerts
kubectl exec -it prometheus-0 -- promtool query instant 'up{job="kubernetes-nodes"}==0'
```

---

## 💾 Backup and Recovery

### Automated Backup Setup

```bash
# Configure backup schedule
./Script/noah backup setup --schedule daily --retention 30d

# Manual backup
./Script/noah backup create --full

# List backups
./Script/noah backup list
```

### Recovery Procedures

```bash
# Restore from backup
./Script/noah backup restore --backup-name backup-2024-01-15

# Partial restore (specific service)
./Script/noah backup restore --service nextcloud --backup-name backup-2024-01-15

# Disaster recovery
./Script/noah infra teardown
./Script/noah backup restore --full --backup-name backup-2024-01-15
```

---

## 🌍 Multi-Environment Management

### Environment Promotion

```bash
# Deploy to staging
./Script/noah infra deploy --environment staging

# Validate staging
cd Test && make test

# Promote to production
./Script/noah infra deploy --environment prod --values-file prod-values.yaml
```

### Configuration Management

```bash
# Environment-specific configurations
Helm/values/
├── values-dev.yaml      # 1 CPU, 2GB RAM per service
├── values-staging.yaml  # 2 CPU, 4GB RAM per service  
├── values-prod.yaml     # 4 CPU, 8GB RAM per service

# Custom environment
cp Helm/values/values-prod.yaml Helm/values/values-custom.yaml
./Script/noah infra deploy --values-file values-custom.yaml
```

---

## 🔧 Customization and Extension

### Adding New Services

1. **Create Helm Chart**:
   ```bash
   cd Helm
   helm create myservice
   ```

2. **Configure Integration**:
   ```yaml
   # Add to values file
   myservice:
     enabled: true
     oidc:
       client_id: "myservice-oidc"
       realm: "noah"
   ```

3. **Deploy**:
   ```bash
   ./Script/noah infra upgrade --include myservice
   ```

### Custom Authentication

```bash
# Add LDAP/OIDC integration
# Configure in Keycloak admin console
# Update service configurations
helm upgrade nextcloud ./Helm/nextcloud --set auth.oidc.enabled=true
```

---

## 🆘 Troubleshooting

### Common Issues

#### Deployment Failures

```bash
# Check pod status
kubectl get pods -A

# View events
kubectl get events --sort-by=.metadata.creationTimestamp

# Debug specific deployment
kubectl describe deployment/keycloak
kubectl logs -f deployment/keycloak
```

#### Network Issues

```bash
# Test connectivity
kubectl exec -it debug-pod -- ping keycloak
kubectl exec -it debug-pod -- nslookup keycloak.default.svc.cluster.local

# Check services
kubectl get svc -A
kubectl describe svc/keycloak
```

#### Storage Issues

```bash
# Check persistent volumes
kubectl get pv,pvc -A

# View storage classes
kubectl get storageclass

# Check disk usage
kubectl exec -it deployment/nextcloud -- df -h
```

#### Authentication Issues

```bash
# Check Keycloak logs
kubectl logs -f deployment/keycloak

# Verify OIDC configuration
kubectl get secret keycloak-oidc -o yaml

# Test LDAP connectivity
kubectl exec -it deployment/keycloak -- ldapsearch -H ldap://samba4:389
```

### Debug Mode

```bash
# Enable verbose logging
export NOAH_DEBUG=true
./Script/noah infra status --verbose

# Comprehensive validation
./Script/noah validate --verbose --fix

# Test connectivity
cd Test
./unified_tests.sh --integration --verbose
```

### Getting Help

1. **Check logs**:
   ```bash
   kubectl logs -f deployment/SERVICE_NAME
   ```

2. **Run diagnostics**:
   ```bash
   ./Script/noah validate --scope all
   cd Test && make test
   ```

3. **Community support**:
   - GitHub Issues: [Report bugs](https://github.com/your-org/noah/issues)
   - Documentation: Check `docs/` directory
   - Examples: See `examples/` directory

---

## 📈 Performance Optimization

### Resource Optimization

```bash
# Check resource usage
kubectl top nodes
kubectl top pods -A

# Optimize resource requests/limits
helm upgrade SERVICE ./Helm/SERVICE --set resources.requests.memory=1Gi
```

### Scaling

```bash
# Horizontal scaling
kubectl scale deployment/nextcloud --replicas=3

# Vertical scaling
kubectl patch deployment nextcloud -p '{"spec":{"template":{"spec":{"containers":[{"name":"nextcloud","resources":{"requests":{"cpu":"500m","memory":"1Gi"}}}]}}}}'

# Auto-scaling
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nextcloud-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nextcloud
  minReplicas: 2
  maxReplicas: 10
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

### Pre-Deployment

- [ ] **System Requirements**: Verify hardware and software requirements
- [ ] **Network Planning**: Configure DNS, load balancers, firewall rules
- [ ] **Storage Planning**: Configure persistent storage classes
- [ ] **Security Review**: Review security policies and configurations
- [ ] **Backup Strategy**: Configure backup locations and schedules

### Deployment

- [ ] **Environment Configuration**: Customize values files for production
- [ ] **Deploy Infrastructure**: `./Script/noah infra deploy --environment prod`
- [ ] **Enable Monitoring**: `./Script/noah monitoring deploy`
- [ ] **Configure Backups**: `./Script/noah backup setup`
- [ ] **Security Hardening**: Apply security policies and network rules

### Post-Deployment

- [ ] **Validation Testing**: Run comprehensive test suite
- [ ] **Performance Testing**: Load test critical services
- [ ] **Security Audit**: Vulnerability scanning and penetration testing
- [ ] **Documentation**: Update runbooks and operational procedures
- [ ] **Team Training**: Train operations team on management procedures

### Ongoing Operations

- [ ] **Monitoring Setup**: Configure alerts and dashboards
- [ ] **Backup Verification**: Regular backup and restore testing
- [ ] **Security Updates**: Regular security patches and updates
- [ ] **Performance Monitoring**: Track and optimize resource usage
- [ ] **Capacity Planning**: Monitor growth and plan for scaling

---

## 📚 Additional Resources

### Documentation

- **[README.md](../README.md)**: Project overview and quick start
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Contributing guidelines
- **[Test README](../Test/README.md)**: Testing suite documentation
- **[Script README](../Script/README.md)**: CLI tools documentation

### Examples and Templates

```
examples/
├── development/          # Development environment examples
├── production/          # Production deployment templates
├── hybrid/             # Hybrid cloud configurations
└── customizations/     # Service customization examples
```

### Community and Support

- **GitHub Repository**: [https://github.com/your-org/noah](https://github.com/your-org/noah)
- **Issue Tracker**: Report bugs and request features
- **Discussions**: Community Q&A and knowledge sharing
- **Wiki**: Additional documentation and tutorials

---

**🎉 Congratulations! You now have a complete N.O.A.H infrastructure deployment.**

For ongoing support and advanced configurations, please refer to the additional documentation in the `docs/` directory or reach out to the community through GitHub Issues and Discussions.
