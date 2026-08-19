#!/usr/bin/env python3
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

"""Tests for the Garage lot (Specs/To-do/Garage.md §9).

T3 IS THE TEST THAT MATTERS. Without it a regression reopens the path by which
the compute node reaches the storage tier, and no other test would blink: a
Garage whose rpc_secret sits in the canonical store works perfectly, and only
the isolation guarantee is gone.

T8b is the second. It captures the one operational mistake the derivation of
§4.1 exists to prevent, and it captures it BEFORE garage.toml has been written
to the machines — after that, `garage layout apply` refuses and the machines
are already in an inconsistent state.
"""

import json
import re
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project_root(tmp_path, monkeypatch):
    """Project root with both Age identities, in an unlocked environment."""
    monkeypatch.setenv("NOAH_DISABLE_SOPS", "true")
    monkeypatch.delenv("GARAGE_ADMIN_AGE_KEY_FILE", raising=False)
    age = tmp_path / "Age"
    age.mkdir()
    (age / "keys.txt").write_text(
        "# created: 2026-01-01\n"
        "# public key: age1cluster000000000000000000000000000000000000000000000000\n"
        "AGE-SECRET-KEY-1CLUSTER\n"
    )
    (age / "garage-admin.txt").write_text(
        "# created: 2026-01-01\n"
        "# public key: age1admin00000000000000000000000000000000000000000000000000\n"
        "AGE-SECRET-KEY-1ADMIN\n"
    )
    import Scripts.garage.admin_store as admin_store
    import Scripts.security.canonical_store as canonical_store
    monkeypatch.setattr(canonical_store, "_store_instance", None, raising=False)
    monkeypatch.setattr(admin_store, "_admin_store_instance", None, raising=False)
    return tmp_path


def _infra(node_count=2, bastion="noah-compute-dev", public_ips=False, extra=None):
    nodes = []
    zones = ["site-a", "site-a", "site-b"] if node_count == 3 else ["site-a", "site-b"]
    for index in range(node_count):
        node = {
            "name": f"garage-{chr(ord('a') + index)}",
            "public_ip": f"203.0.113.{20 + index}" if public_ips else None,
            "private_ip": f"10.0.2.{10 + index}",
            "zone": zones[index],
            "capacity": "20G",
            "data_device": f"/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol0{index}",
        }
        nodes.append(node)
    data = {
        "provider": "aws",
        "compute_node": {
            "name": "noah-compute-dev",
            "public_ip": "203.0.113.5",
            "private_ip": "10.0.1.5",
        },
        "bastion": bastion,
        "garage_cidr": "10.0.2.0/24",
        "garage_nodes": nodes,
    }
    if extra:
        data.update(extra)
    return data


# ---------------------------------------------------------------------------
# T1 / T1b — inventory construction (§4.1)
# ---------------------------------------------------------------------------

class TestInventory:
    def test_t1_two_nodes(self):
        """T1 — group garage_nodes, zones site-a / site-b, capacity per host."""
        from Scripts.garage.garage_deploy import _build_inventory, default_zones

        zones = default_zones(2)
        nodes = [
            {"name": "a", "address": "10.0.2.10", "zone": zones[0], "capacity": "20G"},
            {"name": "b", "address": "10.0.2.11", "zone": zones[1], "capacity": "20G"},
        ]
        inv = _build_inventory(nodes, "ubuntu", "/tmp/key")
        hosts = inv["all"]["children"]["garage_nodes"]["hosts"]

        assert set(hosts) == {"a", "b"}
        assert [h["garage_zone"] for h in hosts.values()] == ["site-a", "site-b"]
        assert all(h["garage_capacity"] == "20G" for h in hosts.values())
        assert all(h["ansible_ssh_private_key_file"] == "/tmp/key" for h in hosts.values())

    def test_t1_no_proxy_jump_without_bastion(self):
        """No jump host means no ansible_ssh_common_args at all — the sixth
        field appears only when the topology calls for it."""
        from Scripts.garage.garage_deploy import _build_inventory

        nodes = [{"name": "a", "address": "10.0.2.10", "zone": "site-a", "capacity": "20G"}]
        inv = _build_inventory(nodes, "ubuntu", "/tmp/key")
        host = inv["all"]["children"]["garage_nodes"]["hosts"]["a"]
        assert "ansible_ssh_common_args" not in host

    def test_t1b_three_nodes(self):
        """T1b — three nodes: site-a, site-a, site-b."""
        from Scripts.garage.garage_deploy import default_zones
        assert default_zones(3) == ["site-a", "site-a", "site-b"]

    def test_data_device_is_carried_per_host(self):
        """The IaC layer absorbs the device path so the roles stay
        provider-agnostic (§16.3)."""
        from Scripts.garage.garage_deploy import _build_inventory

        nodes = [{
            "name": "a", "address": "10.0.2.10", "zone": "site-a", "capacity": "20G",
            "data_device": "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol0",
        }]
        inv = _build_inventory(nodes, "ubuntu", None)
        host = inv["all"]["children"]["garage_nodes"]["hosts"]["a"]
        assert host["garage_data_device"].startswith("/dev/disk/by-id/")


# ---------------------------------------------------------------------------
# T8 / T8b — replication factor derived, never entered (G8)
# ---------------------------------------------------------------------------

