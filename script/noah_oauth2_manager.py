#!/usr/bin/env python3
"""
NOAH OAuth2 Management Module

This module handles OAuth2 proxy configuration, secret management,
and Keycloak realm setup. Consolidates oauth2-related shell scripts.
"""

import subprocess
import time
import json
import base64
import secrets
import logging
import requests
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NoahOAuth2Manager:
    """OAuth2 configuration and management for NOAH"""
    
    def __init__(self, namespace: str = "noah-namespace", keycloak_service: str = None):
        self.namespace = namespace
        self.keycloak_service = keycloak_service or f"noah-keycloak"
        self.keycloak_url = f"http://{self.keycloak_service}:8080"
        self.realm_name = "noah"
        self.client_id = "oauth2-proxy"
    
    def run_kubectl(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run kubectl command"""
        full_cmd = ["kubectl"] + cmd
        try:
            result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
    
    def get_oauth2_deployment_name(self) -> Optional[str]:
        """Get the actual OAuth2-proxy deployment name"""
        cmd = ["get", "deployments", "-n", self.namespace, "-o", "name"]
        exit_code, stdout, stderr = self.run_kubectl(cmd)
        
        if exit_code == 0:
            for line in stdout.strip().split('\n'):
                if 'oauth2-proxy' in line:
                    # Extract deployment name from "deployment.apps/noah-noah-chart-oauth2-proxy"
                    return line.split('/')[-1]
        
        logger.warning(f"Could not find OAuth2-proxy deployment in namespace {self.namespace}")
        return None
    
    def generate_oauth2_secrets(self) -> Dict[str, str]:
        """Generate OAuth2 secrets with proper entropy"""
        logger.info("Generating OAuth2 secrets...")
        
        # Generate 32-character cookie secret (required by oauth2-proxy)
        cookie_secret = secrets.token_hex(16)
        
        # Generate 64-character client secret for Keycloak
        client_secret = secrets.token_hex(32)
        
        return {
            'cookie-secret': cookie_secret,
            'client-secret': client_secret
        }
    
    def create_or_update_k8s_secret(self, secrets_data: Dict[str, str], secret_name: str = None) -> bool:
        """Create or update Kubernetes secret"""
        if not secret_name:
            secret_name = "oauth2-proxy-secrets"
        
        logger.info(f"Creating/updating secret {secret_name}...")
        
        # Check if secret exists
        check_cmd = ["get", "secret", secret_name, "-n", self.namespace]
        exit_code, _, _ = self.run_kubectl(check_cmd)
        
        # Prepare secret data
        secret_args = []
        for key, value in secrets_data.items():
            secret_args.extend([f"--from-literal={key}={value}"])
        
        if exit_code == 0:
            # Secret exists, delete it first
            delete_cmd = ["delete", "secret", secret_name, "-n", self.namespace]
            self.run_kubectl(delete_cmd)
        
        # Create new secret
        create_cmd = [
            "create", "secret", "generic", secret_name,
            "--namespace", self.namespace
        ] + secret_args
        
        exit_code, stdout, stderr = self.run_kubectl(create_cmd)
        
        if exit_code == 0:
            logger.info(f"✅ Secret {secret_name} created successfully")
            return True
        else:
            logger.error(f"❌ Failed to create secret: {stderr}")
            return False
    
    def get_secret_value(self, secret_name: str, key: str) -> Optional[str]:
        """Get a specific value from a Kubernetes secret"""
        cmd = [
            "get", "secret", secret_name, "-n", self.namespace,
            "-o", f"jsonpath={{.data.{key}}}"
        ]
        exit_code, stdout, stderr = self.run_kubectl(cmd)
        
        if exit_code == 0 and stdout:
            # Decode base64
            try:
                return base64.b64decode(stdout).decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decode secret value: {e}")
                return None
        return None
    
    def setup_port_forward(self, local_port: int = 8080) -> subprocess.Popen:
        """Setup port forward to Keycloak service"""
        cmd = [
            "kubectl", "port-forward", f"svc/{self.keycloak_service}",
            f"{local_port}:8080", "-n", self.namespace
        ]
        
        logger.info(f"Setting up port forward to {self.keycloak_service}...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for port forward to establish
        time.sleep(3)
        return process
    
    def get_keycloak_admin_token(self, keycloak_url: str = "http://localhost:8080") -> Optional[str]:
        """Get admin token from Keycloak"""
        token_url = f"{keycloak_url}/realms/master/protocol/openid-connect/token"
        
        data = {
            'username': 'admin',
            'password': 'admin',
            'grant_type': 'password',
            'client_id': 'admin-cli'
        }
        
        try:
            response = requests.post(
                token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get('access_token')
            else:
                logger.error(f"Failed to get admin token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting admin token: {e}")
            return None
    
    def create_keycloak_realm(self, token: str, keycloak_url: str = "http://localhost:8080") -> bool:
        """Create noah realm in Keycloak"""
        realm_url = f"{keycloak_url}/admin/realms"
        
        realm_config = {
            "realm": self.realm_name,
            "enabled": True,
            "sslRequired": "none",
            "displayName": "NOAH Realm",
            "registrationAllowed": True,
            "loginWithEmailAllowed": True,
            "duplicateEmailsAllowed": False
        }
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(realm_url, json=realm_config, headers=headers, timeout=10)
            
            if response.status_code in [201, 409]:  # 409 = already exists
                logger.info(f"✅ Realm {self.realm_name} created/exists")
                return True
            else:
                logger.error(f"Failed to create realm: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating realm: {e}")
            return False
    
    def create_oauth2_client(self, token: str, client_secret: str, keycloak_url: str = "http://localhost:8080") -> bool:
        """Create OAuth2 client in Keycloak"""
        client_url = f"{keycloak_url}/admin/realms/{self.realm_name}/clients"
        
        client_config = {
            "clientId": self.client_id,
            "enabled": True,
            "publicClient": False,
            "secret": client_secret,
            "redirectUris": ["*"],
            "webOrigins": ["*"],
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "protocol": "openid-connect"
        }
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(client_url, json=client_config, headers=headers, timeout=10)
            
            if response.status_code in [201, 409]:  # 409 = already exists
                logger.info(f"✅ OAuth2 client {self.client_id} created/exists")
                return True
            else:
                logger.error(f"Failed to create client: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating client: {e}")
            return False
    
    def setup_keycloak_complete(self, client_secret: str = None) -> bool:
        """Complete Keycloak setup with realm and client"""
        if not client_secret:
            # Try to get existing client secret
            client_secret = self.get_secret_value("oauth2-proxy-secrets", "client-secret")
            if not client_secret:
                logger.error("No client secret provided and none found in Kubernetes")
                return False
        
        # Setup port forward
        pf_process = self.setup_port_forward()
        
        try:
            # Get admin token
            token = self.get_keycloak_admin_token()
            if not token:
                return False
            
            # Create realm
            if not self.create_keycloak_realm(token):
                return False
            
            # Create client
            if not self.create_oauth2_client(token, client_secret):
                return False
            
            logger.info("✅ Keycloak setup completed successfully")
            return True
            
        finally:
            # Clean up port forward
            try:
                pf_process.terminate()
                pf_process.wait(timeout=5)
            except:
                pf_process.kill()
    
    def regenerate_and_restart(self) -> bool:
        """Regenerate secrets and restart OAuth2-proxy"""
        logger.info("Regenerating OAuth2 secrets and restarting deployment...")
        
        # Generate new secrets
        secrets_data = self.generate_oauth2_secrets()
        
        # Update Kubernetes secret
        if not self.create_or_update_k8s_secret(secrets_data):
            return False
        
        # Update Keycloak client
        if not self.setup_keycloak_complete(secrets_data['client-secret']):
            logger.warning("Failed to update Keycloak client, but continuing...")
        
        # Get the actual OAuth2-proxy deployment name
        deployment_name = self.get_oauth2_deployment_name()
        if not deployment_name:
            logger.error("Failed to find OAuth2-proxy deployment")
            return False
        
        # Restart OAuth2-proxy deployment
        restart_cmd = ["rollout", "restart", f"deployment/{deployment_name}", "-n", self.namespace]
        exit_code, stdout, stderr = self.run_kubectl(restart_cmd)
        
        if exit_code == 0:
            logger.info(f"✅ OAuth2-proxy deployment {deployment_name} restarted")
            
            # Wait for rollout
            wait_cmd = ["rollout", "status", f"deployment/{deployment_name}", "-n", self.namespace]
            self.run_kubectl(wait_cmd)
            
            return True
        else:
            logger.error(f"Failed to restart deployment: {stderr}")
            return False

def main():
    """CLI interface for OAuth2 management"""
    parser = argparse.ArgumentParser(description="NOAH OAuth2 Management")
    parser.add_argument("--namespace", default="noah-namespace", help="Kubernetes namespace")
    parser.add_argument("--keycloak-service", help="Keycloak service name")
    parser.add_argument("--action", required=True,
                       choices=['generate-secrets', 'setup-keycloak', 'regenerate', 'get-secret'],
                       help="Action to perform")
    parser.add_argument("--secret-name", default="oauth2-proxy-secrets", help="Secret name")
    parser.add_argument("--secret-key", help="Secret key to retrieve")
    
    args = parser.parse_args()
    
    oauth2_manager = NoahOAuth2Manager(
        namespace=args.namespace,
        keycloak_service=args.keycloak_service
    )
    
    if args.action == 'generate-secrets':
        secrets_data = oauth2_manager.generate_oauth2_secrets()
        if oauth2_manager.create_or_update_k8s_secret(secrets_data, args.secret_name):
            logger.info("✅ OAuth2 secrets generated and stored")
            for key, value in secrets_data.items():
                logger.info(f"  {key}: {value[:8]}...")
        else:
            return 1
    
    elif args.action == 'setup-keycloak':
        if oauth2_manager.setup_keycloak_complete():
            logger.info("✅ Keycloak setup completed")
        else:
            logger.error("❌ Keycloak setup failed")
            return 1
    
    elif args.action == 'regenerate':
        if oauth2_manager.regenerate_and_restart():
            logger.info("✅ OAuth2 secrets regenerated and deployment restarted")
        else:
            logger.error("❌ Failed to regenerate secrets")
            return 1
    
    elif args.action == 'get-secret':
        if not args.secret_key:
            logger.error("--secret-key is required for get-secret action")
            return 1
        
        value = oauth2_manager.get_secret_value(args.secret_name, args.secret_key)
        if value:
            print(value)
        else:
            logger.error("Failed to get secret value")
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
