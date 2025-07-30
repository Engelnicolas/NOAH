# NOAH Platform CI/CD Pipeline

**Comprehensive Guide to Automated DevOps Infrastructure**

This document provides a complete overview of the NOAH platform's CI/CD pipeline, featuring automated infrastructure provisioning, Kubernetes deployment, and application orchestration through GitHub Actions, Ansible, Kubespray, and Helm.

## 🏗️ Architecture Overview

The NOAH CI/CD pipeline follows a multi-layered architecture designed for scalability, reliability, and maintainability:

```mermaid
graph TD
    A[GitHub Actions] --> B[Environment Setup]
    B --> C[Infrastructure Provisioning]
    C --> D[Kubernetes Installation]
    D --> E[Cluster Configuration]
    E --> F[Application Deployment]
    F --> G[Verification & Monitoring]
    
    subgraph "Infrastructure Layer"
        H[Proxmox VMs]
        I[Cloud Instances]
        J[Bare Metal]
    end
    
    subgraph "Orchestration Layer"
        K[Kubespray]
        L[Ansible Collections]
        M[Custom Playbooks]
    end
    
    subgraph "Application Layer"
        N[Helm Charts]
        O[GitLab]
        P[Keycloak]
        Q[Nextcloud]
        R[Mattermost]
        S[Monitoring Stack]
    end
    
    C --> H
    C --> I
    C --> J
    D --> K
    D --> L
    D --> M
    F --> N
    N --> O
    N --> P
    N --> Q
    N --> R
    N --> S
```

### Core Components

- **GitHub Actions**: Orchestrates the entire deployment pipeline
- **Ansible**: Infrastructure automation and configuration management
- **Kubespray**: Production-ready Kubernetes cluster deployment
- **Helm**: Application package management and deployment
- **Proxmox/Cloud Providers**: Infrastructure provisioning targets

## 🚀 Quick Start Guide

### Prerequisites

