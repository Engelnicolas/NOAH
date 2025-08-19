# NOAH Infrastructure Deployment Guide

## Overview

This guide provides the standard workflow for deploying the complete NOAH (Network Operations and Authentication Hub) infrastructure from scratch. NOAH provides a comprehensive Kubernetes-based platform with SSO authentication, network security, and encrypted secret management.

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ or similar Linux distribution
- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM recommended
- **Storage**: 50GB+ available disk space
- **Network**: Internet connectivity for downloading components

### Required Tools
The NOAH CLI will automatically install missing tools, but you can pre-install:
- `kubectl` - Kubernetes CLI
- `helm` - Helm package manager
- `age` - Age encryption tool
- `sops` - Secrets Operations tool
- `python3` and `pip3`

## Standard Deployment Workflow

### Phase 1: Initial Setup and Prerequisites

#### 1.1 Clone and Setup NOAH Repository
```bash
# Clone the NOAH repository
git clone <noah-repo-url>
cd noah-infrastructure

# Verify NOAH CLI is functional
python noah.py --help
```

#### 1.2 Validate Clean Environment
```bash
# Ensure no existing cluster or conflicting services
python noah.py cluster destroy --force  # If needed
```

### Phase 2: Core Infrastructure Deployment

#### 2.1 Create Fresh Kubernetes Cluster
```bash
# Create new cluster with prerequisite validation
python noah.py cluster create --name noah-cluster --domain noah-infra.com
```

**What this does:**
- ✅ Validates no existing cluster components
- ✅ Generates Age encryption keys
- ✅ Creates SOPS configuration  
- ✅ Generates TLS certificates for domain
- ✅ Initializes K3s Kubernetes cluster
- ✅ Sets up NOAH namespaces (identity, monitoring)

#### 2.2 Deploy CNI (Cilium)
```bash
# Deploy Cilium networking with 10-minute timeout
python noah.py deploy cilium --namespace kube-system --domain noah-infra.com
```

**What this does:**
- ✅ Deploys Cilium CNI via Helm dependency
- ✅ Enables Hubble observability
- ✅ Configures ingress for Hubble UI
- ✅ Sets up network policies and security
- ✅ Validates network connectivity

#### 2.3 Deploy Ingress Controller
```bash
# Deploy NGINX Ingress Controller
python noah.py deploy ingress --namespace ingress-nginx --domain noah-infra.com
```

### Phase 3: Security and Authentication

#### 3.1 Deploy Authentik SSO
```bash
# Deploy Authentik with PostgreSQL and Redis (12-minute timeout)
python noah.py deploy authentik --namespace identity --domain noah-infra.com
```

**What this does:**
- ✅ Deploys PostgreSQL database
- ✅ Deploys Redis cache
- ✅ Deploys Authentik server and worker
- ✅ Configures LDAP outpost
- ✅ Sets up ingress with TLS
- ✅ Encrypts secrets with SOPS

#### 3.2 Deploy Directory Services (Optional)
```bash
# Deploy Samba4 Active Directory (15-minute timeout)
python noah.py deploy samba4 --namespace identity --domain noah-infra.com
```

### Phase 3: Security and Authentication

#### 3.1 Deploy Authentik SSO
```bash
# Deploy Authentik with PostgreSQL and Redis (12-minute timeout)
python noah.py deploy authentik --namespace identity --domain noah-infra.com
```

**What this does:**
- ✅ Deploys PostgreSQL database
- ✅ Deploys Redis cache
- ✅ Deploys Authentik server and worker
- ✅ Configures LDAP outpost
- ✅ Sets up ingress with TLS
- ✅ Encrypts secrets with SOPS

#### 3.2 Deploy Directory Services (Optional)
```bash
# Deploy Samba4 Active Directory (15-minute timeout)
python noah.py deploy samba4 --namespace identity --domain noah-infra.com
```

### Phase 4: Complete Stack Deployment (Alternative)

#### 4.1 Deploy All Components at Once
```bash
# Deploy complete stack (Cilium + Authentik + Samba4)
python noah.py deploy all --namespace identity --domain noah-infra.com
```

### Phase 5: Validation and Testing

#### 5.1 Validate All Components
```bash
# Check overall system health
python noah.py status --all

# Validate network connectivity
python noah.py test network

# Test SSO integration
python noah.py test sso --domain noah-infra.com
```

#### 5.2 Access Deployed Services
- **Authentik SSO**: https://auth.noah-infra.com
- **Hubble Network UI**: https://hubble.noah-infra.com

## Configuration Management

### Secret Management
All secrets are automatically encrypted using SOPS/Age:
```bash
# View encrypted secrets
ls Helm/*/secrets/*.enc.yaml

# Edit secrets (auto-encrypted)
python noah.py secrets edit authentik
python noah.py secrets edit samba4
```

