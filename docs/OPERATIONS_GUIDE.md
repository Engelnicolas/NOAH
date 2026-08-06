# NOAH Operations Guide

**Version 0.0.9** — day-2 operations for a running cluster. For first-time
installation see the [Deployment Guide](DEPLOYMENT_GUIDE.md).

---

## Contents

1. [The GitOps model](#the-gitops-model)
2. [Anatomy of `gitops/`](#anatomy-of-gitops)
3. [Secrets](#secrets)
4. [Common operations](#common-operations)
5. [SSO and OIDC](#sso)
6. [Scaling to HA](#scaling-to-ha)
7. [DNS day-2](#dns-day-2)
8. [Disaster recovery](#disaster-recovery)
9. [Command reference](#command-reference)

---

## The GitOps model

Git is the source of truth for every **non-secret** manifest. FluxCD's
controllers run inside the cluster, poll the repository (default every
10 minutes), and apply the result. For these manifests **you don't
`kubectl apply` in production — you `git push`.**

```bash
# Edit a manifest, then:
git add gitops/ && git commit -m "infra: bump cilium values" && git push
python3 noah.py flux sync     # optional — Flux picks it up within the interval anyway
```

Secrets are the one exception — they are delivered out-of-band, never via Git
(see [Secrets](#secrets)).

---

## Anatomy of `gitops/`

```
gitops/
├── infrastructure/
│   ├── cilium/                 # CNI + Hubble + Cilium Ingress (kube-system)
│   ├── cert-manager/           # cert-manager controller
│   ├── cert-manager-issuers/   # letsencrypt-prod / -staging ClusterIssuers
│   ├── external-dns/           # Cloudflare DNS sync
│   ├── coredns/                # cluster DNS overrides
│   └── nginx-ingress/          # ingress controller (hostPort, 80/443)
├── apps/
│   ├── authentik/              # SSO (HelmRelease; secrets applied out-of-band)
│   ├── headlamp/               # cluster UI (OIDC via Authentik)
│   └── hubble-auth/            # Hubble UI ingress + Authentik forward-auth
└── apps-extra/
    ├── nextcloud/              # file sync & share (OIDC via Authentik)
    └── stalwart/               # mail server (SMTP/IMAP/JMAP) — opt-in, see below
```

The Flux reconciliation root lives at the repo root in `clusters/production/`
(`infrastructure.yaml`, `cert-manager-issuers.yaml`, `apps.yaml`,
`noah-source.yaml`). Order is enforced with `dependsOn`:

```
external-dns → cert-manager → cilium → nginx-ingress
            → authentik → hubble-auth
                        → headlamp
                        → apps-extra (nextcloud, stalwart when opted in)
```

Stalwart is the one component absent from a default install: it is listed in
`gitops/apps-extra/kustomization.yaml` only when `setup gitops` is run with
`--with-stalwart`. Because `apps-extra` reconciles with `prune: true`, dropping
the flag on a later run deletes the `stalwart` namespace and everything in it.
Its manifests and its entries in the canonical secrets store are untouched
either way.

---

## Secrets

The single source of truth is the SOPS/Age-encrypted
`Secrets/canonical-secrets.enc.yaml`. `Scripts/security/canonical_store.py`
loads and saves it; `Age/keys.txt` holds the private key that decrypts it.

**Secrets are never committed to Git and are not reconciled by Flux.** NOAH
renders Kubernetes Secret manifests from the canonical store and applies them
directly to the cluster:

1. **At bootstrap** — the `app-secrets` Ansible role `kubectl apply`s the
   rendered manifests (`gitops_init.render_app_secret_manifests`) right after
   Flux is installed, before Flux reconciles the namespaces.
2. **On demand** — `noah secrets apply` re-renders from the store and applies
   to the running cluster.
3. **On rotation** — `noah secrets rotate --service <svc> --apply` rotates the
   value in the store and pushes it to the cluster in one step.

Because these Secrets are unmanaged by Flux, they are **not** pruned or
drift-corrected — re-run `secrets apply` to re-sync after a manual change.

Authentik picks up a changed value automatically (Flux watches its
`authentik` values Secret via `valuesFrom`). Env-mounted consumers (Headlamp,
external-dns, cert-manager) read their Secret at startup, so restart them after
a rotation, e.g. `kubectl rollout restart deploy -n headlamp`.

> **Back up `Secrets/canonical-secrets.enc.yaml` *and* `Age/keys.txt`
> offline.** Together they are the only copy of your secret material; the
> generated values are unrecoverable if both are lost.

### Rotating a secret

```bash
# Rotate in the store and push to the cluster in one step — no git, no re-bootstrap:
python3 noah.py secrets rotate --service authentik --apply

# Rotate the Authentik admin password specifically:
python3 noah.py password new
python3 noah.py secrets apply
```

Inspect the store (read-only):
```bash
python3 noah.py secrets canonical --show
python3 noah.py secrets validate
```

---

## Common operations

### Add an application

```bash
mkdir -p gitops/apps/myapp
# Add: namespace.yaml, helmrepository.yaml, helmrelease.yaml, kustomization.yaml
echo "  - myapp" >> gitops/apps/kustomization.yaml
git add -A && git commit -m "apps: add myapp" && git push
python3 noah.py flux sync     # optional
```

If the app needs a secret, add it to the canonical store and deliver it with
`secrets apply` — do not commit it.

### Pause / resume a HelmRelease

```yaml
# in gitops/apps/<svc>/helmrelease.yaml
spec:
  suspend: true
```

`git push`, do the manual work, then revert to `suspend: false`. This is the
recommended workflow for a major Cilium upgrade: suspend, run `cilium upgrade`
manually, then unsuspend.

### Force reconciliation

```bash
python3 noah.py flux sync                         # everything
flux reconcile helmrelease authentik -n authentik # one resource
```

### Watch what's happening

```bash
python3 noah.py flux status     # snapshot of every Flux resource
python3 noah.py flux logs -f    # live tail across controllers
python3 noah.py cluster status  # nodes + etcd + Flux roll-up
```

### Tune the reconciliation cadence

The default `interval: 10m` suits most workloads. Drop it on a specific
Kustomization for faster rollouts, but don't go below 30 s (the controller
spends more time list-watching the API than reconciling):

```yaml
spec:
  interval: 1m
```

---

## SSO

Authentik is the OIDC identity provider. The clients for Headlamp and Hubble
are **provisioned automatically** during reconciliation by
`gitops/apps/authentik_provisioner.py` (idempotent) — there is no manual
Authentik configuration step.

**Headlamp** authenticates via OIDC:

- Provider `Headlamp Provider`, `client_id=headlamp`
- Redirect URI `https://headlamp.your-domain.com/oidc-callback`
- Scopes `openid profile email`
- No cluster-admin binding by default — users authenticate with their own
  Authentik identity. A "Forbidden" view before sign-in is expected.

**Hubble UI** has no native auth; access is gated by an Authentik forward-auth
proxy provider defined in `gitops/apps/hubble-auth/`. Hubble's built-in ingress
is disabled in favour of this proxy.

Verify SSO:
```bash
python3 noah.py test sso
python3 noah.py test headlamp --domain your-domain.com
python3 noah.py test hubble --domain your-domain.com

# Authentik OIDC discovery endpoint:
curl https://auth.your-domain.com/application/o/headlamp/.well-known/openid-configuration
```

---

## Scaling to HA

A single-node cluster runs embedded etcd as a single member. To grow to a
3-node quorum:

```bash
python3 noah.py cluster add-nodes --primary <existing-node-ip> --nodes node2,node3 \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519
```

New servers join the etcd cluster; quorum then tolerates one node failure.
Keep inter-node latency below 10 ms.

---

## DNS day-2

external-dns reconciles A records from Ingress resources. To rotate the
Cloudflare token, update it in the canonical store and re-deliver:

```bash
python3 noah.py secrets rotate --service cloudflare --apply
kubectl rollout restart deploy -n external-dns
```

The policy and owner ID are set in
`gitops/infrastructure/external-dns/helmrelease.yaml` (`policy: sync`,
`txtOwnerId: noah`) — edit and push to change either. There is no environment
variable for them.

> [!WARNING]
> `sync` deletes the records external-dns owns when their Ingress or
> DNSEndpoint goes away, and the owner ID is the same constant in every NOAH
> deployment. Two clusters sharing one Cloudflare zone will fight over the same
> records. Use one zone per deployment unless you change `txtOwnerId` first.

Subdomains are literals in the Ingress manifests (`auth.`, `headlamp.`,
`hubble.` — only `${DOMAIN}` is substituted by Flux). To change one, edit the
manifest and push:

```bash
# e.g. gitops/apps/authentik/authentik-ingress.yaml → host: "sso.${DOMAIN}"
git add gitops/ && git commit -m "apps: move authentik to sso." && git push
```

> `config override` and the `NOAH_*_SUBDOMAIN` variables only affect the
> `config` command group's output (process-local); they do **not** change what
> Flux deploys.

---

## Disaster recovery

| Scenario | Recovery |
|---|---|
| Single-node cluster gone | Re-run `noah cluster bootstrap`; Flux reconstructs all state. |
| One HA node down | Quorum holds; replace the node and run `noah cluster add-nodes`. |
| `Age/keys.txt` lost, backup intact | Restore the backup as `Age/keys.txt`, then re-run bootstrap. |
| Canonical store **or** Age key lost | Generated secrets are unrecoverable. Restore the offline backup of `Secrets/canonical-secrets.enc.yaml` **and** `Age/keys.txt`. |
| GitOps repo gone | Restore from any clone — Flux re-reconciles. Secrets are unaffected (not in Git); re-run `secrets apply` if needed. |

**Back up regularly:**
```bash
tar -czf noah-backup-$(date +%Y%m%d).tar.gz Age/ Secrets/ .sops.yaml
```

---

## Command reference

| Group | Command | Purpose |
|---|---|---|
| `setup` | `initialize` / `gitops` / `doctor` / `reset` / `update-sops` | Environment + gitops prep |
| `cluster` | `bootstrap` / `add-nodes` / `status` / `verify` / `destroy` | Cluster lifecycle |
| `flux` | `sync` / `status` / `logs` | Drive the FluxCD controllers |
| `secrets` | `apply` / `rotate` / `canonical` / `generate` / `regenerate` / `validate` / `init` | Manage the canonical store |
| `password` | `show-password` / `new` | Authentik admin credentials |
| `certificates` | `deploy-manager` / `generate-certs` / `list` | TLS certificate helpers |
| `test` | `sso` / `headlamp` / `hubble` | Post-deploy service checks |
| `config` | `domains` / `show` / `override` / `helm-values` | Inspect dynamic-domain config |
| *(top-level)* | `status` | Status of all deployed services |

Run `python3 noah.py <group> --help` for the full option list of any command.
