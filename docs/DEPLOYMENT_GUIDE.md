# NOAH Deployment Guide

**Version**: 0.0.8
**Last Updated**: April 2026

Deploy NOAH (Network Operations & Automation Hub) - a complete Kubernetes infrastructure with SSO authentication and web dashboards.

> **What's new in v0.0.8** — K3s now uses embedded etcd (no more SQLite SPOF), and application services are reconciled by **FluxCD** from a Git repository. The legacy `noah deploy <service>` commands are deprecated; use `noah cluster bootstrap` to provision and `noah flux ...` to operate.
> See [`MIGRATION_GUIDE.md`](MIGRATION_GUIDE.md) for the v0.0.8 upgrade and [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) for the day-to-day GitOps workflow.

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

### What is NOAH?

NOAH deploys a complete Kubernetes stack:

- **Kubernetes (K3s)** - Lightweight K8s distribution
- **Cilium CNI** - eBPF-based networking + Ingress
- **Authentik SSO** - Identity and access management
- **Headlamp Dashboard** - Kubernetes web UI with SSO
- **Hubble UI** - Network observability
- **External-DNS** - Optional automatic DNS (Cloudflare)

### Architecture

```
┌──────────────────────────────────────────────────┐
│  Users → https://auth.yourdomain.com            │
│         https://headlamp.yourdomain.com          │
│         https://hubble.yourdomain.com            │
└────────────────────┬─────────────────────────────┘
                     │ HTTPS/TLS
                     ▼
┌──────────────────────────────────────────────────┐
│         Cilium Ingress (LoadBalancer)            │
└────────┬──────────┬──────────┬───────────────────┘
         │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐
    │Authentik│ │Headlamp│ │Hubble UI│
    │SSO/OIDC │◄┤(OIDC)  │ │         │
    └────┬────┘ └────────┘ └─────────┘
         │
    ┌────┴─────┬──────────┐
    │PostgreSQL│  │Redis │Cilium CNI│
    └──────────┴──┴──────┴──────────┘
───────────────────────────────────────
      Kubernetes (K3s) Cluster
───────────────────────────────────────
```

**Deployment Time**: ~25-45 minutes total

---

## Requirements

### System
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **CPU**: 4 cores minimum (8+ recommended)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB free (100GB+ recommended)
- **Kernel**: Linux 5.10+ (for Cilium eBPF)
- **Network**: Internet connectivity

### Tools (auto-installed)
- Python 3.8+
- kubectl, FluxCD,ansible
- age, sops (encryption)

### DNS Options
1. **Cloudflare** (automatic) - Requires API token
2. **Manual** - Any DNS provider with A record support
3. **Local** - /etc/hosts for testing

---

## Quick Start (v0.0.8, GitOps)

```bash
# 1. One-time setup (dependency check, Age key generation, DNS token).
git clone https://github.com/Engelnicolas/NOAH.git && cd NOAH
python3 noah.py setup initialize   # interactive wizard configures Cloudflare token

# 2. Prepare the GitOps repository automatically.
#    The token is only needed to create and push to GitHub.
export GITHUB_TOKEN=ghp_xxx   # only needed for 
python3 noah.py setup gitops \
  --domain yourdomain.com \
  
  

# 3. Bootstrap K3s + FluxCD. GIT_TOKEN auto-registers the SSH deploy key.
python3 noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain yourdomain.com \
  --flux-repo https://github.com/yourorg/noah-gitops \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GIT_TOKEN

# 4. Watch FluxCD reconcile the stack.
python3 noah.py flux status
python3 noah.py flux logs -f          # live tail (Ctrl-C to stop)

# 5. Get Authentik admin credentials.
python3 noah.py password show-password
```

> For a 3-node HA cluster, replace step 3 with:
> `python3 noah.py cluster bootstrap --ha --nodes n1,n2,n3 --domain ... --flux-repo ...`


**Access services:**
- Authentik: `https://auth.yourdomain.com`
- Headlamp: `https://headlamp.yourdomain.com`
- Hubble: `https://hubble.yourdomain.com`

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
- Generates Age encryption keys
- Creates SOPS configuration
- **Runs the Cloudflare DNS wizard** (interactive — configure API token and DNS zone)

