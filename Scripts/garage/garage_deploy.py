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

"""`noah garage deploy` — build the inventory, run Ansible/deploy-garage.yml.

Modelled on Scripts/cluster_create/bootstrap_utils.py, NOT on a shared runner:
in-memory inventory, TemporaryDirectory, 0600 on the extra-vars file,
NOAH_SKIP_ANSIBLE short-circuit, structured progress. All four are already
proven there, and there is no second execution pattern left to maintain
(decisions G3 and G21).

Two entry sources, one output. `--nodes a,b` is the manual form — the one used
in production on physical machines. `--from-infra <path>` reads the file
OpenTofu produced (§16.3) and derives the same fields. Inventory construction,
factor derivation and every refusal below are identical in both cases: the IaC
FEEDS _build_inventory(), it does not bypass it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import click  # type: ignore
import yaml  # type: ignore

from Scripts.garage.admin_store import (
    ensure_admin_secrets,
    ensure_ssh_key,
    get_admin_store,
    materialize_ssh_key,
    require_admin_identity,
)

#: Default Garage zones per node count (§4.1). One zone per node in
#: development rather than two nodes in the same zone: Garage's placement is
#: zone-aware, and spreading the two exercises the code path that will carry
#: geo-distribution in production. Two co-located nodes would not.
_DEFAULT_ZONES = {
    2: ["site-a", "site-b"],
    3: ["site-a", "site-a", "site-b"],
}

#: Field names that must never appear in infra-inventory.json (T12, §16.3).
#: The file holds public infrastructure facts only — that is what allows it to
#: sit on disk in the clear, and it is why the contract is a file rather than a
#: call: a call would sooner or later have carried a secret.
_SECRET_FIELD_PATTERN = re.compile(
    r"(secret|passphrase|password|token|credential|private_key|access_key)",
    re.IGNORECASE,
)


class GarageDeployError(click.UsageError):
    """A refusal that must land before anything is written to a machine."""


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

def derive_replication_factor(node_count: int, explicit: int | None = None) -> int:
    """Return the replication factor for *node_count* nodes.

    DERIVED, NEVER ENTERED (decision G8). A factor greater than the node count
    is only refused by `garage layout apply` — that is, AFTER the roles have
    already written garage.toml on the machines. Deriving removes the one
    genuinely dangerous combination; the explicit refusal below catches it when
    someone forces it anyway (T8b, acceptance criterion 4).

    An explicit factor stays accepted to force 2 on three nodes — a legitimate
    trial — but never above the node count.
    """
    if node_count not in _DEFAULT_ZONES:
        raise GarageDeployError(
            f"{node_count} node(s) requested. Garage takes 2 (development, "
            "factor 2) or 3 (production, factor 3).\n"
            "  One node cannot reproduce CRDT resurrection, so trial V2 would "
            "stay out of reach — that is the point of the two-node topology "
            "(§1.2).\n"
            "  More than three is outside the target of this specification."
        )
    if explicit is None:
        return node_count
    if explicit > node_count:
        raise GarageDeployError(
            f"replication factor {explicit} requested for {node_count} nodes. "
            "Garage requires replication_factor <= node count, and it would "
            "only refuse at `layout apply` — after garage.toml has been "
            "written on every machine. Refused here instead (§4.1, T8b)."
        )
    if explicit < 1:
        raise GarageDeployError("The replication factor must be at least 1.")
    return explicit


def default_zones(node_count: int) -> list[str]:
    if node_count not in _DEFAULT_ZONES:
        raise GarageDeployError(
            f"No default zone layout for {node_count} nodes; expected 2 or 3."
        )
    return list(_DEFAULT_ZONES[node_count])


# ---------------------------------------------------------------------------
# The §16.3 contract
# ---------------------------------------------------------------------------

def _reject_secrets(payload, path: Path, trail: str = "") -> None:
    """Refuse an infra inventory that carries anything secret-shaped (T12).

    Symmetric with T3 on the canonical-store side. The whole reason the
    handover is a file left in the clear is that it contains nothing worth
    protecting; the moment that stops being true, the file becomes a fourth
    secret domain nobody declared.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            where = f"{trail}.{key}" if trail else key
            if _SECRET_FIELD_PATTERN.search(str(key)):
                raise GarageDeployError(
                    f"{path} carries a secret-looking field ({where}). The "
                    "infrastructure handover file must hold public "
                    "infrastructure facts ONLY — no private key, no "
                    "rpc_secret, no S3 credential, no cloud provider token "
                    "(§16.3). Secrets belong to Secrets/garage-admin.enc.yaml."
                )
            _reject_secrets(value, path, where)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _reject_secrets(value, path, f"{trail}[{index}]")


