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

"""`noah garage provision` — buckets and S3 keys (§6, decision G2).

THE DIRECTION OF THE FLOW IS THE WHOLE POINT.

`garage key create` has Garage mint a secret that is NOT readable back
afterwards. Any interruption between creation and persistence would leave a
permanently inaccessible bucket — the single most fragile point this
specification had to avoid.

`garage key import <key_id> <secret_key>` accepts an imposed id AND secret
(signature read in the upstream source, `src/garage/cli/structs.rs`,
KeyImportOpt; confirmed on the admin API side as POST /v2/ImportKey). So NOAH
generates the credentials, persists them, and only then imposes them on Garage:

    _service_generators()  ->  canonical store, service "garage-<consumer>"
                           ->  garage key import <id> <secret> --yes
                           ->  rendered as a Kubernetes Secret (§7)

Two consequences beyond tidiness:

  * the failure mode above ceases to exist — if the import fails, the secret is
    already in the store and the operation replays identically;
  * a Garage rebuilt from nothing re-imports the SAME credentials from the
    restored store. Without import it would mint new ones, forcing a store
    update and a re-apply of the Secrets at the worst possible moment. Upstream
    presents ImportKey as reserved "for migration and backup restoration
    purposes" — which is exactly the use NOAH makes of it.

It is §6.2 that makes `tofu destroy` acceptable (G12): the two decisions hold
together, and criterion 16 exists to demonstrate it.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

import click  # type: ignore

from Scripts.garage.admin_store import (
    ADMIN_SERVICE,
    ensure_admin_secrets,
    get_admin_store,
    materialize_ssh_key,
    require_admin_identity,
)
from Scripts.garage.garage_deploy import (
    GarageDeployError,
    _normalise_manual_nodes,
    load_infra_inventory,
    nodes_from_infra,
    ssh_command,
)
from Scripts.security.security_manager import GARAGE_S3_SERVICES

#: Name given to the owner-class key inside Garage. It stays in secret domain 3
#: and is never rendered into a Kubernetes Secret.
_OWNER_KEY_NAME = "noah-owner"

_KEY_ID_PATTERN = re.compile(r"\bGK[0-9a-f]{24}\b")

_GARAGE_ENV = "GARAGE_CONFIG_FILE=/etc/garage/garage.toml"


# ---------------------------------------------------------------------------
# Planning — pure, hence testable without a machine
# ---------------------------------------------------------------------------

def plan_provisioning(
    credentials: dict[str, dict[str, str]],
    existing_key_ids: set[str],
    existing_buckets: set[str],
    *,
    owner_key_id: str | None = None,
) -> list[dict]:
    """Return the ordered list of actions to bring Garage to the target state.

    Kept separate from execution so idempotence is a property that can be
    tested rather than observed: T5 asserts that a replayed provisioning emits
    NO key_import action for a key Garage already knows.

    Re-importing the same pair has no observable side effect anyway, but
    checking first keeps the run readable and the log honest about what
    actually changed.
    """
    actions: list[dict] = []

    for service, creds in sorted(credentials.items()):
        bucket = GARAGE_S3_SERVICES[service]
        key_id = creds["access_key_id"]

        if bucket not in existing_buckets:
            actions.append({"kind": "bucket_create", "bucket": bucket})

        if key_id not in existing_key_ids:
            actions.append({
                "kind": "key_import",
                "service": service,
                "key_id": key_id,
                "secret_key": creds["secret_access_key"],
                "name": service,
            })

        # Always re-asserted: `bucket allow` is idempotent, and a permission
        # silently dropped by an operator would otherwise stay dropped.
        actions.append({
            "kind": "bucket_allow",
            "bucket": bucket,
            "key_id": key_id,
            "permissions": ["read", "write"],
        })

    if owner_key_id:
        if owner_key_id not in existing_key_ids:
            actions.append({
                "kind": "key_import",
                "service": ADMIN_SERVICE,
                "key_id": owner_key_id,
                "secret_key": None,      # filled in by the caller, never logged
                "name": _OWNER_KEY_NAME,
            })
        for bucket in sorted(set(GARAGE_S3_SERVICES.values())):
            actions.append({
                "kind": "bucket_allow",
                "bucket": bucket,
                "key_id": owner_key_id,
                "permissions": ["owner"],
            })

    return actions


def render_script(actions: list[dict], secrets_by_key: dict[str, str]) -> str:
    """Turn an action plan into a shell script to run on a Garage node.

    Secrets travel in the SCRIPT BODY, never in an argv: the script is piped to
    `bash -s` over stdin, so `ps` on the node shows `bash -s` and nothing else.
    Passing a secret as a command-line argument would expose it to every local
    user for the life of the process, and criterion 8 requires that the S3
    secrets appear in no log at all.
    """
    lines = [
        "set -euo pipefail",
        f"export {_GARAGE_ENV}",
        "",
    ]
    for action in actions:
        kind = action["kind"]
        if kind == "bucket_create":
            bucket = shlex.quote(action["bucket"])
            lines.append(
                f"garage bucket create {bucket} 2>/dev/null || "
                f"echo \"bucket {action['bucket']} already exists\""
            )
        elif kind == "key_import":
            secret = action.get("secret_key") or secrets_by_key[action["key_id"]]
            lines.append(
                "garage key import {id} {secret} -n {name} --yes".format(
                    id=shlex.quote(action["key_id"]),
                    secret=shlex.quote(secret),
                    name=shlex.quote(action["name"]),
                )
            )
        elif kind == "bucket_allow":
            flags = " ".join(f"--{p}" for p in action["permissions"])
            lines.append(
                "garage bucket allow {flags} {bucket} --key {id}".format(
                    flags=flags,
                    bucket=shlex.quote(action["bucket"]),
                    id=shlex.quote(action["key_id"]),
                )
            )
        else:  # pragma: no cover - guarded by the planner
            raise ValueError(f"Unknown action kind: {kind}")
    lines.append("")
    return "\n".join(lines)


def parse_key_ids(key_list_output: str) -> set[str]:
    """Extract the key ids Garage already knows from `garage key list`."""
    return set(_KEY_ID_PATTERN.findall(key_list_output))


def parse_bucket_names(bucket_list_output: str) -> set[str]:
    """Extract bucket names from `garage bucket list`.

    Tolerant on purpose: the upstream output has varied across versions, and a
    parser that fails closed here would only ever cause a redundant
    `bucket create`, which is harmless.
    """
    names: set[str] = set()
    for line in bucket_list_output.splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("list of buckets", "id ", "bucket")):
            continue
        for field in line.split():
            if re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", field):
                names.add(field)
                break
    return names


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _skip_remote() -> bool:
    return os.environ.get("NOAH_SKIP_ANSIBLE", "false").lower() in ("1", "true", "yes")


def _run_remote(ssh: list[str], script: str, *, quiet: bool = False) -> subprocess.CompletedProcess:
    """Pipe *script* to `sudo bash -s` on the node. Never echo *script*."""
    result = subprocess.run(
        [*ssh, "sudo bash -s"],
        input=script, text=True, capture_output=True,
    )
    if result.returncode != 0 and not quiet:
        # stderr may name a bucket or a key id, never a secret: the secrets only
        # ever exist inside the script body, which is not reproduced here.
        raise GarageDeployError(
            f"Remote command failed on the Garage node:\n{result.stderr.strip()}"
        )
    return result


def run_provision(
    *,
    nodes: str | None,
    from_infra: str | None,
    ssh_user: str,
    ssh_key: str | None,
    bastion_user: str | None,
    project_root: Path,
) -> int:
    """Create the buckets, import the keys, grant the permissions."""
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

    # --- Generate and persist BEFORE touching Garage (G2) ------------------
    from Scripts.security.security_manager import NoahSecurityManager
    manager = NoahSecurityManager(project_root=project_root)
    credentials = {
        service: manager.generate_service_secrets(service)
        for service in GARAGE_S3_SERVICES
    }

    admin_store = get_admin_store(project_root)
    admin = ensure_admin_secrets(admin_store)
    owner_key_id = admin["owner_access_key_id"]

    secrets_by_key = {
        creds["access_key_id"]: creds["secret_access_key"]
        for creds in credentials.values()
    }
    secrets_by_key[owner_key_id] = admin["owner_secret_key"]

    click.echo("🔑 NOAH Garage provisioning")
    for service, bucket in sorted(GARAGE_S3_SERVICES.items()):
        click.echo(f"   {bucket:<18} ← {service}")
    click.echo("   credentials are in the canonical store; Garage receives them "
               "by `key import` (never the other way round)")
    click.echo("")

    if _skip_remote():
        click.echo("[TEST-SHORTCUT] NOAH_SKIP_ANSIBLE set; skipping ssh.")
        return 0

    with tempfile.TemporaryDirectory(prefix="noah-garage-prov-") as tmpdir:
        key = Path(ssh_key) if ssh_key else materialize_ssh_key(admin_store, Path(tmpdir))
        target = node_list[0]
        ssh = ssh_command(target["address"], ssh_user, key, bastion, bastion_user)

        # --- Read the current state, so the plan says what actually changes --
        existing_keys = parse_key_ids(_run_remote(
            ssh, f"set -euo pipefail\nexport {_GARAGE_ENV}\ngarage key list\n"
        ).stdout)
        existing_buckets = parse_bucket_names(_run_remote(
            ssh, f"set -euo pipefail\nexport {_GARAGE_ENV}\ngarage bucket list\n"
        ).stdout)

        actions = plan_provisioning(
            credentials, existing_keys, existing_buckets, owner_key_id=owner_key_id,
        )
        imports = [a for a in actions if a["kind"] == "key_import"]
        creates = [a for a in actions if a["kind"] == "bucket_create"]
        click.echo(f"   {len(creates)} bucket(s) to create, "
                   f"{len(imports)} key(s) to import, "
                   f"{len(actions) - len(creates) - len(imports)} grant(s) to assert")

        _run_remote(ssh, render_script(actions, secrets_by_key))

        click.echo("")
        click.echo("✅ Provisioning complete. Deliver the S3 credentials to the "
                   "cluster with `python3 noah.py secrets apply`.")
        return 0