To skip the wizard (e.g. in CI or if you prefer manual DNS):
```bash
python3 noah.py setup initialize --skip-dns-wizard
```

**Verify:**
```bash
python3 noah.py setup doctor
```

**Start over (removes venv, Age keys, secrets store, SOPS config, FluxCD deploy key):**
```bash
python3 noah.py setup reset
```

---

### Step 2: Prepare the GitOps Repository

The `setup gitops` command automates everything: it copies the `flux-repo/` template, substitutes your domain, fills all secrets from the canonical store, SOPS-encrypts the secret files, and optionally creates and pushes to a GitHub repository.

```bash
# Local only (no push) — repo written to ./gitops-yourdomain.com
python3 noah.py setup gitops --domain yourdomain.com

# With automatic GitHub push (recommended)
export GITHUB_TOKEN=ghp_xxx   # only needed for 
python3 noah.py setup gitops \
  --domain yourdomain.com \
  
  
```

The command prints the exact `cluster bootstrap` invocation to run next.

**Prerequisites:**
- `setup initialize` completed (Age keys + canonical secrets store present; Cloudflare token configured via the wizard)

---

### Step 3: Bootstrap Cluster

A single command provisions K3s, installs FluxCD, and points it at your GitOps repository.

**Recommended — automatic deploy key registration (no manual step):**
```bash
python3 noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain noah-infra.com \
  --flux-repo https://github.com/Engelnicolas/noah-gitops.git \
  --ssh-user ubuntu \
  --ssh-key ~/.ssh/id_ed25519 \
  --git-token $GIT_TOKEN
```

When `--git-token` is provided (or `$GIT_TOKEN` / `$GITHUB_TOKEN` env var is set), NOAH registers the SSH deploy key automatically via the provider API and skips the interactive prompt. The provider is auto-detected from the URL (GitHub, GitLab, Gitea/Forgejo). For self-hosted instances use `--git-provider gitlab` or `--git-provider gitea` to force the correct API.

**Without a token — manual deploy key step:**
```bash
python3 noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain noah-infra.com \
  --flux-repo https://github.com/Engelnicolas/noah-gitops.git \
  --ssh-user ubuntu \
  --ssh-key ~/.ssh/id_ed25519
```

NOAH will pause and display the SSH public key. Add it as a **read-only deploy key** at `https://github.com/<org>/<repo>/settings/keys`, then press Enter to continue. The key is saved to `Age/flux-deploy-key.pub` and reused on subsequent bootstraps.

**What it does:**
- Installs K3s with embedded etcd on the target node
- Deploys local-path storage provisioner
- Configures kubectl access (`~/.kube/config`)
- Bootstraps FluxCD pointed at your GitOps repository
- FluxCD then reconciles the full stack automatically

> For a 3-node HA cluster: add `--ha --nodes node1,node2,node3`

**Verify:**
```bash
kubectl get nodes       # Should show Ready
python3 noah.py flux status
```

---

### Step 4: Monitor Reconciliation

FluxCD deploys all services in order. Watch it progress:

```bash
python3 noah.py flux status          # overall reconciliation state
python3 noah.py flux logs -f         # live log tail (Ctrl-C to stop)
```

**What FluxCD reconciles (~25-45 min total):**

| Phase | Component | Duration | Notes |
|-------|-----------|----------|-------|
| 0 | External-DNS | ~2-3 min | `upsert-only` by default — creates/updates Cloudflare A records. Use `--policy sync` to also remove stale records. |
| 1 | cert-manager | ~2-3 min | `letsencrypt-prod` and `letsencrypt-staging` ClusterIssuers |
| 2 | Cilium CNI | ~5-7 min | eBPF networking, Cilium Operator, Hubble Relay + UI |
| 2.5 | nginx-ingress | ~2-3 min | DaemonSet with `hostNetwork: true`, binds ports 80/443 on node public IP |
| 3 | Authentik SSO | ~7-10 min | PostgreSQL, Redis, Authentik Server + Worker (~2 GB RAM) |
| 3.5 | Hubble SSO | ~1-2 min | Forward-auth proxy app auto-provisioned in Authentik |
| 4 | Headlamp | ~3-5 min | OIDC client auto-registered in Authentik |
| 5 | Validation | ~1-2 min | Pod readiness, service health, network connectivity |