def load_infra_inventory(path: Path) -> dict:
    """Read and validate infra-inventory.json (§16.3)."""
    path = Path(path)
    if not path.exists():
        raise GarageDeployError(
            f"Infrastructure inventory not found: {path}\n"
            "  It is produced by `tofu apply` in Infra/<target>/, or written "
            "by hand for the baremetal target."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GarageDeployError(f"{path} is not valid JSON: {exc}") from exc

    _reject_secrets(data, path)

    for field in ("provider", "compute_node", "garage_cidr", "garage_nodes"):
        if field not in data:
            # A MISSING field reads as an oversight of the generator, a null
            # one as a topology decision. Only the second is admitted (§16.3).
            raise GarageDeployError(
                f"{path} has no `{field}` field. One null field is admitted in "
                "this file, never a missing one: a missing field reads as an "
                "oversight of the generator."
            )
    if not data["garage_nodes"]:
        raise GarageDeployError(f"{path} declares no Garage node.")
    return data


def _resolve_bastion(data: dict) -> str | None:
    """Return the address of the jump host named by `bastion`, or None.

    `bastion` names a machine in the file rather than carrying an address, so
    the schema stays identical across targets: a provider that gives every
    machine a public address sets it to null and the consumer connects direct.
    """
    bastion = data.get("bastion")
    if not bastion:
        return None
    compute = data.get("compute_node") or {}
    if compute.get("name") == bastion:
        address = compute.get("public_ip") or compute.get("private_ip")
        if not address:
            raise GarageDeployError(
                f"The file names {bastion!r} as the jump host but gives it no "
                "address. With the Garage nodes on a private subnet there is "
                "then no way in."
            )
        return address
    for node in data.get("garage_nodes", []):
        if node.get("name") == bastion:
            return node.get("public_ip") or node.get("private_ip")
    raise GarageDeployError(
        f"The file names {bastion!r} as the jump host, but no machine in it "
        "carries that name."
    )


def nodes_from_infra(data: dict) -> tuple[list[dict], str | None, str]:
    """Turn an infra inventory into (node dicts, bastion address, garage_cidr)."""
    bastion = _resolve_bastion(data)
    nodes: list[dict] = []
    for entry in data["garage_nodes"]:
        # With G19 the Garage nodes have no public address, so ansible_host
        # carries the PRIVATE one and the connection transits by ProxyJump.
        address = entry.get("public_ip") or entry.get("private_ip")
        if not address:
            raise GarageDeployError(
                f"Garage node {entry.get('name')!r} has neither a public nor a "
                "private address."
            )
        nodes.append({
            "name": entry.get("name") or address,
            "address": address,
            "zone": entry.get("zone"),
            "capacity": entry.get("capacity"),
            "data_device": entry.get("data_device"),
        })

    # A target that leaves zone or capacity out must not render `None` into the
    # inventory — Ansible would carry the string through to `layout assign`.
    fallback_zones = default_zones(len(nodes)) if len(nodes) in _DEFAULT_ZONES else None
    for index, node in enumerate(nodes):
        if not node["zone"] and fallback_zones:
            node["zone"] = fallback_zones[index]
        if not node["capacity"]:
            node["capacity"] = "20G"

    return nodes, bastion, data.get("garage_cidr")


def _normalise_manual_nodes(
    nodes_csv: str,
    zones: str | None,
    capacity: str,
    data_device: str | None,
    *,
    require_topology: bool = True,
) -> list[dict]:
    """Turn `--nodes a,b` into node dicts.

    *require_topology* is False for `status` and `provision`, which only need
    an address to reach: the 2-or-3 refusal belongs to `deploy`, where the
    topology is actually being decided, and refusing to REPORT on a cluster
    would help nobody.
    """
    addresses = [n.strip() for n in nodes_csv.split(",") if n.strip()]
    if not addresses:
        raise GarageDeployError("--nodes is empty.")
    if zones:
        zone_list = [z.strip() for z in zones.split(",") if z.strip()]
    elif require_topology or len(addresses) in _DEFAULT_ZONES:
        zone_list = default_zones(len(addresses))
    else:
        zone_list = ["site-a"] * len(addresses)
    if len(zone_list) != len(addresses):
        raise GarageDeployError(
            f"{len(zone_list)} zone(s) for {len(addresses)} node(s). Pass one "
            "zone per node, or none at all to take the defaults of §4.1."
        )
    return [
        {
            "name": address,
            "address": address,
            "zone": zone,
            "capacity": capacity,
            "data_device": data_device,
        }
        for address, zone in zip(addresses, zone_list, strict=True)
    ]


# ---------------------------------------------------------------------------
# Secret domain separation — the refusals of §3 and §4.1
# ---------------------------------------------------------------------------

def _public_half(key_file: Path) -> str | None:
    pub = key_file.with_suffix(key_file.suffix + ".pub") if key_file.suffix else Path(str(key_file) + ".pub")
    try:
        return pub.read_text(encoding="utf-8").split()[1]
    except (OSError, IndexError):
        return None


def refuse_cluster_ssh_key(ssh_key: str | Path, project_root: Path) -> None:
    """Refuse an SSH key that the cluster already uses (T2, criterion 3).

    Condition 3 of §10.2 requires that no system access of the compute node
    reaches the Garage nodes. On physical machines the network is the only way
    in, and a distinct SSH key is what closes it — so a shared key undoes the
    isolation on its own, without anything else going wrong.
    """
    candidate = Path(ssh_key).expanduser()
    resolved = candidate.resolve() if candidate.exists() else candidate

    known_cluster_keys = [project_root / "Age" / "flux-deploy-key"]
    try:
        from Scripts.security.canonical_store import get_canonical_store
        recorded = get_canonical_store(project_root).get_cluster_ssh_key_file()
        if recorded:
            known_cluster_keys.append(Path(recorded).expanduser())
    except Exception:
        # The canonical store may be unavailable (locked, no key). That must
        # not turn a refusal into a crash — the path comparison below still
        # covers the key NOAH itself creates.
        pass

    for cluster_key in known_cluster_keys:
        cluster_resolved = cluster_key.resolve() if cluster_key.exists() else cluster_key
        if resolved == cluster_resolved:
            raise GarageDeployError(
                f"{candidate} is the SSH key the cluster uses.\n"
                "  Condition 3 of §10.2 requires that no system access of the "
                "compute node reaches the Garage nodes: a shared key hands the "
                "storage tier to whoever gets root on the compute node, and D6 "
                "goes with it.\n"
                "  The Garage key comes from secret domain 3. Leave --ssh-key "
                "out and NOAH materialises it from "
                "Secrets/garage-admin.enc.yaml."
            )
        candidate_pub = _public_half(candidate)
        cluster_pub = _public_half(cluster_key)
        if candidate_pub and cluster_pub and candidate_pub == cluster_pub:
            raise GarageDeployError(
                f"{candidate} has the same public key as the cluster key "
                f"({cluster_key}). Two files, one key, is the same failure: "
                "condition 3 of §10.2 is about the key, not the path."
            )


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def _proxy_jump_args(bastion: str, bastion_user: str) -> str:
    """SSH options routing the connection through *bastion*.

    NO KEY PATH DESIGNATES THE JUMP HOST, and that is the point (G20, T11b).
    Making the Garage nodes private makes the hop necessary, and the reflex is
    then to drop the administration key on the jump machine — the exact
    opposite of what §3.1 requires. `ssh -J` needs nothing on the hop but a
    running sshd: it CARRIES the connection, it does not hold the key.
    """
    return (
        f"-o ProxyJump={bastion_user}@{bastion} "
        "-o StrictHostKeyChecking=accept-new"
    )


def _build_inventory(
    nodes: list[dict],
    ssh_user: str,
    ssh_key: str | None,
    *,
    bastion: str | None = None,
    bastion_user: str | None = None,
    compute_node: dict | None = None,
) -> dict:
    """Construct the inventory consumed by deploy-garage.yml (§4.1).

    One group, `garage_nodes`, with five per-host fields — ansible_host,
    ansible_user, ansible_ssh_private_key_file, garage_zone, garage_capacity —
    plus garage_data_device, which the IaC layer absorbs so the Ansible roles
    stay provider-agnostic.

    A sixth field, ansible_ssh_common_args, appears ONLY when the
    infrastructure file names a jump host (§16.3, G19): the Garage nodes are
    then on a private subnet, ansible_host carries their private address, and
    the connection transits by ProxyJump.

    `compute_node` adds the second group the playbook needs, for the egress
    routing role. Absent on physical machines, where the question is moot.
    """
    common_args = (
        _proxy_jump_args(bastion, bastion_user or ssh_user) if bastion else None
    )

    def _host_block(node: dict) -> dict:
        host: dict = {
            "ansible_host": node["address"],
            "ansible_user": ssh_user,
            "garage_zone": node["zone"],
            "garage_capacity": node["capacity"],
        }
        if ssh_key:
            host["ansible_ssh_private_key_file"] = str(ssh_key)
        if node.get("data_device"):
            host["garage_data_device"] = node["data_device"]
        if common_args:
            host["ansible_ssh_common_args"] = common_args
        return host

    children: dict = {
        "garage_nodes": {
            "hosts": {node["name"]: _host_block(node) for node in nodes},
        },
    }

    if compute_node:
        # The compute node is reached directly — it is the one machine with a
        # public address — and with the CLUSTER's SSH key, never the Garage
        # one. Two key pairs, and the code says which is which.
        compute_host: dict = {
            "ansible_host": compute_node["address"],
            "ansible_user": compute_node.get("user", ssh_user),
        }
        if compute_node.get("ssh_key"):
            compute_host["ansible_ssh_private_key_file"] = str(compute_node["ssh_key"])
        children["compute_node"] = {
            "hosts": {compute_node["name"]: compute_host},
        }

    return {"all": {"children": children}}


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def _skip_ansible() -> bool:
    return os.environ.get("NOAH_SKIP_ANSIBLE", "false").lower() in ("1", "true", "yes")


def run_deploy(
    *,
    nodes: str | None,
    from_infra: str | None,
    ssh_user: str,
    ssh_key: str | None,
    bastion_user: str | None,
    replication_factor: int | None,
    domain: str,
    capacity: str,
    data_device: str | None,
    zones: str | None,
    tls_enabled: bool,
    skip_nat: bool,
    compute_ssh_key: str | None,
    project_root: Path,
    ansible_dir: Path,
) -> int:
    """Drive the Garage deployment end to end. Returns the Ansible exit code."""

    # --- Refusals, all of them BEFORE anything touches a machine ------------
    #
    # Order matters. The identity check comes first because writing the
    # administration secrets in the wrong place is the one defect no later step
    # repairs, and which §3 makes invisible once the deployment is in place.
    require_admin_identity(project_root)

    if nodes and from_infra:
        raise GarageDeployError(
            "Pass --nodes or --from-infra, not both: they are two entries to "
            "the same inventory construction."
        )

    bastion: str | None = None
    garage_cidr: str | None = None
    compute_node: dict | None = None

    if from_infra:
        data = load_infra_inventory(Path(from_infra))
        node_list, bastion, garage_cidr = nodes_from_infra(data)
        compute = data.get("compute_node") or {}
        if compute.get("name"):
            compute_node = {
                "name": compute["name"],
                "address": compute.get("public_ip") or compute.get("private_ip"),
                "user": ssh_user,
                "ssh_key": compute_ssh_key,
            }
    elif nodes:
        node_list = _normalise_manual_nodes(nodes, zones, capacity, data_device)
    else:
        raise GarageDeployError(
            "No node given. Pass --nodes a,b (manual form, used in production "
            "on physical machines) or --from-infra "
            "Infra/aws/infra-inventory.json."
        )

    factor = derive_replication_factor(len(node_list), replication_factor)

    if ssh_key:
        refuse_cluster_ssh_key(ssh_key, project_root)

    # --- Domain 3 ----------------------------------------------------------
    store = get_admin_store(project_root)
    admin = ensure_admin_secrets(store)
    ensure_ssh_key(store)

    click.echo("🗄  NOAH Garage deploy")
    click.echo(f"   nodes:       {', '.join(n['name'] for n in node_list)}")
    click.echo(f"   zones:       {', '.join(str(n['zone']) for n in node_list)}")
    click.echo(f"   replication: {factor}"
               + ("  (development topology — losing a node stops writes)"
                  if factor == 2 else ""))
    click.echo(f"   jump host:   {bastion or 'none (direct)'}")
    click.echo(f"   TLS:         {'enabled' if tls_enabled else 'DISABLED — explicit choice'}")
    click.echo("")

    with tempfile.TemporaryDirectory(prefix="noah-garage-") as tmpdir:
        tmp = Path(tmpdir)

        # The administration SSH key exists on disk only for the length of this
        # run, at 0600, inside a directory that goes away with the context
        # manager. It is never copied to the jump host (G20).
        effective_key = Path(ssh_key) if ssh_key else materialize_ssh_key(store, tmp)

        inventory = _build_inventory(
            node_list,
            ssh_user,
            str(effective_key),
            bastion=bastion,
            bastion_user=bastion_user,
            compute_node=None if skip_nat else compute_node,
        )

        extra_vars = {
            "garage_replication_factor": factor,
            "garage_rpc_secret": admin["rpc_secret"],
            "garage_admin_token": admin["admin_token"],
            "garage_domain": domain,
            "garage_tls_enabled": bool(tls_enabled),
        }
        if garage_cidr:
            extra_vars["garage_cidr"] = garage_cidr

        inv_path = tmp / "inventory.yml"
        vars_path = tmp / "extra-vars.yml"
        inv_path.write_text(yaml.safe_dump(inventory, sort_keys=False))
        vars_path.write_text(yaml.safe_dump(extra_vars, sort_keys=False))
        # 0600 — the file carries rpc_secret and the administration token.
        os.chmod(vars_path, 0o600)

        if _skip_ansible():
            click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ansible-playbook.")
            click.echo(f"  inventory : {inv_path}")
            click.echo("  extra-vars: (redacted)")
            return 0

        cmd = [
            "ansible-playbook",
            "-i", str(inv_path),
            "deploy-garage.yml",
            "--extra-vars", f"@{vars_path}",
        ]
        env = os.environ.copy()
        env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")
        env["ANSIBLE_NOCOLOR"] = "1"
        env["ANSIBLE_FORCE_COLOR"] = "0"

        # Reuses the bootstrap's progress renderer rather than a second one.
        from Scripts.cluster_create.bootstrap_utils import _run_ansible_with_progress
        return _run_ansible_with_progress(cmd, cwd=ansible_dir, env=env)


def ssh_command(
    address: str,
    ssh_user: str,
    ssh_key: Path,
    bastion: str | None = None,
    bastion_user: str | None = None,
) -> list[str]:
    """Build an ssh argv reaching *address*, through *bastion* when given.

    Shared by `garage status` and the provisioning path so the jump-host rule
    is expressed once: `-J` names the hop, never a key on it.
    """
    cmd = [
        "ssh",
        "-i", str(ssh_key),
        "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
    ]
    if bastion:
        cmd += ["-J", f"{bastion_user or ssh_user}@{bastion}"]
    cmd.append(f"{ssh_user}@{address}")
    return cmd


def run_status(
    *,
    nodes: str | None,
    from_infra: str | None,
    ssh_user: str,
    ssh_key: str | None,
    bastion_user: str | None,
    project_root: Path,
) -> int:
    """`noah garage status` — cluster state and applied layout."""
    require_admin_identity(project_root)

    bastion = None
    if from_infra:
        data = load_infra_inventory(Path(from_infra))
        node_list, bastion, _cidr = nodes_from_infra(data)
    elif nodes:
        node_list = _normalise_manual_nodes(nodes, None, "20G", None,
                                            require_topology=False)
    else:
        raise GarageDeployError("Pass --nodes or --from-infra.")

    if _skip_ansible():
        click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ssh.")
        return 0

    store = get_admin_store(project_root)
    with tempfile.TemporaryDirectory(prefix="noah-garage-status-") as tmpdir:
        key = Path(ssh_key) if ssh_key else materialize_ssh_key(store, Path(tmpdir))
        target = node_list[0]
        cmd = ssh_command(target["address"], ssh_user, key, bastion, bastion_user)
        rc = 0
        for label, remote in (
            ("cluster status", "garage status"),
            ("layout", "garage layout show"),
            ("buckets", "garage bucket list"),
        ):
            click.echo(click.style(f"── {label} ─────────────────", bold=True))
            result = subprocess.run(
                [*cmd, f"sudo GARAGE_CONFIG_FILE=/etc/garage/garage.toml {remote}"],
                capture_output=True, text=True,
            )
            click.echo(result.stdout.strip() or result.stderr.strip())
            rc = rc or result.returncode
        return rc