class TestReplicationFactor:
    def test_t8_derived_from_node_count(self):
        from Scripts.garage.garage_deploy import derive_replication_factor
        assert derive_replication_factor(2) == 2
        assert derive_replication_factor(3) == 3

    def test_t8b_factor_above_node_count_is_refused(self):
        """T8b — refused BEFORE any Ansible call.

        Garage would accept garage.toml and then refuse `layout apply`, with
        every machine already written to. The refusal has to land earlier.
        """
        from Scripts.garage.garage_deploy import GarageDeployError, derive_replication_factor
        with pytest.raises(GarageDeployError, match="layout apply"):
            derive_replication_factor(2, explicit=3)

    def test_lower_factor_stays_accepted(self):
        """Factor 2 on three nodes is a legitimate trial, not a mistake."""
        from Scripts.garage.garage_deploy import derive_replication_factor
        assert derive_replication_factor(3, explicit=2) == 2

    def test_one_node_is_refused(self):
        """One node cannot reproduce CRDT resurrection, so V2 stays out of
        reach — which is the whole reason the default is two (§1.2)."""
        from Scripts.garage.garage_deploy import GarageDeployError, derive_replication_factor
        with pytest.raises(GarageDeployError):
            derive_replication_factor(1)

    def test_four_nodes_are_refused(self):
        from Scripts.garage.garage_deploy import GarageDeployError, derive_replication_factor
        with pytest.raises(GarageDeployError):
            derive_replication_factor(4)


# ---------------------------------------------------------------------------
# T2 — a shared SSH key is refused (condition 3 of §10.2)
# ---------------------------------------------------------------------------

class TestSshKeySeparation:
    def test_t2_flux_deploy_key_is_refused(self, project_root):
        from Scripts.garage.garage_deploy import GarageDeployError, refuse_cluster_ssh_key

        key = project_root / "Age" / "flux-deploy-key"
        key.write_text("PRIVATE")
        with pytest.raises(GarageDeployError, match="§10.2"):
            refuse_cluster_ssh_key(key, project_root)

    def test_t2_recorded_cluster_key_is_refused(self, project_root, monkeypatch):
        """The key `cluster bootstrap` actually used, whatever its path."""
        from Scripts.garage.garage_deploy import GarageDeployError, refuse_cluster_ssh_key
        from Scripts.security.canonical_store import get_canonical_store

        cluster_key = project_root / "my-cluster-key"
        cluster_key.write_text("PRIVATE")
        get_canonical_store(project_root).set_cluster_ssh_key_file(str(cluster_key))

        with pytest.raises(GarageDeployError):
            refuse_cluster_ssh_key(cluster_key, project_root)

    def test_t2_same_public_half_under_another_path_is_refused(self, project_root):
        """Two files, one key, is the same failure: the condition is about the
        key, not the path."""
        from Scripts.garage.garage_deploy import GarageDeployError, refuse_cluster_ssh_key

        shared = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISHARED comment\n"
        (project_root / "Age" / "flux-deploy-key").write_text("PRIVATE")
        (project_root / "Age" / "flux-deploy-key.pub").write_text(shared)
        other = project_root / "elsewhere"
        other.write_text("PRIVATE")
        (project_root / "elsewhere.pub").write_text(shared)

        with pytest.raises(GarageDeployError, match="same public key"):
            refuse_cluster_ssh_key(other, project_root)

    def test_a_distinct_key_is_accepted(self, project_root):
        from Scripts.garage.garage_deploy import refuse_cluster_ssh_key

        (project_root / "Age" / "flux-deploy-key").write_text("CLUSTER")
        (project_root / "Age" / "flux-deploy-key.pub").write_text(
            "ssh-ed25519 AAAACLUSTER cluster\n"
        )
        garage_key = project_root / "garage-key"
        garage_key.write_text("GARAGE")
        (project_root / "garage-key.pub").write_text("ssh-ed25519 AAAAGARAGE garage\n")

        refuse_cluster_ssh_key(garage_key, project_root)   # must not raise


# ---------------------------------------------------------------------------
# T3 — the test that matters (§3, criterion 2)
# ---------------------------------------------------------------------------

