# 🚀 NOAH Documentation

Welcome to **NOAH** (Network Operations & Automation Hub) - a comprehensive Kubernetes infrastructure platform with integrated SSO, networking, and security automation.


## 🏗️ **What is NOAH?**

NOAH provides a complete infrastructure stack:

- **🔐 Authentik SSO** - Identity and access management
- **🌐 Cilium CNI** - Advanced networking with ingress
- **🔒 SOPS Encryption** - Secure secret management with Age keys
- **🔄 Automated Deployment** - Single-command infrastructure setup
- **🧪 Testing Suite** - Built-in validation and health checks
- **🚀 CI/CD Ready** - GitHub Actions workflows included

## ⚡ **Quick Start**

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

## 🎯 **Architecture Overview**

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

## 🌐 **Service Access**

After deployment, access services at:

- **Authentik SSO**: `https://auth.your-domain.com`
- **Cilium Hubble**: `https://hubble.your-domain.com`

Default credentials available via: `python noah.py password show`

## 📋 **Requirements**

### **System**
- **OS**: Ubuntu 20.04+ (recommended)
- **Resources**: 4+ CPU cores, 8GB+ RAM, 50GB+ storage
- **Network**: Internet connectivity for component downloads

---
## Apache 2.0 licence
Made with ❤️
---