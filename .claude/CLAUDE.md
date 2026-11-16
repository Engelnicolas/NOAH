# CLAUDE.md

Guidance for Claude Code working in the NOAH repository. Read it whole before the first
change: the pitfalls section records mistakes that already cost hours.

## Behavioral prerequisites

These rules apply to every task, without exception.

1. **If ambiguous: ask, don't choose silently.** Stop and ask one focused question before writing any code.
2. **Minimal diff.** Touch only what is explicitly requested. No opportunistic cleanup, no "while I'm here" changes.
3. **Define "Done" before starting.** State in one line what the completed task looks like, then proceed.
4. **Verify in code, never assume.** Read the actual source before referencing a function, path, or version.
5. **Minimum code.** No speculative features, no extra abstractions, no future-proofing.
6. **Never push, merge or delete without explicit user confirmation** (branches, cloud resources, DNS records). Work on a branch, never directly on `main`.

## What NOAH is

A Python CLI (`noah.py`, Click) that builds a Kubernetes platform:

- **Machines**: OpenTofu in `Infra/aws/` (or a hand-written inventory for bare metal).
- **Machine contents**: Ansible (`Ansible/`): K3s, a first Cilium pass, Flux bootstrap,
  out-of-band secrets; ZFS, Garage and the TLS proxy on the storage nodes; NAT.
- **Everything on the cluster**: FluxCD reconciling `clusters/production/` and `gitops/`
  from this repository: Cilium, ingress-nginx, cert-manager, external-dns, CoreDNS,
  Authentik, Headlamp, Hubble UI, Nextcloud, Stalwart (opt-in).
- **Object storage**: Garage on separate machines, out of the cluster's reach.

Picture of the whole: `docs/images/how-it-works.svg`. Order of operations:
`docs/images/deployment-flow.svg`.

**Always run NOAH from the repository root**: it checks for `Scripts/`, `Ansible/`,
`noah.py`. Run it from the operator workstation, not from the compute node.

## Repository map

| Path | What lives there |
|---|---|
| `noah.py` | every CLI command; Garage and `garage infra` (the OpenTofu wrapper) are defined inline |
| `Scripts/cluster_create/` | `bootstrap_utils.py` (bootstrap, add-nodes), `verify_utils.py`, `flux_utils.py` |
| `Scripts/gitops/gitops_init.py` | `setup gitops`: placeholder filling, Stalwart opt-in, templates of every out-of-band Secret (`render_app_secret_manifests`) |
| `Scripts/security/` | `canonical_store.py` (cluster store, refuses Garage admin keys), `security_manager.py` (secret generators), `sops_client.py`, `set_cloudflare_token.py`, rotation |
| `Scripts/garage/` | `admin_store.py` (second Age identity, `tofu_environment`), `garage_deploy.py`, `garage_provision.py` |
| `Scripts/core_helm/authentik_credentials.py` | `password show-password` and the admin accounts summary |
| `Scripts/env_init/` | `setup initialize`, `setup doctor`, Cloudflare wizard |
| `Ansible/bootstrap-k3s.yml` | phases 1 to 7 of `cluster bootstrap` |
| `Ansible/deploy-garage.yml` | `garage nat` / `garage deploy`; roles `compute-nat`, `garage-*` |
| `Infra/aws/` | OpenTofu: `main.tf` (network, keys, inventory file), `spot.tf`, `security.tf`, `variables.tf`, `outputs.tf`; `launch-templates/` is reference only |
| `clusters/production/` | the four Flux Kustomizations and `flux-system/` (written by `flux bootstrap`) |
| `gitops/apps/authentik_provisioner.py` | creates every Authentik provider and application; run by one Job per service |
| `gitops/apps-extra/stalwart/` | Stalwart; its configuration is the apply plan in `apply-plan-configmap.yaml` |
| `Tests/` | pytest suite (`pytest.ini` excludes the `integration` and `cluster` markers) |
| `docs/` | Deployment Guide, Operations Guide, index, `images/` (SVG diagrams) |
| `Age/`, `Secrets/`, `Kube/`, `Infra/**/*.tfstate`, `infra-inventory.json` | local only, gitignored |

The project specifications live **outside** the repository, in `../Specs/`
(`Garage.md`, `cilium_sso.md`, `carte-etat-noah.md`). Code comments cite them as
`Specs/Garage.md §…`, `G…` (decisions), `T…` (tests), `V…` (verifications).

## Commands

```bash
python3 noah.py setup initialize         # venv, Age key, SOPS config, Cloudflare wizard (apt-only)
python3 noah.py garage admin init        # second Age identity, Garage admin secrets
python3 noah.py garage infra init|plan|apply|power|destroy --operator-cidr <ip>/32
python3 noah.py garage nat|deploy|provision|status --from-infra Infra/aws/infra-inventory.json
python3 noah.py setup gitops --domain example.com --node-ip <ip> [--with-stalwart]
python3 noah.py cluster bootstrap [--flux-branch <b>]   # deploy-key token from $GITHUB_TOKEN
python3 noah.py cluster verify | status | destroy
python3 noah.py flux sync | status | logs
python3 noah.py secrets canonical --show | apply | rotate --service <svc> [--apply]
```