class TestSecretDomainSeparation:
    @pytest.mark.parametrize("key", [
        "rpc_secret", "admin_token", "ssh_private_key",
        "owner_access_key_id", "owner_secret_key",
        "cloud_secret_access_key", "tofu_state_passphrase",
    ])
    def test_t3_admin_key_in_canonical_store_is_refused(self, project_root, key):
        """T3 — an administration secret must never enter the canonical store.

        The cluster's Age key is handed to the compute node as the `sops-age`
        Secret, so everything the canonical store holds is readable from there.
        Putting an administration credential in it delivers the storage tier
        along with the compute node, and cancels D6.
        """
        from Scripts.security.canonical_store import (
            AdminSecretLeakError,
            get_canonical_store,
        )
        store = get_canonical_store(project_root)
        with pytest.raises(AdminSecretLeakError):
            store.ensure_service_entries("nextcloud", {key: lambda: "leaked"})

    def test_t3_admin_service_in_canonical_store_is_refused(self, project_root):
        from Scripts.security.canonical_store import (
            AdminSecretLeakError,
            get_canonical_store,
        )
        with pytest.raises(AdminSecretLeakError):
            get_canonical_store(project_root).ensure_service("garage-admin")

    def test_t3_guard_also_fires_on_a_direct_write(self, project_root):
        """save() is the choke point: writing straight into .data must not get
        round the refusal."""
        from Scripts.security.canonical_store import (
            AdminSecretLeakError,
            get_canonical_store,
        )
        store = get_canonical_store(project_root)
        store.data.setdefault("services", {})["nextcloud"] = {"rpc_secret": "leaked"}
        with pytest.raises(AdminSecretLeakError):
            store.save()

    def test_consumption_keys_are_welcome_in_the_canonical_store(self, project_root):
        """The S3 consumption keys are MEANT to be readable from the compute
        node — that is their purpose, and the accepted risk is covered by the
        ZFS snapshots."""
        from Scripts.security.canonical_store import get_canonical_store
        store = get_canonical_store(project_root)
        out = store.ensure_service_entries("garage-nextcloud", {
            "access_key_id": lambda: "GK" + "0" * 24,
            "secret_access_key": lambda: "f" * 64,
        })
        assert out["access_key_id"].startswith("GK")

    def test_admin_store_accepts_what_the_canonical_store_refuses(self, project_root):
        from Scripts.garage.admin_store import ADMIN_SERVICE, ensure_admin_secrets, get_admin_store
        secrets_map = ensure_admin_secrets(get_admin_store(project_root))
        assert set(secrets_map) >= {
            "rpc_secret", "admin_token", "owner_access_key_id",
            "owner_secret_key", "tofu_state_passphrase",
        }
        assert ADMIN_SERVICE == "garage-admin"

    def test_admin_store_writes_to_its_own_file(self, project_root):
        """Criterion 2 — the administration secrets live in a separate file,
        encrypted to a separate identity."""
        from Scripts.garage.admin_store import ensure_admin_secrets, get_admin_store
        ensure_admin_secrets(get_admin_store(project_root))
        names = {p.name for p in (project_root / "Secrets").iterdir()}
        assert "garage-admin.yaml" in names or "garage-admin.enc.yaml" in names
        assert not (names & {"canonical-secrets.yaml", "canonical-secrets.enc.yaml"})

    def test_admin_store_targets_a_distinct_age_identity(self, project_root):
        from Scripts.garage.admin_store import get_admin_store
        store = get_admin_store(project_root)
        assert store.age_key_file.name == "garage-admin.txt"
        assert store.age_key_file != project_root / "Age" / "keys.txt"

    def test_rpc_secret_is_32_bytes_hex(self, project_root):
        """`openssl rand -hex 32` shape, identical on every node (§5)."""
        from Scripts.garage.admin_store import ensure_admin_secrets, get_admin_store
        secrets_map = ensure_admin_secrets(get_admin_store(project_root))
        assert re.fullmatch(r"[0-9a-f]{64}", secrets_map["rpc_secret"])

    def test_tofu_passphrase_clears_the_pbkdf2_floor(self, project_root):
        """G14 — pbkdf2 imposes a 16-character minimum."""
        from Scripts.garage.admin_store import ensure_admin_secrets, get_admin_store
        secrets_map = ensure_admin_secrets(get_admin_store(project_root))
        assert len(secrets_map["tofu_state_passphrase"]) >= 16


# ---------------------------------------------------------------------------
# T4 — no administration identity, no deployment
# ---------------------------------------------------------------------------

class TestAdminIdentityRequired:
    def test_t4_missing_identity_refuses_before_any_ssh(self, project_root):
        from Scripts.garage.admin_store import GarageAdminIdentityError, require_admin_identity

        (project_root / "Age" / "garage-admin.txt").unlink()
        with pytest.raises(GarageAdminIdentityError, match="garage admin init"):
            require_admin_identity(project_root)

    def test_t4_identity_equal_to_the_cluster_key_is_refused(self, project_root, monkeypatch):
        """Pointing domain 3 at the cluster identity publishes every
        administration secret to the compute node."""
        from Scripts.garage.admin_store import GarageAdminIdentityError, require_admin_identity

        monkeypatch.setenv("GARAGE_ADMIN_AGE_KEY_FILE",
                           str(project_root / "Age" / "keys.txt"))
        with pytest.raises(GarageAdminIdentityError):
            require_admin_identity(project_root)

    def test_t4_identity_with_the_cluster_public_key_is_refused(self, project_root):
        """Two files, one identity, is the same leak."""
        from Scripts.garage.admin_store import GarageAdminIdentityError, require_admin_identity

        (project_root / "Age" / "garage-admin.txt").write_text(
            "# public key: age1cluster000000000000000000000000000000000000000000000000\n"
            "AGE-SECRET-KEY-1OTHER\n"
        )
        with pytest.raises(GarageAdminIdentityError, match="same public key"):
            require_admin_identity(project_root)

    def test_deploy_refuses_without_the_identity(self, project_root, monkeypatch):
        """The refusal is wired into run_deploy, not only available as a helper."""
        from Scripts.garage.admin_store import GarageAdminIdentityError
        from Scripts.garage.garage_deploy import run_deploy

        monkeypatch.setenv("NOAH_SKIP_ANSIBLE", "true")
        (project_root / "Age" / "garage-admin.txt").unlink()
        with pytest.raises(GarageAdminIdentityError):
            run_deploy(
                nodes="10.0.2.10,10.0.2.11", from_infra=None, ssh_user="ubuntu",
                ssh_key=None, bastion_user=None, replication_factor=None,
                domain="example.com", capacity="20G", data_device=None, zones=None,
                tls_enabled=True, skip_nat=True, compute_ssh_key=None,
                project_root=project_root, ansible_dir=project_root / "Ansible",
            )


# ---------------------------------------------------------------------------
# T5 — replayed provisioning imports nothing twice (§6.2)
# ---------------------------------------------------------------------------

