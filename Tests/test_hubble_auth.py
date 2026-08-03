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

"""
Hubble UI Auth Integration Test

Tests the Hubble UI deployment (from the Cilium chart) and the Authentik
forward-auth integration that gates external access — i.e. the path
covered by gitops/apps/hubble-auth/ (provisioner Job + ingress with
nginx auth-url annotations).
"""

import importlib.util
import json
import os
import subprocess
import sys

import pytest
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))


def _load_authentik_provisioner():
    """Load gitops/apps/authentik_provisioner.py — the exact script the
    provisioning Jobs run — so these tests exercise the production code."""
    path = Path(__file__).resolve().parent.parent / 'gitops' / 'apps' / 'authentik_provisioner.py'
    spec = importlib.util.spec_from_file_location('authentik_provisioner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HubbleAuthTester:
    """Test Hubble UI deployment + Authentik proxy provider integration."""

    def __init__(self, domain: str = 'noah-infra.com'):
        self.domain = domain
        # Cilium's chart installs hubble-ui / hubble-relay in kube-system.
        self.cilium_namespace = 'kube-system'
        # Provisioner Job lives in the authentik namespace alongside the
        # bootstrap-token Secret it consumes.
        self.authentik_namespace = 'authentik'
        self.hubble_url = f'https://hubble.{domain}'
        self.authentik_url = f'https://auth.{domain}'

    def print_status(self, status: str, message: str) -> None:
        icons = {'OK': '✅', 'WARN': '⚠️', 'ERROR': '❌', 'INFO': 'ℹ️'}
        print(f"{icons.get(status, '•')} {message}")

    def run_kubectl(self, command: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                f"kubectl {command}", shell=True,
                capture_output=True, text=True, timeout=30,
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _deployment_ready(self, namespace: str, label_selector: str, display: str) -> bool:
        ok, out = self.run_kubectl(
            f"get deployment -n {namespace} -l {label_selector} -o json"
        )
        if not ok:
            self.print_status('ERROR', f'Failed to query {display}: {out}')
            return False
        try:
            items = json.loads(out).get('items', [])
        except json.JSONDecodeError as e:
            self.print_status('ERROR', f'Failed to parse {display}: {e}')
            return False
        if not items:
            self.print_status('ERROR', f'No {display} deployment found')
            return False
        d = items[0]
        spec = d['spec'].get('replicas', 0)
        ready = d.get('status', {}).get('readyReplicas', 0)
        if ready == spec and spec > 0:
            self.print_status('OK', f'{display}: {ready}/{spec} replicas ready')
            return True
        self.print_status('ERROR', f'{display}: {ready}/{spec} replicas ready')
        return False

    def test_hubble_relay_deployment(self) -> bool:
        self.print_status('INFO', 'Testing Hubble Relay deployment...')
        return self._deployment_ready(
            self.cilium_namespace, 'k8s-app=hubble-relay', 'hubble-relay'
        )

    def test_hubble_ui_deployment(self) -> bool:
        self.print_status('INFO', 'Testing Hubble UI deployment...')
        return self._deployment_ready(
            self.cilium_namespace, 'k8s-app=hubble-ui', 'hubble-ui'
        )

    def test_hubble_ui_service(self) -> bool:
        self.print_status('INFO', 'Testing Hubble UI service...')
        ok, out = self.run_kubectl(
            f"get service hubble-ui -n {self.cilium_namespace} -o json"
        )
        if not ok:
            self.print_status('ERROR', f'hubble-ui service missing: {out}')
            return False
        self.print_status('OK', 'hubble-ui service present')
        return True

    def test_hubble_ingress(self) -> bool:
        """Verify the hubble-ui ingress exists, has the expected hostname,
        and carries the Authentik forward-auth annotations — without those
        annotations the UI would be reachable unauthenticated."""
        self.print_status('INFO', 'Testing Hubble UI ingress + auth annotations...')
        ok, out = self.run_kubectl(
            f"get ingress hubble-ui -n {self.cilium_namespace} -o json"
        )
        if not ok:
            self.print_status('ERROR', f'hubble-ui ingress missing: {out}')
            return False
        try:
            ing = json.loads(out)
        except json.JSONDecodeError as e:
            self.print_status('ERROR', f'Failed to parse ingress: {e}')
            return False

        annotations = ing.get('metadata', {}).get('annotations', {}) or {}
        required = (
            'nginx.ingress.kubernetes.io/auth-url',
            'nginx.ingress.kubernetes.io/auth-signin',
            'cert-manager.io/cluster-issuer',
        )
        missing = [a for a in required if a not in annotations]
        if missing:
            self.print_status('ERROR', f'Missing annotations: {", ".join(missing)}')
            return False

        hosts = [
            rule.get('host', '')
            for rule in ing.get('spec', {}).get('rules', [])
        ]
        expected = f'hubble.{self.domain}'
        if expected not in hosts:
            self.print_status('ERROR', f'Expected host {expected} not in {hosts}')
            return False

        self.print_status('OK', f'Ingress wired to {expected} with auth annotations')
        return True

    def test_hubble_tls_certificate(self) -> bool:
        """cert-manager should have issued (or be issuing) hubble-tls."""
        self.print_status('INFO', 'Testing Hubble TLS certificate...')
        ok, out = self.run_kubectl(
            f"get certificate hubble-tls -n {self.cilium_namespace} -o json"
        )
        if not ok:
            self.print_status('ERROR', f'hubble-tls certificate missing: {out}')
            return False
        try:
            cert = json.loads(out)
        except json.JSONDecodeError as e:
            self.print_status('ERROR', f'Failed to parse certificate: {e}')
            return False
        conditions = cert.get('status', {}).get('conditions', []) or []
        ready = next((c for c in conditions if c.get('type') == 'Ready'), None)
        if ready and ready.get('status') == 'True':
            self.print_status('OK', 'hubble-tls Ready=True')
            return True
        reason = ready.get('reason') if ready else 'no Ready condition'
        self.print_status('ERROR', f'hubble-tls not ready ({reason})')
        return False

    def test_provisioner_job(self) -> bool:
        """The authentik-provision-hubble Job registers Hubble UI as an
        Authentik Proxy Provider. Pass = at least one Succeeded run."""
        self.print_status('INFO', 'Testing authentik-provision-hubble Job...')
        ok, out = self.run_kubectl(
            f"get job authentik-provision-hubble -n {self.authentik_namespace} -o json"
        )
        if not ok:
            self.print_status('ERROR', f'Provisioner Job missing: {out}')
            return False
        try:
            job = json.loads(out)
        except json.JSONDecodeError as e:
            self.print_status('ERROR', f'Failed to parse Job: {e}')
            return False
        succeeded = job.get('status', {}).get('succeeded', 0)
        failed = job.get('status', {}).get('failed', 0)
        if succeeded >= 1:
            self.print_status('OK', f'Provisioner Job succeeded ({succeeded} pod(s))')
            return True
        self.print_status('ERROR', f'Provisioner Job not yet succeeded (succeeded={succeeded} failed={failed})')
        return False

    def test_hubble_proxy_app_in_authentik(self) -> bool:
        """Live check: hit Authentik's API to confirm the `hubble` Proxy
        Provider/Application actually exists. Skipped when no token is set."""
        self.print_status('INFO', 'Checking Hubble proxy app in Authentik…')
        authentik_url = os.environ.get('AUTHENTIK_URL', self.authentik_url)
        token = os.environ.get('AUTHENTIK_BOOTSTRAP_TOKEN', '')
        if not token:
            self.print_status('WARN', 'AUTHENTIK_BOOTSTRAP_TOKEN not set — skipping live check')
            return False
        try:
            mod = _load_authentik_provisioner()
            os.environ['AUTHENTIK_URL'] = authentik_url
            os.environ['AUTHENTIK_TOKEN'] = token
            resp = mod.requests.get(
                f"{mod.base_url()}/core/applications/",
                headers=mod.headers(), params={'search': 'hubble'},
                verify=False, timeout=10,
            )
            apps = resp.json().get('results', []) if resp.ok else []
            app = next((a for a in apps if a.get('slug') == 'hubble'), None)
            if app:
                self.print_status('OK', f"Hubble application found in Authentik (slug={app['slug']})")
                return True
            self.print_status('WARN', 'Hubble application not yet provisioned in Authentik')
            return False
        except Exception as exc:
            self.print_status('WARN', f'Authentik API check skipped: {exc}')
            return False

    def run_all_tests(self) -> bool:
        print("\n" + "=" * 60)
        print("🧪 HUBBLE UI AUTH INTEGRATION TEST")
        print("=" * 60)
        print(f"Domain:        {self.domain}")
        print(f"Hubble URL:    {self.hubble_url}")
        print(f"Authentik URL: {self.authentik_url}")
        print("=" * 60 + "\n")

        tests = [
            ('Hubble Relay deployment', self.test_hubble_relay_deployment),
            ('Hubble UI deployment',    self.test_hubble_ui_deployment),
            ('Hubble UI service',       self.test_hubble_ui_service),
            ('Hubble UI ingress',       self.test_hubble_ingress),
            ('Hubble TLS certificate',  self.test_hubble_tls_certificate),
            ('Authentik provision Job', self.test_provisioner_job),
            ('Hubble app in Authentik', self.test_hubble_proxy_app_in_authentik),
        ]

        passed = failed = 0
        for name, fn in tests:
            print(f"\n--- {name} ---")
            try:
                if fn():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.print_status('ERROR', f'Test exception: {e}')
                failed += 1

        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        self.print_status('OK' if failed == 0 else 'ERROR', f'Passed: {passed}/{len(tests)}')
        self.print_status('ERROR' if failed > 0 else 'OK', f'Failed: {failed}/{len(tests)}')
        print("=" * 60 + "\n")
        return failed == 0


# ---------------------------------------------------------------------------
# pytest wrappers
#
# The checks above live on a class with an __init__, which pytest cannot collect
# directly. These wrappers expose each one as an individual test case. They shell
# out to kubectl, so they carry the `cluster` marker and are excluded from the
# default run; use `pytest -m cluster` against a live cluster.
# ---------------------------------------------------------------------------

_CLUSTER_CHECKS = sorted(n for n in vars(HubbleAuthTester) if n.startswith('test_'))


@pytest.fixture(scope='module')
def hubble_tester():
    return HubbleAuthTester(domain=os.getenv('NOAH_DOMAIN', 'noah-infra.com'))


@pytest.mark.cluster
@pytest.mark.parametrize('check', _CLUSTER_CHECKS)
def test_hubble_auth_check(hubble_tester, check):
    assert getattr(hubble_tester, check)(), f'{check} failed'


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description='Test Hubble UI + Authentik integration')
    parser.add_argument('--domain', default='noah-infra.com', help='Domain for services')
    args = parser.parse_args()
    return 0 if HubbleAuthTester(domain=args.domain).run_all_tests() else 1


if __name__ == '__main__':
    sys.exit(main())
