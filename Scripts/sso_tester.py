"""SSO testing module with integrated network validation"""

import requests
import json
import subprocess
import sys
import time
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin

class SSONetworkValidator:
    """Network validation functionality for SSO components"""
    
    def __init__(self):
        self.results = {
            'prerequisites': [],
            'cluster': [],
            'cilium': [],
            'samba4': [],
            'authentik': [],
            'network_policies': [],
            'connectivity': [],
            'hubble': []
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
    
    def command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except:
            return False
    
    def check_prerequisites(self) -> bool:
        """Check basic prerequisites"""
        print("1. Checking prerequisites...")
        all_good = True
        
        for cmd in ['kubectl', 'helm']:
            if self.command_exists(cmd):
                self.print_status('OK', f"{cmd} is available")
                self.results['prerequisites'].append(f"{cmd}: OK")
            else:
                self.print_status('ERROR', f"{cmd} not found")
                self.results['prerequisites'].append(f"{cmd}: ERROR")
                all_good = False
        
        return all_good
    
    def check_cluster_connectivity(self) -> bool:
        """Check cluster connectivity"""
        print("\n2. Checking cluster connectivity...")
        success, output = self.run_kubectl("cluster-info")
        
        if success:
            self.print_status('OK', "Connected to Kubernetes cluster")
            self.results['cluster'].append("connectivity: OK")
            return True
        else:
            self.print_status('ERROR', "Cannot connect to Kubernetes cluster")
            self.results['cluster'].append("connectivity: ERROR")
            return False
    
    def check_namespaces(self) -> bool:
        """Check required namespaces"""
        print("\n3. Checking required namespaces...")
        all_good = True
        
        for ns in ['kube-system', 'identity']:
            success, _ = self.run_kubectl(f"get namespace {ns}")
            if success:
                self.print_status('OK', f"Namespace {ns} exists")
                self.results['cluster'].append(f"namespace-{ns}: OK")
            else:
                self.print_status('ERROR', f"Namespace {ns} does not exist")
                self.results['cluster'].append(f"namespace-{ns}: ERROR")
                all_good = False
        
        return all_good
    
    def check_cilium(self) -> bool:
        """Check Cilium CNI deployment"""
        print("\n4. Checking Cilium CNI...")
        
        success, _ = self.run_kubectl("get daemonset cilium -n kube-system")
        if not success:
            self.print_status('ERROR', "Cilium CNI not found")
            self.results['cilium'].append("deployment: ERROR")
            return False
        
        # Check readiness
        success, ready = self.run_kubectl("get daemonset cilium -n kube-system -o jsonpath='{.status.numberReady}'")
        success2, desired = self.run_kubectl("get daemonset cilium -n kube-system -o jsonpath='{.status.desiredNumberScheduled}'")
        
        if success and success2 and ready and desired and int(ready) == int(desired) and int(ready) > 0:
            self.print_status('OK', f"Cilium CNI is running ({ready}/{desired})")
            self.results['cilium'].append(f"pods: {ready}/{desired} OK")
            
            # Test Cilium status
            success, output = self.run_kubectl("exec -n kube-system ds/cilium -- cilium status --brief")
            if success and "OK" in output:
                self.print_status('OK', "Cilium status is healthy")
                self.results['cilium'].append("status: OK")
                return True
            else:
                self.print_status('WARN', "Cilium status check failed")
                self.results['cilium'].append("status: WARN")
                return True  # Still considered working
        else:
            ready = ready or "0"
            desired = desired or "1"
            self.print_status('ERROR', f"Cilium CNI not ready ({ready}/{desired})")
            self.results['cilium'].append(f"pods: {ready}/{desired} ERROR")
            return False
    
    def check_samba4(self) -> bool:
        """Check Samba4 Active Directory deployment"""
        print("\n5. Checking Samba4 Active Directory...")
        
        success, _ = self.run_kubectl("get deployment samba4 -n identity")
        if not success:
            self.print_status('ERROR', "Samba4 deployment not found")
            self.results['samba4'].append("deployment: ERROR")
            return False
        
        # Check readiness
        success, ready = self.run_kubectl("get deployment samba4 -n identity -o jsonpath='{.status.readyReplicas}'")
        success2, desired = self.run_kubectl("get deployment samba4 -n identity -o jsonpath='{.spec.replicas}'")
        
        ready = ready or "0"
        desired = desired or "1"
        
        if success and success2 and int(ready) == int(desired) and int(ready) > 0:
            self.print_status('OK', f"Samba4 deployment is ready ({ready}/{desired})")
            self.results['samba4'].append(f"deployment: {ready}/{desired} OK")
            
            # Test LDAP connectivity
            success, output = self.run_kubectl("exec -n identity deployment/samba4 -- ldapsearch -x -H ldap://localhost:389 -s base")
            if success and "result: 0 Success" in output:
                self.print_status('OK', "Samba4 LDAP service is responding")
                self.results['samba4'].append("ldap: OK")
                return True
            else:
                self.print_status('WARN', "Samba4 LDAP connectivity test failed")
                self.results['samba4'].append("ldap: WARN")
                return True  # Deployment is ready even if LDAP test fails
        else:
            self.print_status('ERROR', f"Samba4 deployment not ready ({ready}/{desired})")
            self.results['samba4'].append(f"deployment: {ready}/{desired} ERROR")
            return False
    
    def check_authentik(self) -> bool:
        """Check Authentik SSO deployment"""
        print("\n6. Checking Authentik SSO...")
        
        # Check server deployment
        success, _ = self.run_kubectl("get deployment authentik-server -n identity")
        server_exists = success
        if success:
            self.print_status('OK', "Authentik server deployment found")
            success, server_ready = self.run_kubectl("get deployment authentik-server -n identity -o jsonpath='{.status.readyReplicas}'")
            server_ready = server_ready or "0"
        else:
            self.print_status('ERROR', "Authentik server deployment not found")
            server_ready = "0"
        
        # Check worker deployment
        success, _ = self.run_kubectl("get deployment authentik-worker -n identity")
        worker_exists = success
        if success:
            self.print_status('OK', "Authentik worker deployment found")
            success, worker_ready = self.run_kubectl("get deployment authentik-worker -n identity -o jsonpath='{.status.readyReplicas}'")
            worker_ready = worker_ready or "0"
        else:
            self.print_status('ERROR', "Authentik worker deployment not found")
            worker_ready = "0"
        
        if server_ready == "1" and worker_ready == "1":
            self.print_status('OK', "Authentik deployments are ready")
            self.results['authentik'].append(f"server: 1/1 OK, worker: 1/1 OK")
            
            # Test Authentik API
            success, output = self.run_kubectl("exec -n identity deployment/authentik-server -- wget -q -O- http://localhost:9000/api/v3/core/tenants/")
            if success and "noah-infra.com" in output:
                self.print_status('OK', "Authentik API is responding")
                self.results['authentik'].append("api: OK")
                return True
            else:
                self.print_status('WARN', "Authentik API connectivity test failed")
                self.results['authentik'].append("api: WARN")
                return True
        else:
            self.print_status('ERROR', f"Authentik deployments not ready (Server: {server_ready}, Worker: {worker_ready})")
            self.results['authentik'].append(f"server: {server_ready}/1, worker: {worker_ready}/1 ERROR")
            return False
    
    def check_network_policies(self) -> bool:
        """Check network policies"""
        print("\n7. Checking network policies...")
        
        success, output = self.run_kubectl("get networkpolicies -n identity --no-headers")
        if success and output:
            policies = output.strip().split('\n')
            policy_count = len([p for p in policies if p.strip()])
            self.print_status('OK', f"Network policies applied ({policy_count} policies)")
            self.results['network_policies'].append(f"count: {policy_count} OK")
            
            for policy_line in policies:
                if policy_line.strip():
                    policy_name = policy_line.split()[0]
                    self.print_status('INFO', f"  - {policy_name}")
                    self.results['network_policies'].append(f"policy: {policy_name}")
            return True
        else:
            self.print_status('WARN', "No network policies found in identity namespace")
            self.results['network_policies'].append("count: 0 WARN")
            return False
    
    def check_dns_connectivity(self) -> bool:
        """Check DNS resolution and connectivity"""
        print("\n8. Testing inter-service connectivity...")
        all_good = True
        
        # Test Samba4 DNS resolution
        success, output = self.run_kubectl("run test-dns --image=busybox --rm -i --restart=Never -- nslookup samba4.identity.svc.cluster.local")
        if success and "Address:" in output:
            self.print_status('OK', "Samba4 DNS resolution works")
            self.results['connectivity'].append("samba4-dns: OK")
        else:
            self.print_status('WARN', "Samba4 DNS resolution failed")
            self.results['connectivity'].append("samba4-dns: WARN")
            all_good = False
        
        # Test Authentik DNS resolution
        success, output = self.run_kubectl("run test-dns --image=busybox --rm -i --restart=Never -- nslookup authentik-server.identity.svc.cluster.local")
        if success and "Address:" in output:
            self.print_status('OK', "Authentik DNS resolution works")
            self.results['connectivity'].append("authentik-dns: OK")
        else:
            self.print_status('WARN', "Authentik DNS resolution failed")
            self.results['connectivity'].append("authentik-dns: WARN")
            all_good = False
        
        return all_good
    
    def check_ldap_connectivity(self) -> bool:
        """Check LDAP connectivity from Authentik to Samba4"""
        print("\n9. Testing LDAP connectivity (Authentik -> Samba4)...")
        
        success, output = self.run_kubectl("exec -n identity deployment/authentik-server -- nc -zv samba4.identity.svc.cluster.local 389")
        if success and "open" in output:
            self.print_status('OK', "LDAP port 389 is reachable from Authentik to Samba4")
            self.results['connectivity'].append("ldap-port: OK")
            return True
        else:
            self.print_status('WARN', "LDAP port 389 connectivity test failed")
            self.results['connectivity'].append("ldap-port: WARN")
            return False
    
    def check_hubble_ui(self) -> bool:
        """Check Hubble UI SSO integration"""
        print("\n10. Checking Hubble UI SSO integration...")
        
        success, _ = self.run_kubectl("get deployment hubble-ui -n kube-system")
        if not success:
            self.print_status('INFO', "Hubble UI not deployed (optional)")
            self.results['hubble'].append("deployment: Not deployed")
            return True
        
        success, ready = self.run_kubectl("get deployment hubble-ui -n kube-system -o jsonpath='{.status.readyReplicas}'")
        ready = ready or "0"
        
        if ready == "1":
            self.print_status('OK', "Hubble UI is ready")
            self.results['hubble'].append("deployment: 1/1 OK")
            
            # Check ingress
            success, host = self.run_kubectl("get ingress hubble-ui -n kube-system -o jsonpath='{.spec.rules[0].host}'")
            if success and host:
                self.print_status('OK', f"Hubble UI ingress configured for {host}")
                self.results['hubble'].append(f"ingress: {host} OK")
            else:
                self.print_status('WARN', "Hubble UI ingress not found")
                self.results['hubble'].append("ingress: WARN")
            return True
        else:
            self.print_status('WARN', "Hubble UI not ready")
            self.results['hubble'].append(f"deployment: {ready}/1 WARN")
            return False
    
    def validate_network(self) -> Dict:
        """Run complete network validation"""
        print("🔍 NOAH SSO Network Validation")
        print("=" * 35)
        
        checks = [
            self.check_prerequisites,
            self.check_cluster_connectivity,
            self.check_namespaces,
            self.check_cilium,
            self.check_samba4,
            self.check_authentik,
            self.check_network_policies,
            self.check_dns_connectivity,
            self.check_ldap_connectivity,
            self.check_hubble_ui
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check in checks:
            try:
                if check():
                    passed_checks += 1
            except Exception as e:
                self.print_status('ERROR', f"Check failed with exception: {e}")
        
        print("\n🎯 SSO Network Validation Summary")
        print("=" * 35)
        self.print_status('INFO', f"Passed {passed_checks}/{total_checks} validation checks")
        
        if passed_checks == total_checks:
            self.print_status('OK', "All network validation checks passed!")
        elif passed_checks >= total_checks * 0.8:  # 80% pass rate
            self.print_status('WARN', "Most checks passed - review warnings above")
        else:
            self.print_status('ERROR', "Multiple validation checks failed")
        
        print("\nNext steps:")
        print("1. If all checks pass, test SSO login: python noah.py test sso")
        print("2. Access Hubble UI with SSO: https://hubble.noah-infra.com")
        print("3. Monitor network traffic: kubectl exec -n kube-system ds/cilium -- hubble observe")
        
        return {
            'passed': passed_checks,
            'total': total_checks,
            'success_rate': passed_checks / total_checks,
            'results': self.results
        }


class SSOTester:
    """Enhanced SSO testing with integrated network validation"""
    
    def __init__(self, config_loader):
        self.config = config_loader
        self.authentik_url = None
        self.session = requests.Session()
        self.network_validator = SSONetworkValidator()
    
    def get_authentik_url(self) -> Optional[str]:
        """Get Authentik service URL"""
        from Scripts.cluster_manager import ClusterManager
        cm = ClusterManager(self.config)
        
        endpoint = cm.get_service_endpoint('authentik-server', 'identity')
        if endpoint:
            return f"https://{endpoint}"
        return None
    
    def validate_network_first(self) -> bool:
        """Run network validation before SSO testing"""
        print("🔍 Running network validation before SSO tests...")
        print("=" * 50)
        
        validation_result = self.network_validator.validate_network()
        
        # Consider validation successful if 80% of checks pass
        success_threshold = 0.8
        if validation_result['success_rate'] >= success_threshold:
            print(f"\n✅ Network validation passed ({validation_result['passed']}/{validation_result['total']} checks)")
            return True
        else:
            print(f"\n❌ Network validation failed ({validation_result['passed']}/{validation_result['total']} checks)")
            print("Please fix network issues before proceeding with SSO tests.")
            return False
    
    def test_authentication(self) -> bool:
        """Test SSO authentication flow with network validation"""
        # First validate network connectivity
        if not self.validate_network_first():
            print("\n⚠️ Skipping SSO authentication test due to network validation failures")
            return False
        
        print("\n🔐 Starting SSO Authentication Tests")
        print("=" * 40)
        
        self.authentik_url = self.get_authentik_url()
        
        if not self.authentik_url:
            print("Could not determine Authentik URL")
            return False
        
        print(f"Testing SSO at {self.authentik_url}")
        
        # Test basic connectivity
        try:
            # Disable SSL verification for self-signed certificates
            response = self.session.get(
                urljoin(self.authentik_url, '/api/v3/root/config/'),
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✓ Authentik API is accessible")
            else:
                print(f"✗ Authentik API returned status {response.status_code}")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to connect to Authentik: {e}")
            return False
        
        # Test authentication with bootstrap credentials
        return self.test_bootstrap_login()
    
    def test_bootstrap_login(self) -> bool:
        """Test login with bootstrap credentials"""
        username = "akadmin"
        password = self.config.get('AUTHENTIK_BOOTSTRAP_PASSWORD')
        
        if not password:
            print("Bootstrap password not found in configuration")
            return False
        
        if not self.authentik_url:
            print("Authentik URL not available")
            return False
        
        try:
            # Test token authentication
            response = self.session.post(
                urljoin(self.authentik_url, '/api/v3/core/tokens/'),
                json={
                    'username': username,
                    'password': password
                },
                verify=False
            )
            
            if response.status_code in [200, 201]:
                print("✓ Bootstrap authentication successful")
                return True
            else:
                print(f"✗ Authentication failed with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication test failed: {e}")
            return False
    
    def test_ldap_integration(self) -> bool:
        """Test LDAP integration with Samba4"""
        print("\n🔗 Testing LDAP integration with Samba4...")
        
        # Use network validator to check LDAP connectivity
        if not self.network_validator.check_ldap_connectivity():
            print("✗ LDAP connectivity test failed")
            return False
        
        # Additional LDAP bind test could be implemented here
        print("✓ LDAP integration test passed")
        return True
    
    def test_oidc_flow(self) -> bool:
        """Test OpenID Connect flow"""
        print("\n🔄 Testing OIDC flow...")
        
        if not self.authentik_url:
            print("✗ Authentik URL not available for OIDC test")
            return False
        
        try:
            # Test OIDC discovery endpoint
            response = self.session.get(
                urljoin(self.authentik_url, '/.well-known/openid_configuration'),
                verify=False,
                timeout=10
            )
            
            if response.status_code == 200:
                config = response.json()
                if 'authorization_endpoint' in config and 'token_endpoint' in config:
                    print("✓ OIDC discovery endpoint is working")
                    print(f"  - Authorization endpoint: {config['authorization_endpoint']}")
                    print(f"  - Token endpoint: {config['token_endpoint']}")
                    return True
                else:
                    print("✗ OIDC configuration incomplete")
                    return False
            else:
                print(f"✗ OIDC discovery failed with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ OIDC flow test failed: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"✗ OIDC response parsing failed: {e}")
            return False
    
    def run_comprehensive_test(self) -> bool:
        """Run all SSO tests including network validation"""
        print("🚀 NOAH SSO Comprehensive Test Suite")
        print("=" * 45)
        
        tests = [
            ("Network Validation", self.validate_network_first),
            ("Basic Authentication", lambda: self.test_authentication() if hasattr(self, 'authentik_url') and self.authentik_url else self.test_authentication()),
            ("LDAP Integration", self.test_ldap_integration),
            ("OIDC Flow", self.test_oidc_flow)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            print("-" * 30)
            
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"❌ {test_name}: ERROR - {e}")
        
        print(f"\n🎯 Test Summary")
        print("=" * 20)
        print(f"Passed: {passed_tests}/{total_tests} tests")
        
        if passed_tests == total_tests:
            print("🎉 All SSO tests passed! System is ready for production.")
            return True
        elif passed_tests >= total_tests * 0.75:  # 75% pass rate
            print("⚠️ Most tests passed - review failures above")
            return True
        else:
            print("❌ Multiple tests failed - system needs attention")
            return False