class TestProvisioningIdempotence:
    def _credentials(self):
        from Scripts.security.security_manager import GARAGE_S3_SERVICES
        return {
            service: {
                "access_key_id": f"GK{index:024x}",
                "secret_access_key": f"{index:064x}",
            }
            for index, service in enumerate(GARAGE_S3_SERVICES)
        }

    def test_t5_known_key_is_not_reimported(self):
        from Scripts.garage.garage_provision import plan_provisioning
        from Scripts.security.security_manager import GARAGE_S3_SERVICES

        creds = self._credentials()
        existing_keys = {c["access_key_id"] for c in creds.values()}
        existing_buckets = set(GARAGE_S3_SERVICES.values())

        actions = plan_provisioning(creds, existing_keys, existing_buckets)
        assert [a for a in actions if a["kind"] == "key_import"] == []
        assert [a for a in actions if a["kind"] == "bucket_create"] == []

    def test_first_run_imports_every_key_and_creates_every_bucket(self):
        from Scripts.garage.garage_provision import plan_provisioning
        from Scripts.security.security_manager import GARAGE_S3_SERVICES

        creds = self._credentials()
        actions = plan_provisioning(creds, set(), set())
        imports = [a for a in actions if a["kind"] == "key_import"]
        creates = [a for a in actions if a["kind"] == "bucket_create"]

        assert len(imports) == len(GARAGE_S3_SERVICES)
        assert {a["bucket"] for a in creates} == set(GARAGE_S3_SERVICES.values())

    def test_permissions_are_reasserted_on_every_run(self):
        """`bucket allow` is idempotent, and a grant dropped by hand would
        otherwise stay dropped."""
        from Scripts.garage.garage_provision import plan_provisioning
        from Scripts.security.security_manager import GARAGE_S3_SERVICES

        creds = self._credentials()
        actions = plan_provisioning(
            creds,
            {c["access_key_id"] for c in creds.values()},
            set(GARAGE_S3_SERVICES.values()),
        )
        allows = [a for a in actions if a["kind"] == "bucket_allow"]
        assert len(allows) == len(GARAGE_S3_SERVICES)
        assert all(a["permissions"] == ["read", "write"] for a in allows)

    def test_the_five_buckets_of_the_specification(self):
        from Scripts.security.security_manager import GARAGE_S3_SERVICES
        assert set(GARAGE_S3_SERVICES.values()) == {
            "nextcloud-objects", "pg-wal", "velero", "git-mirror", "logs",
        }

    def test_owner_key_is_granted_owner_on_every_bucket(self):
        """The owner key stays in domain 3 and is never rendered to the
        cluster, but it must be able to administer every bucket."""
        from Scripts.garage.garage_provision import plan_provisioning
        from Scripts.security.security_manager import GARAGE_S3_SERVICES

        creds = self._credentials()
        owner = "GK" + "f" * 24
        actions = plan_provisioning(creds, set(), set(), owner_key_id=owner)
        owner_allows = [
            a for a in actions
            if a["kind"] == "bucket_allow" and a["key_id"] == owner
        ]
        assert {a["bucket"] for a in owner_allows} == set(GARAGE_S3_SERVICES.values())
        assert all(a["permissions"] == ["owner"] for a in owner_allows)

    def test_secrets_never_reach_an_argv(self):
        """Rendered into a script piped to `bash -s`, so `ps` on the node shows
        `bash -s` and nothing more (criterion 8)."""
        from Scripts.garage.garage_provision import plan_provisioning, render_script

        creds = self._credentials()
        actions = plan_provisioning(creds, set(), set())
        secrets_by_key = {
            c["access_key_id"]: c["secret_access_key"] for c in creds.values()
        }
        script = render_script(actions, secrets_by_key)
        assert "garage key import" in script
        assert "--yes" in script
        # The secret is in the script BODY, which never becomes an argument of
        # the ssh command.
        for secret in secrets_by_key.values():
            assert secret in script

    def test_key_list_parsing(self):
        from Scripts.garage.garage_provision import parse_key_ids
        out = (
            "List of keys:\n"
            "GK0123456789abcdef01234567\tgarage-nextcloud\n"
            "GKfedcba9876543210fedcba98\tgarage-velero\n"
        )
        assert parse_key_ids(out) == {
            "GK0123456789abcdef01234567", "GKfedcba9876543210fedcba98",
        }


# ---------------------------------------------------------------------------
# T6 — generators emit the shape Garage itself emits (§6.2)
# ---------------------------------------------------------------------------

class TestGarageKeyFormat:
    def test_t6_access_key_id_shape(self, project_root):
        from Scripts.security.security_manager import NoahSecurityManager
        manager = NoahSecurityManager(project_root=project_root)
        for _ in range(20):
            assert re.fullmatch(r"GK[0-9a-f]{24}", manager.generate_garage_access_key_id())

    def test_t6_secret_key_shape(self, project_root):
        from Scripts.security.security_manager import NoahSecurityManager
        manager = NoahSecurityManager(project_root=project_root)
        for _ in range(20):
            assert re.fullmatch(r"[0-9a-f]{64}", manager.generate_garage_secret_key())

    def test_t6_every_garage_service_uses_them(self, project_root):
        from Scripts.security.security_manager import GARAGE_S3_SERVICES, NoahSecurityManager
        manager = NoahSecurityManager(project_root=project_root)
        for service in GARAGE_S3_SERVICES:
            creds = manager.generate_service_secrets(service)
            assert re.fullmatch(r"GK[0-9a-f]{24}", creds["access_key_id"]), service
            assert re.fullmatch(r"[0-9a-f]{64}", creds["secret_access_key"]), service

    def test_generic_password_generator_would_not_fit(self, project_root):
        """generate_secure_password() emits arbitrary alphanumerics: stating in
        a test why it cannot be reused here (§6.2)."""
        from Scripts.security.security_manager import NoahSecurityManager
        manager = NoahSecurityManager(project_root=project_root)
        assert not re.fullmatch(r"GK[0-9a-f]{24}", manager.generate_secure_password(26))

    def test_generators_are_stable_once_created(self, project_root):
        """The store is the source of truth: a second call returns the same
        credentials, which is what makes `key import` replayable."""
        from Scripts.security.security_manager import NoahSecurityManager
        manager = NoahSecurityManager(project_root=project_root)
        first = manager.generate_service_secrets("garage-velero")
        second = manager.generate_service_secrets("garage-velero")
        assert first == second


