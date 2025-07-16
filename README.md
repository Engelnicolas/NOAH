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
- 8GB+ RAM available (see [Technical Requirements](docs/TECHNICAL_REQUIREMENTS.md) for detailed specifications)

### Deploy NOAH Platform
```bash
# Clone the repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Initialize infrastructure
./Script/noah infra setup

# Deploy complete NOAH stack (11 Helm charts)
./Script/noah infra deploy

# Check deployment status
./Script/noah infra status

# Deploy monitoring stack
./Script/noah monitoring deploy

# View logs if needed
./Script/noah logs latest
```

### Access Services
- **Keycloak**: https://keycloak.your-domain.com
- **Nextcloud**: https://nextcloud.your-domain.com  
- **Mattermost**: https://mattermost.your-domain.com
- **Grafana**: https://grafana.your-domain.com

---

## 📚 Documentation

- **📖 [USER_GUIDE.md](docs/USER_GUIDE.md)**: Complete deployment and configuration guide
- **🔧 [TECHNICAL_REQUIREMENTS.md](docs/TECHNICAL_REQUIREMENTS.md)**: Detailed system requirements and specifications
- **📊 [DEPLOYMENT_PROFILES.md](docs/DEPLOYMENT_PROFILES.md)**: Comparison of deployment profiles (minimal vs root)
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

## 🆕 What's New in Version 4.0.0

### 🔧 Modernized CLI Interface
- **Unified Command Structure**: Single `./noah` entry point for all operations
- **Enhanced Help System**: Comprehensive documentation with examples
- **Color-coded Output**: Visual indicators for better user experience
- **Smart Script Routing**: Automatic validation and execution of specialized scripts

### 🐍 Python Migration
- **Infrastructure Management**: `noah-deploy.py` with 11 Helm charts deployment
- **Monitoring Stack**: `noah-monitoring.py` for Prometheus/Grafana management
- **Code Quality**: `noah-linter.py` unified linting with Super-Linter integration
- **Auto-fixing**: `noah-fix.py` for intelligent issue resolution

### 📊 Enhanced Monitoring
- **Structured Logging**: Better error tracking and debugging
- **Deployment Phases**: Organized 3-phase deployment strategy
- **Status Validation**: Real-time health checks and validation
- **Log Management**: Centralized log viewing and analysis

### 🛠️ Developer Experience
- **Makefile 3.0.0**: Professional project management interface
- **Comprehensive Documentation**: Detailed script documentation and examples
- **Error Handling**: Robust error recovery and user guidance
- **Validation Tools**: Automated YAML, Ansible, and Helm validation

### 📈 Available Commands
```bash
# Infrastructure lifecycle
./noah infra setup|deploy|status|teardown

# Monitoring operations  
./noah monitoring deploy|status|teardown

# Code quality and validation
./noah linting setup|lint|report
./noah fix yaml|shell|all
./noah validate yaml|ansible|helm|all

# Log management
./noah logs latest|errors|summary|clean
```
