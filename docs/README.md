# 🚀 NOAH  - Network Operations & Automation Hub

**NOAH** (Network Operations & Automation Hub) is a comprehensive Kubernetes infrastructure platform with integrated SSO, networking, and security automation.


## **What is NOAH?**

NOAH provides a complete infrastructure stack:

- **🔐 Authentik SSO** - Identity and access management
- **🌐 Cilium CNI** - Advanced networking with ingress
- **🔒 Canonical Secrets Store** - Single authoritative encrypted secrets file (Age/SOPS protected)
- **🔄 Automated Deployment** - Single-command infrastructure setup
- **🧪 Testing Suite** - Built-in validation and health checks
- **🚀 CI/CD Ready** - GitHub Actions workflows included

## **Use Cases**

NOAH is designed for various infrastructure scenarios:

### **🏢 Small and Medium Enterprise & Organizations**
- **Corporate SSO** - Centralized authentication for all internal applications
- **Development Teams** - Rapid Kubernetes environment provisioning
- **IT Infrastructure** - Self-hosted identity provider with SSO integration
- **Security Compliance** - Encrypted secrets management and audit trails

### **🎓 Educational & Research**
- **Computer Science Labs** - Teaching Kubernetes, networking, and security
- **Research Projects** - Isolated, secure computing environments
- **Student Authentication** - Campus-wide SSO for academic applications
- **Lab Management** - Quick setup/teardown of experimental clusters

### **☁️ Cloud & DevOps**
- **Multi-Cloud Deployment** - Consistent infrastructure across providers
- **Development Environments** - Rapid dev/test cluster provisioning
- **CI/CD Integration** - Automated testing and deployment pipelines
- **Container Orchestration** - Production-ready Kubernetes with networking

## **Quick Start**

### **Single Command Deployment**
```bash

# Clone repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Install Python dependencies
pip install -r Scripts/requirements.txt

# Create the cluster
python noah.py cluster create --name your-cluster --domain your-domain.com

# Complete infrastructure deployment
python noah.py deploy all --domain your-domain.com

# Check status
python noah.py status

# Get credentials
python noah.py password show

# Test deployment
python noah.py test sso
```

## **Architecture Overview**

```
┌─────────────────────────────────────────┐
│               Users/Apps                │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│            Load Balancer                │
│             (MetalLB)                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Ingress Controller              │
│            (Cilium)                     │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│           Authentik SSO                 │
│    (Identity & Access Management)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Kubernetes Cluster              │
│              (K3s)                      │
└─────────────────────────────────────────┘
```

## **Service Access**

After deployment, access services at:

- **Authentik SSO**: `https://auth.your-domain.com`
- **Cilium Hubble**: `https://hubble.your-domain.com`

Retrieve Authentik credentials via: `python noah.py password show`

Rotate Authentik admin password (versioned with metadata):
```bash
python noah.py password new
# or during deployment
python noah.py deploy authentik --regenerate-password
```

Each secret carries metadata `{ value, version, rotated_at }` and an integrity hash is computed deterministically across services.

## **Requirements**

### **System**
- **OS**: Ubuntu 20.04+ (recommended)
- **Resources**: 4+ CPU cores, 8GB+ RAM, 50GB+ storage
- **Network**: Internet connectivity for component downloads

---
Apache 2.0 licence - Made with ❤️