## Gates

Local, before every commit:

```bash
NOAH_SKIP_ANSIBLE=true .venv/bin/python -m pytest Tests/ -q
.venv/bin/ruff check Scripts/ noah.py        # 201 pre-existing findings on main: do not add any
.venv/bin/bandit -r Scripts/ noah.py -ll
tofu -chdir=Infra/aws fmt -check             # and `tofu validate` after `tofu init`
ansible-lint Ansible/ || true
```

On GitHub, **CodeQL and GitGuardian** run on every pull request (repository settings, no
workflow file). There is no other CI, no `.github/`. Merges use `--squash`.

The `noah-reviewer` agent (`.claude/agents/`) runs the gates read-only on the current diff.

## Architecture: what the source does not make obvious

### Secrets are out of band, in two stores

- **Cluster store**: `Secrets/canonical-secrets.enc.yaml`, Age key `Age/keys.txt`,
  loaded by `canonical_store.py`. NOAH renders Kubernetes Secrets from it and
  `kubectl apply`s them directly (bootstrap role `app-secrets`, `secrets apply`,
  `secrets rotate --apply`). Never commit a secret; never add a `kind: Secret` or a
  plaintext value under `gitops/`. The compute node can read this store by design.
- **Garage administration store**: `Secrets/garage-admin.enc.yaml`, Age key
  `Age/garage-admin.txt` (node SSH key, `rpc_secret`, admin token, owner S3 key, cloud
  credentials, OpenTofu state passphrase). Never transmitted to any node. The canonical
  store raises `AdminSecretLeakError` on these keys: keep it that way.
- `sops_client.py` wraps `sops` behind typed exceptions (`SopsError` → …); new failure
  paths follow that pattern.

### Flux ordering lives only in `clusters/production/`

`dependsOn` chains the Kustomizations: infrastructure → cert-manager-issuers → apps →
apps-extra → network-policies (the Cilium default-deny baseline, always last). There is none under `gitops/`; the components inside a stage are unordered.
`${DOMAIN}`, `${NODE_PUBLIC_IP}` and the Stalwart DNS values are substituted by Flux
`postBuild` from ConfigMaps/Secrets seeded at bootstrap.

### Garage is isolated on purpose

Garage nodes sit in a private subnet, reachable only through the compute node as an SSH
jump host with a key the cluster never holds. Egress comes from NAT on the compute node
(`garage nat`, a bootstrap prerequisite). Cilium's `bpf.masquerade` must stay `false` or
that NAT silently stops. One S3 key per bucket; credentials are generated in the
canonical store, then imposed on Garage with `key import`. OpenTofu never connects to the
machines: the handover is `infra-inventory.json`, which must contain no secret (tested).

### Stalwart is configured through its API, not files

v0.16 keeps its settings in its datastore. The `stalwart-config` Job renders
`apply-plan-configmap.yaml` and runs `stalwart-cli apply`. Rules for editing the plan:

- **Bump `noah/apply-plan-revision`** in `provision-config-job.yaml` with every plan
  change, or Flux never re-runs the Job.
- `upsert` of an object can reset fields you omit: restate all fields (see
  `Application`).
- A `Custom` role set **replaces** the default user role: list `b` (User) next to `e`
  (System Administrator), or the account cannot receive mail.
- New listeners and `Application.oauthClientId` take effect only after a pod restart.
- The mailbox address is the Authentik **email** claim. Authentik group names become
  Stalwart group principals (`admin` → `admin@<domain>`): a user email equal to a group
  name cannot sign in. That is why the Authentik bootstrap email is `akadmin@<domain>`.
- `:2525` is an unauthenticated in-cluster relay (no `hostPort`) used by Authentik and
  Nextcloud; it is exempt from spam filtering. Rules are keyed on the port, never on the
  client address (all external traffic arrives SNATed to a pod address).

### venv bootstrap

`noah.py` re-execs itself under `.venv/bin/python3` and prepends `.venv/bin` to `PATH`,
so subprocesses find `ansible-playbook`. Scripts run outside `noah.py` need
`PYTHONPATH=$PWD` to import `Scripts.*`.

## Where versions are pinned

