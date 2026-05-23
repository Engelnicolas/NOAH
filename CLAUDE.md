# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is NOAH

NOAH (Network Operations & Automation Hub) is a Python CLI (`noah.py`) that provisions and manages a full Kubernetes infrastructure stack on K3s. It orchestrates: K3s cluster bootstrap via Ansible, FluxCD GitOps reconciliation, SOPS/Age-encrypted secrets, Authentik SSO, Cilium CNI, Headlamp dashboard, and Hubble UI.

## Commands

### Setup and development

```bash
# First-time setup (installs tools, generates Age key, runs Cloudflare DNS wizard)
python3 noah.py setup initialize

# Install Python dependencies manually (for development without venv bootstrap)
pip install -r Scripts/utils/requirements.txt

# Lint
ruff check Scripts/ noah.py

# Security scan
bandit -r Scripts/ noah.py -ll

# Ansible lint
ansible-lint Ansible/ || true
```

### Testing

```bash
# Run all unit tests (integration tests excluded by default)
pytest Tests/ -v

# Run a single test file
pytest Tests/test_canonical_secrets.py -v

# Run a single test by name
pytest Tests/test_canonical_secrets.py::TestCanonicalStore::test_load_empty -v

# Run including integration tests (requires real sops binary)
pytest Tests/ -v -m integration

# Skip Ansible during CI
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q
```

### Key CLI commands

```bash
python3 noah.py setup doctor                    # diagnose environment
python3 noah.py setup gitops --domain example.com   # fill & encrypt gitops/ secrets
python3 noah.py cluster bootstrap --node IP --domain D --flux-repo URL --ssh-user ubuntu --ssh-key ~/.ssh/id_ed25519 --git-token $GITHUB_TOKEN
python3 noah.py cluster status
python3 noah.py flux sync / status / logs
python3 noah.py password show-password
python3 noah.py secrets canonical --show
python3 noah.py secrets rotate --service authentik
```

**NOAH must always be run from the repository root** — it checks for `Scripts/`, `Ansible/`, and `noah.py`.

## Architecture

### Python module layout

| Package | Responsibility |
|---|---|
| `Scripts/env_init/` | `setup initialize`: installs tools, generates Age key, Cloudflare DNS wizard |
| `Scripts/cluster_create/` | K3s + FluxCD bootstrap via Ansible, HA mode, node addition |
| `Scripts/cluster_destroy/` | Cluster teardown and kubectl cleanup |
| `Scripts/security/` | Canonical secrets store, SOPS client, rotation CLI, Authentik provisioner |
| `Scripts/core_helm/` | Authentik credential retrieval and password management |
| `Scripts/gitops/` | Domain substitution, secret filling, encryption of `gitops/` for FluxCD |
| `Scripts/utils/` | Config loader, Ansible runner, path resolution, dict utilities |

### Secrets model

Secrets have a single source of truth: `Secrets/canonical-secrets.enc.yaml` (SOPS/Age encrypted). `Scripts/security/canonical_store.py` loads/saves this file. `Scripts/security/sops_client.py` wraps the `sops` binary with a typed exception hierarchy (`SopsError` → `SopsBinaryNotFoundError`, `SopsDecryptionError`, etc.).

`setup gitops` reads from the canonical store and writes SOPS-encrypted `*.enc.yaml` files into `gitops/`. The kustomize controller decrypts these at apply time via the `sops-age` Secret bootstrapped by Ansible.

Age keys live in `Age/keys.txt`. The public key recipient in `gitops/.sops.yaml` controls which key can decrypt gitops secrets.

### GitOps / FluxCD structure

```
clusters/production/          ← Flux reconciliation root (written by flux bootstrap)
  kustomization.yaml
  noah-source.yaml            ← GitRepository pointing at gitops/
  infrastructure.yaml         ← Kustomization CR
  apps.yaml                   ← Kustomization CR (dependsOn infrastructure)

gitops/                       ← Actual Helm manifests reconciled by Flux
  infrastructure/             ← Cilium, cert-manager, external-dns
  apps/                       ← Authentik, Headlamp, hubble-auth
  .sops.yaml                  ← Encryption rules (Age recipients)
```

Reconciliation order enforced via `dependsOn`: external-dns → cert-manager → Cilium → nginx-ingress → Authentik → Hubble/Headlamp.

### venv bootstrap

`noah.py` re-execs itself under `.venv/bin/python3` at startup if the venv exists and the current interpreter is not already the venv's. This means `python3 noah.py` always uses the venv without the user needing to activate it.

### CI

- **`ci-python.yml`**: runs on changes to `Scripts/`, `Tests/`, `noah.py`. Steps: ruff lint → bandit → syntax check → pytest → NOAH CLI smoke test → ansible-lint.
- **`ci-gitops.yml`**: runs on changes to `gitops/`. Steps: yamllint → kubeconform (skips `*.enc.yaml`) → Helm dry-run on `helmrelease.yaml` files.

### Environment variables

| Variable | Purpose |
|---|---|
| `NOAH_ROOT_DIR` | Override repo root (default: cwd) |
| `AGE_KEY_FILE` | Path to Age private key (default: `Age/keys.txt`) |
| `NOAH_SKIP_ANSIBLE` | Skip Ansible execution in tests |
| `NOAH_DISABLE_SOPS` | Store secrets in plaintext (dev/test only) |
| `NOAH_DOMAIN` | Default domain for CLI commands |
| `GITHUB_TOKEN` / `GIT_TOKEN` | Git provider API token for deploy key registration |
