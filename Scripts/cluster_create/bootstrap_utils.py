# SPDX-License-Identifier: AGPL-3.0-or-later
#
# NOAH - Network Operations & Automation Hub
# Copyright (C) 2026 Nicolas Engel <contact@nicolasengel.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
NOAH v0.0.9 — `noah cluster bootstrap` implementation.

Provisions a K3s cluster (single-node by default, --ha for a 3+ node
embedded-etcd control plane — quorum and scheduling capacity, not a
redundant entry point) and runs `flux bootstrap` against a GitOps
repository. This replaces the v0.0.8 `noah cluster create` flow,
which was SQLite-backed and had no continuous reconciliation layer.

The Python side is intentionally thin: it
  1. validates CLI inputs (multi-node needs an odd >=3 node count),
  2. writes a temporary Ansible inventory with k3s_primary / k3s_joiners
     groups derived from --node / --nodes,
  3. loads the Age private key from the canonical SOPS store,
  4. invokes Ansible/bootstrap-k3s.yml with the right extra-vars.

All real work lives in the Ansible roles under Ansible/roles/.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
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
    raise click.UsageError(
        "No node IP available. Pass --node <ip>, run `noah setup gitops --node-ip <ip>` "
        "first (it records the IP in the canonical store), or use --ha --nodes n1,n2,n3."
    )


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
        r"(?:https?|ssh)://(?:[^@/]*@)?([^/]+)/([^/]+)/([^/]+?)(?:\.git)?$",
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
        create_body = {"title": KEY_TITLE, "key": public_key.strip(), "read_only": False}
        existing_key_field = "key"

    elif provider == "gitlab":
        encoded_path = f"{owner}%2F{repo}"
        base = f"https://{host}/api/v4/projects/{encoded_path}/deploy_keys"
        list_url = create_url = base
        req_headers = {
            "PRIVATE-TOKEN": git_token,
            "Content-Type": "application/json",
        }
        create_body = {"title": KEY_TITLE, "key": public_key.strip(), "can_push": True}
        existing_key_field = "key"

    elif provider in ("gitea", "forgejo"):
        base = f"https://{host}/api/v1/repos/{owner}/{repo}/keys"
        list_url = create_url = base
        req_headers = {
            "Authorization": f"token {git_token}",
            "Content-Type": "application/json",
        }
        create_body = {"title": KEY_TITLE, "key": public_key.strip(), "read_only": False}
        existing_key_field = "key"

    else:
        click.echo(
            f"[WARNING] Unsupported git provider '{provider}' — falling back to manual prompt.",
            err=True,
        )
        return False

    click.echo(f"[INFO] Registering deploy key via {provider} API ({host})…")

    # ── Check for an existing identical key (idempotent re-runs) ─────────
    # For GitHub/Gitea/Forgejo: if the same key is already registered as
    # read-only, delete it and re-add it with write access so Flux can push.
    delete_url_template = None
    if provider == "github":
        delete_url_template = f"https://api.github.com/repos/{owner}/{repo}/keys/{{id}}"
    elif provider in ("gitea", "forgejo"):
        delete_url_template = f"https://{host}/api/v1/repos/{owner}/{repo}/keys/{{id}}"

    try:
        req = urllib.request.Request(list_url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            existing = json.loads(resp.read())
        match = next((k for k in existing if key_body in k.get(existing_key_field, "")), None)
        if match:
            needs_write = (
                delete_url_template is not None
                and match.get("read_only") is True
            )
            if needs_write:
                click.echo("[INFO] Existing deploy key is read-only — deleting and re-adding with write access.")
                del_url = delete_url_template.format(id=match["id"])
                del_req = urllib.request.Request(del_url, headers=req_headers, method="DELETE")
                urllib.request.urlopen(del_req, timeout=15).close()  # nosec B310
            else:
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
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
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


def _is_localhost(repo_url: str) -> bool:
    """Return True when the repo URL points at the local machine."""
    from urllib.parse import urlparse
    host = urlparse(repo_url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1")


def _host_primary_ip() -> str:
    """Return the primary non-loopback IP of this machine.

    Flux runs inside a K3s pod so it can't reach 127.0.0.1 — it needs the
    host's real interface IP.  We probe by connecting a UDP socket to a
    public address (no traffic is sent) so the OS picks the preferred route.
    """
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def _register_local_deploy_key(public_key: str) -> bool:
    """Add the Flux deploy key to ~/.ssh/authorized_keys for local SSH access."""
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    authorized_keys = ssh_dir / "authorized_keys"
    existing = authorized_keys.read_text() if authorized_keys.exists() else ""
    if public_key.strip() in existing:
        click.echo("[INFO] Flux deploy key already in ~/.ssh/authorized_keys")
        return True
    with authorized_keys.open("a") as f:
        f.write(f"\n{public_key.strip()}\n")
    authorized_keys.chmod(0o600)
    click.echo("[SUCCESS] Flux deploy key added to ~/.ssh/authorized_keys")
    return True


def _key_is_accepted_by_remote(repo_url: str, key_file: Path) -> bool:
    """Return True if the key authenticates successfully against the git remote."""
    if _is_localhost(repo_url):
        pub = key_file.with_suffix(".pub")
        if not pub.exists():
            return False
        authorized_keys = Path.home() / ".ssh" / "authorized_keys"
        existing = authorized_keys.read_text() if authorized_keys.exists() else ""
        return pub.read_text().strip() in existing

    ssh_url = _flux_ssh_url(repo_url)
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", ssh_url, "HEAD"],
        capture_output=True,
        env={
            **os.environ,
            "GIT_SSH_COMMAND": (
                f"ssh -i {key_file} -o StrictHostKeyChecking=no "
                "-o BatchMode=yes -o ConnectTimeout=10"
            ),
        },
    )
    return result.returncode == 0


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

    Both files contain cluster credentials and are excluded by .gitignore.
    The encrypted copy exists as a local backup decryptable with the Age key.
    """
    import shutil
    plain = project_root / "Kube" / "noah-cluster.yaml"
    enc = project_root / "Kube" / "noah-cluster.enc.yaml"
    if not plain.exists():
        click.echo("[WARNING] Kube/noah-cluster.yaml not found — skipping kubeconfig encryption.", err=True)
        return
    if shutil.which("sops") is None:
        # The cluster is already up; this step is only a local encrypted backup.
        # Skip before copying so we never leave a plaintext file named *.enc.yaml.
        click.echo("[WARNING] sops not found on PATH — skipping kubeconfig backup encryption. "
                   "Install sops (e.g. `setup initialize`) and re-run; the working "
                   "kubeconfig remains at Kube/noah-cluster.yaml.", err=True)
        return
    shutil.copy2(plain, enc)
    env = {**os.environ, "SOPS_AGE_KEY_FILE": str(age_key_file)}
    result = subprocess.run(
        ["sops", "--encrypt", "--in-place", str(enc)],
        env=env, capture_output=True, text=True,
    )
    if result.returncode == 0:
        click.echo("[SUCCESS] Kubeconfig encrypted → Kube/noah-cluster.enc.yaml")
        click.echo("[INFO]    Decrypt when needed:")
        click.echo("          sops -d Kube/noah-cluster.enc.yaml > ~/.kube/config")
    else:
        enc.unlink(missing_ok=True)
        click.echo(f"[WARNING] Could not encrypt kubeconfig: {result.stderr.strip()}", err=True)


def _run_ansible_with_progress(cmd: list, cwd: Path, env: dict) -> int:
    """Stream ansible-playbook output and render it as structured progress.

    Parses PLAY / TASK / result lines from Ansible's default output and
    prints a compact, icon-annotated view.  Errors are collected and
    reprinted as a focused summary at the end.
    """
    _ANSI = re.compile(r"\x1b\[[0-9;]*m")
    _RULE = "─" * 60

    def _strip(line: str) -> str:
        return _ANSI.sub("", line).rstrip()

    TASK_ICONS = {
        "ok":       ("✔", "green"),
        "changed":  ("↺", "yellow"),
        "skipping": ("⏩", "bright_black"),
        "fatal":    ("✗", "red"),
        "failed":   ("✗", "red"),
        "censored": ("🔒", "bright_black"),
    }

    errors: list[dict] = []          # {phase, task, detail}
    current_phase = ""
    current_task = ""
    phase_index = 0
    in_fatal_block = False
    fatal_lines: list[str] = []

    def _flush_fatal():
        nonlocal in_fatal_block, fatal_lines
        if not in_fatal_block:
            return
        detail = "\n".join(fatal_lines).strip()
        # Extract the human-readable message buried in the JSON-ish blob
        for pattern in [r'"msg":\s*"([^"]+)"', r'stderr["\s:]+([^\n]{10,200})', r'(✗[^\n]+)']:
            m = re.search(pattern, detail)
            if m:
                detail = m.group(1)
                break
        errors.append({"phase": current_phase, "task": current_task, "detail": detail})
        in_fatal_block = False
        fatal_lines = []

    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )

    for raw in proc.stdout:
        line = _strip(raw)

        # ── PLAY header ───────────────────────────────────────────────
        if re.match(r"PLAY \[", line):
            _flush_fatal()
            in_fatal_block = False
            phase_index += 1
            current_phase = re.sub(r"\s*\*+$", "", line[6:]).strip(" []─")
            click.echo(f"\n{_RULE}")
            click.echo(click.style(f" Phase {phase_index}: {current_phase}", bold=True))
            click.echo(_RULE)
            continue

        # ── TASK header ───────────────────────────────────────────────
        if re.match(r"TASK \[", line):
            _flush_fatal()
            current_task = re.sub(r"\s*\*+$", "", line[5:]).strip(" []─")
            # Shorten "role_name : task description" → keep both parts
            continue

        # ── Result lines ──────────────────────────────────────────────
        result_match = re.match(r"(ok|changed|skipping|fatal|failed)\s*:\s*\[([^\]]+)\]", line)
        if result_match:
            _flush_fatal()
            status = result_match.group(1)
            icon, color = TASK_ICONS.get(status, ("·", "white"))
            label = click.style(icon, fg=color, bold=(status in ("fatal", "failed")))
            click.echo(f"  {label}  {current_task}")
            if status in ("fatal", "failed"):
                in_fatal_block = True
                fatal_lines = [line]
            continue

        # ── censored (no_log) ─────────────────────────────────────────
        if "censored:" in line and current_task:
            _flush_fatal()
            icon, color = TASK_ICONS["censored"]
            click.echo(f"  {icon}  {current_task}  (output hidden — no_log)")
            continue

        # ── PLAY RECAP — flush before accumulating ────────────────────
        if re.match(r"PLAY RECAP", line):
            _flush_fatal()
            continue

        # ── accumulate fatal detail ───────────────────────────────────
        if in_fatal_block:
            fatal_lines.append(line)
            continue

        # ── recap host line  (host : ok=N changed=N …) ───────────────
        recap = re.match(r"(\S+)\s+: ok=(\d+)\s+changed=(\d+)\s+\S+\s+failed=(\d+)", line)
        if recap:
            host, ok, changed, failed = recap.group(1), recap.group(2), recap.group(3), recap.group(4)
            click.echo(
                f"\n  host={host}  ok={ok}  changed={changed}  failed={click.style(failed, fg='red' if failed != '0' else 'green', bold=True)}"
            )
            continue

        # ── skip noisy boilerplate ────────────────────────────────────
        if re.match(r"\s*\*+\s*$|^Gathering Facts|^$", line):
            continue

        # ── anything else (warnings, skipped plays, etc.) ────────────
        if line.strip():
            click.echo(f"  {click.style('·', fg='bright_black')}  {line.strip()}")

    proc.wait()

    # ── Error summary ─────────────────────────────────────────────────
    if errors:
        click.echo(f"\n{_RULE}")
        click.echo(click.style(f" {len(errors)} error(s) during bootstrap", fg="red", bold=True))
        click.echo(_RULE)
        for err in errors:
            click.echo(f"  {click.style('✗', fg='red', bold=True)}  [{err['phase']}] {err['task']}")
            if err["detail"]:
                for detail_line in err["detail"].splitlines():
                    click.echo(f"     {detail_line.strip()}")
    else:
        click.echo(f"\n{click.style('✔ All tasks completed successfully', fg='green', bold=True)}")

    return proc.returncode


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

    ssh_url = _flux_ssh_url(flux_repo)
    if _is_localhost(flux_repo):
        # Local SSH repo: add the deploy key to authorized_keys — no provider API needed.
        _register_local_deploy_key(public_key)
        deploy_key_is_new = False
        # Flux runs inside a K3s pod and cannot reach 127.0.0.1 — replace with the
        # host's real IP so the GitRepository source can connect from within the cluster.
        host_ip = _host_primary_ip()
        ssh_url = ssh_url.replace("127.0.0.1", host_ip).replace("localhost", host_ip)
        click.echo(f"[INFO] Resolved local flux-repo URL to {ssh_url}")
    elif git_token:
        # Remote repo with token: register via provider API.
        registered = _register_deploy_key(flux_repo, git_token, public_key, git_provider)
        deploy_key_is_new = not registered
    else:
        # Remote repo, no token: prompt when key is new or rejected by remote.
        if key_was_new:
            deploy_key_is_new = True
        else:
            not_accepted = not _key_is_accepted_by_remote(flux_repo, deploy_key_file)
            if not_accepted:
                click.echo(
                    "[WARNING] Deploy key exists locally but is not accepted by the remote. "
                    "Please re-add it to the repository.",
                    err=True,
                )
            deploy_key_is_new = not_accepted

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
    # Seed the operator-declared node public IP (recorded by `setup gitops
    # --node-ip` in the canonical store) so the flux-bootstrap role writes
    # NODE_PUBLIC_IP into cluster-vars and Flux substitutes ${NODE_PUBLIC_IP}
    # into nginx's publish-status-address at apply time.
    from Scripts.security.canonical_store import get_canonical_store
    declared_ip = get_canonical_store(ansible_dir.parent).get_node_public_ip()
    if declared_ip:
        extra_vars["node_public_ip"] = declared_ip

    # Render application secrets from the canonical store and deliver them
    # out-of-band (the app-secrets role kubectl-applies this manifest). Secrets
    # are never committed to Git, so a fresh deploy doesn't depend on a push.
    from Scripts.gitops.gitops_init import render_app_secret_manifests
    extra_vars["app_secrets_manifest"] = render_app_secret_manifests(
        ansible_dir.parent, domain
    )

    mode_label = (
        "multi-node control plane (embedded etcd quorum)" if ha
        else "single-node (embedded etcd)"
    )
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
            click.echo("  extra-vars: (redacted)")
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
        env["ANSIBLE_NOCOLOR"] = "1"          # clean output for the parser
        env["ANSIBLE_FORCE_COLOR"] = "0"

        rc = _run_ansible_with_progress(cmd, cwd=ansible_dir, env=env)
        if rc == 0:
            _encrypt_kubeconfig(ansible_dir.parent, age_key_file)
        return rc


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


def _tcp_open(port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _host_port_report(run) -> str:
    """Report declared hostPorts that are not actually answering on the node.

    `run` is the command runner from show_cluster_status_v2: it takes an argv
    list and returns (returncode, combined output).

    Cilium (kube-proxy replacement) publishes hostPorts as load-balancer
    frontends. When a pod is recreated the previous frontend is not always
    released first, and the new registration is refused with "frontend already
    owned by another service" — a warn-level log nobody reads. The pod stays
    Running and the manifest still declares the port, yet nothing listens on the
    node. Connecting is the only reliable way to catch it.

    Probes 127.0.0.1, so this is meaningful when run on the node itself, which
    is the case in the single-node topology NOAH deploys.
    """
    rc, out = run(["kubectl", "get", "pods", "--all-namespaces", "-o", "json"])
    if rc != 0:
        return out or "(kubectl unavailable)"
    try:
        items = json.loads(out).get("items", [])
    except ValueError:
        return "(could not parse kubectl output)"

    declared = [
        (port["hostPort"], pod["metadata"]["namespace"], pod["metadata"]["name"])
        for pod in items
        if (pod.get("status") or {}).get("phase") == "Running"
        for container in (pod.get("spec") or {}).get("containers") or []
        for port in container.get("ports") or []
        if port.get("hostPort")
    ]
    if not declared:
        return "(no hostPort declared)"

    lines, down = [], []
    for port, namespace, name in sorted(declared):
        reachable = _tcp_open(port)
        lines.append(f"{'OK  ' if reachable else 'DOWN'}  :{port:<5}  {namespace}/{name}")
        if not reachable:
            down.append(str(port))

    if down:
        lines += [
            "",
            f"Declared but not listening: {', '.join(down)}",
            "Cilium likely refused the frontend registration. Confirm with:",
            "  kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent \\",
            "    | grep 'already owned by another service'",
            "Recreating the pod re-registers it: kubectl delete pod -n NS NAME",
        ]
    return "\n".join(lines)


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

    click.echo("\n== hostPort reachability ==")
    click.echo(_host_port_report(_run))

    return 0
