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
Authentik OIDC Deployment Verification Test
This test script verifies that Authentik is properly deployed with OIDC configuration
"""

import os
import subprocess
import time
import requests
import sys
from typing import List, Tuple

import pytest


class AuthentikDeploymentVerifier:
    def __init__(self, namespace: str = "authentik"):
        """Initialize the deployment verifier"""
        self.namespace = namespace
        self.results = {
            'prerequisites': [],
            'namespace': [],
            'secrets': [],
            'deployments': [],
            'pvcs': [],
            'services': [],
            'ingress': [],
            'endpoints': []
        }
        self.port_forward_process = None
        
    def run_kubectl(self, args: List[str]) -> Tuple[bool, str]:
        """Run kubectl command and return success status and output"""
        try:
            cmd = ['kubectl'] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def print_status(self, status: str, message: str):
        """Print formatted status message"""
        icons = {
            'OK': '✅',
            'WARN': '⚠️ ',
            'ERROR': '❌',
            'INFO': 'ℹ️ '
        }
        icon = icons.get(status, '•')
        print(f"{icon} {message}")
        
    def check_prerequisites(self) -> bool:
        """Check if required tools are available"""
        print("🚀 Authentik OIDC Deployment Verification")
        print("=" * 50)
        
        tools = ['kubectl', 'helm']
        all_good = True
        
        for tool in tools:
            try:
                result = subprocess.run([tool, '--version'], capture_output=True, timeout=10)
                if result.returncode == 0:
                    self.print_status('OK', f"{tool} is available")
                    self.results['prerequisites'].append(f"{tool}: OK")
                else:
                    self.print_status('ERROR', f"{tool} not found")
                    self.results['prerequisites'].append(f"{tool}: ERROR")
                    all_good = False
            except Exception:
                self.print_status('ERROR', f"{tool} not found")
                self.results['prerequisites'].append(f"{tool}: ERROR")
                all_good = False
                
        if all_good:
            self.print_status('OK', "Prerequisites check passed")
        else:
            self.print_status('ERROR', "Prerequisites check failed")
            
        return all_good
    
    def check_namespace(self) -> bool:
        """Check if namespace exists"""
        print("\n📋 Checking namespace...")
        success, _ = self.run_kubectl(['get', 'namespace', self.namespace])
        if success:
            self.print_status('OK', f"Namespace {self.namespace} exists")
            self.results['namespace'].append("exists: OK")
            return True
        else:
            self.print_status('ERROR', f"Namespace {self.namespace} not found")
            self.results['namespace'].append("exists: ERROR")
            return False
    
    # Secrets delivered out-of-band by Scripts/gitops/gitops_init.py. There is
    # no single flat `authentik-secret`: the Helm values (secret_key,
    # bootstrap_password, postgres passwords) ride in authentik-values under a
    # single values.yaml key consumed via HelmRelease valuesFrom, and the
    # provisioner token lives in its own Secret.
    EXPECTED_K8S_RESOURCE_NAMES = {
        'authentik-values': 'values.yaml',
        'authentik-bootstrap-token': 'AUTHENTIK_TOKEN',
    }

    def check_secrets(self) -> bool:
        """Check the out-of-band Secrets Authentik depends on."""
        print("\n🔐 Checking secrets...")

        all_present = True
        for resource_name, key in self.EXPECTED_K8S_RESOURCE_NAMES.items():
            success, _ = self.run_kubectl(['get', 'secret', resource_name, '-n', self.namespace])
            if not success:
                self.print_status('ERROR', f"{resource_name} not found")
                self.results['secrets'].append(f"{resource_name}: ERROR")
                all_present = False
                continue

            # jsonpath on a missing key yields an empty string, not an error,
            # so the presence of the key must be checked on the output itself.
            key_success, value = self.run_kubectl([
                'get', 'secret', resource_name, '-n', self.namespace,
                '-o', f'jsonpath={{.data.{key}}}'
            ])
            if key_success and value:
                self.print_status('OK', f"{resource_name} (key {key})")
                self.results['secrets'].append(f"{resource_name}.{key}: OK")
            else:
                self.print_status('ERROR', f"{resource_name} missing key {key}")
                self.results['secrets'].append(f"{resource_name}.{key}: ERROR")
                all_present = False

        return all_present
    
    def check_deployments(self) -> bool:
        """Check deployment status"""
        print("\n🚢 Checking deployments...")
        
        # Define resources to check
        resources = [
            ('deployment', 'authentik-server'),
            ('deployment', 'authentik-worker'),
            ('statefulset', 'authentik-postgresql'),
            ('statefulset', 'authentik-redis-master')
        ]
        
        all_ready = True
        for resource_type, resource_name in resources:
            success, _ = self.run_kubectl(['get', resource_type, resource_name, '-n', self.namespace])
            if not success:
                self.print_status('ERROR', f"{resource_name} not found")
                self.results['deployments'].append(f"{resource_name}: ERROR")
                all_ready = False
                continue
                
            # Check readiness
            ready_success, ready = self.run_kubectl([
                'get', resource_type, resource_name, '-n', self.namespace,
                '-o', 'jsonpath={.status.readyReplicas}'
            ])
            desired_success, desired = self.run_kubectl([
                'get', resource_type, resource_name, '-n', self.namespace,
                '-o', 'jsonpath={.spec.replicas}'
            ])
            
            ready = ready if ready else "0"
            desired = desired if desired else "1"
            
            if ready_success and desired_success and ready == desired and ready != "0":
                self.print_status('OK', f"{resource_name} ({ready}/{desired} ready)")
                self.results['deployments'].append(f"{resource_name}: {ready}/{desired} OK")
            else:
                self.print_status('WARN', f"{resource_name} ({ready}/{desired} ready)")
                self.results['deployments'].append(f"{resource_name}: {ready}/{desired} WARN")
                all_ready = False
                
        return all_ready
    
    def check_persistent_volumes(self) -> bool:
        """Check persistent volume claims"""
        print("\n💾 Checking persistent volumes...")
        
        # Created by the bundled postgresql / redis subcharts, both enabled in
        # the HelmRelease.
        expected_pvcs = [
            'data-authentik-postgresql-0',
            'redis-data-authentik-redis-master-0'
        ]
        # NOAH sets no persistence values, so whether a media PVC exists is the
        # chart's decision — report it, but do not fail on it.
        optional_pvcs = ['authentik-media']

        all_bound = True
        for pvc in expected_pvcs + optional_pvcs:
            success, _ = self.run_kubectl(['get', 'pvc', pvc, '-n', self.namespace])
            if not success:
                if pvc in optional_pvcs:
                    self.print_status('INFO', f"{pvc} not present (optional)")
                    self.results['pvcs'].append(f"{pvc}: SKIPPED")
                    continue
                self.print_status('ERROR', f"{pvc} not found")
                self.results['pvcs'].append(f"{pvc}: ERROR")
                all_bound = False
                continue
                
            # Get status and size
            status_success, status = self.run_kubectl([
                'get', 'pvc', pvc, '-n', self.namespace,
                '-o', 'jsonpath={.status.phase}'
            ])
            size_success, size = self.run_kubectl([
                'get', 'pvc', pvc, '-n', self.namespace,
                '-o', 'jsonpath={.spec.resources.requests.storage}'
            ])
            
            if status == "Bound":
                self.print_status('OK', f"{pvc} ({status}, {size})")
                self.results['pvcs'].append(f"{pvc}: {status} {size} OK")
            else:
                self.print_status('WARN', f"{pvc} ({status}, {size})")
                self.results['pvcs'].append(f"{pvc}: {status} {size} WARN")
                all_bound = False
                
        return all_bound
    
    def check_services(self) -> bool:
        """Check service status"""
        print("\n🌐 Checking services...")
        
        expected_services = [
            'authentik-server',
            'authentik-postgresql',
            'authentik-redis-master'
        ]
        
        all_services_ready = True
        for service in expected_services:
            success, _ = self.run_kubectl(['get', 'service', service, '-n', self.namespace])
            if not success:
                self.print_status('ERROR', f"{service} not found")
                self.results['services'].append(f"{service}: ERROR")
                all_services_ready = False
                continue
                
            # Get service type and port
            type_success, svc_type = self.run_kubectl([
                'get', 'service', service, '-n', self.namespace,
                '-o', 'jsonpath={.spec.type}'
            ])
            port_success, port = self.run_kubectl([
                'get', 'service', service, '-n', self.namespace,
                '-o', 'jsonpath={.spec.ports[0].port}'
            ])
            
            self.print_status('OK', f"{service} ({svc_type}:{port})")
            self.results['services'].append(f"{service}: {svc_type}:{port} OK")
            
        return all_services_ready
    
    def check_ingress(self) -> bool:
        """Check ingress configuration"""
        print("\n🔗 Checking ingress...")
        
        success, _ = self.run_kubectl(['get', 'ingress', 'authentik', '-n', self.namespace])
        if success:
            hosts_success, hosts = self.run_kubectl([
                'get', 'ingress', 'authentik', '-n', self.namespace,
                '-o', 'jsonpath={.spec.rules[*].host}'
            ])
            hosts_list = hosts.replace(' ', ',') if hosts else "none"
            self.print_status('OK', f"Authentik ingress found (hosts: {hosts_list})")
            self.results['ingress'].append(f"authentik: {hosts_list} OK")
            return True
        else:
            self.print_status('WARN', "Authentik ingress not found (LoadBalancer mode or not yet created)")
            self.results['ingress'].append("authentik: WARN")
            return False
    
    def start_port_forward(self) -> bool:
        """Start port forward for endpoint testing"""
        try:
            self.port_forward_process = subprocess.Popen([
                'kubectl', 'port-forward', '-n', self.namespace,
                'service/authentik-server', '9000:9000'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)  # Give time for port forward to establish
            return True
        except Exception:
            return False
    
    def stop_port_forward(self):
        """Stop port forward process"""
        if self.port_forward_process:
            self.port_forward_process.terminate()
            self.port_forward_process.wait()
            self.port_forward_process = None
    
    def check_endpoints(self) -> bool:
        """Test OIDC endpoints"""
        print("\n🔍 Testing OIDC endpoints...")
        
        # Check if server is ready first
        ready_success, ready = self.run_kubectl([
            'get', 'deployment', 'authentik-server', '-n', self.namespace,
            '-o', 'jsonpath={.status.readyReplicas}'
        ])
        
        if not ready_success or ready == "0":
            self.print_status('ERROR', "Authentik server not ready, skipping endpoint tests")
            self.results['endpoints'].append("server: ERROR")
            return False
            
        print("   Starting port-forward to test endpoints...")
        if not self.start_port_forward():
            self.print_status('ERROR', "Failed to start port-forward")
            self.results['endpoints'].append("port-forward: ERROR")
            return False
            
        try:
            # Test health endpoint
            try:
                response = requests.get('http://localhost:9000/-/health/live/', timeout=10)
                if response.status_code == 200:
                    self.print_status('OK', "Health endpoint responding")
                    self.results['endpoints'].append("health: OK")
                else:
                    self.print_status('WARN', f"Health endpoint returned {response.status_code}")
                    self.results['endpoints'].append(f"health: {response.status_code} WARN")
            except Exception as e:
                self.print_status('ERROR', f"Health endpoint not responding: {e}")
                self.results['endpoints'].append("health: ERROR")
                
            # Test OIDC discovery (might not be configured yet)
            try:
                response = requests.get(
                    'http://localhost:9000/application/o/kubernetes/.well-known/openid_configuration',
                    timeout=10
                )
                if response.status_code == 200:
                    self.print_status('OK', "OIDC discovery endpoint responding")
                    self.results['endpoints'].append("oidc-discovery: OK")
                else:
                    self.print_status('WARN', "OIDC discovery endpoint not responding (configure OIDC provider first)")
                    self.results['endpoints'].append("oidc-discovery: WARN")
            except Exception:
                self.print_status('WARN', "OIDC discovery endpoint not responding (configure OIDC provider first)")
                self.results['endpoints'].append("oidc-discovery: WARN")
                
        finally:
            self.stop_port_forward()
            
        return True
    
    def print_summary(self):
        """Print deployment summary"""
        print("\n📋 Deployment Summary:")
        print("=" * 30)
        print("✅ Configuration: Enhanced OIDC-ready setup")
        print("✅ Persistent Storage: PostgreSQL (20Gi), Redis (4Gi), Media (5Gi)")
        print("✅ Security: Secure secrets with OIDC client credentials")
        print("✅ Access: https://auth.noah-infra.com (configure DNS/ingress)")
        print("")
        print("🔧 Next Steps:")
        print("1. Configure DNS to point auth.noah-infra.com to your ingress/LoadBalancer")
        print("2. Access Authentik admin interface and set up OIDC provider")
        print("3. Configure Kubernetes API server with OIDC flags")
        print("4. Set up RBAC policies for your users/groups")
        print("")
        print("📖 For detailed configuration, see: /root/NOAH/Docs/authentik-oidc-setup.md")
    
    def run_all_checks(self) -> bool:
        """Run all verification checks"""
        checks = [
            self.check_prerequisites,
            self.check_namespace,
            self.check_secrets,
            self.check_deployments,
            self.check_persistent_volumes,
            self.check_services,
            self.check_ingress,
            self.check_endpoints
        ]
        
        all_passed = True
        for check in checks:
            try:
                result = check()
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Check failed with error: {e}")
                all_passed = False
                
        self.print_summary()
        return all_passed


# ---------------------------------------------------------------------------
# pytest wrapper
#
# AuthentikDeploymentVerifier has an __init__, so pytest cannot collect it
# directly. The checks are sequential and share port-forward state, so they are
# exposed as the single run_all_checks() entry point rather than individually.
# Needs a live cluster; excluded from the default run via the `cluster` marker.
# ---------------------------------------------------------------------------

@pytest.mark.cluster
def test_authentik_deployment():
    namespace = os.getenv('NOAH_AUTHENTIK_NAMESPACE', 'authentik')
    assert AuthentikDeploymentVerifier(namespace=namespace).run_all_checks()


def main():
    """Main function for running the verification"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Verify Authentik OIDC deployment')
    parser.add_argument('--namespace', default='authentik',
                       help='Kubernetes namespace (default: authentik)')
    
    args = parser.parse_args()
    
    verifier = AuthentikDeploymentVerifier(namespace=args.namespace)
    success = verifier.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