# ---------------------------------------------------------------------------
# T7 — rendered Secrets (§7)
# ---------------------------------------------------------------------------

class TestSecretRendering:
    def test_t7_four_garage_secrets_and_no_gitmirror(self):
        from Scripts.gitops.gitops_init import _DEFAULT_TEMPLATES

        garage_templates = {
            path: body for path, body in _DEFAULT_TEMPLATES.items()
            if "garage-s3-secret" in path
        }
        assert len(garage_templates) == 4
        assert not any("git-mirror" in body for body in garage_templates.values())
        assert not any("gitmirror" in body.lower() for body in garage_templates.values())

    def test_t7_secrets_land_in_the_consumer_namespaces(self):
        from Scripts.gitops.gitops_init import _DEFAULT_TEMPLATES

        namespaces = set()
        for path, body in _DEFAULT_TEMPLATES.items():
            if "garage-s3-secret" in path:
                namespaces.update(re.findall(r"namespace:\s*(\S+)", body))
        assert namespaces == {"nextcloud", "cnpg-system", "velero", "observability"}

    def test_t7_gitmirror_has_a_key_but_no_manifest(self, project_root):
        """Its key stays in the canonical store — readable from the compute
        node like the others, which is coherent: an attacker who gets it can
        destroy the mirror, and the ZFS snapshot is what protects it."""
        from Scripts.gitops.gitops_init import _DEFAULT_TEMPLATES
        from Scripts.security.security_manager import GARAGE_S3_SERVICES, NoahSecurityManager

        assert "garage-gitmirror" in GARAGE_S3_SERVICES
        manager = NoahSecurityManager(project_root=project_root)
        assert manager.generate_service_secrets("garage-gitmirror")["access_key_id"]
        assert not any("garage-gitmirror" in body for body in _DEFAULT_TEMPLATES.values())

    def test_consumer_namespaces_are_declared_for_pre_creation(self):
        from Scripts.gitops.gitops_init import _SECRET_NAMESPACES
        assert {"nextcloud", "cnpg-system", "velero", "observability"} <= set(_SECRET_NAMESPACES)

    def test_the_three_namespace_lists_coincide(self):
        """The risk cilium_sso.md §7.2 names: THREE lists that must agree and
        that nothing related until this test — _SECRET_NAMESPACES, the
        app-secrets role loop, and the flow matrix. A Secret delivered without
        a matching egress rule, or the reverse, only shows up at the first real
        use of the bucket.
        """
        from Scripts.gitops.gitops_init import _SECRET_NAMESPACES

        role = yaml.safe_load(
            (REPO_ROOT / "Ansible/roles/app-secrets/tasks/main.yml").read_text()
        )
        loops = [
            task["loop"] for block in role
            for task in block.get("block", [])
            if isinstance(task, dict) and "loop" in task
        ]
        assert loops, "the app-secrets role no longer has a namespace loop"
        assert set(loops[0]) == set(_SECRET_NAMESPACES)


# ---------------------------------------------------------------------------
# T11 / T11b / T12 — the §16.3 contract
# ---------------------------------------------------------------------------

