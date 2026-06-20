# NOAH Deployment Guide

**Version**: 0.0.8
**Last Updated**: June 2026

Deploy NOAH (Network Operations & Automation Hub) — a complete Kubernetes infrastructure with SSO authentication and web dashboards.

> **v0.0.8** — K3s uses embedded etcd (no SQLite SPOF). All application services are reconciled by FluxCD from `gitops/` in this repository. The legacy `noah deploy <service>` commands are removed; use `noah cluster bootstrap` to provision and `noah flux ...` to operate.
> See [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) for day-to-day GitOps workflow.

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Quick Start](#quick-start)
4. [Detailed Steps](#detailed-steps)
5. [DNS Configuration](#dns-configuration)
6. [Accessing Services](#accessing-services)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### What NOAH deploys

- **Kubernetes (K3s)** - Lightweight K8s with embedded etcd
- **Cilium CNI** - eBPF networking + Ingress
- **Authentik SSO** - Identity and access management
- **Headlamp Dashboard** - Kubernetes web UI with SSO
- **Hubble UI** - Network observability (SSO-gated)
- **External-DNS** - Optional automatic DNS via Cloudflare

### Repository layout (Flux paths)

```
NOAH/
├── clusters/production/         ← Flux bootstrap root (path: ./clusters/production)
│   ├── kustomization.yaml       ← entry point, references all Kustomization CRs
│   ├── flux-system/             ← Flux component manifests (managed by flux bootstrap)
│   ├── noah-source.yaml         ← GitRepository pointing at gitops/ subtree
│   ├── infrastructure.yaml      ← deploys cert-manager, Cilium, external-dns
│   ├── cert-manager-issuers.yaml
│   └── apps.yaml                ← deploys Authentik, Headlamp, Hubble
└── gitops/                      ← actual HelmRelease / Secret manifests
    ├── infrastructure/
    └── apps/
```

**Deployment time**: ~25-45 minutes total

---

## Requirements

### System
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **CPU**: 4 cores minimum (8+ recommended)
- **RAM**: 8 GB minimum (16 GB+ recommended)
- **Storage**: 50 GB free (100 GB+ recommended)
- **Kernel**: Linux 5.10+ (for Cilium eBPF)
- **Network**: Internet connectivity

### Tools (auto-installed)
- Python 3.8+, kubectl, FluxCD CLI, Ansible
- age, sops

### DNS Options
1. **Cloudflare** (automatic) - API token required
2. **Manual** - Any provider, create A records after deployment
3. **Local** - `/etc/hosts` for testing

---

## Quick Start

```bash
# 1. Initialize environment
git clone https://github.com/Engelnicolas/NOAH.git && cd NOAH
python3 noah.py setup initialize        # wizard: installs tools, generates Age key, configures Cloudflare token

# 2. Fill and encrypt secrets in gitops/ (records the node's public IP / EIP)
python3 noah.py setup gitops --domain your-domain.com --node-ip <EIP>

# 3. Push gitops changes to GitHub
export GITHUB_TOKEN=ghp_xxx
git add gitops/ && git commit -m "chore: configure domain and secrets"
git push origin main

# 4. Bootstrap K3s + FluxCD (single-node: --node defaults to the IP recorded in step 2)
python3 noah.py cluster bootstrap \
  --domain your-domain.com \
  --flux-repo https://github.com/Engelnicolas/NOAH.git \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GITHUB_TOKEN

# 5. Watch FluxCD reconcile the stack
watch kubectl get kustomization,helmrelease -A

# 6. Get credentials
python3 noah.py password show-password
```

> For a 3-node HA cluster, add `--ha --nodes n1,n2,n3` to step 4.

---

## Detailed Steps

### Step 1: Initialize Environment

```bash
python3 noah.py setup initialize
```

**What it does:**
- Checks Python 3.8+ version
- Creates virtual environment (`.venv/`)
- Installs Python dependencies
- Validates kernel for Cilium (BPF support)
- Installs system packages (age, kubectl, helm, ansible)
- Generates Age encryption keys (`Age/keys.txt`)
- Creates SOPS configuration (`.sops.yaml`)
- Runs the Cloudflare DNS wizard (interactive)

To skip the DNS wizard:
```bash
python3 noah.py setup initialize --skip-dns-wizard
```

Verify the environment:
```bash
python3 noah.py setup doctor
```

Reset and start over (removes venv, Age keys, secrets store, SOPS config):
```bash
python3 noah.py setup reset
```

> **Important**: if you run `setup reset`, the Age key changes. Any previously encrypted `*.enc.yaml` files in `gitops/` will no longer be decryptable. Re-run `setup gitops` to regenerate them.

---

### Step 2: Prepare GitOps Secrets

```bash
python3 noah.py setup gitops --domain your-domain.com --node-ip <EIP>
```

**What it does:**
- Substitutes `example.com` / `${DOMAIN}` placeholders in `gitops/` with your domain
- Records the node's public IP (EC2 EIP) in the canonical store and substitutes `${NODE_PUBLIC_IP}` in `gitops/` (external-dns publishes it as the A-record target)
- Loads secrets from the canonical store (generating any missing ones)
- Fills `*.enc.yaml` placeholder values with real secrets
- Writes `.sops.yaml` with the current Age public key
- SOPS-encrypts every `*.enc.yaml` in-place

> `--node-ip` is optional on later runs — it falls back to the IP already stored in the canonical store. This recorded IP is the single entry-point address: single-node `cluster bootstrap` reuses it as the default `--node`.

**Prerequisites:** `setup initialize` completed (Age key present, Cloudflare token configured).

After running, commit and push so FluxCD can reconcile:
```bash
git add gitops/ && git commit -m "chore: configure domain and secrets"
git push origin main
```

---

### Step 3: Bootstrap Cluster

```bash
python3 noah.py cluster bootstrap \
  --domain your-domain.com \
  --flux-repo https://github.com/Engelnicolas/NOAH.git \
  --ssh-user ubuntu \
  --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GITHUB_TOKEN
```

> **Single-node:** `--node` is optional — it defaults to the IP recorded by `setup gitops --node-ip` (the single source of truth for the entry-point IP). Pass `--node <IP>` to override.
>
> **AWS:** add `--eip-alloc-id eipalloc-…` to bind an Elastic IP to the node during bootstrap; its address is published as `${NODE_PUBLIC_IP}`. The allocation id is persisted in the canonical store, so later bootstraps reuse it automatically.

**`--flux-repo` must point at the NOAH mono-repo** (`Engelnicolas/NOAH.git`), not a separate gitops repository. Flux reads from `clusters/production/` at the repo root and pulls manifests from `gitops/` via the `noah` GitRepository source.

When `--git-token` is set (or `$GITHUB_TOKEN` / `$GIT_TOKEN` env var), NOAH auto-registers the SSH deploy key on GitHub and continues without prompting. The provider is detected from the URL (GitHub, GitLab, Gitea/Forgejo).

**Without a token — manual deploy key step:**
NOAH pauses and displays the SSH public key. Add it as a read-only deploy key at `https://github.com/Engelnicolas/NOAH/settings/keys`, then press Enter.

**What it does:**
1. Installs K3s with embedded etcd on the target node
2. Deploys local-path storage provisioner
3. Writes kubeconfig to `~/.kube/config`
4. Installs Cilium CNI (bootstrap pass)
5. Bootstraps FluxCD, pointing it at `clusters/production/` in this repo
6. FluxCD reconciles the full stack automatically

> For a 3-node HA cluster: add `--ha --nodes node1,node2,node3`

Verify:
```bash
kubectl get nodes
kubectl get kustomization,helmrelease -A
```

---

### Step 4: Monitor Reconciliation

```bash
# Overview
watch kubectl get kustomization,helmrelease -A

# Live Flux logs
python3 noah.py flux logs -f
```

**Reconciliation order and timing (~25-45 min total):**

| Phase | Component | Duration | Notes |
|---|---|---|---|
| 0 | External-DNS | ~2-3 min | Creates/updates Cloudflare A records |
| 1 | cert-manager | ~2-3 min | `letsencrypt-prod` + `letsencrypt-staging` ClusterIssuers |
| 2 | Cilium CNI | ~5-7 min | Full eBPF config, Hubble Relay + UI |
| 2.5 | nginx-ingress | ~2-3 min | DaemonSet, `hostNetwork: true`, ports 80/443 |
| 3 | Authentik SSO | ~7-10 min | PostgreSQL, Redis, Server + Worker (~2 GB RAM) |
| 3.5 | Hubble SSO | ~1-2 min | Forward-auth proxy auto-provisioned in Authentik |
| 4 | Headlamp | ~3-5 min | OIDC client auto-registered in Authentik |
| 5 | Validation | ~1-2 min | Pod readiness, service health |

---

### Step 5: Get Credentials

```bash
python3 noah.py password show-password
```

---

## DNS Configuration

### Option A: Automatic (Cloudflare)

Configured during `setup initialize` via the interactive wizard. External-DNS creates A records automatically after bootstrap.

To configure manually after skipping the wizard:
```bash
export CLOUDFLARE_API_TOKEN='your-token'
```

Verify:
```bash
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns
nslookup auth.your-domain.com
```

---

### Option B: Manual DNS

After deployment, get the node IP:
```bash
kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.externalIPs[0]}'
```

Create A records at your DNS provider:

| Hostname | Type | Value |
|---|---|---|
| `auth.your-domain.com` | A | `<node-ip>` |
| `headlamp.your-domain.com` | A | `<node-ip>` |
| `hubble.your-domain.com` | A | `<node-ip>` |

---

### Option C: Local Testing

```bash
EXTERNAL_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.externalIPs[0]}')
echo "$EXTERNAL_IP auth.your-domain.com headlamp.your-domain.com hubble.your-domain.com" | sudo tee -a /etc/hosts
```

---

## Accessing Services

| Service | URL |
|---|---|
| Authentik SSO | `https://auth.your-domain.com` |
| Headlamp Dashboard | `https://headlamp.your-domain.com` |
| Hubble UI | `https://hubble.your-domain.com` |

**Login:**
- Authentik: username `admin`, password from `python3 noah.py password show-password`
- Headlamp: click "Sign in with OIDC", use Authentik credentials
- Hubble UI: no authentication required

**Rotate password** (see [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md)):
```bash
python3 noah.py password new
python3 noah.py setup gitops --domain your-domain.com
python3 noah.py flux sync
```

---

## Troubleshooting

### Services unreachable

```bash
kubectl get pods -A
kubectl get svc ingress-nginx-controller -n ingress-nginx
nslookup auth.your-domain.com
```

### FluxCD kustomizations not progressing

```bash
kubectl get kustomization -A
kubectl describe kustomization infrastructure -n flux-system
```

Common causes:
- **`GitRepository "noah" not found`** — `noah-source.yaml` missing from `clusters/production/`. Re-run bootstrap or add it manually.
- **SOPS decryption failed** — Age key mismatch (see below).
- **Dependency not ready** — `apps` waits on `infrastructure`; `cert-manager-issuers` waits on `infrastructure`. Normal during initial rollout.

### SOPS decryption failed (Age key mismatch)

If you see `no identity matched any of the recipients`, the `*.enc.yaml` files in `gitops/` were encrypted with a different Age key than the one in `Age/keys.txt`. This happens after `setup reset` or when deploying from a fresh clone.

**Recovery:**
```bash
# Re-encrypt all secrets with the current key
python3 noah.py setup gitops --domain your-domain.com
git add gitops/ && git commit -m "fix: re-encrypt secrets with current Age key"
git push origin main
flux reconcile kustomization flux-system --with-source
```

If the `*.enc.yaml` files are still encrypted (i.e., the `setup gitops` command itself fails to decrypt them), replace them with plaintext templates first — the file format expected by each service is documented in `Scripts/gitops/gitops_init.py` (`_get_or_generate_secrets` function).

### Pods not starting

```bash
kubectl get events -A --sort-by=.metadata.creationTimestamp | tail -20
kubectl logs -n authentik deployment/authentik-server
kubectl logs -n kube-system ds/cilium
```

### Certificate errors

```bash
kubectl get certificate -A
kubectl describe challenge -A   # shows ACME HTTP-01 status
```

Certificates require valid DNS records. Ensure A records resolve before expecting TLS.

### Resource shortfall

```bash
kubectl top nodes
kubectl top pods -A
# Minimum: 4 CPU, 8 GB RAM, 50 GB storage
```

### Full reset

```bash
python3 noah.py password show-password > backup-credentials.txt
python3 noah.py cluster destroy --force
python3 noah.py cluster bootstrap \
  --domain your-domain.com \
  --flux-repo https://github.com/Engelnicolas/NOAH.git \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GITHUB_TOKEN
```

---

## Validation Checklist

```bash
kubectl get pods -A                  # all Running
kubectl get kustomization -A         # all True
kubectl get helmrelease -A           # all Ready
kubectl top nodes                    # resource headroom
```

- All pods `Running`
- All kustomizations `True`
- All HelmReleases `Ready`
- DNS resolves to node IP
- HTTPS works (valid cert after ~5 min)
- Authentik login succeeds
- Headlamp shows cluster resources
- Hubble UI shows network flows

---

## Maintenance

```bash
# Check status
python3 noah.py cluster status
kubectl get kustomization,helmrelease -A

# View credentials
python3 noah.py password show-password

# Update NOAH
git pull origin main
python3 noah.py setup initialize --skip-tests

# Backup critical files
tar -czf noah-backup-$(date +%Y%m%d).tar.gz \
  Age/ Secrets/ gitops/.sops.yaml
```

---

## Additional Resources

- [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) — day-to-day GitOps workflow and secret rotation
- [`DNS_MANAGEMENT_GUIDE.md`](DNS_MANAGEMENT_GUIDE.md) — Cloudflare DNS setup details
- [`HEADLAMP_INTEGRATION.md`](HEADLAMP_INTEGRATION.md) — Headlamp OIDC configuration

---

Made with love by the NOAH Team
