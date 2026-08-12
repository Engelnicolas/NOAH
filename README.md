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
[![Release](https://img.shields.io/badge/release-v0.1.0-green.svg)](https://github.com/Engelnicolas/NOAH/releases)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-K3s-326CE5.svg?logo=kubernetes&logoColor=white)](https://k3s.io/)
[![GitOps](https://img.shields.io/badge/GitOps-FluxCD-5468FF.svg)](https://fluxcd.io/)

[Quick start](#quick-start) · [Architecture](#architecture) · [CLI](#cli-reference) · [Docs](docs/)

</div>

---

## Overview

Standing up a real Kubernetes platform means wiring together a CNI, an ingress
controller, certificate automation, DNS, an identity provider and a GitOps engine —
then keeping every secret out of Git while still getting it into the cluster.

NOAH is a single Python CLI that does that wiring. Give it a bare Linux host and a
domain; get back a reconciling, SSO-protected, HTTPS-terminated cluster.

```bash
python3 noah.py cluster bootstrap
```

**Design principles**

- **One entry point.** The node IP and domain are recorded once, then reused as
  defaults by every later command.
- **Git is the source of truth — except for secrets.** Flux reconciles `gitops/`
  continuously; secrets live in a SOPS/Age-encrypted store and are applied
  out-of-band, so they are never committed.
- **No hidden state.** Everything NOAH knows is in the repo or in the encrypted
  canonical store, both readable and backupable.

| Component | Role |
|---|---|
| **K3s** (embedded etcd) | Lightweight Kubernetes control plane |
| **Cilium** | eBPF CNI with Hubble network observability |
| **FluxCD** | Continuous GitOps reconciliation from `gitops/` |
| **cert-manager** | Automatic TLS certificates via Let's Encrypt |
| **external-dns** | Automatic Cloudflare DNS records |
| **nginx-ingress** | L7 ingress bound to the node's :80/:443 via `hostPort` |
| **Authentik** | SSO / OIDC identity provider |
| **Headlamp** | Kubernetes dashboard, SSO-gated |
| **Hubble UI** | Live network flows, SSO-gated via forward-auth |
| **Nextcloud** | File sync & share, OIDC-integrated |
| **Stalwart** | Mail server (SMTP / IMAP / JMAP) — **opt-in** |

## Quick start

> **Prerequisites:** a Linux host you can SSH into (4 CPU / 16 GB RAM / 250 GB NVMe,
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

# 4. Provision K3s and bootstrap FluxCD (domain, IP and Git remote reused as defaults)
export GITHUB_TOKEN=ghp_xxx
python3 noah.py cluster bootstrap

# 5. Wait for the stack to converge, then print the verdict (~25–45 min)
python3 noah.py cluster verify --domain your-domain.com

# 6. Retrieve the Authentik admin credentials
python3 noah.py password show-password
```

> [!IMPORTANT]
> NOAH must always be run **from the repository root** — it checks that `Scripts/`,
> `Ansible/` and `noah.py` are present before doing anything.

## Architecture

### Request path

```
                          Internet
                             │
                             │  external-dns publishes every record
                             │  in Cloudflare → NODE_PUBLIC_IP
                             ▼
             nginx-ingress · single Deployment · hostPort :80/:443
                             │  TLS terminated with Let's Encrypt certs
                             │  issued by cert-manager
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ┌──────────┐       ┌──────────┐       ┌────────────┐
    │Authentik │◄──────┤ Headlamp │       │ Hubble UI  │
    │SSO / OIDC│ OIDC  └──────────┘       └──────┬─────┘
    └────┬─────┘                                 │ forward-auth
         │                                       └──► Authentik
    PostgreSQL + Redis
─────────────────────────────────────────────────────────────────
  Cilium (eBPF datapath + Hubble)   ·   CoreDNS   ·   cert-manager
─────────────────────────────────────────────────────────────────
                    K3s — embedded etcd
```

### GitOps reconciliation

Two trees, two jobs. `clusters/production/` holds the Flux `Kustomization` custom
resources — the control plane of the reconciliation. `gitops/` holds the actual Helm
and Kustomize manifests they point at.

```
clusters/production/            ← Flux reconciliation root
├── noah-source.yaml            GitRepository → gitops/
├── infrastructure.yaml         → gitops/infrastructure/
├── cert-manager-issuers.yaml   → gitops/infrastructure/cert-manager-issuers/
├── apps.yaml                   → gitops/apps/
├── apps-extra.yaml             → gitops/apps-extra/
└── flux-system/                written by `flux bootstrap`
```

Ordering is declared **only between those four Kustomizations**, through `dependsOn`:

```
infrastructure → cert-manager-issuers → apps → apps-extra
```

Nothing under `gitops/` declares a `dependsOn`. The components inside
`gitops/infrastructure/` — Cilium, nginx-ingress, cert-manager, external-dns, CoreDNS —
carry no ordering between them and converge independently. The four-stage chain is what
guarantees that issuers exist before apps request certificates, and that the slow
second-phase apps (Nextcloud, Stalwart) can never block or time out the core ones.

### Secrets

The part most GitOps setups get wrong, stated plainly:

- **Single source of truth:** `Secrets/canonical-secrets.enc.yaml`, encrypted with SOPS/Age.
- **Never committed, never reconciled by Flux.** NOAH renders Kubernetes `Secret`
  manifests from the canonical store and applies them to the cluster directly — at
  bootstrap, on demand via `noah secrets apply`, and on rotation.
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
| Nextcloud | `nextcloud.your-domain.com` | Authentik (OIDC), or local |
| Stalwart mail *(opt-in)* | `mail.your-domain.com` | break-glass `admin` (`secrets canonical --show`) |

Stalwart is **not deployed by default**. Add it with
`python3 noah.py setup gitops --domain … --with-stalwart` (re-running without the flag
removes it again), then commit and push. Mail protocols (SMTP 25/587/465, IMAP 143/993)
bind the node's public IP directly, and sending real mail needs AWS-side steps — outbound
port 25 unblocking and an EIP PTR record. See the
[Deployment Guide](docs/DEPLOYMENT_GUIDE.md#mail-prerequisites-stalwart).

## Requirements

| | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | **16 GB** | **32 GB** |
| Disk | 1 × NVMe 250 GB | 2 × NVMe 500 GB, mirrored |
| Network | 1 GbE | 2.5 GbE or better |

- Ubuntu 20.04+, Debian 11+, or RHEL/CentOS 8+ — Ubuntu Server 24.04 LTS is the reference
- Kernel 5.10 or newer (required by Cilium's eBPF datapath)
- NVMe or SSD for `/var/lib/rancher/k3s` — etcd is write-heavy

**8 GB is not enough.** Authentik alone — server, worker and Redis — takes about 2 GB,
before Nextcloud and its database, Cilium, Hubble and the ingress controller.

**Workstation** — Python 3.12+ (set by the pinned `ansible-core`; `click>=8.3.3` already
rules out 3.9 and below). `kubectl`, the FluxCD CLI, Ansible, `age` and `sops` are
installed by `setup initialize`.

### On availability

Adding nodes gives you **etcd quorum and scheduling capacity, not high availability.**
Three properties make the entry point single:

- the ingress controller is one `Deployment` bound to `:80`/`:443` on a single node via
  `hostPort`, fronted by a `ClusterIP` service. Two controller pods can never coexist on
  that node, so its rollout is pinned to `maxSurge: 0` — every update is a brief outage;
- every DNS record external-dns publishes points at one node's IP, pinned through
  `publish-status-address`;
- servers join via `--server https://<node1>:6443`, and the kubeconfig targets that same
  address.

Lose that node and the cluster survives — the traffic does not. **Planned maintenance
means a planned interruption.** Real HA needs a floating entry point, not implemented today.

## Repository layout

```
NOAH/
├── noah.py                  # CLI entry point (run from repo root)
├── Scripts/                 # Python orchestration modules
├── Ansible/                 # K3s + FluxCD bootstrap roles
├── Tests/                   # pytest suite
├── Age/keys.txt             # Age private key (encrypts the canonical store)
├── Secrets/                 # canonical-secrets.enc.yaml — single source of truth
├── clusters/production/     # Flux Kustomization CRs — the reconciliation root
├── gitops/                  # manifests Flux reconciles
│   ├── infrastructure/      # cilium, nginx-ingress, cert-manager,
│   │                        #   cert-manager-issuers, external-dns, coredns
│   ├── apps/                # authentik, headlamp, hubble-auth
│   └── apps-extra/          # nextcloud, stalwart (opt-in)
└── docs/                    # documentation
```

## Development

```bash
pip install -r Scripts/utils/requirements.txt   # deps, without the venv bootstrap

pytest Tests/ -q                                # default suite
pytest Tests/ -v -m integration                 # needs a real sops binary
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q         # skip Ansible

ruff check Scripts/ noah.py
bandit -r Scripts/ noah.py -ll
ansible-lint Ansible/
```

`Tests/pytest.ini` excludes two markers by default: `integration` (needs the real `sops`
binary, or mutates the canonical store) and `cluster` (needs a live cluster via `kubectl`).

`noah.py` re-execs itself under `.venv/bin/python3` when the venv exists, so
`python3 noah.py` always runs with the right interpreter — no activation needed.

| Variable | Purpose |
|---|---|
| `NOAH_ROOT_DIR` | Override the repo root (default: cwd) |
| `NOAH_DOMAIN` | Default domain for CLI commands |
| `AGE_KEY_FILE` | Path to the Age private key (default: `Age/keys.txt`) |
| `GITHUB_TOKEN` / `GIT_TOKEN` | Git provider token, for deploy-key registration |
| `NOAH_SKIP_ANSIBLE` | Skip Ansible execution (tests) |
| `NOAH_DISABLE_SOPS` | Store secrets in plaintext (dev/test only) |

## Contributing

Issues and pull requests are welcome — read [`CONTRIBUTING.md`](docs/CONTRIBUTING.md)
first, and run the lint, security and test commands above before opening a PR.

NOAH uses the [Developer Certificate of Origin](docs/DCO) — **no CLA, no paperwork**.
Sign off your commits with `git commit -s`. You keep your copyright, and your
contribution is licensed to the project under the AGPL and nothing beyond it.

## License

Copyright (C) 2026 Nicolas Engel.

NOAH is free software under the **GNU Affero General Public License, version 3 or later**
(AGPL-3.0-or-later). Full text in [`LICENSE`](LICENSE), project-level notice in
[`COPYRIGHT`](COPYRIGHT), and a short header in every Python source file.

Under the AGPL, if you modify NOAH and make it available to users over a network, you
must also offer those users the corresponding source code.

<div align="center">

---

Made with ❤️ by [me](https://www.linkedin.com/in/nicolas-engel-france/).

</div>