**Get credentials once reconciliation is complete:**
```bash
python3 noah.py password show-password
```

---

## DNS Configuration

### Option A: Automatic (Cloudflare)

**Prerequisites:** Domain on Cloudflare + API token (Zone → DNS → Edit, Zone → Zone → Read)

**Configure token:** The Cloudflare DNS wizard runs interactively during `python3 noah.py setup initialize` and stores the token encrypted in the canonical store. If you skipped the wizard (`--skip-dns-wizard`), export the token as an environment variable before bootstrapping:
```bash
export CLOUDFLARE_API_TOKEN='your-cloudflare-api-token'
```

`NOAH_EXTERNAL_DNS_ENABLED` defaults to `true` — no extra step needed after the wizard.

**Verify:**
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns
nslookup auth.yourdomain.com
```

---

### Option B: Manual DNS

**Configure AFTER deployment:**

**1. Get the node public IP:**
```bash
kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.externalIPs[0]}'
# e.g., 15.237.252.242
```

**2. Create A records at your DNS provider:**
| Hostname | Type | Value |
|----------|------|-------|
| `auth.yourdomain.com` | A | `<node-public-ip>` |
| `headlamp.yourdomain.com` | A | `<node-public-ip>` |
| `hubble.yourdomain.com` | A | `<node-public-ip>` |

**3. Verify:**
```bash
nslookup auth.yourdomain.com  # Should return LoadBalancer IP
```

---

### Option C: Local Testing

**Configure AFTER deployment:**
```bash
# Get node public IP
EXTERNAL_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.externalIPs[0]}')

# Add to /etc/hosts
echo "$EXTERNAL_IP auth.yourdomain.com headlamp.yourdomain.com hubble.yourdomain.com" | sudo tee -a /etc/hosts
```

---

## Accessing Services

### Get Credentials

```bash
python noah.py password show-password
```

**Example output:**
```
🔍 Current Authentik admin credentials:
==================================================
📍 URL:         https://auth.yourdomain.com
🌐 External IP: 65.21.238.126
👤 Username:    admin
📧 Email:       admin@localhost
🔑 Password:    test-password-abc123xyz
==================================================
```

### Login Flow

**1. Authentik SSO:**
- Open: `https://auth.yourdomain.com`
- Username: `admin`
- Password: (from `password show` command)

**2. Headlamp Dashboard:**
- Open: `https://headlamp.yourdomain.com`
- Click "Sign in with OIDC"
- Use same Authentik credentials
- View Kubernetes resources

**3. Hubble UI:**
- Open: `https://hubble.yourdomain.com`
- No authentication required
- View network flows

### Password Management

**Rotate password** (see [`GITOPS_GUIDE.md`](GITOPS_GUIDE.md) for the full workflow):
```bash
python3 noah.py password new
python3 noah.py setup gitops --domain yourdomain.com
python3 noah.py flux sync
```

---

## Troubleshooting

### Quick Fixes

**Can't access services?**
```bash
# Check pods
kubectl get pods -A

# Check node public IP
kubectl get svc ingress-nginx-controller -n ingress-nginx

# Check DNS
nslookup auth.yourdomain.com

# Add to /etc/hosts if DNS not working
EXTERNAL_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.externalIPs[0]}')
echo "$EXTERNAL_IP auth.yourdomain.com headlamp.yourdomain.com hubble.yourdomain.com" | sudo tee -a /etc/hosts
```

**Pods not starting?**
```bash
# Check events
kubectl get events -A --sort-by=.metadata.creationTimestamp

# Check logs
kubectl logs -n identity deployment/authentik-server
kubectl logs -n kube-system ds/cilium

# Restart pod
kubectl delete pod -n identity <pod-name>
```

**Certificate errors?**
```bash
# Check certificate status
kubectl get certificate -A
kubectl describe challenge -A  # shows ACME HTTP-01 status

# Certificates require valid DNS records — ensure A records resolve before expecting TLS
```

