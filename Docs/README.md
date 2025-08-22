# NOAH Infrastructure Documentation

Welcome to the NOAH (Network Operations and Authentication Hub) infrastructure documentation. This comprehensive guide covers everything you need to deploy, manage, and troubleshoot your NOAH platform.

## 📚 Documentation Index

### 🚀 Getting Started
- **[Deployment Guide](deployment-guide.md)** - Complete step-by-step deployment workflow
- **[Quick Reference](quick-reference.md)** - Essential commands and common operations

### 🔧 Technical Guides
- **[Troubleshooting Guide](troubleshooting-guide.md)** - Solutions for common issues
- **[Cilium Integration Options](cilium-integration-options.md)** - CNI integration best practices
- **[Timeout Strategy](timeout-strategy.md)** - Deployment timeout configuration

## 🏗️ What is NOAH?

NOAH is a comprehensive Kubernetes-based infrastructure platform that provides:

- **🔐 Single Sign-On (SSO)** via Authentik
- **🌐 Network Security** via Cilium CNI
- **🗂️ Directory Services** via Samba4 (optional)
- **🔒 Secret Management** via SOPS/Age encryption
- **🚪 Ingress Management** via NGINX

## 🎯 Quick Start

For a complete deployment from scratch:

```bash
# 1. Destroy any existing setup
python noah.py cluster destroy --force

# 2. Create fresh cluster
python noah.py cluster create --name noah-cluster --domain noah-infra.com

# 3. Deploy networking
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com

# 4. Deploy authentication
python noah.py deploy authentik --namespace identity --domain noah-infra.com

# 5. Validate deployment
python noah.py status --all
```

## 📋 Component Overview

| Component | Namespace | Purpose | Timeout |
|-----------|-----------|---------|---------|
| **Cilium** | kube-system | CNI networking | 10 min |
| **Authentik** | identity | SSO authentication | 12 min |
| **Samba4** | identity | Directory services | 15 min |

## 🔍 Service Access Points

Once deployed, access your services at:

- **Authentik SSO**: https://auth.noah-infra.com
- **Hubble Network UI**: https://hubble.noah-infra.com

## 🏛️ Architecture

```
┌──────────────────────────────────────────────┐
│              NOAH Platform                   │
│  ┌─────────────────────────────────────────┐ │
│  │         Ingress Layer                   │ │
│  │  NGINX → TLS → Service Routing          │ │
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │      Authentication Layer               │ │
│  │  Authentik SSO + LDAP + Samba4 AD       │ │
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │         Network Layer                   │ │
│  │  Cilium CNI + Hubble + Policies         │ │
│  └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────┐ │
│  │        Security Layer                   │ │
│  │  SOPS/Age + TLS + RBAC + Encryption     │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

## 🛠️ Management Tools

### NOAH CLI Commands
```bash
# Cluster management
python noah.py cluster create/destroy

# Component deployment
python noah.py deploy <component>

# Secret management
python noah.py secrets edit/list

# Certificate management
python noah.py certificates regenerate/info

# Testing and validation
python noah.py test sso/network/ldap
python noah.py status --all
```

### Standard Kubernetes Tools
```bash
# Pod management
kubectl get pods --all-namespaces
kubectl logs -n <namespace> <pod>

# Helm management
helm list --all-namespaces
helm status <release> -n <namespace>

# Secret inspection
kubectl get secrets --all-namespaces
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
# Check all pods
kubectl get pods --all-namespaces | grep -v Running

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check Helm releases
helm list --all-namespaces --failed
```

## 📝 File Structure

```
noah-infrastructure/
├── Docs/                          # Documentation (you are here)
│   ├── deployment-guide.md        # Complete deployment workflow
│   ├── quick-reference.md          # Essential commands
│   ├── troubleshooting-guide.md    # Problem solutions
│   └── README.md                   # This file
├── Helm/                           # Helm charts
│   ├── authentik/                  # SSO authentication
│   ├── cilium/                     # CNI networking
│   ├── samba4/                     # Directory services
│   └── monitoring/                 # Observability stack
├── Ansible/                        # Infrastructure automation
│   ├── cluster-create.yml          # Cluster initialization
│   ├── cluster-destroy.yml         # Cleanup automation
│   └── deploy-*.yml               # Component deployments
├── Scripts/                        # Python modules
│   ├── helm_deployer.py           # Helm deployment logic
│   ├── cluster_manager.py         # Cluster operations
│   └── secret_manager.py          # SOPS/Age integration
├── Certificates/                   # TLS certificates (auto-generated)
├── Age/                           # Encryption keys (auto-generated)
└── noah.py                        # Main CLI interface
```

## 🔄 Regular Maintenance

### Weekly
- Run `python noah.py status --all`
- Check certificate expiration
- Review pod resource usage

### Monthly
- Update component versions
- Backup encryption keys
- Review security logs

### Quarterly
- Security audit
- Performance optimization
- Documentation updates

---

## 📖 Additional Resources

- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Helm Documentation**: https://helm.sh/docs/
- **Cilium Documentation**: https://docs.cilium.io/
- **Authentik Documentation**: https://goauthentik.io/docs/
- **SOPS Documentation**: https://github.com/mozilla/sops

---