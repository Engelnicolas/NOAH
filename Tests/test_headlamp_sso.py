#!/usr/bin/env python3
"""
Headlamp SSO Integration Test
Tests Headlamp Kubernetes Dashboard deployment and Authentik SSO integration
"""

import importlib.util
import os
import subprocess
import sys
import json

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


class HeadlampSSOTester:
    """Test Headlamp deployment and SSO integration"""

    def __init__(self, domain='noah-infra.com'):
        self.domain = domain
        self.namespace = 'headlamp'
        self.headlamp_url = f'https://headlamp.{domain}'
        self.authentik_url = f'https://auth.{domain}'
        self.results = {
            'deployment': [],
            'service': [],
            'ingress': [],
            'oidc': [],
            'connectivity': []
        }

    def print_status(self, status: str, message: str):
        """Print status with emoji indicators"""
        icons = {
            'OK': '✅',
            'WARN': '⚠️',
            'ERROR': '❌',
            'INFO': 'ℹ️'
        }
        print(f"{icons.get(status, '•')} {message}")

    def run_kubectl(self, command: str) -> Tuple[bool, str]:
        """Run kubectl command and return success status and output"""
        try:
            result = subprocess.run(
                f"kubectl {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def test_headlamp_deployment(self) -> bool:
        """Test if Headlamp deployment exists and is ready"""
        self.print_status('INFO', 'Testing Headlamp deployment...')

        # Check deployment exists
        success, output = self.run_kubectl(
            f"get deployment -n {self.namespace} -l app.kubernetes.io/name=headlamp -o json"
        )

        if not success:
            self.print_status('ERROR', f'Failed to get Headlamp deployment: {output}')
            self.results['deployment'].append(('deployment_exists', False, output))
            return False

        try:
            data = json.loads(output)
            if not data.get('items'):
                self.print_status('ERROR', 'No Headlamp deployment found')
                self.results['deployment'].append(('deployment_exists', False, 'No deployment found'))
                return False

            deployment = data['items'][0]
            name = deployment['metadata']['name']

            # Check replicas
            spec_replicas = deployment['spec'].get('replicas', 0)
            status = deployment.get('status', {})
            ready_replicas = status.get('readyReplicas', 0)
            available_replicas = status.get('availableReplicas', 0)

            self.print_status('OK', f'Deployment "{name}" found')
            self.print_status('OK', f'Replicas: {ready_replicas}/{spec_replicas} ready, {available_replicas} available')

            self.results['deployment'].append(('deployment_exists', True, name))
            self.results['deployment'].append(('replicas_ready', ready_replicas == spec_replicas, f'{ready_replicas}/{spec_replicas}'))

            return ready_replicas == spec_replicas

        except (json.JSONDecodeError, KeyError) as e:
            self.print_status('ERROR', f'Failed to parse deployment data: {e}')
            self.results['deployment'].append(('deployment_parse', False, str(e)))
            return False

    def test_headlamp_pods(self) -> bool:
        """Test if Headlamp pods are running"""
        self.print_status('INFO', 'Testing Headlamp pods...')

        success, output = self.run_kubectl(
            f"get pods -n {self.namespace} -l app.kubernetes.io/name=headlamp -o json"
        )

        if not success:
            self.print_status('ERROR', f'Failed to get Headlamp pods: {output}')
            return False

        try:
            data = json.loads(output)
            pods = data.get('items', [])

            if not pods:
                self.print_status('ERROR', 'No Headlamp pods found')
                return False

            all_running = True
            for pod in pods:
                name = pod['metadata']['name']
                phase = pod['status'].get('phase', 'Unknown')

                if phase == 'Running':
                    self.print_status('OK', f'Pod "{name}" is Running')
                else:
                    self.print_status('ERROR', f'Pod "{name}" is {phase}')
                    all_running = False

            return all_running

        except (json.JSONDecodeError, KeyError) as e:
            self.print_status('ERROR', f'Failed to parse pods data: {e}')
            return False

    def test_headlamp_service(self) -> bool:
        """Test if Headlamp service exists"""
        self.print_status('INFO', 'Testing Headlamp service...')

        success, output = self.run_kubectl(
            f"get service -n {self.namespace} -l app.kubernetes.io/name=headlamp -o json"
        )

        if not success:
            self.print_status('ERROR', f'Failed to get Headlamp service: {output}')
            self.results['service'].append(('service_exists', False, output))
            return False

        try:
            data = json.loads(output)
            services = data.get('items', [])

            if not services:
                self.print_status('ERROR', 'No Headlamp service found')
                self.results['service'].append(('service_exists', False, 'No service found'))
                return False

            service = services[0]
            name = service['metadata']['name']
            service_type = service['spec'].get('type', 'Unknown')
            ports = service['spec'].get('ports', [])

            self.print_status('OK', f'Service "{name}" found (Type: {service_type})')
            for port in ports:
                self.print_status('OK', f'  Port: {port.get("port")} -> {port.get("targetPort")}')

            self.results['service'].append(('service_exists', True, name))
            self.results['service'].append(('service_type', True, service_type))

            return True

        except (json.JSONDecodeError, KeyError) as e:
            self.print_status('ERROR', f'Failed to parse service data: {e}')
            self.results['service'].append(('service_parse', False, str(e)))
            return False

    def test_headlamp_ingress(self) -> bool:
        """Test if Headlamp ingress exists and is configured"""
        self.print_status('INFO', 'Testing Headlamp ingress...')

        success, output = self.run_kubectl(
            f"get ingress -n {self.namespace} -l app.kubernetes.io/name=headlamp -o json"
        )

        if not success:
            self.print_status('ERROR', f'Failed to get Headlamp ingress: {output}')
            self.results['ingress'].append(('ingress_exists', False, output))
            return False

        try:
            data = json.loads(output)
            ingresses = data.get('items', [])

            if not ingresses:
                self.print_status('ERROR', 'No Headlamp ingress found')
                self.results['ingress'].append(('ingress_exists', False, 'No ingress found'))
                return False

            ingress = ingresses[0]
            name = ingress['metadata']['name']

            # Check rules
            rules = ingress['spec'].get('rules', [])
            tls_configs = ingress['spec'].get('tls', [])

            self.print_status('OK', f'Ingress "{name}" found')

            for rule in rules:
                host = rule.get('host', 'N/A')
                self.print_status('OK', f'  Host: {host}')

                if host == f'headlamp.{self.domain}':
                    self.results['ingress'].append(('correct_host', True, host))

            if tls_configs:
                self.print_status('OK', f'  TLS enabled with {len(tls_configs)} config(s)')
                self.results['ingress'].append(('tls_enabled', True, str(len(tls_configs))))
            else:
                self.print_status('WARN', '  TLS not configured')
                self.results['ingress'].append(('tls_enabled', False, 'No TLS'))

            return True

        except (json.JSONDecodeError, KeyError) as e:
            self.print_status('ERROR', f'Failed to parse ingress data: {e}')
            self.results['ingress'].append(('ingress_parse', False, str(e)))
            return False

    def test_oidc_secret(self) -> bool:
        """Test if OIDC secret exists for Headlamp"""
        self.print_status('INFO', 'Testing OIDC secret configuration...')

        success, output = self.run_kubectl(
            f"get secret headlamp-oidc -n {self.namespace} -o json"
        )

        if not success:
            # Try alternative secret name
            success, output = self.run_kubectl(
                f"get secret headlamp-secret -n {self.namespace} -o json"
            )

        if not success:
            self.print_status('WARN', 'OIDC secret not found (may be configured differently)')
            self.results['oidc'].append(('secret_exists', False, 'Secret not found'))
            return False

        try:
            data = json.loads(output)
            secret_data = data.get('data', {})

            # Env-format keys consumed via envFrom (config.oidc.externalSecret).
            # issuerURL/scopes live in the HelmRelease .Values.env, not the Secret.
            required_keys = ['OIDC_CLIENT_ID', 'OIDC_CLIENT_SECRET']
            missing_keys = [key for key in required_keys if key not in secret_data]

            if not missing_keys:
                self.print_status('OK', 'OIDC secret configured with all required fields')
                self.results['oidc'].append(('secret_complete', True, 'All fields present'))
                return True
            else:
                self.print_status('WARN', f'OIDC secret missing fields: {missing_keys}')
                self.results['oidc'].append(('secret_complete', False, f'Missing: {missing_keys}'))
                return False

        except (json.JSONDecodeError, KeyError) as e:
            self.print_status('ERROR', f'Failed to parse secret data: {e}')
            self.results['oidc'].append(('secret_parse', False, str(e)))
            return False

    def test_authentik_provisioner_import(self) -> bool:
        """Test that the canonical Authentik provisioner script is importable and well-formed."""
        self.print_status('INFO', 'Testing Authentik provisioner script…')
        try:
            mod = _load_authentik_provisioner()
            # Verify the key entry points exist (the script the Jobs invoke).
            for fn in ('provision_oidc', 'provision_proxy', 'wait_for_authentik',
                       'find_or_create', 'main'):
                assert callable(getattr(mod, fn, None)), f"Missing function: {fn}"
            self.print_status('OK', 'Authentik provisioner script imported and validated')
            self.results['oidc'].append(('provisioner_import', True, 'All functions present'))
            return True
        except Exception as exc:
            self.print_status('ERROR', f'Authentik provisioner import failed: {exc}')
            self.results['oidc'].append(('provisioner_import', False, str(exc)))
            return False

    def test_headlamp_oidc_provisioned_in_authentik(self) -> bool:
        """Check whether Headlamp OIDC application exists in Authentik (live cluster only)."""
        import os
        self.print_status('INFO', 'Checking Headlamp OIDC app in Authentik…')

        authentik_url = os.environ.get('AUTHENTIK_URL', f'https://auth.{self.domain}')
        token = os.environ.get('AUTHENTIK_BOOTSTRAP_TOKEN', '')
        if not token:
            self.print_status('WARN', 'AUTHENTIK_BOOTSTRAP_TOKEN not set — skipping live check')
            self.results['oidc'].append(('authentik_live_check', False, 'No token'))
            return False

        try:
            mod = _load_authentik_provisioner()
            os.environ['AUTHENTIK_URL'] = authentik_url
            os.environ['AUTHENTIK_TOKEN'] = token
            resp = mod.requests.get(
                f"{mod.base_url()}/core/applications/",
                headers=mod.headers(), params={'search': 'headlamp'},
                verify=False, timeout=10,
            )
            apps = resp.json().get('results', []) if resp.ok else []
            app = next((a for a in apps if a.get('slug') == 'headlamp'), None)
            if app:
                self.print_status('OK', f"Headlamp application found in Authentik (slug={app['slug']})")
                self.results['oidc'].append(('authentik_app_exists', True, app['slug']))
                return True
            else:
                self.print_status('WARN', 'Headlamp application not yet provisioned in Authentik')
                self.results['oidc'].append(('authentik_app_exists', False, 'Not found'))
                return False
        except Exception as exc:
            self.print_status('WARN', f'Authentik API check skipped: {exc}')
            self.results['oidc'].append(('authentik_app_exists', False, str(exc)))
            return False

    def run_all_tests(self) -> bool:
        """Run all Headlamp integration tests"""
        print("\n" + "="*60)
        print("🧪 HEADLAMP SSO INTEGRATION TEST")
        print("="*60)
        print(f"Domain: {self.domain}")
        print(f"Namespace: {self.namespace}")
        print(f"Headlamp URL: {self.headlamp_url}")
        print(f"Authentik URL: {self.authentik_url}")
        print("="*60 + "\n")

        tests = [
            ('Deployment', self.test_headlamp_deployment),
            ('Pods', self.test_headlamp_pods),
            ('Service', self.test_headlamp_service),
            ('Ingress', self.test_headlamp_ingress),
            ('OIDC Configuration', self.test_oidc_secret),
            ('Authentik provisioner script', self.test_authentik_provisioner_import),
            ('Headlamp App in Authentik', self.test_headlamp_oidc_provisioned_in_authentik),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n--- {test_name} Test ---")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.print_status('ERROR', f'Test exception: {e}')
                failed += 1

        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        self.print_status('OK' if failed == 0 else 'ERROR', f'Passed: {passed}/{len(tests)}')
        self.print_status('ERROR' if failed > 0 else 'OK', f'Failed: {failed}/{len(tests)}')
        print("="*60 + "\n")

        return failed == 0


# ---------------------------------------------------------------------------
# pytest wrappers
#
# The checks above live on a class with an __init__, which pytest cannot collect
# directly. These wrappers expose each one as an individual test case. They shell
# out to kubectl, so they carry the `cluster` marker and are excluded from the
# default run; use `pytest -m cluster` against a live cluster.
# ---------------------------------------------------------------------------

_CLUSTER_CHECKS = sorted(n for n in vars(HeadlampSSOTester) if n.startswith('test_'))


@pytest.fixture(scope='module')
def headlamp_tester():
    return HeadlampSSOTester(domain=os.getenv('NOAH_DOMAIN', 'noah-infra.com'))


@pytest.mark.cluster
@pytest.mark.parametrize('check', _CLUSTER_CHECKS)
def test_headlamp_sso_check(headlamp_tester, check):
    assert getattr(headlamp_tester, check)(), f'{check} failed'


def main():
    """Main test entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Headlamp SSO integration')
    parser.add_argument('--domain', default='noah-infra.com', help='Domain name')
    args = parser.parse_args()

    tester = HeadlampSSOTester(domain=args.domain)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
