# NOAH Documentation

Welcome to the NOAH (Network Operations and Authentication Hub) infrastructure documentation. This comprehensive guide covers everything you need to deploy, manage, and troubleshoot your NOAH platform.

## 📚 Documentation Index

### 🚀 Getting Started
- **[Deployment Guide](deployment-guide.md)** - Complete step-by-step deployment workflow
- **[Quick Reference](quick-reference.md)** - Essential commands and common operations

### 🔧 Technical Guides
- **[Troubleshooting Guide](troubleshooting-guide.md)** - Solutions for common issues

## 🏗️ What is NOAH?

NOAH is a comprehensive Kubernetes-based infrastructure platform that provides:

- **🔐 Single Sign-On (SSO)** via Authentik
- **🌐 Network Security** via Cilium CNI
- **🗂️ Directory Services** via Samba4 (optional)
- **🔒 Secret Management** via SOPS/Age encryption
- **🚪 Ingress Management** via NGINX

## 🎯 Quick Start

### Complete Infrastructure Deployment
```bash
# 1. Create the cluster
python noah.py cluster create --name noah-cluster --domain noah-infra.com

# 2. Deploy complete infrastructure with optimized order
python noah.py deploy all --domain noah-infra.com

# 3. Test SSO and network integration
python noah.py test sso

# 4. Validate deployment status
python noah.py status --all
```

### Manual Component Deployment
```bash
# 1. Create cluster with enhanced validation
python noah.py cluster create --name noah-cluster --domain noah-infra.com

# 2. Deploy networking first (SSO-ready configuration)
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com

# 3. Deploy directory services
python noah.py deploy samba4 --namespace identity --domain noah-infra.com

# 4. Deploy authentication (connects to Samba4)
python noah.py deploy authentik --namespace identity --domain noah-infra.com

# 5. Validate complete stack
python noah.py test sso
```

## 📋 Component Overview

| Component | Namespace | Purpose | Timeout | Deployment Order |
|-----------|-----------|---------|---------|------------------|
| **Cilium** | kube-system | CNI networking + SSO network policies | 10 min | 1st (Foundation) |
| **Samba4** | identity | Active Directory + LDAP services | 15 min | 2nd (Identity Backend) |
| **Authentik** | identity | SSO authentication + LDAP integration | 12 min | 3rd (SSO Frontend) |


## 🔍 Service Access Points

Once deployed, access your services at:

- **Authentik SSO**: https://auth.noah-infra.com
- **Hubble Network UI**: https://hubble.noah-infra.com (Cilium observability)
- **Samba4 LDAP**: ldap://samba4.identity.svc.cluster.local:389 (internal)

### Service Integration
- **Authentik** connects to **Samba4** for user authentication via LDAP
- **Cilium** provides the network foundation with service mesh and policies
- **Hubble UI** offers real-time network visibility and troubleshooting

## 🏛️ Architecture

```
┌────────────────────────────────────────────────────────┐
│                   NOAH Platform v2.0                  │
│  ┌───────────────────────────────────────────────────┐ │
│  │              Ingress Layer                        │ │
│  │       NGINX → TLS → Service Routing               │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │           Authentication Layer                    │ │
│  │  ┌─────────────────┐  ┌─────────────────────────┐ │ │
│  │  │   Authentik     │←→│      Samba4 AD          │ │ │
│  │  │   (SSO Web)     │  │   (LDAP Backend)        │ │ │
│  │  └─────────────────┘  └─────────────────────────┘ │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │            Network Layer                          │ │
│  │  Cilium CNI + Service Mesh + Hubble UI            │ │
│  │  • Network Policies (SSO Communication)           │ │
│  │  • Service Discovery & Load Balancing             │ │
│  │  • Real-time Network Observability                │ │
│  └───────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │             Security Layer                        │ │
│  │  SOPS/Age + TLS + RBAC + Network Policies         │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

### Deployment Flow
1. **Cilium CNI**: Establishes network foundation with SSO-ready policies
2. **Samba4**: Provides LDAP/AD backend for user authentication  
3. **Authentik**: Connects to Samba4 and provides SSO web interface

## 🛠️ Management Tools

### NOAH CLI Commands
```bash
# Cluster management (enhanced)
python noah.py cluster create/destroy        # Individual operations
ansible-playbook Ansible/cluster-redeploy.yml  # Complete redeployment

# Component deployment (optimized order)
python noah.py deploy cilium                 # Deploy CNI foundation first
python noah.py deploy samba4                 # Deploy LDAP backend second  
python noah.py deploy authentik              # Deploy SSO frontend third

# Testing and validation (enhanced)
python noah.py test sso                      # SSO + network validation
python noah.py status --all                  # Comprehensive status check

# Secret management
python noah.py secrets edit/list

# Certificate management  
python noah.py certificates regenerate/info
```

### Ansible Automation
```bash
# Complete infrastructure redeployment (recommended)
ansible-playbook Ansible/cluster-redeploy.yml \
  -e cluster_name=noah-production \
  -e domain_name=noah-infra.com

# Individual component deployment
ansible-playbook Ansible/deploy-cilium.yml     # SSO-ready networking
ansible-playbook Ansible/deploy-samba4.yml     # Active Directory  
ansible-playbook Ansible/deploy-authentik.yml  # SSO integration
```

## 🔐 Security Features

- **Encrypted Secrets**: All sensitive data encrypted with SOPS/Age
- **TLS Everywhere**: Auto-generated certificates for all services
- **Network Policies**: Cilium-based micro-segmentation
- **RBAC**: Kubernetes role-based access control
- **SSO Integration**: Centralized authentication for all services

## 🆘 Getting Help

### Quick Fixes
1. **Check the [Quick Reference](quick-reference.md)** for common commands
2. **Review [Troubleshooting Guide](troubleshooting-guide.md)** for specific issues
3. **Run health checks**: `python noah.py status --all`

### Emergency Recovery
```bash
# Complete reset (destroys everything)
python noah.py cluster destroy --force

# Fresh deployment
python noah.py cluster create --name noah-cluster --domain noah-infra.com
```

### Useful Debugging
```bash
# Check all pods (when cluster exists)
kubectl get pods --all-namespaces | grep -v Running

# Note: After cluster destroy, kubectl will show connection errors - this is normal!
# Connection refused + memcache errors = successful cluster destruction

# Check events (when cluster exists)
kubectl get events --sort-by=.metadata.creationTimestamp

# Check Helm releases
helm list --all-namespaces --failed
```
---

## �📖 Additional Resources

- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Helm Documentation**: https://helm.sh/docs/
- **Cilium Documentation**: https://docs.cilium.io/
- **Authentik Documentation**: https://goauthentik.io/docs/
- **Samba4 Documentation**: https://wiki.samba.org/index.php/Setting_up_Samba_as_an_Active_Directory_Domain_Controller
- **SOPS Documentation**: https://github.com/mozilla/sops
- **Ansible Documentation**: https://docs.ansible.com/

---