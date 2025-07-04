# N.O.A.H - Next Open-source Architecture Hub

<div align="center">

![CI/CD](https://img.shields.io/badge/pipeline-gitlab-orange)
![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue)
![Kubernetes](https://img.shields.io/badge/containerized-Kubernetes-blueviolet)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![Maintenance](https://img.shields.io/badge/maintained-yes-brightgreen)

*A comprehensive, automated infrastructure platform for deploying secure, scalable open-source solutions*

</div>

---

## 🌟 Overview

**N.O.A.H** (Next Open-source Architecture Hub) is a production-ready infrastructure automation platform that deploys and manages a complete secure information system using industry-standard open-source tools. It provides a unified solution for organizations seeking to deploy enterprise-grade services with full control over their data and infrastructure.

### Key Features

This project automates the full-stack deployment of an open source secure information system using:
- 🏗️ **Terraform** for infrastructure provisioning and state management
- 🛠️ **Ansible** for configuration management and service deployment
- ☸️ **Kubernetes + Helm** for container orchestration and application lifecycle
- 🔒 **Samba4 AD & Keycloak** for centralized identity and access management
- 📦 **Nextcloud, Mattermost** for secure collaboration and communication
- 🛡️ **Wazuh, OpenEDR, OpenVPN, UFW** for comprehensive security monitoring
- 📈 **Prometheus & Grafana** for monitoring and observability
- 🚀 **GitLab CI/CD & GitHub Actions** for continuous integration and deployment

### 🎯 Why Choose N.O.A.H?

- **Complete Automation**: Zero-touch deployment from infrastructure to applications
- **Security-First**: Built-in security controls, monitoring, and compliance features
- **Vendor Independence**: 100% open-source stack with no vendor lock-in
- **Scalable Architecture**: Supports everything from single-node to multi-cluster deployments
- **Production Ready**: Battle-tested configurations with monitoring and backup strategies

---

## 🎯 Project Objectives

- **🤖 Full Automation**: Complete infrastructure, configuration, and service rollout without manual intervention
- **🌍 Environment Flexibility**: Seamless deployment across development, staging, and production environments
- **🔐 Security & Compliance**: Role-based security, single sign-on via LDAP/OIDC, and comprehensive audit trails
- **🌐 Network Architecture**: Dynamic DNS management, secure networking, and VPN-based access control
- **🔄 DevOps Integration**: Automated testing, deployment validation, and rollback capabilities
- **📊 Observability**: Full-stack monitoring, alerting, and performance metrics
- **🏗️ Infrastructure as Code**: Version-controlled, reproducible infrastructure management

---

## 🔧 Components Overview

| Category | Components | Purpose |
|----------|------------|---------|
| **Automation** | Ansible, GitLab CI, GitHub Actions | Configuration management, CI/CD pipelines |
| **Identity & Access** | Samba4 AD, Keycloak (OIDC/SAML) | Centralized authentication, SSO, user management |
| **Collaboration** | Nextcloud, Mattermost | File sharing, team communication, document collaboration |
| **Monitoring** | Prometheus, Grafana, Alertmanager | Metrics collection, visualization, alerting |
| **Security** | OpenVPN, UFW, Wazuh, OpenEDR | VPN access, firewall, SIEM, endpoint detection |
| **Container Platform** | Kubernetes, Helm, Docker | Container orchestration, package management |
| **Storage** | Persistent Volumes, NFS, Local Storage | Data persistence, backup, disaster recovery |

---

## 🚀 Quick Start

### Prerequisites

- **Operating System**: Linux (Ubuntu 20.04+ or CentOS 8+ recommended)
- **Hardware**: Minimum 16GB RAM, 4 CPU cores, 100GB storage
- **Software**: Docker, Terraform (≥1.0), Ansible (≥2.9), kubectl
- **Network**: Internet access for initial setup and package downloads

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/noah.git
cd noah

# Make setup script executable and run initial configuration
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2. Infrastructure Deployment

```bash
# Initialize Terraform workspace
cd terraform/
terraform init

# Plan and apply infrastructure changes
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"
```

### 3. Service Configuration

```bash
# Deploy all services using Ansible
cd ../ansible/
ansible-playbook -i inventories/dev/hosts deploy_all.yml

# Verify deployment status
ansible-playbook -i inventories/dev/hosts test_post_deploy.yml
```

### 4. Access Your Services

Once deployment is complete, access your services at:
- **Keycloak**: `https://auth.your-domain.com`
- **Nextcloud**: `https://cloud.your-domain.com`
- **Mattermost**: `https://chat.your-domain.com`
- **Grafana**: `https://monitoring.your-domain.com`

> 💡 **Tip**: Check the `docs/` folder for detailed configuration guides and troubleshooting.

---

## 🎭 Use Cases by Context

### 👤 Individual Developer / DevOps Engineer
**Scenario**: Personal learning lab or development workspace
- **Deployment**: Single-node Kubernetes (Minikube/K3s) or Docker Compose
- **Benefits**: Learn DevSecOps, test automation pipelines, experiment with tools
- **Resources**: Laptop/workstation with 8GB+ RAM
- **Timeline**: 2-4 hours for complete setup

### 🧑‍💼 Small to Medium Business (10-100 employees)
**Scenario**: Replace expensive SaaS tools with self-hosted alternatives
- **Deployment**: Small Kubernetes cluster or VM-based deployment
- **Benefits**: Data sovereignty, cost reduction, customization flexibility
- **Features**: Centralized SSO, secure file sharing, team communication
- **ROI**: 60-80% cost savings compared to commercial alternatives

### 🏢 Enterprise Organization (500+ employees)
**Scenario**: Hybrid cloud infrastructure with compliance requirements
- **Deployment**: Multi-cluster Kubernetes with high availability
- **Benefits**: Full compliance control, custom integrations, scalability
- **Features**: Advanced RBAC, audit logging, disaster recovery
- **Integration**: Existing AD/LDAP, monitoring systems, backup solutions

### 🏛️ Government / Public Sector
**Scenario**: Secure, auditable infrastructure for public services
- **Deployment**: Air-gapped or VPN-only access deployment
- **Benefits**: Data sovereignty, compliance with regulations, transparency
- **Security**: Enhanced monitoring, encrypted communications, access controls
- **Compliance**: GDPR, HIPAA, government security standards

### 🎓 Educational Institutions
**Scenario**: Digital learning platform and administration tools
- **Deployment**: Campus-wide deployment with student/faculty access
- **Benefits**: Cost-effective digital transformation, learning opportunities
- **Features**: Classroom collaboration, secure communication, file management
- **Educational Value**: Hands-on experience with enterprise technologies

### � Healthcare Organizations
**Scenario**: HIPAA-compliant collaboration and file sharing
- **Deployment**: Secure, isolated network with strict access controls
- **Benefits**: Patient data protection, secure communication, compliance
- **Security**: End-to-end encryption, audit trails, access monitoring
- **Integration**: EHR systems, medical imaging, secure messaging

---

## 🔐 Security & Identity Management

### Single Sign-On (SSO) Architecture

N.O.A.H implements a comprehensive identity management system using:

- **🏢 Samba4 Active Directory**: Primary identity provider with LDAP protocol
- **🔑 Keycloak**: Modern identity broker supporting OIDC, SAML, and social logins
- **🛡️ Role-Based Access Control (RBAC)**: Granular permissions for all services
- **🔒 Multi-Factor Authentication (MFA)**: TOTP, WebAuthn, and SMS support

### Integrated Services with SSO

All platform services are pre-configured with Keycloak integration:

| Service | Protocol | Features |
|---------|----------|----------|
| **Nextcloud** | OIDC | File sharing, calendar, contacts |
| **Mattermost** | OIDC | Team messaging, file sharing |
| **Grafana** | OIDC | Monitoring dashboards, alerting |
| **Wazuh** | SAML | Security monitoring, threat detection |
| **GitLab** | OIDC | Source code management, CI/CD |

### Security Hardening Features

- **🔥 Firewall Rules**: Automated UFW configuration with service-specific rules
- **🛡️ Network Segmentation**: Isolated networks for different service tiers
- **🔍 Security Monitoring**: Real-time threat detection with Wazuh SIEM
- **📊 Compliance Reporting**: Automated compliance checks and reporting
- **🚫 Zero-Trust Architecture**: Default-deny policies with explicit allow rules

---

## 📊 Monitoring & Operations

### Observability Stack

- **📈 Prometheus**: Metrics collection and time-series database
- **📊 Grafana**: Visualization, dashboards, and alerting
- **🔍 Elasticsearch**: Log aggregation and search (via Wazuh)
- **📋 Alertmanager**: Alert routing and notification management

### Pre-configured Dashboards

- **Infrastructure Overview**: CPU, memory, disk, and network metrics
- **Kubernetes Cluster**: Pod status, resource utilization, cluster health
- **Application Performance**: Service response times, error rates, throughput
- **Security Dashboard**: Failed logins, suspicious activities, compliance status

### Automated Backup & Recovery

- **📦 Velero**: Kubernetes backup and disaster recovery
- **💾 Database Backups**: Automated PostgreSQL and MySQL backups
- **🔄 Configuration Backups**: Automated backup of Ansible inventories and Terraform state
- **⚡ Point-in-Time Recovery**: Granular recovery options for critical data

---

## 📚 Documentation & Support

### Available Documentation

- **📖 [USER_GUIDE.md](docs/USER_GUIDE.md)**: Complete step-by-step deployment guide


### Getting Help

- **🐛 Issues**: Report bugs or request features via [GitHub Issues](https://github.com/your-org/noah/issues)
- **💬 Discussions**: Join the community in [GitHub Discussions](https://github.com/your-org/noah/discussions)
- **📧 Email**: Contact the maintainers at noah-support@your-domain.com
- **📖 Wiki**: Additional resources and community contributions in the [project wiki](https://github.com/your-org/noah/wiki)

---

## 🤝 Contributing

We welcome contributions from the community! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) guide for:

- **🔀 Code Contributions**: Pull request guidelines and development workflow
- **📝 Documentation**: Improving and expanding documentation
- **🐛 Bug Reports**: How to report issues effectively
- **💡 Feature Requests**: Proposing new features and enhancements
- **🧪 Testing**: Contributing to our test suite

### Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/your-username/noah.git
cd noah

# Set up development environment
./scripts/dev-setup.sh

# Run tests
./scripts/run-tests.sh
```

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**.

- ✅ **Freedom to Use**: Use the software for any purpose
- ✅ **Freedom to Study**: Examine and learn from the source code
- ✅ **Freedom to Modify**: Adapt the software to your needs
- ✅ **Freedom to Share**: Distribute copies and modifications

See the [LICENSE](LICENSE) file for complete terms and conditions.

### Third-Party Licenses

This project includes components with their own licenses:
- **Kubernetes**: Apache License 2.0
- **Terraform**: Mozilla Public License 2.0
- **Ansible**: GNU General Public License v3.0
- **Prometheus**: Apache License 2.0

---

## 👨‍💻 Author

**Nicolas Engel**  
📧 Email: [contact@nicolasengel.fr](mailto:contact@nicolasengel.fr)  
🌐 Website: [nicolasengel.fr](https://nicolasengel.fr)  

*Passionate about cybersecurity, open-source infrastructure, DevSecOps, and building secure, scalable solutions for organizations of all sizes.*

---

## 🏆 Acknowledgments

Special thanks to the open-source community and the maintainers of all the incredible tools that make N.O.A.H possible:

- **HashiCorp** for Terraform
- **Red Hat** for Ansible
- **CNCF** for Kubernetes, Prometheus, and the cloud-native ecosystem
- **Keycloak Team** for identity and access management
- **Nextcloud GmbH** for secure collaboration tools
- **Elastic** for the ELK stack components

---

<div align="center">

**⭐ If you find N.O.A.H useful, please give it a star on GitHub! ⭐**

Built with ❤️ by the open-source community

</div>