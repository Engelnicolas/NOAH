<div align="center">

```
   _   _   ___      _     _   _
  | \ | | / _ \    / \   | | | |
  |  \| || | | |  / _ \  | |_| |
  | |\  || |_| | / ___ \ |  _  |
  |_| \_| \___/ /_/   \_\|_| |_|
```

### Network Operations & Automation Hub

**A production-grade Kubernetes platform — SSO, TLS, DNS, GitOps and observability — from a single command.**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v0.0.9-green.svg)](https://github.com/Engelnicolas/NOAH/releases)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-K3s-326CE5.svg?logo=kubernetes&logoColor=white)](https://k3s.io/)
[![GitOps](https://img.shields.io/badge/GitOps-FluxCD-5468FF.svg)](https://fluxcd.io/)

[Quick start](#quick-start) · [What you get](#what-you-get) · [Architecture](#architecture) · [CLI](#cli-reference) · [Docs](docs/)

</div>

---

## Overview

Standing up a "real" Kubernetes platform means wiring together a CNI, an ingress
controller, certificate automation, DNS, an identity provider and a GitOps engine
— then keeping every secret out of Git while still getting it into the cluster.

NOAH does that wiring for you. It is a single Python CLI (`noah.py`) that takes a
bare Linux host and a domain name, and returns a reconciling, SSO-protected,
HTTPS-terminated Kubernetes cluster.

```bash
python3 noah.py cluster bootstrap
```

**Design principles**

- **One entry point.** A single node IP and domain are recorded once, then reused as
  defaults by every subsequent command.
- **Git is the source of truth — except for secrets.** Flux reconciles `gitops/`
  continuously; secrets live in a SOPS/Age-encrypted store and are applied
  **out-of-band**, so they are never committed.
- **Declarative ordering.** Reconciliation dependencies are explicit, so the stack
  converges in one pass instead of a retry storm.
- **No hidden state.** Everything NOAH knows lives in the repo or in the encrypted
  canonical store — both of which you can read and back up.

## What you get

| Component | Role |
|---|---|
| **K3s** (embedded etcd) | Lightweight Kubernetes — single-node or 3-node HA |
| **Cilium** | eBPF CNI with Hubble network observability |
| **FluxCD** | Continuous GitOps reconciliation from `gitops/` |
| **cert-manager** | Automatic TLS certificates via Let's Encrypt |
| **external-dns** | Automatic Cloudflare DNS record management |
| **nginx-ingress** | L7 ingress on `hostNetwork` (ports 80/443) |
| **Authentik** | SSO / OIDC identity provider |
| **Headlamp** | Kubernetes dashboard, SSO-gated |
| **Hubble UI** | Live network flows, SSO-gated via forward-auth |
| **Nextcloud** | File sync & share, OIDC-integrated |
| **Stalwart** | Mail server (SMTP / IMAP / JMAP) |

## Quick start

> **Prerequisites:** a Linux host you can SSH into (4 CPU / 8 GB RAM / 50 GB disk,
> kernel 5.10+), a domain on Cloudflare, and a GitHub token. Everything else is
> installed for you.

```bash
# 1. Clone and initialize — installs tooling, generates the Age key, runs the DNS wizard
git clone https://github.com/Engelnicolas/NOAH.git && cd NOAH
python3 noah.py setup initialize

# 2. Point the GitOps tree at your domain and record the node's public IP
python3 noah.py setup gitops --domain your-domain.com --node-ip <NODE_PUBLIC_IP>

# 3. Commit and push, so Flux has something to reconcile
git add gitops/ && git commit -m "chore: configure domain" && git push origin main

# 4. Provision K3s and bootstrap FluxCD
#    Domain, node IP and Git remote from step 2 are reused as defaults
export GITHUB_TOKEN=ghp_xxx
python3 noah.py cluster bootstrap

# 5. Wait for the stack to converge, then print the verdict (~25–45 min)
python3 noah.py cluster verify --domain your-domain.com

# 6. Retrieve the Authentik admin credentials
python3 noah.py password show-password
```

> [!IMPORTANT]
> NOAH must always be run **from the repository root**. It verifies that
> `Scripts/`, `Ansible/` and `noah.py` are present before doing anything.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    User access layer                      │
│  https://auth.your-domain.com      (Authentik SSO)        │
│  https://headlamp.your-domain.com  (K8s dashboard)        │
│  https://hubble.your-domain.com    (network flows)        │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS / TLS (Let's Encrypt)
                         ▼
┌──────────────────────────────────────────────────────────┐
│        nginx-ingress (hostNetwork, ports 80/443)          │
└────────────────────────┬─────────────────────────────────┘
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌───────────────┐
│  Authentik   │  │  Headlamp    │  │   Hubble UI   │
│  SSO / OIDC  │◄─┤   (OIDC)     │  │ (forward-auth)│
└──────┬───────┘  └──────────────┘  └───────────────┘
       ├──────────┬──────────┐
       ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────────┐
│PostgreSQL│ │ Redis  │ │   Cilium   │
└──────────┘ └────────┘ └────────────┘
────────────────────────────────────────────────────────────
              Kubernetes (K3s, embedded etcd)
────────────────────────────────────────────────────────────
```

**Reconciliation order**, enforced through Flux `dependsOn`:

```
external-dns → cert-manager → Cilium → nginx-ingress → Authentik → Hubble UI → Headlamp
```

### The secrets model

This is the part most GitOps setups get wrong, so it is worth stating plainly:

- **Single source of truth:** `Secrets/canonical-secrets.enc.yaml`, encrypted with
  SOPS/Age.
- **Never committed, never reconciled by Flux.** NOAH renders Kubernetes `Secret`
  manifests from the canonical store and applies them to the cluster directly —
  at bootstrap, on demand via `noah secrets apply`, and on rotation.
- **Two files are your entire recovery story:** `Age/keys.txt` and
  `Secrets/canonical-secrets.enc.yaml`. Back both up offline.

See the [Operations Guide](docs/OPERATIONS_GUIDE.md) for rotation and recovery.

## CLI reference

```
noah.py
├── setup         initialize · gitops · doctor · update-sops · reset
├── cluster       bootstrap · verify · status · add-nodes · destroy
├── flux          sync · status · logs
├── secrets       canonical · apply · rotate · generate · validate · regenerate · init
├── password      show-password · new
├── certificates  generate-certs · list · deploy-manager
├── config        show · domains · helm-values · override
├── test          sso · headlamp · hubble
└── status        overall status of deployed services
```

Common day-2 operations:

```bash
python3 noah.py setup doctor                     # diagnose the environment
python3 noah.py cluster status                   # nodes, etcd quorum, Flux state
python3 noah.py flux sync                        # force immediate reconciliation
python3 noah.py secrets canonical --show         # inspect the canonical store
python3 noah.py secrets rotate --service authentik --apply
```

Every command supports `--help`.

## Service access

| Service | URL | Authentication |
|---|---|---|
| Authentik SSO | `auth.your-domain.com` | `admin` + `noah password show-password` |
| Headlamp | `headlamp.your-domain.com` | Sign in with OIDC → Authentik |
| Hubble UI | `hubble.your-domain.com` | Authentik forward-auth |
| Nextcloud | `nextcloud.your-domain.com` | Log in with Authentik (OIDC), or local |
| Stalwart mail | `mail.your-domain.com` | break-glass `admin` (`secrets canonical --show`) |

Mail protocols (SMTP 25/587/465, IMAP 143/993) bind the node's public IP directly.
Sending real mail needs additional AWS-side steps — outbound port 25 unblocking and
an EIP PTR record. See the
[Deployment Guide](docs/DEPLOYMENT_GUIDE.md#mail-prerequisites-stalwart).

## Requirements

**Target node(s)**

- Ubuntu 20.04+, Debian 11+, or RHEL/CentOS 8+
- Kernel 5.10 or newer (required by Cilium's eBPF datapath)
- Minimum 4 CPU / 8 GB RAM / 50 GB disk — recommended 8 CPU / 16 GB / 100 GB
- Outbound internet connectivity

**Workstation** — Python 3.8+. `kubectl`, the FluxCD CLI, Ansible, `age` and `sops`
are installed automatically by `setup initialize`.

## Repository layout

```
NOAH/
├── noah.py                  # CLI entry point (run from repo root)
├── Scripts/                 # Python orchestration modules
├── Ansible/                 # K3s + FluxCD bootstrap roles
├── Tests/                   # pytest suite
├── Age/keys.txt             # Age private key (encrypts the canonical store)
├── Secrets/                 # canonical-secrets.enc.yaml — single source of truth
├── clusters/production/     # Flux reconciliation root (written by flux bootstrap)
├── gitops/                  # Helm/Kustomize manifests Flux reconciles
│   ├── infrastructure/      # cilium, cert-manager, coredns, external-dns, nginx-ingress
│   ├── apps/                # authentik, headlamp, hubble-auth
│   └── apps-extra/          # nextcloud, stalwart
└── docs/                    # documentation
```

`flux bootstrap` writes to `clusters/production/`; the `gitops/` subtree holds the
actual manifests, pulled through the `noah` GitRepository source.

## Development

```bash
# Install dependencies without the venv bootstrap
pip install -r Scripts/utils/requirements.txt

# Tests
pytest Tests/ -v                          # unit tests (integration excluded)
pytest Tests/ -v -m integration           # include integration (needs a real sops)
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q   # skip Ansible

# Lint and security scan
ruff check Scripts/ noah.py
bandit -r Scripts/ noah.py -ll
ansible-lint Ansible/
```

`noah.py` re-execs itself under `.venv/bin/python3` when the venv exists, so
`python3 noah.py` always runs with the right interpreter — no activation needed.

### Environment variables

| Variable | Purpose |
|---|---|
| `NOAH_ROOT_DIR` | Override the repo root (default: cwd) |
| `NOAH_DOMAIN` | Default domain for CLI commands |
| `AGE_KEY_FILE` | Path to the Age private key (default: `Age/keys.txt`) |
| `GITHUB_TOKEN` / `GIT_TOKEN` | Git provider token, for deploy-key registration |
| `NOAH_SKIP_ANSIBLE` | Skip Ansible execution (tests) |
| `NOAH_DISABLE_SOPS` | Store secrets in plaintext (dev/test only) |

## Contributing

Issues and pull requests are welcome. Before opening a PR, please run the lint,
security and test commands listed under [Development](#development).

## License

NOAH is free software, licensed under the **GNU Affero General Public License,
version 3 or later** (AGPL-3.0-or-later). The full text is in [`LICENSE`](LICENSE),
and every source file carries a short notice.

Under the AGPL, if you modify NOAH and make it available to users over a network,
you must also offer those users the corresponding source code.

<div align="center">

---

Made with ❤️ by [![me](https://www.nicolasengel.fr)].

</div>