**Insufficient resources?**
```bash
# Check resources
kubectl top nodes
kubectl top pods -A

# Minimum required: 4 CPU, 8GB RAM, 50GB storage
```

### Complete Reset

```bash
# Backup credentials
python noah.py password show-password > backup-passwords.txt

# Destroy and re-bootstrap
python noah.py cluster destroy --force
python3 noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain yourdomain.com \
  --flux-repo https://github.com/yourorg/your-noah-gitops \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519
```

### Common Issues

| Issue | Solution |
|-------|----------|
| DNS resolution fails | Add to `/etc/hosts` or wait 5-10min for propagation |
| Pods CrashLoopBackOff | Check logs: `kubectl logs <pod>` |
| Connection refused | Verify LoadBalancer IP: `kubectl get svc -A` |
| Permission denied | Fix kubeconfig: `chmod 600 ~/.kube/config` |
| Low memory | Need minimum 8GB RAM |
| Kernel too old | Need Linux 5.10+ for Cilium |

---

## Validation

### Check Status

```bash
python3 noah.py cluster status
```

### Manual Verification

```bash
# All pods running
kubectl get pods -A

# Services accessible
curl -I https://auth.yourdomain.com
curl -I https://headlamp.yourdomain.com
curl -I https://hubble.yourdomain.com

# Resource usage
kubectl top nodes
kubectl top pods -A
```

### Success Checklist

- ✅ All pods `Running`: `kubectl get pods -A`
- ✅ LoadBalancer has EXTERNAL-IP
- ✅ DNS resolves to LoadBalancer IP
- ✅ HTTPS works (accept self-signed cert)
- ✅ Can login to Authentik
- ✅ Headlamp shows cluster resources
- ✅ Hubble UI shows network flows
- ✅ `python3 noah.py cluster status` shows healthy

---

## Advanced Configuration

### Custom Subdomains

Set the subdomain environment variables in your GitOps repo's values files before bootstrapping:

```bash
# In flux-repo, edit the relevant HelmRelease values:
# NOAH_AUTHENTIK_SUBDOMAIN: "sso"
# NOAH_HEADLAMP_SUBDOMAIN: "k8s"
# Results: sso.yourdomain.com, k8s.yourdomain.com
```

### Development Mode

Pass `--validation-mode development` to skip some checks during bootstrap:

```bash
python3 noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain yourdomain.com \
  --flux-repo https://github.com/yourorg/your-noah-gitops \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 \
  --validation-mode development
```

### Resource Tuning

**For low-resource systems (8GB RAM):**
- Edit `Helm/authentik/values.yaml`
- Reduce PostgreSQL/Redis resource requests
- Redeploy: `python noah.py deploy authentik`

**For production (32GB+ RAM):**
- Increase resource limits
- Enable persistent storage
- Use production validation mode

---

## Maintenance

### Regular Operations

```bash
# Check status
python3 noah.py cluster status

# View credentials
python3 noah.py password show-password

# Rotate password (see GITOPS_GUIDE.md)
python3 noah.py password new
python3 noah.py setup gitops --domain yourdomain.com
python3 noah.py flux sync

# Update NOAH
git pull origin main
python noah.py setup initialize --skip-tests

# Wipe local environment and start fresh (keeps cluster untouched)
python noah.py setup reset
python noah.py setup initialize
```

### Backup

```bash
# Backup critical files
tar -czf noah-backup-$(date +%Y%m%d).tar.gz \
  Age/ Certificates/ Config/canonical-secrets.yaml .sops.yaml

# Backup Kubernetes resources
kubectl get all -A -o yaml > k8s-backup-$(date +%Y%m%d).yaml
```

---

## Additional Resources

- **Troubleshooting**: [troubleshooting-guide.md](troubleshooting-guide.md)
- **DNS Management**: [DNS_MANAGEMENT_GUIDE.md](DNS_MANAGEMENT_GUIDE.md)
- **Headlamp Integration**: [HEADLAMP_INTEGRATION.md](HEADLAMP_INTEGRATION.md)

---

**Made with ❤️ by the NOAH Team**
