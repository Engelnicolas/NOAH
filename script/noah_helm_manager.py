#!/usr/bin/env python3
"""
NOAH Helm Deployment Module

This module consolidates all Helm-related operations for the NOAH platform.
It replaces the shell scripts with Python functions that can be used standalone
or imported by other modules/Ansible.
"""

import subprocess
import time
import json
import base64
import secrets
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import yaml
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NoahHelmManager:
    """Main class for managing NOAH Helm deployments"""
    
    def __init__(self, namespace: str = "noah-namespace", chart_path: str = "helm/noah-chart"):
        self.namespace = namespace
        
        # Convert chart_path to absolute path if it's relative
        if not Path(chart_path).is_absolute():
            # Assume we're working from the project root (NOAH directory)
            project_root = Path(__file__).parent.parent
            self.chart_path = str(project_root / chart_path)
        else:
            self.chart_path = chart_path
            
        self.release_name = "noah"
        logger.debug(f"Initialized with chart_path: {self.chart_path}")
    
    def run_command(self, cmd: List[str], check: bool = True, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        if cwd is None:
            # Use project root as default working directory
            cwd = str(Path(__file__).parent.parent)
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=check,
                cwd=cwd
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Error: {e.stderr}")
            if check:
                raise
            return e.returncode, e.stdout, e.stderr
    
    def generate_oauth2_secrets(self) -> Dict[str, str]:
        """Generate OAuth2 secrets (cookie and client secret)"""
        logger.info("Generating OAuth2 secrets...")
        
        # Generate 32-character cookie secret
        cookie_secret = secrets.token_hex(16)
        
        # Generate 64-character client secret
        client_secret = secrets.token_hex(32)
        
        secrets_data = {
            'cookie-secret': cookie_secret,
            'client-secret': client_secret
        }
        
        logger.info(f"Generated cookie secret: {cookie_secret[:8]}...")
        logger.info(f"Generated client secret: {client_secret[:8]}...")
        
        return secrets_data
    
    def create_k8s_secret(self, secrets_data: Dict[str, str]) -> bool:
        """Create Kubernetes secret with OAuth2 data"""
        secret_name = f"{self.release_name}-oauth2-secrets"
        
        # Prepare kubectl command
        cmd = [
            "kubectl", "create", "secret", "generic", secret_name,
            "--namespace", self.namespace,
            "--dry-run=client", "-o", "yaml"
        ]
        
        # Add secret data
        for key, value in secrets_data.items():
            cmd.extend([f"--from-literal={key}={value}"])
        
        # Create secret
        exit_code, stdout, stderr = self.run_command(cmd)
        if exit_code == 0:
            # Apply the secret
            apply_cmd = ["kubectl", "apply", "-f", "-"]
            process = subprocess.Popen(
                apply_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=stdout)
            
            if process.returncode == 0:
                logger.info(f"Secret {secret_name} created successfully")
                return True
            else:
                logger.error(f"Failed to apply secret: {stderr}")
                return False
        else:
            logger.error(f"Failed to create secret YAML: {stderr}")
            return False
    
    def update_helm_dependencies(self) -> bool:
        """Update Helm chart dependencies"""
        logger.info("Updating Helm dependencies...")
        cmd = ["helm", "dependency", "update", self.chart_path]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code == 0:
            logger.info("Helm dependencies updated successfully")
            return True
        else:
            logger.error(f"Failed to update dependencies: {stderr}")
            return False
    
    def deploy_helm_chart(self, wait: bool = True, timeout: str = "600s") -> bool:
        """Deploy NOAH using Helm"""
        logger.info(f"Deploying NOAH Helm chart to namespace {self.namespace}...")
        
        cmd = [
            "helm", "upgrade", "--install", self.release_name, self.chart_path,
            "--namespace", self.namespace,
            "--create-namespace"
        ]
        
        if wait:
            cmd.extend(["--wait", f"--timeout={timeout}"])
        
        exit_code, stdout, stderr = self.run_command(cmd, check=False)
        
        if exit_code == 0:
            logger.info("Helm deployment completed successfully")
            return True
        else:
            logger.warning(f"Helm deployment had issues: {stderr}")
            # Check if pods are actually running despite Helm timeout
            return self.verify_deployment()
    
    def verify_deployment(self) -> bool:
        """Verify that the deployment is actually working"""
        logger.info("Verifying deployment status...")
        
        # Check pods
        cmd = ["kubectl", "get", "pods", "-n", self.namespace]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code == 0:
            logger.info("Pod status:")
            for line in stdout.strip().split('\n'):
                logger.info(f"  {line}")
            
            # Check if Keycloak is accessible
            return self.test_keycloak_connectivity()
        else:
            logger.error(f"Failed to get pod status: {stderr}")
            return False
    
    def test_keycloak_connectivity(self) -> bool:
        """Test if Keycloak noah realm is accessible"""
        logger.info("Testing Keycloak connectivity...")
        
        cmd = [
            "kubectl", "run", "-it", "--rm", "debug",
            "--image=curlimages/curl", "--restart=Never",
            "-n", self.namespace, "--",
            "curl", "-s", f"http://{self.release_name}-keycloak:8080/realms/noah/.well-known/openid-configuration"
        ]
        
        exit_code, stdout, stderr = self.run_command(cmd, check=False)
        
        if exit_code == 0 and "noah" in stdout:
            logger.info("✅ Keycloak noah realm is accessible")
            return True
        else:
            logger.warning("❌ Keycloak noah realm is not accessible yet")
            return False
    
    def setup_keycloak_realm(self) -> bool:
        """Setup Keycloak realm and OAuth2 client"""
        logger.info("Setting up Keycloak realm...")
        
        # This would typically be done via Keycloak API
        # For now, we'll just log that this step needs to be done
        logger.info("Keycloak realm setup would be implemented here")
        logger.info("This should create the noah realm and oauth2-proxy client")
        
        return True
    
    def get_deployment_status(self) -> Dict:
        """Get comprehensive deployment status"""
        status = {
            'helm_release': {},
            'pods': {},
            'services': {},
            'secrets': {}
        }
        
        # Helm status
        cmd = ["helm", "status", self.release_name, "-n", self.namespace, "-o", "json"]
        exit_code, stdout, stderr = self.run_command(cmd, check=False)
        if exit_code == 0:
            status['helm_release'] = json.loads(stdout)
        
        # Pod status
        cmd = ["kubectl", "get", "pods", "-n", self.namespace, "-o", "json"]
        exit_code, stdout, stderr = self.run_command(cmd, check=False)
        if exit_code == 0:
            status['pods'] = json.loads(stdout)
        
        # Service status
        cmd = ["kubectl", "get", "services", "-n", self.namespace, "-o", "json"]
        exit_code, stdout, stderr = self.run_command(cmd, check=False)
        if exit_code == 0:
            status['services'] = json.loads(stdout)
        
        return status

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="NOAH Helm Deployment Manager")
    parser.add_argument("--namespace", default="noah-namespace", help="Kubernetes namespace")
    parser.add_argument("--chart-path", default="helm/noah-chart", help="Path to Helm chart")
    parser.add_argument("--action", required=True, 
                       choices=['deploy', 'status', 'secrets', 'verify'],
                       help="Action to perform")
    parser.add_argument("--no-wait", action="store_true", help="Don't wait for deployment")
    
    args = parser.parse_args()
    
    helm_manager = NoahHelmManager(
        namespace=args.namespace,
        chart_path=args.chart_path
    )
    
    if args.action == 'deploy':
        logger.info("🚀 Starting NOAH deployment...")
        
        # Update dependencies
        if not helm_manager.update_helm_dependencies():
            return 1
        
        # Deploy with Helm
        if not helm_manager.deploy_helm_chart(wait=not args.no_wait):
            return 1
        
        # Verify deployment
        if not helm_manager.verify_deployment():
            logger.warning("Deployment verification failed, but services may still be starting")
        
        logger.info("🎉 Deployment completed!")
        
    elif args.action == 'secrets':
        secrets_data = helm_manager.generate_oauth2_secrets()
        if helm_manager.create_k8s_secret(secrets_data):
            logger.info("✅ OAuth2 secrets created successfully")
        else:
            logger.error("❌ Failed to create OAuth2 secrets")
            return 1
    
    elif args.action == 'verify':
        if helm_manager.verify_deployment():
            logger.info("✅ Deployment verification passed")
        else:
            logger.error("❌ Deployment verification failed")
            return 1
    
    elif args.action == 'status':
        status = helm_manager.get_deployment_status()
        print(json.dumps(status, indent=2))
    
    return 0

if __name__ == "__main__":
    exit(main())