class TestInfraInventory:
    def test_t11_from_infra_matches_the_manual_form(self, tmp_path):
        """T11 — with bastion null, --from-infra yields an inventory IDENTICAL
        to the one --nodes a,b produces. The IaC feeds _build_inventory(), it
        does not bypass it."""
        from Scripts.garage.garage_deploy import (
            _build_inventory,
            _normalise_manual_nodes,
            load_infra_inventory,
            nodes_from_infra,
        )

        path = tmp_path / "infra.json"
        path.write_text(json.dumps(_infra(bastion=None, public_ips=True)))
        data = load_infra_inventory(path)
        infra_nodes, bastion, cidr = nodes_from_infra(data)
        assert bastion is None
        assert cidr == "10.0.2.0/24"

        from_infra = _build_inventory(infra_nodes, "ubuntu", "/tmp/k", bastion=bastion)
        manual = _build_inventory(
            _normalise_manual_nodes("203.0.113.20,203.0.113.21", None, "20G", None),
            "ubuntu", "/tmp/k",
        )

        def _fields(inv):
            return sorted(
                (h["ansible_host"], h["garage_zone"], h["garage_capacity"],
                 h.get("ansible_ssh_common_args"))
                for h in inv["all"]["children"]["garage_nodes"]["hosts"].values()
            )

        assert _fields(from_infra) == _fields(manual)

    def test_t11b_bastion_produces_proxyjump_on_private_addresses(self, tmp_path):
        """T11b — bastion set and public_ip null: ansible_host carries the
        PRIVATE address, ansible_ssh_common_args carries the ProxyJump, and NO
        KEY PATH DESIGNATES THE JUMP HOST.

        That last clause is the one easiest to lose: making the nodes private
        makes the hop necessary, and the reflex is to drop the administration
        key on the hop — the exact opposite of §3.1.
        """
        from Scripts.garage.garage_deploy import (
            _build_inventory,
            load_infra_inventory,
            nodes_from_infra,
        )

        path = tmp_path / "infra.json"
        path.write_text(json.dumps(_infra(bastion="noah-compute-dev", public_ips=False)))
        data = load_infra_inventory(path)
        nodes, bastion, _cidr = nodes_from_infra(data)
        assert bastion == "203.0.113.5"

        inv = _build_inventory(nodes, "ubuntu", "/tmp/garage-key", bastion=bastion)
        hosts = inv["all"]["children"]["garage_nodes"]["hosts"]

        for host in hosts.values():
            assert host["ansible_host"].startswith("10.0.2.")
            args = host["ansible_ssh_common_args"]
            assert "ProxyJump=ubuntu@203.0.113.5" in args
            # The jump host is NAMED, never keyed: `ssh -J` needs nothing on it
            # but a running sshd (G20).
            assert "-i " not in args
            assert "IdentityFile" not in args
            assert "garage-key" not in args

    def test_t12_a_secret_in_the_infra_file_is_refused(self, tmp_path):
        """T12 — symmetric with T3. The handover file may sit on disk in the
        clear only because it holds nothing worth protecting."""
        from Scripts.garage.garage_deploy import GarageDeployError, load_infra_inventory

        for field, value in [
            ("rpc_secret", "deadbeef"),
            ("ssh_private_key", "-----BEGIN"),
            ("api_token", "tok"),
            ("state_passphrase", "hunter2"),
            ("aws_secret_access_key", "abc"),
        ]:
            path = tmp_path / f"infra-{field}.json"
            path.write_text(json.dumps(_infra(extra={field: value})))
            with pytest.raises(GarageDeployError, match="secret-looking"):
                load_infra_inventory(path)

    def test_t12_a_nested_secret_is_refused_too(self, tmp_path):
        from Scripts.garage.garage_deploy import GarageDeployError, load_infra_inventory

        data = _infra()
        data["garage_nodes"][0]["secret_access_key"] = "leaked"
        path = tmp_path / "infra.json"
        path.write_text(json.dumps(data))
        with pytest.raises(GarageDeployError, match="secret-looking"):
            load_infra_inventory(path)

    def test_a_missing_field_is_refused_but_a_null_one_is_not(self, tmp_path):
        """One null field is admitted, never a missing one: a missing field
        reads as an oversight of the generator, a null one as a topology
        decision (§16.3)."""
        from Scripts.garage.garage_deploy import GarageDeployError, load_infra_inventory

        data = _infra()
        del data["garage_cidr"]
        path = tmp_path / "missing.json"
        path.write_text(json.dumps(data))
        with pytest.raises(GarageDeployError, match="never a missing one"):
            load_infra_inventory(path)

        ok = tmp_path / "null.json"
        ok.write_text(json.dumps(_infra(bastion=None, public_ips=True)))
        load_infra_inventory(ok)   # must not raise

    def test_a_missing_bastion_is_refused(self, tmp_path):
        """`bastion` is part of the schema. Null means "reachable directly";
        absent means the generator forgot, and the two must not look alike."""
        from Scripts.garage.garage_deploy import GarageDeployError, load_infra_inventory

        data = _infra()
        del data["bastion"]
        path = tmp_path / "nobastion.json"
        path.write_text(json.dumps(data))
        with pytest.raises(GarageDeployError, match="never a missing one"):
            load_infra_inventory(path)

    def test_three_node_infra_file(self, tmp_path):
        from Scripts.garage.garage_deploy import (
            derive_replication_factor,
            load_infra_inventory,
            nodes_from_infra,
        )
        path = tmp_path / "infra3.json"
        path.write_text(json.dumps(_infra(node_count=3)))
        nodes, _bastion, _cidr = nodes_from_infra(load_infra_inventory(path))
        assert [n["zone"] for n in nodes] == ["site-a", "site-a", "site-b"]
        assert derive_replication_factor(len(nodes)) == 3

    def test_the_baremetal_example_satisfies_the_contract(self):
        """The demonstration that the §16.3 cut is the right one: production
        consumes the same chain with a hand-written file and no IaC at all."""
        from Scripts.garage.garage_deploy import load_infra_inventory, nodes_from_infra

        example = REPO_ROOT / "Infra/baremetal/infra-inventory.example.json"
        data = load_infra_inventory(example)
        nodes, bastion, cidr = nodes_from_infra(data)
        assert bastion is None          # reachable directly, no ProxyJump
        assert len(nodes) == 3          # production topology
        assert cidr
        for node in nodes:
            assert node["data_device"].startswith("/dev/disk/by-id/")


# ---------------------------------------------------------------------------
# Roles and playbook — the guarantees that live in YAML
# ---------------------------------------------------------------------------