Before starting, ensure you have:
- Access to target infrastructure (Proxmox, cloud provider, or bare metal)
- GitHub repository with Actions enabled
- Domain name and DNS configuration capabilities
- SSL certificates (or Let's Encrypt integration)

### 1. Environment Initialization

```bash
# Clone the repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Initialize the pipeline environment
./script/setup-pipeline.sh

# Validate all dependencies
./script/test-dependencies.sh
```

### 2. GitHub Secrets Configuration

Configure the following secrets in your GitHub repository settings:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SSH_PRIVATE_KEY` | ED25519 private key for server access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `ANSIBLE_VAULT_PASSWORD` | Password for encrypted Ansible secrets | `your-secure-vault-password` |
| `MASTER_HOST` | Primary server IP/hostname | `192.168.1.10` or `master.noah.local` |
| `WORKER_HOSTS` | Worker server IPs (comma-separated) | `192.168.1.11,192.168.1.12` |
| `PROXMOX_API_USER` | Proxmox API user (if using Proxmox) | `noah@pve` |
| `PROXMOX_API_PASSWORD` | Proxmox API password | `your-proxmox-password` |
| `PROXMOX_API_HOST` | Proxmox server URL | `https://proxmox.yourdomain.com:8006` |

### 3. SSH Key Setup

Generate and configure SSH keys for secure server access:

```bash
# Generate ED25519 key pair (recommended for security)
ssh-keygen -t ed25519 -C "noah-deployment@yourdomain.com" -f ~/.ssh/noah_deployment

# Display private key for GitHub secret
cat ~/.ssh/noah_deployment

# Deploy public key to target servers
ssh-copy-id -i ~/.ssh/noah_deployment.pub root@your-master-server
ssh-copy-id -i ~/.ssh/noah_deployment.pub root@your-worker-server-1
ssh-copy-id -i ~/.ssh/noah_deployment.pub root@your-worker-server-2

# Verify SSH access
ssh -i ~/.ssh/noah_deployment root@your-master-server "echo 'SSH connection successful'"
```

### 4. Configuration Customization

Adapt the configuration to your environment:

```bash
# Edit server inventory
vim ansible/inventory/mycluster/hosts.yaml

# Customize global variables
vim ansible/vars/global.yml

# Configure application values
vim values/values-prod.yaml

# Set up secrets (will be encrypted)
vim ansible/vars/secrets.yml
ansible-vault encrypt ansible/vars/secrets.yml
```

### 5. Deployment Trigger

Initiate the deployment by pushing to the main branch:

```bash
git add .
git commit -m "Configure NOAH deployment for production"
git push origin main
```

## 📁 Project Structure

The NOAH project follows a well-organized structure optimized for DevOps automation:

```
NOAH/
├── 📋 Documentation
│   ├── docs/
│   │   ├── PIPELINE_CI_CD.md          # This document
│   │   ├── DOMAIN_CONFIGURATION.md    # DNS and SSL setup
│   │   ├── SECRETS_MANAGEMENT.md      # Security practices
│   │   ├── SECURITY.md                # Security guidelines
│   │   └── NOAH_CLI.md                # Command-line usage
│   └── README.md                      # Project overview
│
├── 🔄 CI/CD Workflows
│   └── .github/workflows/
│       ├── ci.yml                     # Continuous integration
│       └── deploy.yml                 # Deployment pipeline
│
├── 🎯 Automation Engine
│   ├── ansible/
│   │   ├── ansible.cfg                # Ansible configuration
│   │   ├── requirements.yml           # Required collections
│   │   ├── inventory/mycluster/
│   │   │   ├── hosts.yaml            # Server inventory
│   │   │   └── group_vars/           # Group variables
│   │   ├── kubespray/                # Kubernetes installer (submodule)
│   │   ├── playbooks/
│   │   │   ├── 01-provision.yml      # Infrastructure provisioning
│   │   │   ├── 02-install-k8s.yml    # Kubernetes installation
│   │   │   ├── 03-configure-cluster.yml # Cluster configuration
│   │   │   ├── 04-deploy-apps.yml    # Application deployment
│   │   │   ├── 05-verify-deployment.yml # Health verification
│   │   │   └── 99-cleanup.yml        # Cleanup procedures
│   │   ├── templates/
│   │   │   ├── k8s-cluster.yml.j2    # Kubespray configuration
│   │   │   ├── deployment_report.j2  # Deployment summary
│   │   │   └── *.yml.j2              # Secret templates
│   │   └── vars/
│   │       ├── global.yml            # Global variables
│   │       └── secrets.yml           # Encrypted secrets
│
├── 📦 Application Packages
│   └── helm/
│       ├── noah-chart/               # Main umbrella chart
│       ├── noah-common/              # Shared templates and values
│       ├── gitlab/                   # GitLab DevOps platform
│       ├── keycloak/                 # Identity and access management
│       ├── nextcloud/                # File sharing and collaboration
│       ├── mattermost/               # Team communication
│       ├── grafana/                  # Metrics visualization
│       ├── prometheus/               # Metrics collection
│       ├── wazuh/                    # Security monitoring
│       ├── openedr/                  # Endpoint detection and response
│       ├── oauth2-proxy/             # Authentication proxy
│       └── samba4/                   # File sharing service
│
├── 🛠️ Utility Scripts
│   └── script/
│       ├── setup-pipeline.sh         # Environment initialization
│       ├── configure-pipeline.sh     # Pipeline configuration
│       ├── configure-ssh.sh          # SSH setup automation
│       ├── test-dependencies.sh      # Dependency validation
│       ├── sops-secrets-manager.sh   # SOPS integration
│       └── requirements.txt          # Python dependencies
│
├── ⚙️ Configuration
│   ├── values/
│   │   ├── values-prod.yaml          # Production configuration
│   │   ├── values-staging.yaml       # Staging configuration
│   │   └── values-dev.yaml           # Development configuration
│   ├── .gitmodules                   # Git submodule configuration
│   └── LICENSE                       # Project license
│
└── 🔐 Security
    └── age/
        └── keys/                     # Age encryption keys
```

## 🔄 Deployment Pipeline Stages

### Stage 1: Infrastructure Provisioning
**Duration**: 5-15 minutes  
**Playbook**: `ansible/playbooks/01-provision.yml`

This stage handles the creation and initial configuration of virtual machines or cloud instances:

```yaml
# Key features:
- name: Create infrastructure
  tasks:
    - VM/instance creation (Proxmox, AWS, Azure, GCP)
    - Network configuration and security groups
    - SSH key deployment and user setup
    - Basic OS configuration and hardening
    - Firewall rules and port configuration
```

**Supported Infrastructure**:
- **Proxmox**: On-premises virtualization
- **AWS EC2**: Cloud instances with VPC configuration
- **Azure VMs**: Resource groups and virtual networks
- **Google Cloud**: Compute Engine instances
- **Bare Metal**: Physical server preparation

### Stage 2: Kubernetes Installation
**Duration**: 10-25 minutes  
**Playbook**: `ansible/playbooks/02-install-k8s.yml`

Deploys a production-ready Kubernetes cluster using Kubespray:

```yaml
# Kubespray configuration:
- Kubernetes version: 1.28+ (configurable)
- Container runtime: containerd
- Network plugin: Calico (default) or Flannel
- DNS: CoreDNS
- Ingress: NGINX Ingress Controller
- Storage: Local storage or cloud provider CSI
```

**Features**:
- High availability master nodes (3+ nodes recommended)
- Automatic certificate management
- RBAC security configuration
- Network policies enforcement
- Persistent volume provisioning

### Stage 3: Cluster Configuration
**Duration**: 5-10 minutes  
**Playbook**: `ansible/playbooks/03-configure-cluster.yml`

Configures the Kubernetes cluster for application deployment:

```yaml
# Configuration tasks:
- Helm 3 installation and repository setup
- Namespace creation (noah, monitoring, security)
- Secret management (TLS certificates, API keys)
- Ingress controller configuration
- Monitoring stack preparation
- Network policies and security contexts
```

### Stage 4: Application Deployment
**Duration**: 15-30 minutes  
**Playbook**: `ansible/playbooks/04-deploy-apps.yml`

Deploys the complete NOAH application stack:

#### Core Applications
- **PostgreSQL**: Shared database with high availability
- **Keycloak**: Single Sign-On and identity management
- **OAuth2 Proxy**: Authentication layer for all services

#### Collaboration Platform
- **GitLab**: Code repository, CI/CD, and project management
- **Nextcloud**: File storage, sharing, and collaboration
- **Mattermost**: Team chat and communication

#### Monitoring & Security
- **Prometheus + Grafana**: Metrics collection and visualization
- **Wazuh**: Security information and event management
- **OpenEDR**: Endpoint detection and response

#### Additional Services
- **Samba4**: Network file sharing
- **Custom applications**: Deployed via noah-chart

### Stage 5: Verification & Health Checks
**Duration**: 2-5 minutes  
**Playbook**: `ansible/playbooks/05-verify-deployment.yml`

Validates the deployment and generates reports:

```yaml
# Verification tasks:
- Pod health and readiness checks
- Service connectivity tests
- Ingress and DNS resolution verification
- SSL certificate validation
- Application-specific health endpoints
- Performance baseline establishment
- Deployment report generation
```

## 🔐 Advanced Security & Secrets Management

### Ansible Vault Integration

The NOAH platform uses Ansible Vault for secure secrets management:

```bash
# Initialize secrets file
echo "secrets_initialized: true" > ansible/vars/secrets.yml

# Encrypt the secrets file
ansible-vault encrypt ansible/vars/secrets.yml

# Edit encrypted secrets safely
ansible-vault edit ansible/vars/secrets.yml

# View encrypted content without editing
ansible-vault view ansible/vars/secrets.yml

# Rekey (change password)
ansible-vault rekey ansible/vars/secrets.yml

# Temporarily decrypt for automation
ansible-vault decrypt ansible/vars/secrets.yml --output /tmp/secrets.yml
```

### SOPS Integration (Alternative)

For more advanced secret management, NOAH supports SOPS with Age encryption:

```bash
# Initialize SOPS with Age
./script/sops-secrets-manager.sh init

# Create encrypted secret
sops --encrypt --age $(cat age/keys/public.key) secrets.yaml > secrets.enc.yaml

# Edit encrypted file
sops secrets.enc.yaml

# Decrypt for use
sops --decrypt secrets.enc.yaml
```

### Secret Categories

| Category | Examples | Storage Method |
|----------|----------|----------------|
| **Infrastructure** | API keys, credentials | Ansible Vault |
| **Application** | Database passwords, JWT secrets | Kubernetes Secrets |
| **Certificates** | TLS certificates, CA keys | Sealed Secrets or External Secrets |
| **CI/CD** | GitHub tokens, registry credentials | GitHub Secrets |

### Security Best Practices

1. **Principle of Least Privilege**: Each service runs with minimal required permissions
2. **Network Segmentation**: Applications isolated using Kubernetes Network Policies
3. **Encryption at Rest**: All persistent data encrypted
4. **Encryption in Transit**: TLS 1.3 for all communications
5. **Regular Rotation**: Automated certificate and credential rotation
6. **Audit Logging**: Comprehensive logging with Wazuh integration
7. **Vulnerability Scanning**: Regular container and dependency scanning

## 🛠️ Customization & Extensions

### Adding New Applications

1. **Create Helm Chart**:
   ```bash
   # Create new chart
   helm create helm/my-new-app
   
   # Customize values
   vim helm/my-new-app/values.yaml
   
   # Add to umbrella chart
   vim helm/noah-chart/Chart.yaml
   ```

2. **Integrate with Deployment**:
   ```yaml
   # Add to ansible/playbooks/04-deploy-apps.yml
   - name: Deploy My New App
     kubernetes.core.helm:
       name: my-new-app
       chart_ref: "{{ playbook_dir }}/../helm/my-new-app"
       namespace: noah
       values: "{{ my_new_app_values }}"
   ```

3. **Configure Ingress**:
   ```yaml
   # Add to ingress configuration
   - host: mynewapp.{{ domain_name }}
     http:
       paths:
       - path: /
         pathType: Prefix
         backend:
           service:
             name: my-new-app
             port: 80
   ```

### Infrastructure Provider Extension

Support for additional infrastructure providers can be added by extending the provisioning playbook:

```yaml
# Example: DigitalOcean support
- name: Create DigitalOcean droplets
  community.digitalocean.digital_ocean_droplet:
    name: "{{ item.name }}"
    size: "{{ item.size }}"
    image: "{{ item.image }}"
    region: "{{ item.region }}"
    ssh_keys: "{{ ssh_key_ids }}"
  loop: "{{ digitalocean_droplets }}"
  when: infrastructure_provider == "digitalocean"
```

### Custom Monitoring & Alerting

1. **Custom Metrics**:
   ```yaml
   # Add Prometheus ServiceMonitor
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: my-app-metrics
   spec:
     selector:
       matchLabels:
         app: my-app
     endpoints:
     - port: metrics
   ```

2. **Custom Alerts**:
   ```yaml
   # Add PrometheusRule
   apiVersion: monitoring.coreos.com/v1
   kind: PrometheusRule
   metadata:
     name: my-app-alerts
   spec:
     groups:
     - name: my-app
       rules:
       - alert: MyAppDown
         expr: up{job="my-app"} == 0
         annotations:
           summary: "My App is down"
   ```

## 🔍 Monitoring & Observability

### Metrics Stack

The NOAH platform includes comprehensive monitoring:

```yaml
# Monitoring components:
- Prometheus: Metrics collection and storage
- Grafana: Visualization and dashboards
- AlertManager: Alert routing and management
- Node Exporter: System metrics
- kube-state-metrics: Kubernetes metrics
- Custom exporters: Application-specific metrics
```

### Pre-configured Dashboards

- **Cluster Overview**: Node status, resource usage, pod health
- **Application Metrics**: Response times, error rates, throughput
- **Infrastructure**: CPU, memory, disk, network utilization
- **Security**: Failed login attempts, vulnerability alerts
- **Business**: User activity, feature usage, performance KPIs

### Log Management

```yaml
# Logging pipeline:
- Fluent Bit: Log collection and forwarding
- Elasticsearch: Log storage and indexing
- Kibana: Log visualization and analysis
- Wazuh: Security event correlation
```

### Alerting Rules

Critical alerts are configured for:
- **Infrastructure**: Node down, high resource usage, disk full
- **Application**: Service unavailable, high error rate, slow response
- **Security**: Unauthorized access, malware detection, policy violations
- **Business**: Service degradation, user experience issues

## 🚨 Troubleshooting Guide

### Common Issues & Solutions

#### 1. SSH Connection Failures
```bash
# Check SSH configuration
./script/configure-ssh.sh

# Verify key permissions
chmod 600 ~/.ssh/noah_deployment
chmod 644 ~/.ssh/noah_deployment.pub

# Test SSH connectivity
ssh -i ~/.ssh/noah_deployment -o ConnectTimeout=10 root@your-server
```

#### 2. Ansible Playbook Failures
```bash
# Run with verbose output
ansible-playbook -vvv ansible/playbooks/01-provision.yml

# Check syntax
ansible-playbook --syntax-check ansible/playbooks/01-provision.yml

# Dry run
ansible-playbook --check ansible/playbooks/01-provision.yml
```

#### 3. Kubernetes Issues
```bash
# Check cluster status
kubectl get nodes
kubectl get pods --all-namespaces

# View logs
kubectl logs -n noah deployment/gitlab
kubectl describe pod -n noah gitlab-xxx

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp
```

#### 4. Helm Deployment Problems
```bash
# List releases
helm list --all-namespaces

# Check status
helm status gitlab -n noah

# View values
helm get values gitlab -n noah

# Rollback if needed
helm rollback gitlab 1 -n noah
```

### Debug Workflows

#### Infrastructure Issues
1. Check provider API connectivity
2. Verify authentication credentials
3. Review resource quotas and limits
4. Examine network configuration

#### Application Issues
1. Check pod logs and events
2. Verify service discovery
3. Test database connectivity
4. Review ingress configuration

#### Performance Issues
1. Analyze resource usage metrics
2. Check network latency
3. Review database performance
4. Examine storage I/O

### Emergency Procedures

#### Complete Rollback
```bash
# Run cleanup playbook
ansible-playbook ansible/playbooks/99-cleanup.yml

# Or manual cleanup
kubectl delete namespace noah
helm uninstall --all
```

#### Partial Recovery
```bash
# Restart specific services
kubectl rollout restart deployment/gitlab -n noah

# Restore from backup
./script/restore-backup.sh --service=postgresql --date=2025-01-01
```

## 🌐 Domain & SSL Configuration

### DNS Setup

Configure DNS records for all NOAH services:

```bash
# A Records (replace with your ingress IP)
keycloak.noah.local      A    192.168.1.100
gitlab.noah.local        A    192.168.1.100
nextcloud.noah.local     A    192.168.1.100
mattermost.noah.local    A    192.168.1.100
grafana.noah.local       A    192.168.1.100
prometheus.noah.local    A    192.168.1.100
wazuh.noah.local        A    192.168.1.100

# Wildcard record (alternative)
*.noah.local            A    192.168.1.100
```

### SSL Certificate Management

#### Option 1: Let's Encrypt (Recommended)
```yaml
# Automatic certificate management
cert-manager:
  enabled: true
  issuer:
    email: admin@yourdomain.com
    server: https://acme-v02.api.letsencrypt.org/directory
```

#### Option 2: Custom Certificates
```bash
# Generate self-signed certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout noah.key -out noah.crt \
  -subj "/CN=*.noah.local"

# Create Kubernetes secret
kubectl create secret tls noah-tls \
  --cert=noah.crt --key=noah.key -n noah
```

## 📋 Deployment Checklist

Before running the deployment, ensure all items are completed:

### Pre-deployment
- [ ] Infrastructure resources available (CPU, RAM, Storage)
- [ ] Network connectivity to target servers
- [ ] SSH access configured and tested
- [ ] GitHub secrets configured correctly
- [ ] DNS records created
- [ ] SSL certificates prepared
- [ ] Ansible Vault password set
- [ ] Configuration files customized

### Post-deployment Verification
- [ ] All pods running successfully
- [ ] Services accessible via ingress
- [ ] SSL certificates valid
- [ ] Authentication working (Keycloak)
- [ ] Applications integrated with SSO
- [ ] Monitoring dashboards accessible
- [ ] Backup systems operational
- [ ] Security scanning enabled

## 🔄 CI/CD Workflow Details

### GitHub Actions Workflow

The main workflow (`.github/workflows/deploy.yml`) consists of 5 parallel jobs after initial setup:

```yaml
# Job sequence:
1. Infrastructure (01-provision.yml)
   ├── Create VMs/instances
   ├── Configure networking
   └── Setup SSH access

2. SSO Foundation (02-install-k8s.yml + 03-configure-cluster.yml)
   ├── Install Kubernetes
   ├── Configure cluster
   └── Deploy core services

3. Applications (04-deploy-apps.yml)
   ├── Deploy GitLab
   ├── Deploy Nextcloud
   ├── Deploy Mattermost
   └── Configure integrations

4. Verification (05-verify-deployment.yml)
   ├── Health checks
   ├── Connectivity tests
   └── Generate report

5. Cleanup (99-cleanup.yml - on failure)
   ├── Remove resources
   ├── Clean up secrets
   └── Generate failure report
```

### Workflow Triggers

```yaml
# Automatic triggers:
- Push to main branch
- Pull request to main
- Manual workflow dispatch
- Scheduled runs (weekly)

# Environment-specific triggers:
- Development: Any branch push
- Staging: Release branch
- Production: Tag creation
```

## 🚀 Performance Optimization

### Resource Allocation

Recommended minimum resources per environment:

| Environment | Nodes | CPU per Node | RAM per Node | Storage |
|-------------|-------|-------------|-------------|---------|
| Development | 1 | 4 cores | 8 GB | 100 GB |
| Staging | 2 | 4 cores | 16 GB | 200 GB |
| Production | 3+ | 8 cores | 32 GB | 500 GB |

### Scaling Configuration

```yaml
# Horizontal Pod Autoscaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gitlab-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gitlab
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Storage Optimization

```yaml
# Storage classes for different workloads
- Fast SSD: Databases, high-performance applications
- Standard SSD: General application storage
- Slow HDD: Backup and archival storage
```

## � Backup & Disaster Recovery

### Automated Backups

```bash
# Database backups
kubectl create cronjob postgresql-backup \
  --image=postgres:15 \
  --schedule="0 2 * * *" \
  -- pg_dump -h postgresql noah > /backup/noah-$(date +%Y%m%d).sql

# Application data backups
kubectl create cronjob app-backup \
  --image=restic/restic \
  --schedule="0 3 * * *" \
  -- restic backup /data
```

### Recovery Procedures

1. **Database Recovery**:
   ```bash
   # Restore from backup
   kubectl exec -it postgresql-0 -- psql -d noah < backup-20250130.sql
   ```

2. **Application Recovery**:
   ```bash
   # Restore persistent volumes
   kubectl apply -f backup/pvc-restore.yaml
   ```

3. **Complete Infrastructure Recovery**:
   ```bash
   # Re-run deployment with restore flag
   ansible-playbook ansible/playbooks/01-provision.yml --extra-vars "restore_mode=true"
   ```

## 🤝 Contributing & Development

### Development Workflow

1. **Fork & Clone**:
   ```bash
   git clone https://github.com/your-username/NOAH.git
   cd NOAH
   git remote add upstream https://github.com/Engelnicolas/NOAH.git
   ```

2. **Create Feature Branch**:
   ```bash
   git checkout -b feature/new-functionality
   ```

3. **Test Changes**:
   ```bash
   # Validate Ansible syntax
   ansible-playbook --syntax-check ansible/playbooks/*.yml
   
   # Test with check mode
   ansible-playbook --check ansible/playbooks/04-deploy-apps.yml
   
   # Run dependency tests
   ./script/test-dependencies.sh
   ```

4. **Submit Changes**:
   ```bash
   git add .
   git commit -m "feat: add new functionality"
   git push origin feature/new-functionality
   ```

### Code Standards

- **Ansible**: Follow Ansible best practices and use `ansible-lint`
- **Helm**: Use Helm chart best practices, validate with `helm lint`
- **Documentation**: Update relevant docs with changes
- **Testing**: Include tests for new functionality
- **Security**: Follow security guidelines, no hardcoded secrets

### Review Process

1. Automated CI checks must pass
2. Security scan must be clean
3. Documentation must be updated
4. At least one maintainer review required
5. All discussions resolved

## 📞 Support & Community

### Getting Help

1. **Documentation**: Check all docs in the `docs/` directory
2. **Issues**: Create GitHub issue with detailed information
3. **Discussions**: Use GitHub Discussions for questions
4. **Security**: Email security@noah.local for security issues

### Community Resources

- **Project Homepage**: https://github.com/Engelnicolas/NOAH
- **Documentation**: https://noah-platform.readthedocs.io
- **Community Chat**: https://mattermost.noah.local/noah-community
- **Support Forum**: https://discourse.noah.local

### Reporting Issues

When reporting issues, include:
- NOAH version/commit hash
- Environment details (OS, Kubernetes version)
- Error messages and logs
- Steps to reproduce
- Expected vs actual behavior

## 📚 Additional Resources

### Technical Documentation
- [Kubespray Documentation](https://kubespray.io/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- [Helm Chart Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

### Security Resources
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Container Security](https://owasp.org/www-project-container-security/)

### Monitoring & Observability
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [Kubernetes Monitoring Guide](https://kubernetes.io/docs/tasks/debug-application-cluster/resource-usage-monitoring/)

---

**NOAH Platform** - Comprehensive DevOps Infrastructure for Modern Organizations  
*Last Updated: July 30, 2025*  
*Version: 2.0.0*
