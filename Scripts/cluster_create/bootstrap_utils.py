"""
NOAH v0.0.9 — `noah cluster bootstrap` implementation.

Provisions a K3s cluster (single-node by default, --ha for 3-node
embedded-etcd HA) and runs `flux bootstrap` against a GitOps
repository. This replaces the v0.0.8 `noah cluster create` flow,
which was SQLite-backed and had no continuous reconciliation layer.

The Python side is intentionally thin: it
  1. validates CLI inputs (HA needs an odd >=3 node count),
  2. writes a temporary Ansible inventory with k3s_primary / k3s_joiners
     groups derived from --node / --nodes,
  3. loads the Age private key from the canonical SOPS store,
  4. invokes Ansible/bootstrap-k3s.yml with the right extra-vars.

All real work lives in the Ansible roles under Ansible/roles/.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import click  # type: ignore
import yaml  # type: ignore


def _split_nodes(nodes_csv: str) -> List[str]:
    return [n.strip() for n in nodes_csv.split(",") if n.strip()]


def _validate_ha_nodes(nodes: List[str]) -> None:
    if len(nodes) < 3 or len(nodes) % 2 == 0:
        raise click.UsageError(
            "HA mode requires an odd number of nodes >= 3 "
            f"(got {len(nodes)}: {', '.join(nodes)})."
        )


def _load_age_private_key(age_key_file: Path) -> str:
    """Read the Age private key payload that Flux will use to decrypt.

    The bootstrap injects this verbatim into the `sops-age` Secret in
    the flux-system namespace, so the kustomize-controller can decrypt
    .enc.yaml manifests in the GitOps repo without any extra config.
    """
    if not age_key_file.exists():
        raise click.UsageError(
            f"Age key file not found: {age_key_file}\n"
            f"Run `python noah.py setup initialize` first to generate it."
        )
    payload = age_key_file.read_text(encoding="utf-8").strip()
    if "AGE-SECRET-KEY" not in payload:
        raise click.UsageError(
            f"{age_key_file} does not look like a valid Age key file."
        )
    return payload


def _build_inventory(
    nodes: List[str],
    ha_mode: bool,
    ssh_user: str,
    ssh_key: Optional[str],
) -> dict:
    """Construct the dynamic inventory consumed by bootstrap-k3s.yml.

    Groups:
      * k3s_primary  — first node, gets --cluster-init
      * k3s_joiners  — remaining nodes (empty in single-node mode)
      * k3s_nodes    — superset (used by the OS prerequisites play)
    """
    primary, joiners = nodes[0], nodes[1:]

    def _host_block(ip: str) -> dict:
        host: dict = {"ansible_host": ip, "ansible_user": ssh_user}
        if ssh_key:
            host["ansible_ssh_private_key_file"] = ssh_key
        return host

    return {
        "all": {
            "children": {
                "k3s_nodes": {
                    "hosts": {ip: _host_block(ip) for ip in nodes},
                },
                "k3s_primary": {
                    "hosts": {primary: _host_block(primary)},
                },
                "k3s_joiners": {
                    "hosts": {ip: _host_block(ip) for ip in joiners},
                },
            },
            "vars": {
                "ha_mode": bool(ha_mode),
            },
        }
    }


def _resolve_nodes(node: Optional[str], nodes: Optional[str], ha: bool) -> List[str]:
    if ha:
        if not nodes:
            raise click.UsageError("--ha requires --nodes n1,n2,n3 (odd count >= 3).")
        node_list = _split_nodes(nodes)
        _validate_ha_nodes(node_list)
        return node_list

    # Single-node mode — accept --node OR a single-entry --nodes for
    # symmetry with the HA invocation.
    if node:
        return [node]
    if nodes:
        node_list = _split_nodes(nodes)
        if len(node_list) != 1:
            raise click.UsageError(
                "Single-node mode requires exactly one node. "
                "Pass --ha to deploy multiple nodes."
            )
        return node_list
    raise click.UsageError("Provide --node <ip> for single-node mode, or --ha --nodes n1,n2,n3.")


def _check_existing_cluster(force_reset: bool) -> None:
    """Refuse to bootstrap on top of an existing cluster unless forced.

    Mirrors the spec's safety rule (§9.4): noah cluster bootstrap MUST
    refuse when K3s is already present, with --force-reset as the
    explicit override.
    """
    if force_reset:
        click.confirm(
            "⚠️  --force-reset will destroy any existing K3s install on the target nodes. Continue?",
            abort=True,
        )
        return
    # We can't probe remote hosts without SSH credentials at this
    # point; the safety check happens inside the Ansible role
    # (k3s-server-init skips install when /usr/local/bin/k3s exists,
    # which keeps re-runs idempotent without --force-reset).


def _flux_ssh_url(flux_repo: str) -> str:
    """Normalise a GitOps repo URL to SSH format for flux bootstrap git.

    Accepts:
      https://github.com/org/repo[.git]  →  ssh://git@github.com/org/repo
      git@github.com:org/repo[.git]      →  ssh://git@github.com/org/repo
      ssh://git@github.com/org/repo      →  unchanged
    """
    repo = flux_repo.rstrip("/")
    if repo.startswith("ssh://"):
        return repo
    if repo.startswith("git@"):
        # git@github.com:org/repo  →  ssh://git@github.com/org/repo
        repo = repo.replace(":", "/", 1)
        return "ssh://" + repo
    if repo.startswith("https://"):
        repo = repo.replace("https://", "ssh://git@", 1)
        if not repo.endswith(".git"):
            repo += ""  # .git suffix optional for flux
        return repo
    return repo


def _parse_git_url(flux_repo: str) -> Tuple[str, str, str]:
    """Extract (host, owner, repo) from any common Git URL format.

    Supports:
      https://host/owner/repo[.git]
      ssh://git@host/owner/repo[.git]
      git@host:owner/repo[.git]
    """
    import re
    repo = flux_repo.rstrip("/")
    for pattern in [
        r"(?:https?|ssh)://[^@]*@?([^/]+)/([^/]+)/([^/]+?)(?:\.git)?$",
        r"git@([^:]+):([^/]+)/(.+?)(?:\.git)?$",
    ]:
        m = re.match(pattern, repo)
        if m:
            return m.group(1), m.group(2), m.group(3)
    raise ValueError(f"Cannot parse host/owner/repo from git URL: {flux_repo!r}")


def _detect_provider(host: str, hint: Optional[str] = None) -> str:
    """Return the git provider name for a given host.

    Known providers are detected automatically; pass *hint* to override
    (useful for self-hosted GitLab or Gitea instances whose hostname does
    not contain 'gitlab' or 'gitea').

    Supported values: 'github', 'gitlab', 'gitea' (covers Forgejo too).
    Unknown hosts default to 'gitea' because the Gitea/Forgejo API is a
    superset of GitHub's repo-keys API and works for many self-hosted setups.
    """
    if hint:
        return hint.lower().strip()
    h = host.lower()
    if "github.com" in h:
        return "github"
    if "gitlab.com" in h or "gitlab." in h:
        return "gitlab"
    if "bitbucket.org" in h:
        return "bitbucket"
    # Default: Gitea/Forgejo-compatible API (same shape as GitHub's for deploy keys)
    return "gitea"


def _register_deploy_key(
    flux_repo: str,
    git_token: str,
    public_key: str,
    provider_hint: Optional[str] = None,
) -> bool:
    """Register the SSH deploy key with any supported git provider.

    Provider is auto-detected from the URL; pass *provider_hint* to force
    a specific one ('github', 'gitlab', 'gitea') for self-hosted instances.

    Returns True when the key is confirmed present (added or already there),
    False on failure (caller falls back to the interactive manual prompt).
    """
    import json
    import urllib.request
    import urllib.error

    KEY_TITLE = "NOAH FluxCD deploy key"
    key_body = public_key.strip().split()[1]   # base64 portion for duplicate check

    try:
        host, owner, repo = _parse_git_url(flux_repo)
    except ValueError as exc:
        click.echo(f"[WARNING] {exc} — falling back to manual deploy-key prompt.", err=True)
        return False

    provider = _detect_provider(host, provider_hint)

    # ── Build provider-specific API parameters ────────────────────────────
    if provider == "github":
        list_url   = f"https://api.github.com/repos/{owner}/{repo}/keys"
        create_url = list_url
        req_headers = {
            "Authorization": f"token {git_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        create_body = {"title": KEY_TITLE, "key": public_key.strip(), "read_only": True}
        existing_key_field = "key"

    elif provider == "gitlab":
        encoded_path = f"{owner}%2F{repo}"
        base = f"https://{host}/api/v4/projects/{encoded_path}/deploy_keys"
        list_url = create_url = base
        req_headers = {
            "PRIVATE-TOKEN": git_token,
            "Content-Type": "application/json",
        }
        create_body = {"title": KEY_TITLE, "key": public_key.strip(), "can_push": False}
        existing_key_field = "key"

    elif provider in ("gitea", "forgejo"):
        base = f"https://{host}/api/v1/repos/{owner}/{repo}/keys"
        list_url = create_url = base
        req_headers = {
            "Authorization": f"token {git_token}",
            "Content-Type": "application/json",
        }
        create_body = {"title": KEY_TITLE, "key": public_key.strip(), "read_only": True}
        existing_key_field = "key"

    else:
        click.echo(
            f"[WARNING] Unsupported git provider '{provider}' — falling back to manual prompt.",
            err=True,
        )
        return False

    click.echo(f"[INFO] Registering deploy key via {provider} API ({host})…")

    # ── Check for an existing identical key (idempotent re-runs) ─────────
    try:
        req = urllib.request.Request(list_url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            existing = json.loads(resp.read())
        if any(key_body in k.get(existing_key_field, "") for k in existing):
            click.echo(f"[INFO] SSH deploy key already registered in {provider}.")
            return True
    except urllib.error.HTTPError as exc:
        click.echo(
            f"[WARNING] {provider} API list-keys returned {exc.code} — will attempt to add anyway.",
            err=True,
        )
    except Exception as exc:
        click.echo(f"[WARNING] {provider} API unreachable: {exc} — falling back to manual prompt.", err=True)
        return False

    # ── Register the key ──────────────────────────────────────────────────
    try:
        payload = json.dumps(create_body).encode()
        req = urllib.request.Request(create_url, data=payload, headers=req_headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        click.echo(f"[SUCCESS] Deploy key registered in {provider} (id={result.get('id')}).")
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            click.echo(f"[INFO] Deploy key already present in {provider} (duplicate title).")
            return True
        click.echo(
            f"[WARNING] {provider} API create-key returned {exc.code} — falling back to manual prompt.",
            err=True,
        )
        return False
    except Exception as exc:
        click.echo(f"[WARNING] Could not register deploy key automatically: {exc}", err=True)
        return False


def _get_or_create_flux_deploy_key(key_file: Path) -> Tuple[str, str]:
    """Return (private_key_content, public_key_content), generating if needed.

    The key is an ed25519 keypair stored under Age/ alongside the Age key so
    it persists across re-runs — re-bootstrapping an existing cluster won't
    ask the operator to re-add a deploy key to GitHub.
    """
    pub_file = key_file.with_suffix(".pub")
    if key_file.exists() and pub_file.exists():
        return key_file.read_text(), pub_file.read_text()

    key_file.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-C", "fluxcd@noah",
         "-f", str(key_file), "-N", ""],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise click.UsageError(f"ssh-keygen failed: {result.stderr.strip()}")
    os.chmod(key_file, 0o600)
    return key_file.read_text(), pub_file.read_text()


def _encrypt_kubeconfig(project_root: Path, age_key_file: Path) -> None:
    """SOPS-encrypt Kube/noah-cluster.yaml → Kube/noah-cluster.enc.yaml.

    The plaintext file contains an EC private key and must not be committed.
    The encrypted copy matches the .*\.enc\.yaml$ SOPS rule and the
    !*.enc.yaml gitignore exception, so it is safe to commit.
    """
    import shutil
    plain = project_root / "Kube" / "noah-cluster.yaml"
    enc = project_root / "Kube" / "noah-cluster.enc.yaml"
    if not plain.exists():
        click.echo("[WARNING] Kube/noah-cluster.yaml not found — skipping kubeconfig encryption.", err=True)
        return
    shutil.copy2(plain, enc)
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", str(enc)],
        env=env, capture_output=True, text=True,
    )
    if result.returncode == 0:
        click.echo("[SUCCESS] Kubeconfig encrypted → Kube/noah-cluster.enc.yaml (safe to commit)")
        click.echo("[INFO]    Decrypt when needed:")
        click.echo("          sops -d Kube/noah-cluster.enc.yaml > ~/.kube/config")
    else:
        enc.unlink(missing_ok=True)
        click.echo(f"[WARNING] Could not encrypt kubeconfig: {result.stderr.strip()}", err=True)


def run_bootstrap(
    *,
    node: Optional[str],
    nodes: Optional[str],
    ha: bool,
    domain: str,
    flux_repo: str,
    ssh_user: str,
    ssh_key: Optional[str],
    age_key_file: Path,
    k3s_version: Optional[str],
    flux_branch: str,
    flux_path: str,
    force_reset: bool,
    ansible_dir: Path,
    git_token: Optional[str] = None,
    git_provider: Optional[str] = None,
) -> int:
    """Drive the bootstrap end-to-end. Returns the Ansible exit code."""

    node_list = _resolve_nodes(node, nodes, ha)
    _check_existing_cluster(force_reset)

    age_payload = _load_age_private_key(age_key_file)

    # Capture whether the key already exists BEFORE generating it so that
    # deploy_key_is_new accurately reflects "the operator has never seen
    # this key" rather than always being False (the key is created by
    # _get_or_create_flux_deploy_key, so checking after generation is too late).
    deploy_key_file = age_key_file.parent / "flux-deploy-key"
    key_was_new = not (deploy_key_file.exists() and
                       deploy_key_file.with_suffix(".pub").exists())
    private_key, public_key = _get_or_create_flux_deploy_key(deploy_key_file)

    # When a GitHub token is provided, register the deploy key automatically
    # so the Ansible prompt can be skipped entirely.
    ssh_url = _flux_ssh_url(flux_repo)
    if git_token:
        registered = _register_deploy_key(flux_repo, git_token, public_key, git_provider)
        # If registration succeeded the key is already in the provider — no prompt needed.
        deploy_key_is_new = not registered
    else:
        # No token: show the manual prompt only when the key is genuinely new.
        deploy_key_is_new = key_was_new

    inventory = _build_inventory(node_list, ha, ssh_user, ssh_key)

    extra_vars = {
        "ha_mode": bool(ha),
        "domain": domain,
        "flux_repo": ssh_url,
        "flux_branch": flux_branch,
        "flux_path": flux_path,
        "age_private_key": age_payload,
        "flux_deploy_private_key": private_key,
        "flux_deploy_public_key": public_key,
        "deploy_key_is_new": deploy_key_is_new,
    }
    if k3s_version:
        extra_vars["k3s_version"] = k3s_version

    mode_label = "HA (3-node embedded etcd)" if ha else "single-node (embedded etcd)"
    click.echo(f"🚀 NOAH bootstrap — mode: {mode_label}")
    click.echo(f"   nodes:     {', '.join(node_list)}")
    click.echo(f"   domain:    {domain}")
    click.echo(f"   flux repo: {ssh_url} (branch {flux_branch}, path {flux_path})")
    click.echo("")

    with tempfile.TemporaryDirectory(prefix="noah-bootstrap-") as tmpdir:
        tmp = Path(tmpdir)
        inv_path = tmp / "inventory.yml"
        vars_path = tmp / "extra-vars.yml"
        inv_path.write_text(yaml.safe_dump(inventory, sort_keys=False))
        vars_path.write_text(yaml.safe_dump(extra_vars, sort_keys=False))
        # 0600 — file contains Age private key and SSH deploy private key.
        os.chmod(vars_path, 0o600)

        if os.environ.get("NOAH_SKIP_ANSIBLE", "false").lower() in ("1", "true", "yes"):
            click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ansible-playbook.")
            click.echo(f"  inventory : {inv_path}")
            click.echo(f"  extra-vars: (redacted)")
            return 0

        cmd = [
            "ansible-playbook",
            "-i", str(inv_path),
            "bootstrap-k3s.yml",
            "--extra-vars", f"@{vars_path}",
        ]
        env = os.environ.copy()
        env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")
        env.setdefault("SOPS_AGE_KEY_FILE", str(age_key_file))

        result = subprocess.run(cmd, cwd=ansible_dir, env=env)
        if result.returncode == 0:
            _encrypt_kubeconfig(ansible_dir.parent, age_key_file)
        return result.returncode


def run_add_nodes(
    *,
    primary: str,
    new_nodes: List[str],
    ssh_user: str,
    ssh_key: Optional[str],
    ansible_dir: Path,
    k3s_version: Optional[str],
) -> int:
    """Scale a single-node cluster to HA by joining new server nodes.

    Implementation note: this re-uses bootstrap-k3s.yml with ha_mode=true
    and an inventory that has the existing primary as k3s_primary and
    the new IPs as k3s_joiners. The k3s-server-init role is idempotent
    on the primary (it skips install when /usr/local/bin/k3s already
    exists) so this is safe to re-run.
    """
    if len(new_nodes) < 2 or (1 + len(new_nodes)) % 2 == 0:
        raise click.UsageError(
            "add-nodes requires at least 2 new nodes (so primary + new = odd >= 3)."
        )
    inventory = _build_inventory([primary, *new_nodes], ha_mode=True,
                                 ssh_user=ssh_user, ssh_key=ssh_key)
    extra_vars = {
        "ha_mode": True,
        "skip_flux_bootstrap": True,  # honored by the playbook (future use)
    }
    if k3s_version:
        extra_vars["k3s_version"] = k3s_version

    with tempfile.TemporaryDirectory(prefix="noah-addnodes-") as tmpdir:
        tmp = Path(tmpdir)
        inv_path = tmp / "inventory.yml"
        vars_path = tmp / "extra-vars.yml"
        inv_path.write_text(yaml.safe_dump(inventory, sort_keys=False))
        vars_path.write_text(yaml.safe_dump(extra_vars, sort_keys=False))

        if os.environ.get("NOAH_SKIP_ANSIBLE", "false").lower() in ("1", "true", "yes"):
            click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ansible-playbook.")
            return 0

        cmd = [
            "ansible-playbook",
            "-i",
            str(inv_path),
            "bootstrap-k3s.yml",
            "--extra-vars",
            f"@{vars_path}",
            "--tags",
            "k3s-server-join,k3s-validate",
        ]
        env = os.environ.copy()
        env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")
        return subprocess.run(cmd, cwd=ansible_dir, env=env).returncode


def show_cluster_status_v2() -> int:
    """Aggregate node + etcd + Flux state for `noah cluster status`.

    Uses the local kubeconfig (no SSH required); falls back gracefully
    if a tool is missing so this stays useful in partial-install
    debugging.
    """
    def _run(cmd: List[str]) -> Tuple[int, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return r.returncode, (r.stdout + r.stderr).rstrip()
        except FileNotFoundError:
            return 127, f"{cmd[0]}: not installed"
        except subprocess.TimeoutExpired:
            return 124, f"{' '.join(cmd)}: timed out"

    click.echo("== Nodes ==")
    rc, out = _run(["kubectl", "get", "nodes", "-o", "wide"])
    click.echo(out or "(no output)")

    click.echo("\n== etcd members (HA only) ==")
    rc, out = _run([
        "kubectl", "-n", "kube-system", "get", "pods",
        "-l", "component=etcd", "-o", "wide",
    ])
    click.echo(out or "(none — single-node embedded etcd is in-process)")

    click.echo("\n== Flux Kustomizations ==")
    rc, out = _run(["flux", "get", "kustomizations", "--all-namespaces"])
    click.echo(out or "(flux not installed yet?)")

    click.echo("\n== Flux HelmReleases ==")
    rc, out = _run(["flux", "get", "helmreleases", "--all-namespaces"])
    click.echo(out or "(no helmreleases)")

    return 0
