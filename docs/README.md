# 🚀 NOAH  - Network Operations & Automation Hub

**NOAH** (Network Operations & Automation Hub) is a comprehensive Kubernetes infrastructure platform with integrated SSO, networking, and security automation.


## **What is NOAH?**

NOAH provides a complete infrastructure stack:

- **🔐 Authentik SSO** - Identity and access management with automatic OIDC app provisioning
- **🌐 Cilium CNI** - Advanced networking with ingress and Hubble UI (SSO-gated)
- **📊 Headlamp Dashboard** - Kubernetes web UI with auto-provisioned Authentik SSO
- **🔒 Canonical Secrets Store** - Single authoritative encrypted secrets file (Age/SOPS protected)
- **🌍 Cloudflare DNS Wizard** - Interactive DNS automation setup (`setup initialize`)
- **🚢 GitOps with FluxCD (v0.0.9+)** - Continuous reconciliation from a Git repo with SOPS-encrypted secrets
- **🧪 Testing Suite** - Built-in validation and health checks
- **🚀 CI/CD Ready** - GitHub Actions workflows included

### v0.0.9 documentation
- [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) - upgrade from v0.0.8 (greenfield re-deploy)
- [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) - day-to-day FluxCD workflow
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - end-to-end install (updated for v0.0.9)

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
# 1. Clone repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# 2. Initialize environment (runs interactive Cloudflare DNS wizard)
python3 noah.py setup initialize

# To skip the DNS wizard:
python3 noah.py setup initialize --skip-dns-wizard

# 3. Configure DNS (choose one option):

# Option A: Automatic DNS with Cloudflare — store token once, enabled by default
python3 Scripts/security/set_cloudflare_token.py 'your-cloudflare-api-token'

# Option B: Manual DNS - Get node public IP, then create A records:
#   kubectl get svc ingress-nginx-controller -n ingress-nginx
#   Create: auth.your-domain.com → EXTERNAL-IP
#           headlamp.your-domain.com → EXTERNAL-IP
#           hubble.your-domain.com → EXTERNAL-IP

# Option C: Local testing - Add to /etc/hosts (after deploy)

# 4. Create cluster
python3 noah.py cluster create --name noah-cluster --domain your-domain.com

# 5. Deploy infrastructure
python3 noah.py deploy core --domain your-domain.com

# 6. Get credentials & verify
python3 noah.py password show
python3 noah.py status
```

## **Architecture Overview**

```
┌─────────────────────────────────────────────────────────┐
│                    User Access Layer                    │
│  https://auth.your-domain.com     (Authentik SSO)       │
│  https://headlamp.your-domain.com (K8s Dashboard)       │
│  https://hubble.your-domain.com   (Network Observ.)     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS/TLS
                         ▼
┌─────────────────────────────────────────────────────────┐
│         nginx-ingress (hostNetwork, ports 80/443)       │
│  • L7 routing • TLS via cert-manager/Let's Encrypt      │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Authentik   │  │  Headlamp    │  │  Hubble UI   │
│  SSO/OIDC    │◄─┤  Dashboard   │  │  Network     │
│  + Worker    │  │  (OIDC auth) │  │  Flows       │
└──────┬───────┘  └──────────────┘  └──────────────┘
       │
       ├─────────┬──────────┐
       ▼         ▼          ▼
┌──────────┐ ┌────────┐ ┌────────────┐
│PostgreSQL│ │ Redis  │ │   Cilium   │
│ (state)  │ │(cache) │ │ CNI/Proxy  │
└──────────┘ └────────┘ └────────────┘
───────────────────────────────────────────────────────────
              Kubernetes (K3s) Cluster
───────────────────────────────────────────────────────────
Deployment Automation:
  python noah.py deploy core
      ↓
  Ansible Playbook (phased)
      ├─ Phase 0:   External-DNS (Cloudflare, sync policy)
      ├─ Phase 1:   cert-manager + ClusterIssuers
      ├─ Phase 2:   Cilium CNI
      ├─ Phase 2.5: nginx-ingress (hostNetwork)
      ├─ Phase 3:   Authentik SSO
      ├─ Phase 3.5: Hubble UI SSO provisioning
      ├─ Phase 4:   Headlamp Dashboard
      └─ Phase 5:   Validation
      ↓
  Helm Charts + Canonical Secrets (Age/SOPS encrypted)
```

### Key Principles

- **Single Source of Truth**: Canonical encrypted YAML for all secrets with metadata (`value`, `version`, `rotated_at`)
- **Deterministic Deployments**: Ordered rollout (Cilium → Authentik → Headlamp) with validation
- **Separation of Concerns**: CLI (UX) → Ansible (orchestration) → Helm (packaging)
- **Validation Modes**: `development` (fast) vs `production` (full DNS/TLS/health checks)
- **Composable Security**: Isolated secret generation with versioned rotation
- **CI Safety**: `NOAH_SKIP_ANSIBLE=true` for testing without cluster

## **Service Access**

After deployment, access services at:

- **Authentik SSO**: `https://auth.your-domain.com`
- **Headlamp Dashboard**: `https://headlamp.your-domain.com` (SSO via Authentik)
- **Cilium Hubble**: `https://hubble.your-domain.com`

Get credentials: `python noah.py password show`

Rotate password:
```bash
python3 noah.py password new
python3 noah.py deploy authentik --regenerate-password
```

## **Requirements**

### **System**
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **CPU**: 4 cores minimum (8+ recommended)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB free disk space (100GB+ recommended)
- **Kernel**: Linux 5.10+ (for Cilium eBPF support)
- **Network**: Internet connectivity for component downloads

## **Testing**

```bash
# Lightweight test
python3 Tests/test_noah.py

# CI without cluster (skip Ansible, test secrets only)
NOAH_SKIP_ANSIBLE=true python3 -m pytest Tests/test_deploy_core_secrets.py -q
```

---
Made with ❤️