#!/usr/bin/env python3
"""
NOAH Platform CLI Tool

Unified command-line interface for all NOAH platform operations.
Consolidates all shell scripts into a single Python CLI.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

# Add script directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from noah_helm_manager import NoahHelmManager
    from noah_oauth2_manager import NoahOAuth2Manager
except ImportError as e:
    print(f"Error importing NOAH modules: {e}")
    print("Make sure you're running this from the script/ directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NoahCLI:
    """Main CLI class for NOAH platform operations"""
    
    def __init__(self):
        self.helm_manager: Optional[NoahHelmManager] = None
        self.oauth2_manager: Optional[NoahOAuth2Manager] = None
    
    def init_managers(self, namespace: str, chart_path: str = "helm/noah-chart"):
        """Initialize the management classes"""
        try:
            self.helm_manager = NoahHelmManager(namespace=namespace, chart_path=chart_path)
            self.oauth2_manager = NoahOAuth2Manager(namespace=namespace)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize managers: {e}")
            return False
    
    def cmd_deploy(self, args):
        """Deploy NOAH platform"""
        logger.info("🚀 Starting complete NOAH platform deployment...")
        
        if not self.init_managers(args.namespace, args.chart_path):
            logger.error("Failed to initialize managers")
            return 1
        
        # Type assertions for Pylance - we know these are not None after successful init
        assert self.helm_manager is not None
        assert self.oauth2_manager is not None
        
        try:
            # Step 1: Generate OAuth2 secrets
            logger.info("Step 1: Generating OAuth2 secrets...")
            secrets_data = self.oauth2_manager.generate_oauth2_secrets()
            if not self.oauth2_manager.create_or_update_k8s_secret(secrets_data):
                logger.error("Failed to create OAuth2 secrets")
                return 1
            
            # Step 2: Deploy with Helm
            logger.info("Step 2: Deploying with Helm...")
            if not self.helm_manager.update_helm_dependencies():
                return 1
            
            if not self.helm_manager.deploy_helm_chart(wait=not args.no_wait):
                logger.warning("Helm deployment had issues, continuing with verification...")
            
            # Step 3: Setup Keycloak
            logger.info("Step 3: Setting up Keycloak realm...")
            if not self.oauth2_manager.setup_keycloak_complete(secrets_data['client-secret']):
                logger.warning("Keycloak setup had issues, but deployment may still work")
            
            # Step 4: Verify deployment
            logger.info("Step 4: Verifying deployment...")
            if self.helm_manager.verify_deployment():
                logger.info("✅ NOAH platform deployment completed successfully!")
                return 0
            else:
                logger.warning("⚠️  Deployment verification had issues, check manually")
                return 1
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return 1
    
    def cmd_status(self, args):
        """Get deployment status"""
        if not self.init_managers(args.namespace):
            logger.error("Failed to initialize managers")
            return 1
        
        # Type assertion for Pylance
        assert self.helm_manager is not None
        
        logger.info("Getting NOAH platform status...")
        status = self.helm_manager.get_deployment_status()
        
        # Display summary
        if 'helm_release' in status and status['helm_release']:
            release_info = status['helm_release']['info']
            logger.info(f"Helm Release: {release_info.get('status', 'unknown')}")
        
        if 'pods' in status and 'items' in status['pods']:
            pods = status['pods']['items']
            logger.info(f"Pods: {len(pods)} total")
            for pod in pods:
                name = pod['metadata']['name']
                phase = pod['status'].get('phase', 'unknown')
                logger.info(f"  {name}: {phase}")
        
        return 0
    
    def cmd_secrets(self, args):
        """Manage OAuth2 secrets"""
        if not self.init_managers(args.namespace):
            logger.error("Failed to initialize managers")
            return 1
        
        # Type assertion for Pylance
        assert self.oauth2_manager is not None
        
        if args.regenerate:
            logger.info("Regenerating OAuth2 secrets...")
            if self.oauth2_manager.regenerate_and_restart():
                logger.info("✅ Secrets regenerated successfully")
                return 0
            else:
                logger.error("❌ Failed to regenerate secrets")
                return 1
        else:
            logger.info("Generating new OAuth2 secrets...")
            secrets_data = self.oauth2_manager.generate_oauth2_secrets()
            if self.oauth2_manager.create_or_update_k8s_secret(secrets_data):
                logger.info("✅ Secrets generated successfully")
                for key, value in secrets_data.items():
                    logger.info(f"  {key}: {value[:8]}...")
                return 0
            else:
                logger.error("❌ Failed to generate secrets")
                return 1
    
    def cmd_keycloak(self, args):
        """Manage Keycloak configuration"""
        if not self.init_managers(args.namespace):
            logger.error("Failed to initialize managers")
            return 1
        
        # Type assertion for Pylance
        assert self.oauth2_manager is not None
        
        if self.oauth2_manager.setup_keycloak_complete():
            logger.info("✅ Keycloak setup completed")
            return 0
        else:
            logger.error("❌ Keycloak setup failed")
            return 1
    
    def cmd_migrate(self, args):
        """Migrate from Kustomize to Helm"""
        logger.info("🔄 Starting migration from Kustomize to Helm...")
        
        # This would implement the migration logic
        # For now, just call deploy
        return self.cmd_deploy(args)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="NOAH Platform CLI - Unified management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  noah deploy                          # Deploy complete NOAH platform
  noah status                          # Get deployment status
  noah secrets --regenerate           # Regenerate OAuth2 secrets
  noah keycloak                        # Setup Keycloak realm
  
Environment:
  NOAH_NAMESPACE                       # Default namespace (default: noah-namespace)
  NOAH_CHART_PATH                      # Default chart path (default: helm/noah-chart)
        """
    )
    
    # Global options
    parser.add_argument(
        "--namespace", 
        default="noah-namespace",
        help="Kubernetes namespace (default: noah-namespace)"
    )
    parser.add_argument(
        "--chart-path",
        default="helm/noah-chart", 
        help="Path to Helm chart (default: helm/noah-chart)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy NOAH platform")
    deploy_parser.add_argument("--no-wait", action="store_true", help="Don't wait for deployment")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get deployment status")
    
    # Secrets command
    secrets_parser = subparsers.add_parser("secrets", help="Manage OAuth2 secrets")
    secrets_parser.add_argument("--regenerate", action="store_true", help="Regenerate and restart")
    
    # Keycloak command
    keycloak_parser = subparsers.add_parser("keycloak", help="Setup Keycloak realm")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate from Kustomize to Helm")
    migrate_parser.add_argument("--no-wait", action="store_true", help="Don't wait for deployment")
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create CLI instance
    cli = NoahCLI()
    
    # Route to appropriate command
    if args.command == "deploy":
        return cli.cmd_deploy(args)
    elif args.command == "status":
        return cli.cmd_status(args)
    elif args.command == "secrets":
        return cli.cmd_secrets(args)
    elif args.command == "keycloak":
        return cli.cmd_keycloak(args)
    elif args.command == "migrate":
        return cli.cmd_migrate(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    exit(main())
