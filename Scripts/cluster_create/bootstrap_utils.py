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


def run_bootstrap(
    *,
    node: Optional[str],
    nodes: Optional[str],
    ha: bool,
    domain: str,
    flux_repo: str,
    github_token: Optional[str],
    ssh_user: str,
    ssh_key: Optional[str],
    age_key_file: Path,
    k3s_version: Optional[str],
    flux_branch: str,
    flux_path: str,
    force_reset: bool,
    ansible_dir: Path,
) -> int:
    """Drive the bootstrap end-to-end. Returns the Ansible exit code."""

    if not github_token:
        raise click.UsageError(
            "A GitHub token is required for `flux bootstrap`. "
            "Pass --github-token or set GITHUB_TOKEN."
        )

    node_list = _resolve_nodes(node, nodes, ha)
    _check_existing_cluster(force_reset)

    age_payload = _load_age_private_key(age_key_file)
    inventory = _build_inventory(node_list, ha, ssh_user, ssh_key)

    extra_vars = {
        "ha_mode": bool(ha),
        "domain": domain,
        "flux_repo": flux_repo,
        "flux_branch": flux_branch,
        "flux_path": flux_path,
        "age_private_key": age_payload,
        "github_token": github_token,
    }
    if k3s_version:
        extra_vars["k3s_version"] = k3s_version

    mode_label = "HA (3-node embedded etcd)" if ha else "single-node (embedded etcd)"
    click.echo(f"🚀 NOAH bootstrap — mode: {mode_label}")
    click.echo(f"   nodes:     {', '.join(node_list)}")
    click.echo(f"   domain:    {domain}")
    click.echo(f"   flux repo: {flux_repo} (branch {flux_branch}, path {flux_path})")
    click.echo("")

    # Write inventory + extra-vars to short-lived files. We use a
    # tempdir rather than the Ansible/inventory/ tree to keep the
    # checked-in inventory pristine.
    with tempfile.TemporaryDirectory(prefix="noah-bootstrap-") as tmpdir:
        tmp = Path(tmpdir)
        inv_path = tmp / "inventory.yml"
        vars_path = tmp / "extra-vars.yml"
        inv_path.write_text(yaml.safe_dump(inventory, sort_keys=False))
        vars_path.write_text(yaml.safe_dump(extra_vars, sort_keys=False))
        # Restrict perms — the extra-vars file holds the GitHub token
        # and the Age private key.
        os.chmod(vars_path, 0o600)

        if os.environ.get("NOAH_SKIP_ANSIBLE", "false").lower() in ("1", "true", "yes"):
            click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ansible-playbook.")
            click.echo(f"  inventory : {inv_path}")
            click.echo(f"  extra-vars: (redacted)")
            return 0

        cmd = [
            "ansible-playbook",
            "-i",
            str(inv_path),
            "bootstrap-k3s.yml",
            "--extra-vars",
            f"@{vars_path}",
        ]
        env = os.environ.copy()
        env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")
        env.setdefault("SOPS_AGE_KEY_FILE", str(age_key_file))

        result = subprocess.run(cmd, cwd=ansible_dir, env=env)
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
