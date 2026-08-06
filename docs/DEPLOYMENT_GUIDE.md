# NOAH Deployment Guide

**Version 0.0.9** — K3s with embedded etcd (no SQLite SPOF). The full
application stack is reconciled by FluxCD from `gitops/` in this repository.
There is no imperative `noah deploy <service>` — you provision with
`noah cluster bootstrap` and operate with `noah flux …` (see the
[Operations Guide](OPERATIONS_GUIDE.md)).

---

## Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Deployment steps](#deployment-steps)
4. [DNS configuration](#dns-configuration)
5. [Accessing services](#accessing-services)
6. [Troubleshooting](#troubleshooting)
7. [Validation checklist](#validation-checklist)

---

## Overview

`noah cluster bootstrap` does the following on the target node(s):

1. Installs K3s with embedded etcd.
2. Deploys the local-path storage provisioner and writes `~/.kube/config`.
3. Installs Cilium CNI (bootstrap pass).
4. Bootstraps FluxCD, pointing it at `clusters/production/` in this repo.
5. Delivers application secrets out-of-band (the `app-secrets` Ansible role
   `kubectl apply`s manifests rendered from the canonical store — secrets are
   never committed to Git).
6. FluxCD then reconciles the full stack from `gitops/`.

**Total time:** ~25–45 minutes.

### Reconciliation order and timing

| Phase | Component | Duration | Notes |
|---|---|---|---|
| 0 | external-dns | ~2–3 min | Creates/updates Cloudflare A records |
| 1 | cert-manager | ~2–3 min | `letsencrypt-prod` + `letsencrypt-staging` issuers |
| 2 | Cilium CNI | ~5–7 min | Full eBPF config, Hubble Relay + UI |
| 3 | nginx-ingress | ~2–3 min | Deployment, `hostPort` :80/:443, single replica |
| 4 | Authentik SSO | ~7–10 min | PostgreSQL, Redis, Server + Worker (~2 GB RAM) |
| 5 | Hubble auth | ~1–2 min | Forward-auth proxy auto-provisioned in Authentik |
| 6 | Headlamp | ~3–5 min | OIDC client auto-registered in Authentik |
| 7 | `apps-extra` | ~5–10 min | Nextcloud, plus Stalwart mail when opted in (`dependsOn: apps`) |

---

## Requirements

**System (per node):**
- OS: Ubuntu 20.04+, Debian 11+, RHEL/CentOS 8+ — Ubuntu Server 24.04 LTS is the
  reference target
- Kernel 5.10+ (Cilium eBPF)
- **16 GB RAM minimum, 32 GB recommended** — 4 cores minimum, 8 recommended
- **250 GB NVMe minimum**, 2 × 500 GB mirrored recommended
- NVMe or SSD for `/var/lib/rancher/k3s` (etcd is write-heavy)
- 1 GbE minimum, 2.5 GbE or better recommended
- Internet connectivity

> **On the 16 GB floor.** Authentik alone — server, worker and Redis — takes
> about 2 GB, before Nextcloud and its database, Cilium, Hubble and the ingress
> controller. Earlier versions of this guide said 8 GB; that figure was wrong.

**Multi-node:** inter-node latency < 10 ms. Note that additional servers give
etcd quorum and scheduling capacity, **not high availability** — the ingress
controller and every published DNS record still resolve to one node. See
[On availability](../README.md#on-availability).

**Workstation tools** (auto-installed by `setup initialize`): Python 3.8+,
kubectl, FluxCD CLI, Ansible, `age`, `sops`.

**DNS:** Cloudflare (automatic via external-dns), or any provider with manual
A records, or `/etc/hosts` for local testing — see
[DNS configuration](#dns-configuration).

---

## Deployment steps

### Step 1 — Initialize the environment

```bash
python3 noah.py setup initialize
```

This checks Python ≥ 3.8, creates `.venv/`, installs dependencies, validates
the kernel for Cilium, installs system packages (`age`, kubectl, helm,
ansible), generates the Age key (`Age/keys.txt`), writes the SOPS config, and
runs the interactive Cloudflare DNS wizard.

```bash
python3 noah.py setup initialize --skip-dns-wizard   # configure Cloudflare later
python3 noah.py setup doctor                          # diagnose the environment
python3 noah.py setup reset                           # remove venv, Age key, secrets, SOPS config
```

> **`setup reset` changes the Age key.** Anything previously encrypted with the
> old key can no longer be decrypted. Re-run `setup gitops` afterwards.

### Step 2 — Prepare gitops/ for your domain

```bash
python3 noah.py setup gitops --domain your-domain.com --node-ip <NODE_PUBLIC_IP>
```

This records your domain and the node's public IP in the canonical store and
prepares the `gitops/` tree. `${DOMAIN}` and `${NODE_PUBLIC_IP}` are substituted
by Flux at apply time from the `cluster-vars` ConfigMap (seeded by the
flux-bootstrap role), so committed manifests stay environment-agnostic.

`--node-ip` is optional on later runs — it falls back to the IP already in the
canonical store. That recorded IP is the single entry-point address:
single-node `cluster bootstrap` reuses it as the default `--node`.

> Application secrets are **not** written into `gitops/`. They live only in the
> canonical store and are delivered out-of-band (Step 4 / `secrets apply`).
> See the [Operations Guide](OPERATIONS_GUIDE.md#secrets).

### Step 3 — Commit and push

```bash
git add gitops/ && git commit -m "chore: configure domain and secrets"
git push origin main
```

Flux reconciles from the pushed repository, so the `gitops/` changes must be on
the branch Flux tracks (`--flux-branch`, default `main`).

### Step 4 — Bootstrap the cluster

```bash
export GITHUB_TOKEN=ghp_xxx
python3 noah.py cluster bootstrap
```

Every flag has a sensible default for the single-node case:

- **`--domain`** defaults to the domain recorded in Step 2; pass it to
  override.
- **`--flux-repo`** defaults to this repo's `origin` remote — the NOAH
  mono-repo, which is exactly what Flux must track (it reads
  `clusters/production/` at the root and pulls manifests from `gitops/` via
  the `noah` GitRepository source). Do **not** point it at a separate gitops
  repo.
- **`--node`** defaults to the IP recorded in Step 2. Pass `--node <IP>` to
  override; use `--node 127.0.0.1` (or the private IP) when NOAH runs *on* the
  target node — an instance cannot SSH to its own public/Elastic IP, because
  the AWS Internet Gateway does not hairpin it, so the default would time out.
- **`$GITHUB_TOKEN` / `$GIT_TOKEN`** (or `--git-token`) auto-registers the SSH
  deploy key on your git provider (GitHub/GitLab/Gitea, detected from the URL).
  Without a token, NOAH pauses and prints the public key for you to add
  manually as a read-only deploy key, then continues on Enter.
- **`--ssh-user` / `--ssh-key`** default to `ubuntu` and your standard SSH key
  resolution; pass them only for a different user or a non-default key path.
- **Multi-node control plane:** add `--ha --nodes node1,node2,node3`. Despite the
  flag's name this buys etcd quorum and scheduling capacity, **not a redundant
  entry point** — see [Requirements](#requirements).

### Step 5 — Watch reconciliation

```bash
python3 noah.py cluster verify --domain your-domain.com   # wait + print verdict
# or watch manually:
watch kubectl get kustomization,helmrelease -A
python3 noah.py flux logs -f
```

### Step 6 — Get credentials

```bash
python3 noah.py password show-password
```

---

## DNS configuration

Three options. Configure DNS **before** bootstrap so external-dns (Phase 0) can
publish records immediately.

### Option A — Automatic (Cloudflare)

external-dns watches Ingress resources and creates/updates A records in
Cloudflare automatically.

1. **Create a scoped API token** at Cloudflare → Profile → API Tokens →
   "Edit zone DNS" template. Permissions: `Zone → DNS → Edit` and
   `Zone → Zone → Read`, scoped to your zone. Never use a Global API key.
2. **Store it.** The token is captured by the DNS wizard during
   `setup initialize` and stored SOPS/Age-encrypted in the canonical store.
   If you skipped the wizard, export it before bootstrap:
   ```bash
   export CLOUDFLARE_API_TOKEN='your-token'
   ```

Verify after bootstrap:
```bash
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns
nslookup auth.your-domain.com
```

> [!WARNING]
> **DNS policy is `sync`, and it deletes.** external-dns runs with
> `policy: sync` and `txtOwnerId: noah`, both hardcoded in
> `gitops/infrastructure/external-dns/helmrelease.yaml`. It tracks ownership
> with a TXT registry and removes records it owns once the matching Ingress or
> DNSEndpoint disappears.
>
> Because the owner ID is the fixed string `noah` rather than a per-deployment
> value, **two NOAH clusters pointed at the same Cloudflare zone would claim
> each other's records and delete them.** Give each deployment its own zone, or
> change `txtOwnerId` before the second one reconciles.

### Option B — Manual DNS

After bootstrap, point your records at the node's public IP. Create A records:

| Hostname | Type | Value | TTL |
|---|---|---|---|
| `auth.your-domain.com` | A | `<node-public-ip>` | 300 |
| `headlamp.your-domain.com` | A | `<node-public-ip>` | 300 |
| `hubble.your-domain.com` | A | `<node-public-ip>` | 300 |
| `nextcloud.your-domain.com` | A | `<node-public-ip>` | 300 |
| `mail.your-domain.com` | A | `<node-public-ip>` | 300 |

With automatic DNS (Option A), the mail MX/SPF/DKIM/DMARC records are also
published by external-dns (`DNSEndpoint` CRs in `gitops/apps-extra/stalwart/`).
With manual DNS, create them yourself — the DKIM TXT value comes from
`kubectl -n flux-system get secret stalwart-dns-vars -o jsonpath='{.data.DKIM_TXT_VALUE}' | base64 -d`.

Verify:
```bash
nslookup auth.your-domain.com
curl -I https://auth.your-domain.com
```

### Option C — Local testing (`/etc/hosts`)

```bash
IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.spec.externalIPs[0]}')
echo "$IP auth.your-domain.com headlamp.your-domain.com hubble.your-domain.com" | sudo tee -a /etc/hosts
# clean up: sudo sed -i '/your-domain.com/d' /etc/hosts
```

---

## Accessing services

| Service | URL | Login |
|---|---|---|
| Authentik SSO | `https://auth.your-domain.com` | `admin` + `password show-password` |
| Headlamp | `https://headlamp.your-domain.com` | "Sign in with OIDC" → Authentik |
| Hubble UI | `https://hubble.your-domain.com` | Authentik forward-auth |
| Nextcloud | `https://nextcloud.your-domain.com` | "Log in with Authentik" (OIDC) or local `admin` |
| Stalwart mail (web admin) *(opt-in)* | `https://mail.your-domain.com` | break-glass `admin` (`secrets canonical --show`, service `stalwart`) |

Headlamp's OIDC client and Hubble's forward-auth proxy are **auto-provisioned**
in Authentik during reconciliation; so are the Nextcloud and Stalwart OIDC
clients (`apps-extra`). See the
[Operations Guide](OPERATIONS_GUIDE.md#sso) for how SSO is wired.

### Mail prerequisites (Stalwart)

Stalwart is **opt-in and not part of a default install** — precisely because of
the AWS-side prerequisites below. Enable it by re-running `setup gitops` with
the flag, then committing and pushing so Flux picks it up:

```bash
python3 noah.py setup gitops --domain your-domain.com --with-stalwart
git add gitops/ && git commit -m 'feat: enable Stalwart mail' && git push
```

The flag is **not sticky**: a later `setup gitops` run without it drops Stalwart
from `gitops/apps-extra/kustomization.yaml`, and Flux prunes the namespace on the
next reconcile. Its manifests and secrets stay in place either way, so toggling
it back on needs no other change.

Once enabled, Stalwart reconciles like any other app — but **delivering real
mail needs two AWS-side steps no manifest can do**:

1. **Outbound TCP 25 is blocked by default on EC2.** Ask AWS to lift it
   ("Request to Remove Email Sending Limitations" form), and open inbound
   25/587/465/143/993 in the instance security group.
2. **PTR (reverse DNS) for the EIP** must be set at the AWS level and match
   `mail.your-domain.com`. Without it (plus SPF/DKIM/DMARC), Gmail/Outlook
   will reject or spam-folder your mail.

Client notes:
- IMAP/SMTP clients authenticate with **OAUTHBEARER/XOAUTH2** using an
  Authentik access token for the `stalwart` OIDC app (client OAuth support
  varies — see the Operations Guide). The web admin uses the break-glass
  `admin` account.
- A user must **log in once** (IMAP/JMAP) before their address can receive
  mail: Stalwart materializes OIDC accounts on first authentication.
- Stalwart runs **v0.16.x**, which keeps its configuration in the datastore
  rather than a declarative `config.toml`. NOAH applies that configuration with
  `stalwart-cli` from a provisioning Job
  (`gitops/apps-extra/stalwart/provision-config-job.yaml`), driven by the plan
  in `apply-plan-configmap.yaml`.

To rotate the Authentik admin password, see
[Operations Guide → rotating secrets](OPERATIONS_GUIDE.md#rotating-a-secret).

---

## Troubleshooting

### Services unreachable

```bash
kubectl get pods -A
kubectl get svc ingress-nginx-controller -n ingress-nginx
nslookup auth.your-domain.com
```

### Kustomizations not progressing

```bash
kubectl get kustomization -A
kubectl describe kustomization infrastructure -n flux-system
```

- **`GitRepository "noah" not found`** — `noah-source.yaml` is missing from
  `clusters/production/`. Re-run bootstrap.
- **Dependency not ready** — `apps` waits on `infrastructure`; this is normal
  during the initial rollout.
- **SOPS decryption failed** — see below.

### SOPS decryption failed (`no identity matched any of the recipients`)

The `cluster-vars` / sops-age material was encrypted with a different Age key
than the one in `Age/keys.txt` (happens after `setup reset` or from a fresh
clone). Re-run `setup gitops`, push, and reconcile:

```bash
python3 noah.py setup gitops --domain your-domain.com
git add gitops/ && git commit -m "fix: re-encrypt with current Age key" && git push
flux reconcile kustomization flux-system --with-source
```

### Pods not starting

```bash
kubectl get events -A --sort-by=.metadata.creationTimestamp | tail -20
kubectl logs -n authentik deployment/authentik-server
kubectl logs -n kube-system ds/cilium
```

### Certificate errors

```bash
kubectl get certificate -A
kubectl describe challenge -A    # ACME HTTP-01 status
```

Certificates require resolvable DNS — ensure A records resolve before
expecting valid TLS (allow ~5 min after first issuance).

### DNS records not created (external-dns)

```bash
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns
# "authentication error" → invalid token   "permission denied" → token scope
```

The token needs `Zone → DNS → Edit` and `Zone → Zone → Read`. After fixing it
in Cloudflare, re-run `setup gitops` (or re-export `CLOUDFLARE_API_TOKEN`) and
let external-dns retry.

### Resource shortfall

```bash
kubectl top nodes
kubectl top pods -A
# Minimum: 4 cores, 16 GB RAM, 250 GB NVMe
```

### Full reset

```bash
python3 noah.py password show-password > backup-credentials.txt
python3 noah.py cluster destroy --force
python3 noah.py cluster bootstrap
```

`destroy` keeps the canonical store by default, so the domain, node IP, and
Cloudflare token recorded earlier survive the teardown — `bootstrap` reuses
them and needs no flags. For a clean-slate teardown that also wipes the store,
secrets, and certificates, add `--purge-secrets`; you then re-supply the
Cloudflare token via `setup gitops` and pass `--domain` to bootstrap.

---

## Validation checklist

```bash
kubectl get pods -A             # all Running
kubectl get kustomization -A    # all Ready=True
kubectl get helmrelease -A      # all Ready
kubectl top nodes               # resource headroom
```

- [ ] All pods `Running`
- [ ] All kustomizations and HelmReleases `Ready`
- [ ] DNS resolves to the node IP
- [ ] HTTPS works with a valid Let's Encrypt cert
- [ ] Authentik login succeeds (`admin`)
- [ ] Headlamp authenticates via Authentik OIDC
- [ ] Hubble UI prompts for Authentik login (no anonymous access)

---

See the [Operations Guide](OPERATIONS_GUIDE.md) for day-2 work: GitOps
changes, secret rotation, SSO details, scaling to HA, and disaster recovery.