class TestAnsibleAssets:
    def test_the_playbook_and_five_roles_exist(self):
        assert (REPO_ROOT / "Ansible/deploy-garage.yml").exists()
        for role in ("garage-zfs", "garage-install", "garage-config",
                     "garage-cluster", "garage-proxy", "compute-nat"):
            assert (REPO_ROOT / f"Ansible/roles/{role}/tasks/main.yml").exists(), role

    def test_t8_garage_toml_derives_the_factor_and_hides_the_secret(self):
        """T8 — replication_factor comes from the variable the CLI derives, and
        the task writing the file is no_log (criterion 8)."""
        template = (REPO_ROOT
                    / "Ansible/roles/garage-config/templates/garage.toml.j2").read_text()
        assert "replication_factor = {{ garage_replication_factor }}" in template
        assert 'db_engine = "lmdb"' in template
        assert 'consistency_mode = "consistent"' in template

        tasks = yaml.safe_load(
            (REPO_ROOT / "Ansible/roles/garage-config/tasks/main.yml").read_text()
        )
        writer = [t for t in tasks if t.get("template", {}).get("src") == "garage.toml.j2"]
        assert writer, "no task writes garage.toml"
        assert writer[0].get("no_log") is True

    def test_zfs_datasets_follow_appendix_a3(self):
        """recordsize 16K/1M, and compression OFF on data — Garage already
        compresses with zstd, so doubling it spends CPU for nothing."""
        role = (REPO_ROOT / "Ansible/roles/garage-zfs/tasks/main.yml").read_text()
        assert "recordsize=16K" in role
        assert "recordsize=1M" in role
        assert "compression=off" in role
        assert "dedup=off" in role

    def test_zfs_role_refuses_a_short_device_name(self):
        role = (REPO_ROOT / "Ansible/roles/garage-zfs/tasks/main.yml").read_text()
        assert "/dev/disk/by-id/" in role
        assert "nvme1n1" in role   # the trap is named, so it is not re-invented

    def test_nat_role_refuses_ebpf_masquerading(self):
        """N9 — the dependency of G19 that lives in another decision register
        and is the easiest to break."""
        role = (REPO_ROOT / "Ansible/roles/compute-nat/tasks/main.yml").read_text()
        assert "enable-bpf-masquerade" in role
        assert "net.ipv4.ip_forward" in role

    def test_the_playbook_orders_nat_before_the_garage_plays(self):
        """The Garage nodes have NO egress until the compute node routes for
        them, and the failure is a hang rather than a refusal."""
        plays = yaml.safe_load((REPO_ROOT / "Ansible/deploy-garage.yml").read_text())
        hosts = [play["hosts"] for play in plays]
        assert hosts[0] == "compute_node"
        assert hosts[1:] == ["garage_nodes"] * (len(hosts) - 1)

    def test_roles_use_only_collections_the_project_installs(self):
        """No new collection dependency.

        The project declares no requirements.yml, and the one thing that ever
        installed collections went away with AnsibleRunner (§8.1). A role whose
        first task needs an uninstalled collection fails before it can explain
        why — so the Garage roles stay inside ansible.builtin plus the
        community.general the `common` role already relies on.
        """
        import re as _re
        allowed = {"ansible.builtin", "community.general"}
        for path in (REPO_ROOT / "Ansible/roles").glob("*/tasks/main.yml"):
            if not (path.parent.parent.name.startswith("garage-")
                    or path.parent.parent.name == "compute-nat"):
                continue
            used = set(_re.findall(r"^\s+([a-z_]+\.[a-z_]+)\.[a-z_]+:",
                                  path.read_text(), _re.M))
            assert used <= allowed, f"{path.parent.parent.name}: {used - allowed}"

    def test_nat_role_does_not_hijack_nftables_service(self):
        """Ubuntu's /etc/nftables.conf opens with `flush ruleset`.

        Enabling nftables.service on the compute node would wipe the
        iptables-nft rules K3s and Cilium install, at every boot — taking the
        cluster datapath down in order to lay one NAT rule. The role ships its
        own oneshot unit instead.
        """
        raw = (REPO_ROOT / "Ansible/roles/compute-nat/tasks/main.yml").read_text()
        # Comments deliberately NAME the hazard so it is not re-invented; the
        # assertion must read the tasks, not the prose explaining them.
        code = "\n".join(line.split("#", 1)[0] for line in raw.splitlines())
        assert "noah-garage-nat.service" in code
        assert "name: nftables" not in code      # never enabled as a service
        assert "flush ruleset" not in code

    def test_every_retry_has_an_until(self):
        """Ansible ignores `retries` without `until`, so a retry written
        without one is a retry that never happens."""
        for path in (REPO_ROOT / "Ansible/roles").glob("*/tasks/main.yml"):
            tasks = yaml.safe_load(path.read_text())
            stack = list(tasks or [])
            while stack:
                task = stack.pop()
                if not isinstance(task, dict):
                    continue
                stack.extend(task.get("block", []))
                if "retries" in task:
                    assert "until" in task, f"{path}: {task.get('name')}"

    def test_layout_apply_reads_the_version_garage_suggests(self):
        """`layout show` prints "Current cluster layout version: N" BEFORE the
        "layout apply --version N+1" line it means for this. Matching any
        "version N" would pick the first and apply a stale version."""
        role = (REPO_ROOT / "Ansible/roles/garage-cluster/tasks/main.yml").read_text()
        assert "layout apply --version[[:space:]]+[0-9]+" in role
        assert "no staged layout change" in role   # a replay is a no-op

    def test_admin_api_binds_to_the_loopback(self):
        """Flow G5 forbids the cluster the administration API; binding it to
        the loopback makes the refusal structural rather than a firewall rule."""
        template = (REPO_ROOT
                    / "Ansible/roles/garage-config/templates/garage.toml.j2").read_text()
        assert 'api_bind_addr = "127.0.0.1:3903"' in template


# ---------------------------------------------------------------------------
# Infra/aws — what can be checked without OpenTofu installed
# ---------------------------------------------------------------------------

