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

### Core Components

- 🛠️ **Ansible** - Configuration management and service deployment
- ☸️ **Kubernetes + Helm** - Container orchestration and application lifecycle  
- 🔒 **Samba4 AD & Keycloak** - Centralized identity and access management
- 📦 **Nextcloud, Mattermost** - Secure collaboration and communication
- 🛡️ **Wazuh, OpenEDR, OpenVPN** - Comprehensive security monitoring
- 📈 **Prometheus & Grafana** - Monitoring and observability
- 🚀 **GitLab CI/CD** - Continuous integration and deployment

---

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster with kubectl configured
- Helm 3.x installed
- 8GB+ RAM available

### Deploy NOAH Platform
```bash
# Clone the repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Deploy core services (uses root security context for compatibility)
./Script/noah-infra deploy -m root

# Check deployment status
kubectl get pods -n noah

# View logs if needed
./Script/noah-logs --latest
```

### Access Services
- **Keycloak**: https://keycloak.your-domain.com
- **Nextcloud**: https://nextcloud.your-domain.com  
- **Mattermost**: https://mattermost.your-domain.com
- **Grafana**: https://grafana.your-domain.com

---

## 📚 Documentation

- **📖 [USER_GUIDE.md](docs/USER_GUIDE.md)**: Complete deployment and configuration guide
- **🤝 [CONTRIBUTING.md](CONTRIBUTING.md)**: How to contribute to the project

---

## 🏗️ Architecture

### Security & Identity Management
- **Single Sign-On (SSO)**: Unified authentication across all services
- **Role-Based Access Control**: Granular permissions and user management
- **Multi-Factor Authentication**: TOTP, WebAuthn support
- **Comprehensive Monitoring**: Real-time threat detection and alerting

### Deployment Options
- **Development**: Single-node Kubernetes or Docker Compose
- **Production**: Multi-cluster with high availability
- **Security Modes**: Root (compatibility) or secure (restricted) contexts
- **Monitoring**: Built-in error logging and deployment tracking

---

## 🎭 Use Cases

### 👤 Individual Developers
Learn DevSecOps, test automation pipelines, experiment with enterprise tools

### 🧑‍💼 Small-Medium Business  
Replace expensive SaaS tools with self-hosted alternatives, 60-80% cost savings

### 🏢 Enterprise Organizations
Hybrid cloud infrastructure with compliance requirements and custom integrations

### 🏛️ Government/Public Sector
Secure, auditable infrastructure with data sovereignty and regulatory compliance

### 🎓 Educational Institutions
Digital learning platform with hands-on experience in enterprise technologies

---

## 👨‍💻 Author

**Nicolas Engel**  
📧 Email: [contact@nicolasengel.fr](mailto:contact@nicolasengel.fr)  
🌐 Website: [nicolasengel.fr](https://nicolasengel.fr)  

*Passionate about cybersecurity, open-source infrastructure, DevSecOps, and building secure, scalable solutions for organizations of all sizes.*

---

## 🏆 Acknowledgments

Special thanks to the open-source community and the maintainers of all the incredible tools that make N.O.A.H possible:

- **Red Hat** for Ansible
- **CNCF** for Kubernetes, Prometheus, and the cloud-native ecosystem
- **Keycloak Team** for identity and access management
- **Nextcloud GmbH** for secure collaboration tools
- **Elastic** for the ELK stack components

---
