# NOAH - Network Operations & Automation Hub

**NOAH** is a complete Kubernetes infrastructure platform with integrated SSO, networking, and GitOps automation.

## What is NOAH?

NOAH deploys and manages a full infrastructure stack:

- **Authentik SSO** - Identity and access management with automatic OIDC app provisioning
- **Cilium CNI** - eBPF-based networking with Hubble UI (SSO-gated)
- **Headlamp Dashboard** - Kubernetes web UI with Authentik SSO
- **Canonical Secrets Store** - Single encrypted secrets file (Age/SOPS)
- **Cloudflare DNS Wizard** - Interactive DNS automation (`setup initialize`)
- **GitOps with FluxCD** - Continuous reconciliation from `gitops/` with SOPS-encrypted secrets
- **CI/CD Ready** - GitHub Actions for Python and GitOps validation

### Repository structure

```
NOAH/
├── .github/workflows/
│   ├── ci-python.yml            # lint, test, security scan
│   └── ci-gitops.yml            # YAML lint, kubeconform, Helm dry-run
├── Ansible/                     # K3s bootstrap roles
├── Scripts/                     # Python orchestration modules
├── Tests/                       # pytest suite
├── docs/                        # documentation
├── clusters/production/         # Flux reconciliation root (read by FluxCD)
│   ├── kustomization.yaml       # top-level entry point
│   ├── flux-system/             # Flux bootstrap manifests
│   ├── noah-source.yaml         # GitRepository pointing at gitops/
│   ├── infrastructure.yaml      # Kustomization CR for infrastructure
│   ├── cert-manager-issuers.yaml
│   └── apps.yaml                # Kustomization CR for apps
├── gitops/                      # FluxCD manifests (actual Helm/Kustomize content)
│   ├── clusters/production/     # mirrors clusters/ for local tooling
│   ├── apps/                    # Authentik, Headlamp, Hubble
│   └── infrastructure/          # cert-manager, Cilium, external-dns
└── noah.py                      # NOAH CLI entry point
```

> **Note on Flux paths**: `flux bootstrap` writes to `clusters/production/` (repo root). The `gitops/` subtree contains the actual Helm manifests and encrypted secrets that Flux pulls via the `noah` GitRepository source.

### Documentation
- [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - end-to-end install
- [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) - day-to-day FluxCD workflow
- [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) - upgrade from v0.0.7

## Quick Start

```bash
# 1. Clone and initialize (installs tools, generates Age key, runs Cloudflare DNS wizard)
git clone https://github.com/Engelnicolas/NOAH.git && cd NOAH
python3 noah.py setup initialize

# 2. Fill and encrypt secrets in gitops/ (records the node's public IP / EIP)
python3 noah.py setup gitops --domain your-domain.com --node-ip <EIP>

# 3. Bootstrap K3s + FluxCD (single-node: --node defaults to the recorded EIP; auto-registers SSH deploy key)
export GITHUB_TOKEN=ghp_xxx
python3 noah.py cluster bootstrap \
  --domain your-domain.com \
  --flux-repo https://github.com/Engelnicolas/NOAH.git \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GITHUB_TOKEN

# 4. Watch FluxCD reconcile the stack (~25-45 min)
watch kubectl get kustomization,helmrelease -A

# 5. Get credentials
python3 noah.py password show-password
```

> For a 3-node HA cluster add `--ha --nodes node1,node2,node3` to step 3.
>
> Running NOAH **on the target node** (co-located single-node)? Override with `--node 127.0.0.1` (or the node's private IP) — an instance can't SSH to its own public/Elastic IP (the AWS Internet Gateway doesn't hairpin it), so the EIP default times out.

## Architecture Overview

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
│  • L7 routing  • TLS via cert-manager / Let's Encrypt   │
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
       ├──────────┬──────────┐
       ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────────┐
│PostgreSQL│ │ Redis  │ │   Cilium   │
│ (state)  │ │(cache) │ │ CNI/Proxy  │
└──────────┘ └────────┘ └────────────┘
───────────────────────────────────────────────────────────
              Kubernetes (K3s, embedded etcd)
───────────────────────────────────────────────────────────
FluxCD reconciliation order:
  Phase 0:   External-DNS (Cloudflare)
  Phase 1:   cert-manager + ClusterIssuers
  Phase 2:   Cilium CNI
  Phase 2.5: nginx-ingress (hostNetwork)
  Phase 3:   Authentik SSO (PostgreSQL + Redis)
  Phase 3.5: Hubble UI SSO provisioning
  Phase 4:   Headlamp Dashboard
  Phase 5:   Validation
```

## Requirements

### System
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **CPU**: 4 cores minimum (8+ recommended)
- **RAM**: 8 GB minimum (16 GB+ recommended)
- **Storage**: 50 GB free (100 GB+ recommended)
- **Kernel**: Linux 5.10+ (required by Cilium eBPF)
- **Network**: Internet connectivity

### Tools (auto-installed by `setup initialize`)
- Python 3.8+, kubectl, FluxCD CLI, Ansible
- age, sops (encryption)

## Service Access

After deployment:

| Service | URL |
|---|---|
| Authentik SSO | `https://auth.your-domain.com` |
| Headlamp Dashboard | `https://headlamp.your-domain.com` |
| Hubble UI | `https://hubble.your-domain.com` |

```bash
# Show admin credentials
python3 noah.py password show-password

# Rotate password
python3 noah.py password new
python3 noah.py setup gitops --domain your-domain.com
python3 noah.py flux sync
```

## Testing

```bash
# Run test suite
python3 Tests/test_noah.py

# CI without a cluster
NOAH_SKIP_ANSIBLE=true python3 -m pytest Tests/test_deploy_core_secrets.py -q
```

---

Made with love by the NOAH Team
