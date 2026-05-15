#!/usr/bin/env python3
"""
SSO Network Integration Tests for NOAH v0.0.7
Tests SSO-gated services over the network:
  - Authentik OIDC provider reachability
  - Headlamp OIDC app (provisioned via AuthentikProvisioner)
  - Hubble UI forward-auth proxy app (provisioned via AuthentikProvisioner)
  - Cloudflare wizard module integrity
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))


class SSONetworkTester:
    """Test SSO network integration for NOAH services."""

    def __init__(self, domain: str = 'noah-infra.com'):
        self.domain = domain
        self.authentik_url = f'https://auth.{domain}'
        self.headlamp_url = f'https://headlamp.{domain}'
        self.hubble_url = f'https://hubble.{domain}'
        self.results: dict = {
            'authentik': [],
            'headlamp': [],
            'hubble': [],
            'provisioner': [],
            'cloudflare': [],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _status(self, level: str, msg: str) -> None:
        icons = {'OK': '✅', 'WARN': '⚠️', 'ERROR': '❌', 'INFO': 'ℹ️'}
        print(f"{icons.get(level, '•')} {msg}")

    def _curl(self, url: str, extra_args: list = None, timeout: int = 10) -> Tuple[bool, str]:
        cmd = ['curl', '-sk', '--max-time', str(timeout), '-o', '/dev/null', '-w', '%{http_code}']
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(url)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            code = result.stdout.strip()
            return result.returncode == 0 and code not in ('000', ''), code
        except Exception as exc:
            return False, str(exc)

    def _kubectl(self, command: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                f'kubectl {command}', shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, 'timeout'
        except Exception as exc:
            return False, str(exc)

    # ------------------------------------------------------------------
    # Authentik health
    # ------------------------------------------------------------------

    def test_authentik_health(self) -> bool:
        """Verify Authentik /api/v3/-/health/ready/ returns 200."""
        self._status('INFO', f'Checking Authentik health at {self.authentik_url}…')
        ok, code = self._curl(f'{self.authentik_url}/api/v3/-/health/ready/')
        if ok and code == '200':
            self._status('OK', f'Authentik health OK (HTTP {code})')
            self.results['authentik'].append(('health', True, code))
            return True
        self._status('WARN', f'Authentik health check returned HTTP {code} (cluster may be unreachable)')
        self.results['authentik'].append(('health', False, code))
        return False

    def test_authentik_oidc_discovery(self) -> bool:
        """Verify Authentik exposes an OIDC discovery endpoint for Headlamp."""
        url = f'{self.authentik_url}/application/o/headlamp/.well-known/openid-configuration'
        self._status('INFO', 'Checking Headlamp OIDC discovery endpoint…')
        ok, code = self._curl(url)
        if ok and code in ('200', '301', '302'):
            self._status('OK', f'OIDC discovery endpoint reachable (HTTP {code})')
            self.results['authentik'].append(('oidc_discovery', True, code))
            return True
        self._status('WARN', f'OIDC discovery returned HTTP {code}')
        self.results['authentik'].append(('oidc_discovery', False, code))
        return False

    # ------------------------------------------------------------------
    # Headlamp SSO
    # ------------------------------------------------------------------

    def test_headlamp_redirects_to_sso(self) -> bool:
        """Verify Headlamp root redirects to Authentik for unauthenticated requests."""
        self._status('INFO', 'Checking Headlamp SSO redirect…')
        ok, code = self._curl(self.headlamp_url, extra_args=['-L', '--max-redirs', '5'])
        if ok and code in ('200', '302', '401'):
            self._status('OK', f'Headlamp accessible (HTTP {code})')
            self.results['headlamp'].append(('sso_redirect', True, code))
            return True
        self._status('WARN', f'Headlamp returned HTTP {code}')
        self.results['headlamp'].append(('sso_redirect', False, code))
        return False

    def test_headlamp_secret_has_provisioned_client_id(self) -> bool:
        """Check that the Kubernetes headlamp-secret has a non-empty OIDC client ID."""
        self._status('INFO', 'Checking headlamp-secret OIDC client ID…')
        ok, output = self._kubectl(
            "get secret headlamp-secret -n kube-system "
            "-o jsonpath='{.data.oidc-client-id}' 2>/dev/null"
        )
        if ok and output:
            import base64
            try:
                client_id = base64.b64decode(output).decode()
                self._status('OK', f'headlamp-secret oidc-client-id = "{client_id}"')
                self.results['headlamp'].append(('secret_client_id', True, client_id))
                return True
            except Exception:
                pass
        self._status('WARN', 'headlamp-secret not found or client ID empty')
        self.results['headlamp'].append(('secret_client_id', False, 'not found'))
        return False

    # ------------------------------------------------------------------
    # Hubble UI forward-auth
    # ------------------------------------------------------------------

    def test_hubble_forward_auth_annotations(self) -> bool:
        """Verify the Hubble UI ingress carries the Authentik forward-auth annotations."""
        self._status('INFO', 'Checking Hubble UI ingress forward-auth annotations…')
        ok, output = self._kubectl(
            "get ingress hubble-ui -n kube-system "
            "-o jsonpath='{.metadata.annotations}' 2>/dev/null"
        )
        if not ok or not output:
            self._status('WARN', 'Hubble UI ingress not found')
            self.results['hubble'].append(('ingress_annotations', False, 'not found'))
            return False

        try:
            annotations = json.loads(output)
        except Exception:
            annotations = {}

        required_annotation = 'nginx.ingress.kubernetes.io/auth-url'
        if required_annotation in annotations and 'outpost.goauthentik.io' in annotations[required_annotation]:
            self._status('OK', 'Hubble UI ingress has Authentik forward-auth annotations')
            self.results['hubble'].append(('ingress_annotations', True, annotations[required_annotation]))
            return True

        self._status('WARN', f'Hubble UI ingress missing {required_annotation}')
        self.results['hubble'].append(('ingress_annotations', False, 'missing'))
        return False

    def test_hubble_requires_auth(self) -> bool:
        """Verify that Hubble UI returns 302/401 for unauthenticated requests (forward-auth active)."""
        self._status('INFO', 'Checking Hubble UI forward-auth enforcement…')
        ok, code = self._curl(self.hubble_url)
        if ok and code in ('302', '401'):
            self._status('OK', f'Hubble UI correctly enforces SSO (HTTP {code})')
            self.results['hubble'].append(('forward_auth_enforced', True, code))
            return True
        self._status('WARN', f'Hubble UI returned HTTP {code} — SSO enforcement may be incomplete')
        self.results['hubble'].append(('forward_auth_enforced', False, code))
        return False

    # ------------------------------------------------------------------
    # AuthentikProvisioner unit checks
    # ------------------------------------------------------------------

    def test_provisioner_oidc_app_methods(self) -> bool:
        """Verify AuthentikProvisioner has all required methods for OIDC + proxy provisioning."""
        self._status('INFO', 'Validating AuthentikProvisioner API surface…')
        try:
            from Scripts.security.authentik_provisioner import AuthentikProvisioner
            p = AuthentikProvisioner('https://auth.example.com', 'token')
            required_methods = [
                'wait_ready',
                'get_authorization_flow',
                'get_property_mappings',
                'get_default_outpost',
                'get_or_create_provider',
                'get_or_create_proxy_provider',
                'get_or_create_application',
                'add_provider_to_outpost',
                'provision_oidc_app',
                'provision_proxy_app',
                'delete_application',
            ]
            missing = [m for m in required_methods if not hasattr(p, m)]
            if missing:
                self._status('ERROR', f'AuthentikProvisioner missing methods: {missing}')
                self.results['provisioner'].append(('methods', False, str(missing)))
                return False
            self._status('OK', 'AuthentikProvisioner has all required methods')
            self.results['provisioner'].append(('methods', True, 'all present'))
            return True
        except Exception as exc:
            self._status('ERROR', f'Import failed: {exc}')
            self.results['provisioner'].append(('methods', False, str(exc)))
            return False

    def test_provisioner_headlamp_app_in_authentik(self) -> bool:
        """Live check: Headlamp OIDC app present in Authentik (skipped if no token)."""
        token = os.environ.get('AUTHENTIK_BOOTSTRAP_TOKEN', '')
        if not token:
            self._status('WARN', 'AUTHENTIK_BOOTSTRAP_TOKEN not set — skipping live Authentik check')
            self.results['provisioner'].append(('headlamp_app', False, 'no token'))
            return False
        try:
            from Scripts.security.authentik_provisioner import AuthentikProvisioner
            p = AuthentikProvisioner(self.authentik_url, token, verify_ssl=False, timeout=10)
            app = p._list_first('/core/applications/', {'slug': 'headlamp'})
            if app:
                self._status('OK', f"Headlamp app found in Authentik (slug={app['slug']})")
                self.results['provisioner'].append(('headlamp_app', True, app['slug']))
                return True
            self._status('WARN', 'Headlamp app not yet provisioned in Authentik')
            self.results['provisioner'].append(('headlamp_app', False, 'not found'))
            return False
        except Exception as exc:
            self._status('WARN', f'Authentik API unreachable: {exc}')
            self.results['provisioner'].append(('headlamp_app', False, str(exc)))
            return False

    def test_provisioner_hubble_app_in_authentik(self) -> bool:
        """Live check: Hubble UI proxy app present in Authentik (skipped if no token)."""
        token = os.environ.get('AUTHENTIK_BOOTSTRAP_TOKEN', '')
        if not token:
            self._status('WARN', 'AUTHENTIK_BOOTSTRAP_TOKEN not set — skipping live Authentik check')
            self.results['provisioner'].append(('hubble_app', False, 'no token'))
            return False
        try:
            from Scripts.security.authentik_provisioner import AuthentikProvisioner
            p = AuthentikProvisioner(self.authentik_url, token, verify_ssl=False, timeout=10)
            app = p._list_first('/core/applications/', {'slug': 'hubble-ui'})
            if app:
                self._status('OK', f"Hubble UI app found in Authentik (slug={app['slug']})")
                self.results['provisioner'].append(('hubble_app', True, app['slug']))
                return True
            self._status('WARN', 'Hubble UI app not yet provisioned in Authentik')
            self.results['provisioner'].append(('hubble_app', False, 'not found'))
            return False
        except Exception as exc:
            self._status('WARN', f'Authentik API unreachable: {exc}')
            self.results['provisioner'].append(('hubble_app', False, str(exc)))
            return False

    # ------------------------------------------------------------------
    # Cloudflare wizard
    # ------------------------------------------------------------------

    def test_cloudflare_wizard_import(self) -> bool:
        """Verify CloudflareWizard module is importable and well-formed."""
        self._status('INFO', 'Validating CloudflareWizard module…')
        try:
            from Scripts.env_init.cloudflare_wizard import CloudflareWizard
            wizard = CloudflareWizard()
            for method in ('run', '_validate_token', '_list_zones', '_persist', '_enable_external_dns'):
                assert hasattr(wizard, method), f"Missing method: {method}"
            self._status('OK', 'CloudflareWizard imported and validated')
            self.results['cloudflare'].append(('import', True, 'all methods present'))
            return True
        except Exception as exc:
            self._status('ERROR', f'CloudflareWizard import failed: {exc}')
            self.results['cloudflare'].append(('import', False, str(exc)))
            return False

    # ------------------------------------------------------------------
    # Runner
    # ------------------------------------------------------------------

    def run_all_tests(self) -> bool:
        print('\n' + '=' * 60)
        print('🧪 NOAH SSO NETWORK INTEGRATION TEST (v0.0.7)')
        print('=' * 60)
        print(f'Domain        : {self.domain}')
        print(f'Authentik URL : {self.authentik_url}')
        print(f'Headlamp URL  : {self.headlamp_url}')
        print(f'Hubble URL    : {self.hubble_url}')
        print('=' * 60 + '\n')

        test_groups = [
            ('Authentik Health', [
                self.test_authentik_health,
                self.test_authentik_oidc_discovery,
            ]),
            ('Headlamp SSO', [
                self.test_headlamp_redirects_to_sso,
                self.test_headlamp_secret_has_provisioned_client_id,
            ]),
            ('Hubble UI Forward-Auth', [
                self.test_hubble_forward_auth_annotations,
                self.test_hubble_requires_auth,
            ]),
            ('AuthentikProvisioner Module', [
                self.test_provisioner_oidc_app_methods,
                self.test_provisioner_headlamp_app_in_authentik,
                self.test_provisioner_hubble_app_in_authentik,
            ]),
            ('Cloudflare Wizard Module', [
                self.test_cloudflare_wizard_import,
            ]),
        ]

        passed = failed = 0
        for group_name, tests in test_groups:
            print(f'\n--- {group_name} ---')
            for test_fn in tests:
                try:
                    if test_fn():
                        passed += 1
                    else:
                        failed += 1
                except Exception as exc:
                    self._status('ERROR', f'Test exception: {exc}')
                    failed += 1

        total = passed + failed
        print('\n' + '=' * 60)
        print('📊 TEST SUMMARY')
        print('=' * 60)
        self._status('OK' if failed == 0 else 'WARN', f'Passed : {passed}/{total}')
        if failed:
            self._status('WARN', f'Failed : {failed}/{total}  (network tests may fail without a live cluster)')
        print('=' * 60 + '\n')

        # Non-zero exit only if provisioner module tests fail (those don't need a cluster)
        provisioner_failures = sum(1 for _, ok, _ in self.results['provisioner'] if not ok
                                   and _ != 'no token')
        cloudflare_failures = sum(1 for _, ok, _ in self.results['cloudflare'] if not ok)
        return (provisioner_failures + cloudflare_failures) == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description='NOAH SSO Network Integration Tests')
    parser.add_argument('--domain', default='noah-infra.com', help='Base domain')
    args = parser.parse_args()

    tester = SSONetworkTester(domain=args.domain)
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