| Component | Version | Pinned in |
|---|---|---|
| K3s | v1.30.5+k3s1 | `Ansible/bootstrap-k3s.yml` (`k3s_version`, three plays); `--k3s-version` overrides |
| Helm charts | ranges `>=floor <next-major` | `gitops/**/helmrelease.yaml` |
| Flux | v2.10.0 | `clusters/production/flux-system/gotk-components.yaml`, regenerated by `flux bootstrap` with the CLI that the `flux-bootstrap` role installs (latest, **unpinned**) |
| Cilium CLI on the node | latest stable, **unpinned** | `Ansible/roles/cilium-preflight/tasks/main.yml` |
| Garage | v1.0.1 | `Ansible/roles/garage-install/defaults/main.yml` |
| Stalwart / stalwart-cli | v0.16.27 / 1.0.10 | `gitops/apps-extra/stalwart/statefulset.yaml`, `provision-config-job.yaml` |
| Provisioning Job image | `python:3.12-slim` | `gitops/**/provision*-job.yaml` |
| OpenTofu / AWS provider | ≥ 1.10 / ≥ 5.86.0 (lock: 6.73.0) | `Infra/aws/main.tf`, `Infra/aws/.terraform.lock.hcl` (committed) |
| Python dependencies | floors | `Scripts/utils/requirements.txt` |

When you bump a version, update the table in the main README too.

## Pitfalls already paid for

- **EC2 descriptions**: security group rule descriptions accept only
  `a-zA-Z0-9. _-:/()#,@[]+=&;{}!$*`. No em dash, no `§`: the apply fails half-way.
- **`garage infra`** does not pass the SSH public keys: export
  `TF_VAR_compute_ssh_public_key` and `TF_VAR_garage_ssh_public_key` (Deployment Guide,
  step 1). `destroy` needs them too.
- **An EC2 instance cannot reach its own Elastic IP.** Anything running on the node must
  use `127.0.0.1` or the private IP (Cilium `k8sServiceHost` is `127.0.0.1`); anything
  run from the workstation uses the public address (kubeconfig, `cluster verify`).
- **Testing a branch on a live cluster**: `--flux-branch` moves only `flux-system`;
  `noah-source.yaml` hardcodes `main`, and `flux bootstrap` commits `gotk-sync.yaml` to
  the tracked branch. Both, plus any test-only opt-in, must be reverted before merging,
  **on a separate merge branch**: reverting on the branch the cluster tracks makes Flux
  prune live workloads.
- `Tests/test_gitops.py::TestAppsExtraWiring` fails while Stalwart is enabled in
  `gitops/apps-extra/kustomization.yaml`. Expected on a test branch, never on `main`.
- **Flux stuck for 30 minutes** on the health checks of an older revision:
  `kubectl -n flux-system rollout restart deploy/kustomize-controller`.
- **Garage v1.0.1** rejects the streaming checksums of recent S3 clients ("Invalid
  content sha256"); with the AWS CLI set `AWS_REQUEST_CHECKSUM_CALCULATION=when_required`.
- **DNS records outlive `destroy`**: external-dns deletes only while it runs. Clean the
  Cloudflare zone, or the records point at a released Elastic IP.
- `setup initialize` is apt-only; the Ansible roles are apt-only too.
- The Cilium pod CIDR is `10.42.0.0/16`, set identically in the `cilium-preflight` role
  and the Cilium HelmRelease (the chart default `10.0.0.0/8` contains the AWS VPC). It
  cannot change on a live cluster, and no infrastructure prefix may overlap it.

## Documentation

`README.md` (overview, How it works), `docs/DEPLOYMENT_GUIDE.md`, `docs/OPERATIONS_GUIDE.md`,
`Infra/README.md`, `docs/README.md` (index and writing conventions). A behaviour change
updates the matching guide, and the diagram in `docs/images/` if it shows that
behaviour, in the same commit. Diagrams are hand-written SVG in one style (see
`docs/README.md`); render them to check (`magick file.svg out.png`).

## Environment variables

| Variable | Purpose |
|---|---|
| `NOAH_ROOT_DIR` | Override repo root (default: cwd) |
| `AGE_KEY_FILE` | Age private key path (default: `Age/keys.txt`) |
| `NOAH_SKIP_ANSIBLE` | Skip Ansible execution in tests |
| `NOAH_DISABLE_SOPS` | Store secrets in plaintext (dev/test only) |
| `NOAH_DOMAIN` | Default domain for CLI commands |
| `GITHUB_TOKEN` / `GIT_TOKEN` | Git provider token for deploy key registration |
| `AUTHENTIK_BOOTSTRAP_TOKEN` | Enables the live checks of `noah test headlamp/cilium` |
| `TF_VAR_*` | OpenTofu inputs not supplied by the wrapper (SSH public keys, `mail_enabled`, `mail_ptr_domain`) |

## Tooling in `.claude/`

- `agents/noah-reviewer.md`: read-only review of the current diff against the gates and
  invariants.
- `skills/external-tools/`: `gh` and `aws` conventions and safety rules.
- `.mcp.json`: AWS MCP servers (documentation, EKS, pricing). Not auto-loaded; start with
  `claude --mcp-config .claude/.mcp.json`.
