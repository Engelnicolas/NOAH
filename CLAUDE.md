# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavioral prerequisites

These rules apply to every task in this project, without exception.

1. **If ambiguous: ask, don't choose silently.** When a request can be interpreted in more than one way, stop and ask one focused question before writing any code.
2. **Minimal diff.** Touch only what is explicitly requested. No opportunistic cleanup, no related refactors, no "while I'm here" changes.
3. **Define "Done" before starting.** State in one line what the completed task looks like, then proceed.
4. **Verify in code, never assume.** Before referencing a function, variable, file path, or version, read the actual source. No guesses about what "latest" might be.
5. **Minimum code.** Implement exactly what is asked. No speculative features, no extra abstractions, no future-proofing.

## External tools — safety rules

- GitHub: use `gh`; never push or merge without explicit user confirmation;
  merges use `--squash` unless specified otherwise; verify a branch or SHA exists before acting on it.
- AWS: run `aws sts get-caller-identity` before any write; never delete without
  explicit confirmation and a blast-radius estimate; prefer dry-run flags;
  rely on the credential chain, never touch `~/.aws/credentials`.

Command references live in `.claude/skills/github/` and `.claude/skills/aws/`.

## What is NOAH

NOAH (Network Operations & Automation Hub) is a Python CLI (`noah.py`) that provisions and manages a full Kubernetes infrastructure stack on K3s. It orchestrates: K3s cluster bootstrap via Ansible, FluxCD GitOps reconciliation, SOPS/Age-encrypted secrets, Authentik SSO, Cilium CNI, Headlamp dashboard, and Hubble UI.

The root [`README.md`](README.md) is the project landing page (overview + quickstart). User-facing docs live in `docs/`: [`README.md`](docs/README.md) (docs index), [`DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) (install, DNS, troubleshooting), [`OPERATIONS_GUIDE.md`](docs/OPERATIONS_GUIDE.md) (day-2: GitOps, secrets, SSO, DR).

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
pytest Tests/test_canonical_store.py -v

# Run a single test by name
pytest Tests/test_canonical_store.py::test_node_public_ip_roundtrip_persists -v

# Run including integration tests (requires real sops binary)
pytest Tests/ -v -m integration

# Skip Ansible during CI
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q
```

### Key CLI commands

```bash
python3 noah.py setup doctor                    # diagnose environment
python3 noah.py setup gitops --domain example.com --node-ip EIP   # prepare gitops/ for the domain; records the node public IP (single IP entry point)
python3 noah.py cluster bootstrap   # single-node: --node/--domain default to the EIP and domain recorded by `setup gitops`, --flux-repo to the origin remote; deploy-key token read from $GITHUB_TOKEN/$GIT_TOKEN. Pass any flag to override.
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
| `Scripts/security/` | Canonical secrets store, SOPS client, rotation CLI |
| `Scripts/core_helm/` | Authentik credential retrieval and password management |
| `Scripts/gitops/` | Domain/IP prep of `gitops/` for FluxCD; renders out-of-band Secret manifests from the canonical store |
| `Scripts/utils/` | Config loader, Ansible runner, path resolution, dict utilities |

### Secrets model

Secrets have a single source of truth: `Secrets/canonical-secrets.enc.yaml` (SOPS/Age encrypted). `Scripts/security/canonical_store.py` loads/saves this file. `Scripts/security/sops_client.py` wraps the `sops` binary with a typed exception hierarchy (`SopsError` → `SopsBinaryNotFoundError`, `SopsDecryptionError`, etc.).

Secrets are **never committed to Git** and are **not** reconciled by Flux. NOAH renders Kubernetes Secret manifests from the canonical store (`gitops_init.render_app_secret_manifests`) and applies them directly to the cluster — out-of-band. This happens at bootstrap (the `app-secrets` Ansible role `kubectl apply`s them after Flux is installed), on demand via `noah secrets apply`, and on rotation via `noah secrets rotate --service <svc> --apply`. `setup gitops` only prepares the non-secret `gitops/` tree (domain/IP) and records the node public IP in the store.

Age keys live in `Age/keys.txt`. Together with `Secrets/canonical-secrets.enc.yaml` they are the only copy of secret material — back both up offline.

### GitOps / FluxCD structure

```
clusters/production/          ← Flux reconciliation root (written by flux bootstrap)
  kustomization.yaml
  noah-source.yaml            ← GitRepository pointing at gitops/
  infrastructure.yaml         ← Kustomization CR
  apps.yaml                   ← Kustomization CR (dependsOn infrastructure)

gitops/                       ← Actual Helm manifests reconciled by Flux
  infrastructure/             ← cilium, cert-manager, cert-manager-issuers, coredns, external-dns, nginx-ingress
  apps/                       ← authentik, headlamp, hubble-auth
  apps-extra/                 ← nextcloud, stalwart
  apps/authentik_provisioner.py ← OIDC client provisioner (run by a Job)

.sops.yaml                    ← Encryption rules (Age recipients) — repo root, gitignored
```

Reconciliation order enforced via `dependsOn`: external-dns → cert-manager → Cilium → nginx-ingress → Authentik → Hubble/Headlamp.

### venv bootstrap

`noah.py` re-execs itself under `.venv/bin/python3` at startup if the venv exists and the current interpreter is not already the venv's. This means `python3 noah.py` always uses the venv without the user needing to activate it.

### Environment variables

| Variable | Purpose |
|---|---|
| `NOAH_ROOT_DIR` | Override repo root (default: cwd) |
| `AGE_KEY_FILE` | Path to Age private key (default: `Age/keys.txt`) |
| `NOAH_SKIP_ANSIBLE` | Skip Ansible execution in tests |
| `NOAH_DISABLE_SOPS` | Store secrets in plaintext (dev/test only) |
| `NOAH_DOMAIN` | Default domain for CLI commands |
| `GITHUB_TOKEN` / `GIT_TOKEN` | Git provider API token for deploy key registration |