class TestInfraAws:
    def _read(self, name):
        return (REPO_ROOT / "Infra/aws" / name).read_text()

    def _code(self, name):
        """The file with its comments stripped.

        The comments deliberately NAME what the configuration must not do —
        remote-exec, random_password, an instance profile on a Garage node — so
        that the trap is not re-invented later. An assertion that read them
        would fail on the very documentation that prevents the mistake.
        """
        return "\n".join(
            line.split("#", 1)[0]
            for line in self._read(name).splitlines()
        )

    def test_the_five_files_exist(self):
        for name in ("main.tf", "variables.tf", "outputs.tf", "security.tf", "spot.tf"):
            assert (REPO_ROOT / "Infra/aws" / name).exists(), name

    def test_provider_floor_is_pinned(self):
        """The real guard against a persistent Spot request surviving destroy
        is this floor, not where the options are declared (V11, §12.1)."""
        assert 'version = ">= 5.86.0"' in self._read("main.tf")

    def test_state_encryption_is_declared_in_the_configuration(self):
        """G14 — TF_ENCRYPTION alone would write the state in the clear without
        a word when the variable is unset."""
        main = self._read("main.tf")
        assert "encryption {" in main
        assert 'key_provider "pbkdf2" "state"' in main
        assert "passphrase = var.state_passphrase" in main

    def test_the_passphrase_variable_has_no_default(self):
        variables = self._read("variables.tf")
        block = variables.split('variable "state_passphrase"')[1].split("\nvariable ")[0]
        assert "default" not in block
        assert "sensitive   = true" in block

    def test_operator_cidr_refuses_the_whole_internet(self):
        assert '"0.0.0.0/0", "::/0"' in self._read("variables.tf")

    def test_node_count_is_restricted_to_two_or_three(self):
        assert "contains([2, 3], var.node_count)" in self._read("variables.tf")

    def test_spot_options_are_persistent_and_stop(self):
        """G11 — a Garage node in `terminate` is a contradiction: the ZFS pool
        is the very subject of trials V1 to V3."""
        spot = self._read("spot.tf")
        assert spot.count('instance_interruption_behavior = "stop"') == 2
        assert spot.count('spot_instance_type             = "persistent"') == 2

    def test_imds_is_closed_to_containers(self):
        """Path C — hop limit 1 breaks pod access on purpose; cloud-init and
        the host processes stay served."""
        spot = self._read("spot.tf")
        assert spot.count('http_tokens                 = "required"') == 2
        assert spot.count("http_put_response_hop_limit = 1") == 2

    def test_garage_nodes_get_no_instance_profile(self):
        """Not a restricted profile: none at all. With no credentials on the
        machine there is nothing for IMDS to leak."""
        spot = self._code("spot.tf")
        garage_block = spot.split('resource "aws_instance" "garage"')[1].split("\nresource ")[0]
        assert "iam_instance_profile =" not in garage_block

    def test_the_compute_role_denies_the_reach_paths(self):
        """Paths A and B, refused unconditionally: an explicit Deny beats every
        Allow, including one attached later by mistake."""
        security = self._read("security.tf")
        for action in ("ssm:SendCommand", "ssm:StartSession", "ec2:CreateSnapshot",
                       "ec2:CopySnapshot", "ec2:CreateVolume", "ec2:AttachVolume",
                       "ec2:CreateImage"):
            assert action in security, action
        assert 'Effect = "Deny"' in security

    def test_compute_node_forwards_but_grants_nothing(self):
        """G20 — routing is not reaching. The Garage group gains no inbound
        rule from the compute node's position as a router."""
        main = self._read("main.tf")
        security = self._read("security.tf")
        assert "source_dest_check" in self._read("spot.tf")
        assert "network_interface_id = aws_instance.compute.primary_network_interface_id" in main
        # RPC is between Garage nodes only — self-reference, not the compute group.
        rpc = security.split('"garage_rpc"')[1].split("resource ")[0]
        assert "aws_security_group.garage.id" in rpc

    def test_data_device_is_emitted_as_a_by_id_path(self):
        outputs = self._read("outputs.tf")
        assert "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_" in outputs
        assert 'replace(aws_ebs_volume.garage_data[i].id, "-", "")' in outputs

    def test_the_inventory_carries_the_garage_cidr(self):
        """Produced by the layer that creates the subnet, so the cluster egress
        rules cannot be founded on a prefix entered twice."""
        assert "garage_cidr = aws_subnet.garage.cidr_block" in self._read("outputs.tf")

    def test_no_secret_is_generated_by_the_iac(self):
        """§16.7 point 1 — a secret born in OpenTofu lives in the OpenTofu
        state, i.e. in an undeclared fourth domain."""
        for name in ("main.tf", "variables.tf", "outputs.tf", "security.tf", "spot.tf"):
            body = self._code(name)
            assert "random_password" not in body, name
            assert "tls_private_key" not in body, name

    def test_the_iac_never_connects_to_a_machine(self):
        """§16.1 — the handover is a file, not a call."""
        for name in ("main.tf", "spot.tf", "security.tf"):
            body = self._code(name)
            assert "remote-exec" not in body, name
            assert "ansible-playbook" not in body, name

    def test_the_european_targets_are_deliberately_absent(self):
        """§16.8 — Infra/aws/ first and ALONE. Writing the European target in
        parallel would generalise a contract that has carried nothing yet."""
        assert not (REPO_ROOT / "Infra/scaleway").exists()
        assert not (REPO_ROOT / "Infra/ovh").exists()
        assert "16.8" in (REPO_ROOT / "Infra/README.md").read_text()


# ---------------------------------------------------------------------------
# Integration — needs real machines or a real tofu (§9, T9/T10/T13/T14)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRealCluster:
    """T9, T10, T13 and T14 are not runnable here and are not faked.

    T9  — two real nodes: layout apply converges, `garage status` sees 2 nodes,
          the five buckets exist.
    T10 — the same at three, replication_factor 3. Required before any client
          deployment, not before lot 4.
    T13 — `tofu plan` on Infra/aws/ (and later Infra/scaleway/): same variables
          accepted, outputs conforming to the §16.3 schema.
    T14 — the compute node's IAM policy applied to an SSM/EC2 action targeting
          noah:role=garage-node must be REFUSED — verified by a real attempt
          from the compute node, not by reading the policy.

    Marked so `pytest Tests/ -q` stays honest about what it has and has not
    proved: a green suite here says the refusals hold, not that Garage runs.
    """

    def test_placeholder(self):
        pytest.skip("T9/T10/T13/T14 require real machines or a real tofu binary")
