# 🚀 NOAH - Network Operations & Automation Hub

<div align="center">

[![Ansible](https://img.shields.io/badge/Ansible-2.16+-red.svg)](https://www.ansible.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Kubernetes](https://img.shields.io/badge/Platform-Kubernetes-blueviolet.svg)](https://kubernetes.io/)
[![Version](https://img.shields.io/badge/Version-0.2.1-green.svg)](https://github.com/Engelnicolas/NOAH/releases)
[![SOPS](https://img.shields.io/badge/Secrets-SOPS%20%2B%20Age-orange.svg)](https://github.com/mozilla/sops)
[![Maintained](https://img.shields.io/badge/Maintained-Yes-brightgreen.svg)](https://github.com/Engelnicolas/NOAH/commits/main)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue.svg)](https://github.com/features/actions)

*Modern infrastructure platform with Ansible/Helm CI/CD pipelines and secrets management for deploying enterprise-grade open-source solutions*

</div>

---

## ✨ Overview

**NOAH v0.2.1** is a next-generation infrastructure automation platform that uses **modern CI/CD pipelines** to deploy a complete ecosystem of enterprise-level open-source services.

### 🏗️ Architecture & Components

#### 🔐 Identity Management
- **Samba4 Active Directory**: Centralized directory with LDAP authentication
- **Keycloak**: Modern identity provider with SSO and federation

#### 📦 Collaboration Platforms
- **Nextcloud**: Secure file sharing and collaboration
- **Mattermost**: Team messaging with DevOps integrations
- **GitLab**: Software forge with integrated CI/CD

#### 🛡️ Security & Monitoring
- **Wazuh**: SIEM and intrusion detection
- **OpenEDR**: Endpoint threat detection and response
- **OAuth2 Proxy**: Reverse proxy with OAuth2 authentication

#### 📈 Observability
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Advanced visualization and dashboards

#### ⚙️ Modern Infrastructure
- **Ansible + Kubespray**: Automated Kubernetes v1.28.2 deployment
- **GitHub Actions**: CI/CD pipeline with automatic deployment
- **Helm 3.13+**: Cloud-native application management
- **SOPS + Age**: Modern secrets management with GitOps integration

---

## 🎯 Main Use Cases

### 👤 Developers & DevOps
- **Learning**: Master DevSecOps and automation pipelines
- **Sandbox**: Test enterprise tools in a secure environment
- **Prototyping**: Experiment with cloud-native architectures

### 🧑‍💼 SMEs & Startups
- **Savings**: 60-80% savings vs proprietary SaaS solutions
- **Control**: Complete data control and GDPR compliance
- **Scalability**: Infrastructure that grows with your business

### 🏢 Enterprises
- **Hybrid**: Hybrid cloud infrastructure with compliance requirements
- **Integrations**: Custom integrations and connectors
- **Governance**: Complete audit and operation traceability

### 🏛️ Public Sector
- **Sovereignty**: Complete data and infrastructure control
- **Compliance**: Respect for sector regulations
- **Security**: Secure and audited architecture
---

## �🚀 Quick Start (5 minutes)

### 🔧 Prerequisites
- **Servers**: 2+ Ubuntu 24.04 LTS servers (8GB RAM, 50GB disk)
- **Access**: SSH with passwordless sudo
- **GitHub**: Repository with Actions enabled
- **Local**: Git, Ansible 2.16+, SOPS 3.8+, Age 1.1+, kubectl (optional)

### ⚡ Express Installation

#### 1. Automatic Configuration
```bash
# Clone and configure
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Initialize NOAH CLI environment
./noah init

# Automatic configuration with SOPS setup
./noah configure --auto

# Or interactive mode for customization
./noah configure
```

#### 2. Secrets Management Configuration
```bash
# Configure SOPS for secrets management
noah secrets status     # Check SOPS installation and config

# Generate Age encryption keys (if needed)
age-keygen -o ~/.config/sops/age/keys.txt

# Edit secrets with SOPS encryption
noah secrets edit

# Validate secrets configuration
noah secrets validate
```

#### 3. GitHub Actions Configuration
Copy the values displayed by the script to **GitHub secrets**:

| Secret | Default Value | Description |
|--------|---------------|-------------|
| `SSH_PRIVATE_KEY` | *Displayed by script* | SSH private key for server access |
| `SOPS_AGE_KEY` | *From ~/.config/sops/age/keys.txt* | Age private key for SOPS decryption |
| `MASTER_HOST` | `192.168.1.10` | Master server IP |

#### 4. SSH Key Deployment
```bash
# Copy public key to your servers
ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@192.168.1.10
ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@192.168.1.12
```

#### 5. Pipeline Launch
```bash
git add .
git commit -m "Configure NOAH pipeline with SOPS secrets"
git push origin main
```

The GitHub Actions pipeline automatically launches and deploys:
1. **Infrastructure** provisioning
2. **Kubernetes** installation with Kubespray
3. **Cluster** configuration (ingress, storage, monitoring)
4. **Application** deployment via Helm with SOPS-encrypted secrets

### 🎯 Default Configuration

#### Servers
- **Master**: `192.168.1.10`
- **Worker**: `192.168.1.12`
- **Ingress**: `192.168.1.10`

#### Domains
- **Base**: `noah.local`
- **Keycloak**: `keycloak.noah.local`
- **GitLab**: `gitlab.noah.local`
- **Nextcloud**: `nextcloud.noah.local`
- **Mattermost**: `mattermost.noah.local`
- **Grafana**: `grafana.noah.local`

#### Default Accounts
| Service | Username | Password |
|---------|----------|----------|
| Keycloak | `admin` | *Generated in secrets* |
| GitLab | `root` | *Generated in secrets* |
| Nextcloud | `admin` | *Generated in secrets* |
| Grafana | `admin` | *Generated in secrets* |

> 🔐 **Note**: All passwords are automatically generated and stored securely with SOPS encryption. Use `noah secrets view` to see the actual values.

### 🌐 Local DNS Configuration

Add to your `/etc/hosts`:
```bash
192.168.1.10 keycloak.noah.local
192.168.1.10 gitlab.noah.local
192.168.1.10 nextcloud.noah.local
192.168.1.10 mattermost.noah.local
192.168.1.10 grafana.noah.local
```

### ✅ Access Deployed Services

- **🔐 Keycloak**: https://keycloak.noah.local
- **🦊 GitLab**: https://gitlab.noah.local  
- **☁️ Nextcloud**: https://nextcloud.noah.local
- **💬 Mattermost**: https://mattermost.noah.local
- **📊 Grafana**: https://grafana.noah.local

---

## 🛠️ NOAH CLI v0.2.1

### Essential Commands
```bash
# Modern CLI
./noah --help                    # Complete help
./noah --version                 # Version: v0.2.1

# Environment setup
./noah init                      # Initialize environment
./noah configure --auto          # Automatic configuration
./noah status --all              # Complete system status

# Deployment management
./noah deploy --profile prod     # Production deployment
./noah validate                  # Validate configuration
./noah test                      # Connectivity tests
```

### SOPS Secrets Management
```bash
# Modern secrets management with SOPS
./noah secrets status            # Complete SOPS diagnostic
./noah secrets edit              # Edit secrets (auto-encrypted)
./noah secrets view              # View decrypted secrets
./noah secrets validate          # Validate SOPS configuration
./noah secrets generate          # Generate new secure secrets
./noah secrets rotate            # Rotate existing secrets
```

### Service Management
```bash
# Service lifecycle
./noah start                     # Start all services
./noah stop                      # Stop all services
./noah restart                   # Restart all services
./noah logs --service keycloak   # Service logs
./noah health                    # System health check
```

### Monitoring and Debugging
```bash
# Status verification
kubectl get pods -n noah
kubectl get ingress -n noah

# View logs
kubectl logs -n noah deployment/keycloak
kubectl logs -n noah deployment/gitlab
```

---

## 🔧 Customization

### Change Server IPs
```bash
# Edit inventory
nano ansible/inventory/mycluster/hosts.yaml

# Or use configuration script
MASTER_IP=10.0.0.10 WORKER_IP=10.0.0.11 ./script/configure-pipeline.sh --auto
```

### Change Domain
```bash
# Edit Helm values
nano helm/noah-common/values.yaml

# Change line: domain: noah.local
# For example: domain: noah.mycompany.com
```

### Modify Secrets (SOPS)
```bash
# Modern approach with SOPS (recommended)
noah secrets edit               # Direct SOPS editing
noah secrets view               # View current secrets
noah secrets status             # Verify SOPS configuration

# Legacy support (if migrating from Ansible Vault)
noah secrets validate           # Check encryption status
```

### Advanced Configuration
```bash
# Custom domain configuration
nano helm/noah-common/values.yaml
# Change: domain: noah.local to domain: mycompany.com

# SOPS configuration for multiple files
nano .sops.yaml
# Add custom encryption rules

# Age key management
age-keygen -o ~/.config/sops/age/keys.txt  # Generate new keys
noah secrets rotate                         # Apply key rotation
```

---

## 📚 Documentation

- **[Secrets Management](docs/SECRETS_MANAGEMENT.md)**: SOPS integration and security best practices
- **[CI/CD Pipeline](docs/PIPELINE_CI_CD.md)**: Modern pipeline architecture
- **[NOAH CLI](docs/NOAH_CLI.md)**: Complete CLI guide with SOPS commands
- **[Domain Configuration](docs/DOMAIN_CONFIGURATION.md)**: DNS and SSL certificates
- **[Security](docs/SECURITY.md)**: Security hardening and best practices

---

## 📜 License

This project is licensed under **GPL v3**. See [LICENSE](LICENSE) for more details.

## 👨‍💻 Author

**Nicolas Engel**  
📧 Email: [contact@nicolasengel.fr](mailto:contact@nicolasengel.fr)  
🌐 Website: [nicolasengel.fr](https://nicolasengel.fr)  
💼 LinkedIn: [nicolas-engel](https://www.linkedin.com/in/nicolas-engel-france/)

*Expert in cybersecurity, cloud-native infrastructure, and DevSecOps. Passionate about secure and scalable open-source solutions.*

---

## 🏆 Acknowledgments

Thanks to the open-source community and maintainers of the tools that make NOAH possible:

- **⚙️ Ansible** for infrastructure automation
- **☸️ CNCF** for Kubernetes, Prometheus, and the cloud-native ecosystem
- **⎈ Helm** for Kubernetes application management
- **🔐 Mozilla SOPS** for modern secrets management
- **🔑 Age** for simple and secure encryption
- **🔐 Keycloak** for identity and access management
- **☁️ Nextcloud** for secure collaboration
- **💬 Mattermost** for team communication
- **📊 Grafana** for visualization and observability
- **🛡️ Wazuh** for security monitoring
- **🐙 GitHub** for CI/CD pipelines

