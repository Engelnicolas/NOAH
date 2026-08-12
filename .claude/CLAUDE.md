# CLAUDE.md

Guidance for Claude Code working in the NOAH repository.

## Behavioral prerequisites

These rules apply to every task, without exception.

1. **If ambiguous: ask, don't choose silently.** Stop and ask one focused question before writing any code.
2. **Minimal diff.** Touch only what is explicitly requested. No opportunistic cleanup, no "while I'm here" changes.
3. **Define "Done" before starting.** State in one line what the completed task looks like, then proceed.
4. **Verify in code, never assume.** Read the actual source before referencing a function, path, or version.
5. **Minimum code.** No speculative features, no extra abstractions, no future-proofing.

## What is NOAH

NOAH (Network Operations & Automation Hub) is a Python CLI (`noah.py`, Click-based) that
provisions a full K3s stack: cluster bootstrap via Ansible, FluxCD GitOps, SOPS/Age
secrets, Authentik SSO, Cilium, Headlamp, Hubble UI.

Docs: [`README.md`](../README.md) (landing page), [`docs/DEPLOYMENT_GUIDE.md`](../docs/DEPLOYMENT_GUIDE.md)
(install, DNS, troubleshooting), [`docs/OPERATIONS_GUIDE.md`](../docs/OPERATIONS_GUIDE.md)
(day-2: GitOps, secrets, SSO, DR).

**Always run NOAH from the repository root** — it checks for `Scripts/`, `Ansible/`, `noah.py`.

## Commands

```bash
python3 noah.py setup initialize    # first-time setup: tools, Age key, Cloudflare DNS wizard
python3 noah.py setup doctor        # diagnose environment
python3 noah.py setup gitops --domain example.com --node-ip EIP
python3 noah.py cluster bootstrap   # single-node: --node/--domain/--flux-repo default to
                                    # what `setup gitops` recorded + the origin remote;
                                    # deploy-key token from $GITHUB_TOKEN/$GIT_TOKEN
python3 noah.py cluster status | flux sync | flux status | flux logs
python3 noah.py secrets canonical --show
python3 noah.py secrets rotate --service authentik [--apply]
```

Gates (local only — **this repository has no CI workflow, no `.github/`**):

```bash
ruff check Scripts/ noah.py
bandit -r Scripts/ noah.py -ll
NOAH_SKIP_ANSIBLE=true pytest Tests/ -q
ansible-lint Ansible/ || true
pip install -r Scripts/utils/requirements.txt   # deps, if not using the venv bootstrap
```

`Tests/pytest.ini` sets `addopts = -m "not integration and not cluster"`: the `integration`
marker (needs the real `sops` binary, or mutates the canonical store) and the `cluster`
marker (needs a live cluster via `kubectl`) are both excluded by default. Select them
explicitly with `pytest Tests/ -v -m integration`.

## Architecture — the parts that aren't obvious from the source

### Secrets are out-of-band, never reconciled by Flux

Single source of truth: `Secrets/canonical-secrets.enc.yaml` (SOPS/Age), loaded by
`Scripts/security/canonical_store.py`. `sops_client.py` wraps the `sops` binary behind a
typed exception hierarchy (`SopsError` → `SopsBinaryNotFoundError`, `SopsDecryptionError`, …);
new failure paths follow that pattern.

NOAH renders Kubernetes Secret manifests from the store
(`gitops_init.render_app_secret_manifests`) and `kubectl apply`s them **directly** — at
bootstrap (Ansible role `app-secrets`), via `noah secrets apply`, or on rotation. So:
never commit a secret, and never add a `kind: Secret` or a plaintext value under `gitops/`.

`Age/keys.txt` + `Secrets/canonical-secrets.enc.yaml` are the only copy of the secret
material — back both up offline.

### Flux ordering lives only in clusters/production/

`dependsOn` between the Flux Kustomization CRs: infrastructure → cert-manager-issuers →
apps → apps-extra. There is **no `dependsOn` anywhere under `gitops/`**, and the components
inside `gitops/infrastructure/` are unordered — don't add one there or expect one.

`clusters/production/flux-system/` is written by `flux bootstrap`; `.sops.yaml` is
generated and gitignored, so it is normally absent.

### venv bootstrap

`noah.py` re-execs itself under `.venv/bin/python3` at startup, so `python3 noah.py` always
uses the venv without activating it.

## Environment variables

| Variable | Purpose |
|---|---|
| `NOAH_ROOT_DIR` | Override repo root (default: cwd) |
| `AGE_KEY_FILE` | Age private key path (default: `Age/keys.txt`) |
| `NOAH_SKIP_ANSIBLE` | Skip Ansible execution in tests |
| `NOAH_DISABLE_SOPS` | Store secrets in plaintext (dev/test only) |
| `NOAH_DOMAIN` | Default domain for CLI commands |
| `GITHUB_TOKEN` / `GIT_TOKEN` | Git provider token for deploy key registration |

## Tooling in .claude/

- `agents/noah-reviewer.md` — read-only review of Python, GitOps and test changes.
- `skills/external-tools/` — `gh` and `aws` conventions and safety rules. **Never push,
  merge, or delete without explicit user confirmation.**
- `.mcp.json` — AWS MCP servers. Not an auto-loaded path (project scope is `.mcp.json` at
  the repo root), so start with `claude --mcp-config .claude/.mcp.json` to get them.