### Certificate Management
TLS certificates are auto-generated and managed:
```bash
# Regenerate certificates
python noah.py certificates regenerate --domain noah-infra.com

# View certificate info
python noah.py certificates info
```

## Troubleshooting

### Common Issues

#### 1. Deployment Timeouts
```bash
# Check timeout settings in Scripts/helm_deployer.py
# Default timeouts:
# - Cilium: 10 minutes
# - Authentik: 12 minutes  
# - Samba4: 15 minutes

# Increase if needed for slower environments
```

#### 2. Pod Failures
```bash
# Check pod status
kubectl get pods --all-namespaces

# View pod logs
kubectl logs -n <namespace> <pod-name>

# Restart deployment
python noah.py deploy <component> --namespace <namespace> --domain noah-infra.com
```

#### 3. Network Issues
```bash
# Check Cilium status
kubectl exec -n kube-system <cilium-pod> -- cilium status

# Validate connectivity
python noah.py test network
```

#### 4. SSO Issues
```bash
# Check Authentik logs
kubectl logs -n identity deployment/authentik-server

# Verify LDAP connectivity
python noah.py test ldap --domain noah-infra.com
```

### Cleanup and Reset

#### Complete Infrastructure Reset
```bash
# WARNING: This destroys everything
python noah.py cluster destroy --force

# Then start fresh
python noah.py cluster create --name noah-cluster --domain noah-infra.com
```

#### Component-specific Reset
```bash
# Uninstall specific component
helm uninstall <component> -n <namespace>

# Redeploy
python noah.py deploy <component> --namespace <namespace> --domain noah-infra.com
```

## Advanced Configuration

### Custom Domains
```bash
# Use custom domain
python noah.py cluster create --name noah-cluster --domain my-company.com
python noah.py deploy authentik --namespace identity --domain my-company.com
```

### High Availability Setup
```bash
# Multi-node cluster (manual K3s setup required)
# Then deploy NOAH components with HA values
python noah.py deploy authentik --namespace identity --domain noah-infra.com --ha
```

### Custom Values
```bash
# Edit component values before deployment
vim Helm/authentik/values.yaml
python noah.py deploy authentik --namespace identity --domain noah-infra.com
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    NOAH Infrastructure                   │
├─────────────────────────────────────────────────────────┤
│  Ingress Layer (NGINX)                                  │
│  ├── auth.noah-infra.com → Authentik SSO               │
│  ├── grafana.noah-infra.com → Grafana                  │
│  └── hubble.noah-infra.com → Hubble UI                 │
├─────────────────────────────────────────────────────────┤
│  Authentication Layer (identity namespace)              │
│  ├── Authentik Server + Worker                         │
│  ├── PostgreSQL Database                               │
│  ├── Redis Cache                                       │
│  └── Samba4 Active Directory (optional)               │
├─────────────────────────────────────────────────────────┤
│  Monitoring Layer (monitoring namespace)                │
│  ├── Prometheus (metrics)                              │
│  ├── Grafana (dashboards)                              │
│  └── AlertManager (alerts)                             │
├─────────────────────────────────────────────────────────┤
│  Network Layer (kube-system namespace)                  │
│  ├── Cilium CNI (networking)                           │
│  ├── Hubble (observability)                            │
│  └── Network Policies                                  │
├─────────────────────────────────────────────────────────┤
│  Security Layer                                         │
│  ├── SOPS/Age (secret encryption)                      │
│  ├── TLS Certificates (auto-generated)                 │
│  └── RBAC Policies                                     │
└─────────────────────────────────────────────────────────┘
```

## Support and Maintenance

### Regular Maintenance
```bash
# Weekly health check
python noah.py status --all

# Monthly security updates
python noah.py update components

# Backup secrets and certificates
python noah.py backup create
```

### Monitoring Alerts
- Set up alerts for pod failures
- Monitor certificate expiration
- Track resource usage
- Watch for authentication failures

## Security Best Practices

1. **Secrets Management**
   - All secrets encrypted with SOPS/Age
   - Age keys stored securely
   - Regular secret rotation

2. **Network Security**
   - Cilium network policies
   - Ingress TLS termination
   - Pod-to-pod encryption

3. **Access Control**
   - Authentik SSO for all services
   - RBAC policies
   - Audit logging enabled

4. **Certificate Management**
   - Auto-generated TLS certificates
   - Certificate rotation
   - CA certificate security

## Version Information

- **NOAH CLI**: Latest
- **Kubernetes**: K3s (latest stable)
- **Cilium**: 1.14.5
- **Authentik**: 2023.10.5
- **Prometheus Stack**: Latest

---

For detailed troubleshooting and advanced configurations, refer to the component-specific documentation in the respective Helm chart directories.
