#!/usr/bin/env python3
"""
Nextcloud OIDC Application Setup for Authentik
Automatically configures Authentik OIDC provider for Nextcloud SSO integration
"""

import requests
import json
import os
import sys
from pathlib import Path

class AuthentikOIDCConfigurator:
    def __init__(self, authentik_url, admin_token):
        self.authentik_url = authentik_url.rstrip('/')
        self.admin_token = admin_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        })
    
    def create_nextcloud_provider(self):
        """Create OIDC provider for Nextcloud"""
        provider_data = {
            "name": "nextcloud-oidc",
            "authorization_flow": None,  # Will use default
            "property_mappings": [],
            "client_type": "confidential",
            "client_id": "nextcloud-oidc",
            "client_secret": self.generate_client_secret(),
            "redirect_uris": [
                "https://cloud.noah-infra.com/apps/user_oidc/code",
                "https://cloud.noah-infra.com/index.php/apps/user_oidc/code"
            ],
            "signing_alg": "RS256",
            "sub_mode": "hashed_user_id",
            "include_claims_in_id_token": True,
            "issuer_mode": "per_provider"
        }
        
        response = self.session.post(
            f"{self.authentik_url}/api/v3/providers/oauth2/",
            json=provider_data
        )
        
        if response.status_code == 201:
            print("✅ Nextcloud OIDC provider created successfully")
            return response.json()
        else:
            print(f"❌ Failed to create provider: {response.status_code}")
            print(response.text)
            return None
    
    def create_nextcloud_application(self, provider_pk):
        """Create Authentik application for Nextcloud"""
        app_data = {
            "name": "Nextcloud",
            "slug": "nextcloud",
            "provider": provider_pk,
            "meta_launch_url": "https://cloud.noah-infra.com",
            "meta_description": "Nextcloud file sharing and collaboration platform",
            "meta_publisher": "NOAH Infrastructure",
            "policy_engine_mode": "all",
            "group": None
        }
        
        response = self.session.post(
            f"{self.authentik_url}/api/v3/core/applications/",
            json=app_data
        )
        
        if response.status_code == 201:
            print("✅ Nextcloud application created successfully")
            return response.json()
        else:
            print(f"❌ Failed to create application: {response.status_code}")
            print(response.text)
            return None
    
    def generate_client_secret(self):
        """Generate a secure client secret"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))
    
    def setup_property_mappings(self):
        """Create property mappings for user attributes"""
        mappings = [
            {
                "name": "Nextcloud Groups",
                "expression": "return user.ak_groups.all()",
                "managed": "goauthentik.io/providers/oauth2/scope-groups"
            },
            {
                "name": "Nextcloud Email",  
                "expression": "return user.email",
                "managed": "goauthentik.io/providers/oauth2/scope-email"
            },
            {
                "name": "Nextcloud Profile",
                "expression": "return {'name': user.name, 'preferred_username': user.username}",
                "managed": "goauthentik.io/providers/oauth2/scope-profile"
            }
        ]
        
        created_mappings = []
        for mapping in mappings:
            response = self.session.post(
                f"{self.authentik_url}/api/v3/propertymappings/scope/",
                json=mapping
            )
            if response.status_code == 201:
                created_mappings.append(response.json())
                print(f"✅ Created mapping: {mapping['name']}")
            else:
                print(f"⚠️  Mapping may already exist: {mapping['name']}")
        
        return created_mappings

def main():
    """Main configuration function"""
    if len(sys.argv) < 3:
        print("Usage: python configure_nextcloud_oidc.py <authentik_url> <admin_token>")
        print("Example: python configure_nextcloud_oidc.py https://auth.noah-infra.com ak_admin_token_here")
        sys.exit(1)
    
    authentik_url = sys.argv[1]
    admin_token = sys.argv[2]
    
    configurator = AuthentikOIDCConfigurator(authentik_url, admin_token)
    
    print("🔧 Configuring Nextcloud OIDC integration with Authentik...")
    
    # Setup property mappings
    print("📋 Setting up property mappings...")
    configurator.setup_property_mappings()
    
    # Create OIDC provider
    print("🔐 Creating OIDC provider...")
    provider = configurator.create_nextcloud_provider()
    
    if provider:
        # Create application
        print("📱 Creating Nextcloud application...")
        app = configurator.create_nextcloud_application(provider['pk'])
        
        if app:
            print("\n🎉 Nextcloud OIDC configuration completed!")
            print("="*50)
            print(f"Provider ID: {provider['client_id']}")
            print(f"Client Secret: {provider['client_secret']}")
            print(f"Application URL: {authentik_url}/if/admin/#/core/applications")
            print("="*50)
            print("\n💡 Next steps:")
            print("1. The OIDC configuration is automatically applied to Nextcloud")
            print("2. Users can now log in using 'Log in with NOAH SSO' button")
            print("3. Access Nextcloud at: https://cloud.noah-infra.com")
        else:
            print("❌ Failed to create Nextcloud application")
            sys.exit(1)
    else:
        print("❌ Failed to create OIDC provider")
        sys.exit(1)

if __name__ == "__main__":
    main()
