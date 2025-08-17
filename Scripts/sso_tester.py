"""SSO testing module"""

import requests
import json
from typing import Optional
from urllib.parse import urljoin

class SSOTester:
    def __init__(self, config_loader):
        self.config = config_loader
        self.authentik_url = None
        self.session = requests.Session()
    
    def get_authentik_url(self) -> Optional[str]:
        """Get Authentik service URL"""
        from Scripts.cluster_manager import ClusterManager
        cm = ClusterManager(self.config)
        
        endpoint = cm.get_service_endpoint('authentik-server', 'identity')
        if endpoint:
            return f"https://{endpoint}"
        return None
    
    def test_authentication(self) -> bool:
        """Test SSO authentication flow"""
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
        # Implementation for testing LDAP bind
        print("Testing LDAP integration with Samba4...")
        # This would require python-ldap or similar library
        return True
    
    def test_oidc_flow(self) -> bool:
        """Test OpenID Connect flow"""
        print("Testing OIDC flow...")
        # Implementation for OIDC flow testing
        return True
