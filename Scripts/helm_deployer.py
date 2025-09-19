"""Helm chart deployment module"""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Optional imports with graceful fallbacks
yaml: Optional[Any] = None
try:
    import yaml  # type: ignore
except ImportError:
    pass

class HelmDeployer:
    def __init__(self, config_loader):
        self.config = config_loader
        self.chart_dir = Path(self.config.get('HELM_CHART_DIR', './Helm'))
        self.timeout = self.config.get('HELM_TIMEOUT', '600s')  # 10 minutes - reduced from 15
    
    def deploy_chart(self, chart_name: str, namespace: str, values: Optional[Dict] = None):
        """Deploy a Helm chart"""
        chart_path = self.chart_dir / chart_name
        
        if not chart_path.exists():
            raise Exception(f"Chart not found: {chart_path}")
        
        # Chart-specific timeout overrides
        chart_timeouts = {
            'cilium': '600s',      # 10 minutes - CNI deployment
            'authentik': '720s',   # 12 minutes - DB + App initialization 
        }
        timeout = chart_timeouts.get(chart_name, self.timeout)
        
        # Build helm install command  
        cmd = [
            'helm', 'upgrade', '--install',
            chart_name,
            str(chart_path),
            '--namespace', namespace,
            '--create-namespace',
            '--timeout', timeout
        ]
        
        # Add --wait flag for smaller charts, but not for complex ones like authentik and cilium
        if chart_name not in ['authentik', 'cilium']:
            cmd.append('--wait')
        
        # Add values file if exists
        values_file = chart_path / 'values.yaml'
        if values_file.exists():
            cmd.extend(['--values', str(values_file)])

        # Apply canonical secret values if available
        canonical_applied = False
        try:
            from Scripts.security.canonical_store import get_canonical_store  # type: ignore
            store = get_canonical_store(self.chart_dir.parent)
            service_secrets = store.get_service_secrets(chart_name)
            if service_secrets:
                canonical_values = self._transform_canonical_for_chart(chart_name, service_secrets)
                temp_values = chart_path / 'secrets' / '.temp-canonical-values.yaml'
                temp_values.parent.mkdir(exist_ok=True)
                if yaml is None:
                    raise Exception("PyYAML is required for Helm deployments. Install with: pip install PyYAML")
                temp_values.write_text(yaml.dump(canonical_values))
                cmd.extend(['--values', str(temp_values)])
                canonical_applied = True
        except Exception as e:
            print(f"[WARNING] Canonical secret integration failed for {chart_name}: {e}")

        # Legacy encrypted helm secrets pathway removed; canonical store is authoritative
        
        # Add custom values via temporary values file
        if values:
            temp_custom_values = chart_path / 'secrets' / '.temp-custom-values.yaml'
            temp_custom_values.parent.mkdir(exist_ok=True)
            if yaml is None:
                raise Exception("PyYAML is required for Helm deployments. Install with: pip install PyYAML")
            with open(temp_custom_values, 'w') as f:
                yaml.dump(values, f)
            cmd.extend(['--values', str(temp_custom_values)])
        
        print(f"Deploying {chart_name} to namespace {namespace}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully deployed {chart_name}")
            # Clean up temp files
            for temp_name in ['.temp-values.yaml', '.temp-canonical-values.yaml', '.temp-custom-values.yaml']:
                temp_file = chart_path / 'secrets' / temp_name
                if temp_file.exists():
                    temp_file.unlink()
            
            # Synchronize secrets after deployment to ensure consistency
            self._synchronize_secrets_post_deployment(chart_name, namespace)
            return True
        else:
            print(f"Failed to deploy {chart_name}: {result.stderr}")
            return False
    
    # Legacy decryption helper fully removed; only canonical path supported

    def _transform_canonical_for_chart(self, chart_name: str, service_secrets: Dict[str, str]) -> Dict[str, Any]:
        """Map canonical secrets dict to Helm values structure per chart.

        Args:
            chart_name: service/chart identifier (e.g., 'authentik')
            service_secrets: raw canonical secrets mapping
        Returns:
            Dict suitable for passing as helm values
        """
        if chart_name == 'authentik':
            return {
                'authentik': {
                    'secretKey': service_secrets.get('secret_key'),
                    'bootstrap': {
                        'password': service_secrets.get('bootstrap_password'),
                        'token': service_secrets.get('bootstrap_token')
                    }
                },
                'postgresql': {
                    'auth': {
                        'username': 'authentik',
                        'database': 'authentik',
                        'password': service_secrets.get('postgresql_password')
                    },
                    'enabled': True
                },
                'redis': {
                    'auth': {
                        'enabled': True,
                        'password': service_secrets.get('redis_password')
                    },
                    'enabled': True
                }
            }
        elif chart_name == 'cilium':
            # Currently secrets usage minimal; placeholder for future sensitive keys
            return {}
        return {}
    
    def _synchronize_secrets_post_deployment(self, chart_name: str, namespace: str):
        """Synchronize secrets after deployment to ensure all components use the same passwords"""
        if chart_name == 'authentik':
            try:
                import subprocess
                import time
                
                # Wait a moment for the deployment to stabilize
                time.sleep(5)
                
                # Get the passwords from the main secret source
                chart_path = self.chart_dir / chart_name
                encrypted_values = chart_path / 'secrets' / f'{chart_name}-secrets.enc.yaml'
                
                if encrypted_values.exists():
                    decrypted = self._decrypt_helm_secrets(encrypted_values)
                    
                    # Extract the coordinated passwords
                    postgresql_password = decrypted.get('postgresql', {}).get('auth', {}).get('password', '')
                    redis_password = decrypted.get('redis', {}).get('auth', {}).get('password', '')
                    
                    if postgresql_password and redis_password:
                        print(f"[INFO] Synchronizing passwords for {chart_name} components...")
                        
                        # Update the authentik-secret to match what PostgreSQL and Redis actually use
                        self._update_authentik_secret_if_needed(namespace, postgresql_password, redis_password)
                        
                        print(f"[INFO] Password synchronization completed for {chart_name}")
                    
            except Exception as e:
                print(f"[WARNING] Failed to synchronize secrets for {chart_name}: {e}")
    
    def _update_authentik_secret_if_needed(self, namespace: str, postgresql_password: str, redis_password: str):
        """Update authentik-secret if there's a password mismatch"""
        try:
            import subprocess
            import base64
            
            # Check current authentik-secret passwords
            result = subprocess.run([
                'kubectl', 'get', 'secret', 'authentik-secret', '-n', namespace, 
                '-o', 'jsonpath={.data.postgresql-password}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                current_pg_password = base64.b64decode(result.stdout).decode('utf-8')
                
                # Check if passwords match
                if current_pg_password != postgresql_password:
                    print(f"[INFO] Updating authentik-secret with coordinated PostgreSQL password")
                    
                    # Update the secret with the correct passwords
                    pg_b64 = base64.b64encode(postgresql_password.encode()).decode()
                    redis_b64 = base64.b64encode(redis_password.encode()).decode()
                    
                    patch_data = f'{{"data":{{"postgresql-password":"{pg_b64}","redis-password":"{redis_b64}"}}}}'
                    
                    subprocess.run([
                        'kubectl', 'patch', 'secret', 'authentik-secret', '-n', namespace, 
                        '-p', patch_data
                    ], check=True)
                    
                    # Restart deployments to pick up new secrets
                    subprocess.run([
                        'kubectl', 'rollout', 'restart', 
                        'deployment/authentik-server', 
                        'deployment/authentik-worker', 
                        'deployment/authentik-ldap-outpost', 
                        '-n', namespace
                    ], check=True)
                    
                    print(f"[INFO] Authentik deployments restarted with synchronized passwords")
                else:
                    print(f"[INFO] Authentik secret passwords are already synchronized")
                    
        except Exception as e:
            print(f"[WARNING] Failed to update authentik secret: {e}")

    def uninstall_chart(self, chart_name: str, namespace: str):
        """Uninstall a Helm chart"""
        cmd = ['helm', 'uninstall', chart_name, '--namespace', namespace]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully uninstalled {chart_name}")
            return True
        else:
            print(f"Failed to uninstall {chart_name}: {result.stderr}")
            return False
    
    def list_releases(self, namespace: Optional[str] = None) -> list:
        """List Helm releases"""
        cmd = ['helm', 'list', '--output', 'json']
        if namespace:
            cmd.extend(['--namespace', namespace])
        else:
            cmd.append('--all-namespaces')
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"Failed to list releases: {result.stderr}")
            return []
