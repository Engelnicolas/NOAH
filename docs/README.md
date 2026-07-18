# NOAH — Network Operations & Automation Hub

**Version 0.0.9**

NOAH is a Python CLI (`noah.py`) that provisions and operates a complete
Kubernetes platform on K3s: SSO, networking, dashboards, and GitOps
reconciliation — from a single command.

## What NOAH deploys

| Component | Role |
|---|---|
| **K3s** (embedded etcd) | Lightweight Kubernetes, single-node or 3-node HA |
| **Cilium** | eBPF CNI + Hubble network observability |
| **FluxCD** | Continuous GitOps reconciliation from `gitops/` |
| **cert-manager** | Automatic TLS via Let's Encrypt |
| **external-dns** | Automatic Cloudflare DNS records |
| **nginx-ingress** | L7 ingress on `hostNetwork` (ports 80/443) |
| **Authentik** | SSO / OIDC identity provider |
| **Headlamp** | Kubernetes dashboard (SSO-gated) |
| **Hubble UI** | Network flows (SSO-gated via forward-auth) |

Secrets have a single source of truth — the SOPS/Age-encrypted
`Secrets/canonical-secrets.enc.yaml` — and are delivered to the cluster
**out-of-band** (never committed to Git). See the
[Operations Guide](OPERATIONS_GUIDE.md#secrets) for the model.

## Documentation

| Guide | When to read it |
|---|---|
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | Go from zero to a running cluster, incl. DNS and troubleshooting |
| [Operations Guide](OPERATIONS_GUIDE.md) | Day-2: GitOps workflow, secret rotation, SSO, disaster recovery |

## Quick start

```bash
# 1. Clone and initialize (installs tools, generates the Age key, runs the DNS wizard)
git clone https://github.com/Engelnicolas/NOAH.git && cd NOAH
python3 noah.py setup initialize

# 2. Prepare gitops/ for your domain and record the node's public IP
python3 noah.py setup gitops --domain your-domain.com --node-ip <NODE_PUBLIC_IP>

# 3. Commit and push so Flux can reconcile this repo
git add gitops/ && git commit -m "chore: configure domain" && git push origin main

# 4. Bootstrap K3s + FluxCD — the domain and node IP recorded in step 2 and
#    this repo's origin remote are reused as defaults; the deploy-key token
#    is read from the environment
export GITHUB_TOKEN=ghp_xxx
python3 noah.py cluster bootstrap

# 5. Wait for the stack to converge and print the verdict (~25–45 min)
python3 noah.py cluster verify --domain your-domain.com

# 6. Get the Authentik admin credentials
python3 noah.py password show-password
```

> **3-node HA:** add `--ha --nodes node1,node2,node3` to step 4.
>
> **Co-located (NOAH runs on the target node):** add `--node 127.0.0.1` (or the
> node's private IP) — an instance can't SSH to its own public/Elastic IP
> (the AWS Internet Gateway doesn't hairpin it), so the recorded-IP default
> times out.

**NOAH must always be run from the repository root** — it checks for
`Scripts/`, `Ansible/`, and `noah.py`.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User access layer                     │
│  https://auth.your-domain.com      (Authentik SSO)       │
│  https://headlamp.your-domain.com  (K8s dashboard)       │
│  https://hubble.your-domain.com    (network flows)       │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS / TLS (Let's Encrypt)
                         ▼
┌─────────────────────────────────────────────────────────┐
│        nginx-ingress (hostNetwork, ports 80/443)         │
└────────────────────────┬─────────────────────────────────┘
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Authentik   │  │  Headlamp    │  │  Hubble UI   │
│  SSO / OIDC  │◄─┤  (OIDC)      │  │ (forward-auth)│
└──────┬───────┘  └──────────────┘  └──────────────┘
       ├──────────┬──────────┐
       ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────────┐
│PostgreSQL│ │ Redis  │ │   Cilium   │
└──────────┘ └────────┘ └────────────┘
───────────────────────────────────────────────────────────
              Kubernetes (K3s, embedded etcd)
───────────────────────────────────────────────────────────

FluxCD reconciliation order (enforced by dependsOn):
  external-dns → cert-manager → Cilium → nginx-ingress
              → Authentik → Hubble UI → Headlamp
```

## Repository layout

```
NOAH/
├── noah.py                  # CLI entry point (run from repo root)
├── Scripts/                 # Python orchestration modules
├── Ansible/                 # K3s + FluxCD bootstrap roles
├── Tests/                   # pytest suite
├── Age/keys.txt             # Age private key (encrypts the canonical store)
├── Secrets/                 # canonical-secrets.enc.yaml (single source of truth)
├── clusters/production/     # Flux reconciliation root (written by flux bootstrap)
│   ├── kustomization.yaml
│   ├── noah-source.yaml     # GitRepository → gitops/
│   ├── infrastructure.yaml  # Kustomization CR
│   ├── cert-manager-issuers.yaml
│   ├── apps.yaml            # Kustomization CR (dependsOn infrastructure)
│   └── apps-extra.yaml      # Kustomization CR (dependsOn apps)
├── gitops/                  # Helm/Kustomize manifests Flux reconciles
│   ├── infrastructure/      # cilium, cert-manager, external-dns, nginx-ingress
│   ├── apps/                # authentik, headlamp, hubble-auth
│   └── apps-extra/          # nextcloud, stalwart (mail)
└── docs/                    # this documentation
```

> `flux bootstrap` writes to `clusters/production/`. The `gitops/` subtree holds
> the actual manifests, pulled via the `noah` GitRepository source.

## Requirements

**Target node(s):**
- OS: Ubuntu 20.04+, Debian 11+, RHEL/CentOS 8+
- Kernel 5.10+ (required by Cilium eBPF)
- 4 CPU / 8 GB RAM / 50 GB disk minimum (8 CPU / 16 GB / 100 GB recommended)
- Internet connectivity

**Workstation tools** (auto-installed by `setup initialize`): Python 3.8+,
kubectl, FluxCD CLI, Ansible, `age`, `sops`.

## Service access

| Service | URL | Auth |
|---|---|---|
| Authentik SSO | `https://auth.your-domain.com` | `admin` + `password show-password` |
| Headlamp | `https://headlamp.your-domain.com` | "Sign in with OIDC" → Authentik |
| Hubble UI | `https://hubble.your-domain.com` | Authentik forward-auth |
| Nextcloud | `https://nextcloud.your-domain.com` | "Log in with Authentik" (OIDC) or local |
| Stalwart mail (web admin) | `https://mail.your-domain.com` | break-glass `admin` (`secrets canonical --show`, service `stalwart`) |

Mail protocols (SMTP 25/587/465, IMAP 143/993) bind the node's public IP
directly. Sending real mail additionally requires AWS-side steps (outbound
port 25 unblock, EIP PTR record) — see the
[Deployment Guide](DEPLOYMENT_GUIDE.md#mail-prerequisites-stalwart).

## Testing

```bash
pytest Tests/ -v                       # unit tests (integration excluded)
pytest Tests/ -v -m integration        # include integration (needs real sops)
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q # skip Ansible in CI
```

## License

NOAH is free software licensed under the **GNU Affero General Public License,
version 3 or later** (AGPL-3.0-or-later). The full text is in
[`LICENSE`](../LICENSE), and every source file carries a short notice.

Under the AGPL, if you modify NOAH and make it available to users over a
network, you must also offer those users the corresponding source code.

---

Made with care by the NOAH Team.
