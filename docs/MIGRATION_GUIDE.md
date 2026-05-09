# NOAH Migration Guide — v0.0.8 → v0.0.9

NOAH v0.0.9 introduces the architectural shift described in the
[NOAH Migration Spec v0.0.9](#references): **K3s with embedded etcd**
(replacing the SQLite SPOF) and **FluxCD GitOps** (replacing imperative
Ansible/Helm deployments). This guide is the operator-facing recipe.

> **There is no in-place migration path.** v0.0.9 is a greenfield
> re-deployment on a new cluster. Plan a maintenance window of
> 1.5–4 h depending on whether you choose single-node or HA.

---

## 1. What changed

| Concern              | v0.0.8                               | v0.0.9                                          |
|----------------------|--------------------------------------|-------------------------------------------------|
| Datastore            | K3s + SQLite (single SPOF)           | K3s + embedded etcd (single-member or 3-quorum) |
| Service deployment   | `noah deploy <service>` (imperative) | FluxCD reconciles from a Git repo               |
| Source of truth      | SOPS canonical store **and** etcd    | Git (with SOPS-encrypted manifests)             |
| Reconciliation       | None                                 | Continuous (default 10 min)                     |
| Hubble UI auth       | None — exposed unauthenticated       | Authentik Proxy Provider (forward-auth)         |
| Default cluster size | 1 node                               | 1 node (HA opt-in via `--ha`)                   |
| CLI entry            | `noah cluster create` + `noah deploy core` | `noah cluster bootstrap`                  |

The Python CLI itself stays the user entry point — only the underlying
mechanics change.

---

## 2. Pre-migration checklist

Run through this **before** you start the maintenance window.

- [ ] Ubuntu 22.04+ provisioned on the target node(s) with SSH access.
- [ ] SSDs available for `/var/lib/rancher/k3s` (etcd is write-heavy).
- [ ] **HA only:** inter-node latency < 10 ms (verified by `ping`).
- [ ] GitOps repository created on GitHub (or GitLab) — empty is fine.
- [ ] `Age/keys.txt` backed up to **two** locations.
- [ ] **New in v0.0.9:** generate a backup Age key and add it to
      `flux-repo/.sops.yaml` as a second recipient (see §"Age key
      hardening" below).
- [ ] Authentik PostgreSQL exported (`pg_dump` from the v0.0.8 pod).
- [ ] All existing secrets re-encrypted with the new two-recipient
      `.sops.yaml` rule (so the backup key can decrypt them).

---

## 3. Migration phases

| # | Phase                        | Est. | What it does                                                                                                  |
|---|------------------------------|------|---------------------------------------------------------------------------------------------------------------|
| 0 | GitOps repo prep             | 2-3d | Copy `flux-repo/` into a new Git repo, replace placeholders, encrypt secrets, validate `.sops.yaml`.          |
| 1 | v0.0.8 backup                | 2 h  | `pg_dump` Authentik DB, archive `Config/`, snapshot the VM.                                                   |
| 2 | K3s provisioning             | 30-90 min | `noah cluster bootstrap` — runs `bootstrap-k3s.yml` (OS prereqs → K3s init → [HA join] → validate). |
| 3 | FluxCD bootstrap             | 30 min | Folded into phase 2; verify with `noah flux status`.                                                         |
| 4 | Infrastructure deployment    | 30-45 min | Watch FluxCD reconcile Cilium, cert-manager, external-dns.                                              |
| 5 | Services deployment          | 30-45 min | FluxCD reconciles Authentik, Headlamp, Hubble (with auth). Restore Authentik DB.                         |
| 6 | Full validation              | 1-2 h | SSO smoke tests, DNS, TLS, [HA only] etcd resilience (shut down one node, cluster stays up).               |
| 7 | CLI migration / docs handoff | 2-3d | Train operators on `noah flux` commands; remove old runbooks referring to `noah deploy`.                   |

Phases 0 and 7 happen around the maintenance window; phases 1-6 fit
inside it.

---

## 4. Step-by-step

### 4.1 Prepare the GitOps repository (phase 0)

```bash
# 1. Create an empty GitHub repo, e.g. acme-corp/noah-gitops.
# 2. Copy the template tree.
cp -R flux-repo/* /tmp/noah-gitops/
cd /tmp/noah-gitops
git init && git remote add origin git@github.com:acme-corp/noah-gitops.git

# 3. Replace placeholders:
#    - flux-repo/.sops.yaml             → real Age recipients (×2)
#    - apps/*/oidc-secret.enc.yaml      → real OIDC client secrets
#    - apps/authentik/values-secret.enc.yaml → real bootstrap creds
#    - infrastructure/*/cloudflare-secret.enc.yaml → real CF token
#    - apps/headlamp/helmrelease.yaml   → headlamp.<your-domain>
#    - apps/hubble-auth/hubble-ingress.yaml → hubble.<your-domain>
#    - infrastructure/cert-manager/clusterissuer.yaml → admin@<your-domain>

# 4. Encrypt every *.enc.yaml file BEFORE committing.
find . -name '*.enc.yaml' -exec sops --encrypt --in-place {} \;

# 5. Commit + push.
git add -A && git commit -m 'Initial NOAH GitOps tree' && git push -u origin main
```

### 4.2 Bootstrap a single-node cluster (default)

```bash
python noah.py cluster bootstrap \
  --node 127.0.0.1 \
  --domain example.com \
  --flux-repo https://github.com/acme-corp/noah-gitops \
  --ssh-user ubuntu \
  --ssh-key ~/.ssh/id_ed25519
```

### 4.3 Bootstrap a 3-node HA cluster

```bash
python noah.py cluster bootstrap \
  --ha \
  --nodes 192.168.1.10,192.168.1.11,192.168.1.12 \
  --domain example.com \
  --flux-repo https://github.com/acme-corp/noah-gitops \
  --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519
```

### 4.4 Watch reconciliation

```bash
python noah.py flux status      # snapshot
python noah.py flux logs -f     # follow controller logs
python noah.py cluster status   # nodes + etcd + Flux roll-up
```

### 4.5 Update a secret post-migration

The whole point of GitOps: edit, encrypt, commit.

```bash
sops apps/authentik/values-secret.enc.yaml
git commit -am 'Rotate Authentik bootstrap password' && git push
python noah.py flux sync     # don't wait for the 10 min interval
```

---

## 5. Age key hardening (mandatory)

In v0.0.8 `Age/keys.txt` is a single point of failure — losing it
makes every encrypted secret permanently unrecoverable. Migration is
the right moment to add a second recipient.

```bash
# Generate the backup key, store offline (password manager / safe).
age-keygen -o backup-key.txt
grep '^# public key:' backup-key.txt
# → age1yyyyyyyy...

# Add it to flux-repo/.sops.yaml:
#   age: >-
#     age1xxxxxxx,    # primary (Age/keys.txt)
#     age1yyyyyyy     # backup (offline)

# Re-encrypt every secret so the backup key can also decrypt:
find flux-repo -name '*.enc.yaml' -exec sops updatekeys -y {} \;
```

---

## 6. Roll-back

If phase 5/6 reveals a blocker, the safe roll-back is:

1. Restore the v0.0.8 VM snapshot taken in phase 1.
2. Re-point your DNS records back to the v0.0.8 cluster.
3. The new GitOps repo is harmless to leave in place — revisit when
   the blocker is fixed.

`noah cluster destroy` works on v0.0.9 clusters but **does not**
remove the GitOps repo or any committed secrets.

---

## 7. Acceptance criteria

The migration is complete when:

- [ ] `kubectl get nodes` shows every node `Ready`.
- [ ] **HA only:** stop k3s on one node — `kubectl get nodes` still
      responds, etcd quorum holds.
- [ ] `flux get kustomizations -A` — every entry `Ready=True`.
- [ ] `flux get helmreleases -A` — every entry `Ready=True`.
- [ ] Headlamp loads and authenticates via Authentik OIDC.
- [ ] Hubble UI prompts for Authentik login (no anonymous access).
- [ ] cert-manager has issued `letsencrypt-prod` certs for every
      ingress host.
- [ ] `git log` on the GitOps repo is the audit trail for every
      change to the cluster.

---

## References

- `docs/GITOPS_GUIDE.md` — day-to-day GitOps operations.
- `docs/DEPLOYMENT_GUIDE.md` — updated for v0.0.9.
- Spec: *NOAH Migration Spec v0.0.9* (internal).
- Upstream: <https://docs.k3s.io/datastore/ha-embedded>,
  <https://fluxcd.io/flux/installation/>,
  <https://fluxcd.io/flux/guides/mozilla-sops/>.
