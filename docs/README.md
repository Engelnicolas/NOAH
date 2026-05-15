# 🚀 NOAH  - Network Operations & Automation Hub

**NOAH** (Network Operations & Automation Hub) is a comprehensive Kubernetes infrastructure platform with integrated SSO, networking, and security automation.


## **What is NOAH?**

NOAH provides a complete infrastructure stack:

- **🔐 Authentik SSO** - Identity and access management with automatic OIDC app provisioning
- **🌐 Cilium CNI** - Advanced networking with ingress and Hubble UI (SSO-gated)
- **📊 Headlamp Dashboard** - Kubernetes web UI with auto-provisioned Authentik SSO
- **🔒 Canonical Secrets Store** - Single authoritative encrypted secrets file (Age/SOPS protected)
- **🌍 Cloudflare DNS Wizard** - Interactive DNS automation setup (`setup initialize`)
- **🚢 GitOps with FluxCD** - Continuous reconciliation from `gitops/` in this repo with SOPS-encrypted secrets
- **🧪 Testing Suite** - Built-in validation and health checks
- **🚀 CI/CD Ready** - GitHub Actions workflows for Python (`ci-python.yml`) and GitOps (`ci-gitops.yml`)

### Repository structure

```
NOAH/
├── .github/workflows/
│   ├── ci-python.yml       # lint, test, security scan (Python/Ansible)
│   └── ci-gitops.yml       # YAML lint, kubeconform, Helm dry-run
├── Scripts/                # Python orchestration modules
├── Tests/                  # pytest test suite
├── Ansible/                # K3s bootstrap roles
├── docs/                   # documentation
├── gitops/                 # FluxCD manifests (former noah-gitops repo)
│   ├── clusters/production/
│   │   ├── flux-system/    # Flux bootstrap manifests (gotk-sync, gotk-components)
│   │   ├── apps.yaml
│   │   ├── cert-manager-issuers.yaml
│   │   └── infrastructure.yaml
│   ├── apps/               # Authentik, Headlamp, Hubble
│   └── infrastructure/     # cert-manager, Cilium, external-dns
└── noah.py                 # NOAH CLI entry point
```

### Documentation
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - end-to-end install
- [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) - day-to-day FluxCD workflow
- [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) - upgrade from v0.0.7 (greenfield re-deploy)

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

```bash
# 1. Clone and initialize
git clone https://github.com/Engelnicolas/NOAH.git && cd NOAH
python3 noah.py setup initialize   # interactive wizard configures Cloudflare token

# 2. Bootstrap K3s + FluxCD — Flux is pointed at gitops/ in this repo.
#    GIT_TOKEN auto-registers the SSH deploy key on Engelnicolas/NOAH.
python3 noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain your-domain.com \
  --flux-repo https://github.com/Engelnicolas/NOAH \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GIT_TOKEN

# 4. Watch FluxCD reconcile the stack (~25-45 min)
python3 noah.py flux status
python3 noah.py flux logs -f

# 5. Get credentials
python3 noah.py password show-password
```

> For a 3-node HA cluster add `--ha --nodes node1,node2,node3` to step 3.
> To wipe the local environment and start over: `python3 noah.py setup reset`

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
  python3 noah.py cluster bootstrap
      ↓
  K3s + FluxCD bootstrap
      ↓
  FluxCD reconciles GitOps repo (phased)
      ├─ Phase 0:   External-DNS (Cloudflare, upsert-only)
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
- **Separation of Concerns**: CLI (UX) → FluxCD (reconciliation) → Helm (packaging)
- **Validation Modes**: `development` (fast) vs `production` (full DNS/TLS/health checks)
- **Composable Security**: Isolated secret generation with versioned rotation
- **CI Safety**: `NOAH_SKIP_ANSIBLE=true` for testing without cluster

## **Service Access**

After deployment, access services at:

- **Authentik SSO**: `https://auth.your-domain.com`
- **Headlamp Dashboard**: `https://headlamp.your-domain.com` (SSO via Authentik)
- **Cilium Hubble**: `https://hubble.your-domain.com`

Get credentials: `python noah.py password show-password`

Rotate password (GitOps — see [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) for details):
```bash
python3 noah.py password new
# Commit & push updated gitops/ manifests, FluxCD reconciles automatically
python3 noah.py flux sync
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