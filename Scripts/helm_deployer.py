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
        self.timeout = self.config.get('HELM_TIMEOUT', '600s')
    
    def deploy_chart(self, chart_name: str, namespace: str, values: Optional[Dict] = None):
        """Deploy a Helm chart"""
        chart_path = self.chart_dir / chart_name
        
        if not chart_path.exists():
            raise Exception(f"Chart not found: {chart_path}")
        
        # Build helm install command  
        cmd = [
            'helm', 'upgrade', '--install',
            chart_name,
            str(chart_path),
            '--namespace', namespace,
            '--create-namespace',
            '--timeout', self.timeout
        ]
        
        # Add --wait flag for smaller charts, but not for complex ones like samba4 and authentik
        if chart_name not in ['samba4', 'authentik']:
            cmd.append('--wait')
        
        # Add values file if exists
        values_file = chart_path / 'values.yaml'
        if values_file.exists():
            cmd.extend(['--values', str(values_file)])
        
        # Add encrypted values if exists
        encrypted_values = chart_path / 'secrets' / f'{chart_name}-secrets.enc.yaml'
        if encrypted_values.exists():
            # Decrypt and apply secrets
            decrypted = self._decrypt_helm_secrets(encrypted_values)
            temp_values = chart_path / 'secrets' / '.temp-values.yaml'
            if yaml is None:
                raise Exception("PyYAML is required for Helm deployments. Install with: pip install PyYAML")
            temp_values.write_text(yaml.dump(decrypted))
            cmd.extend(['--values', str(temp_values)])
        
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
            temp_values = chart_path / 'secrets' / '.temp-values.yaml'
            if temp_values.exists():
                temp_values.unlink()
            return True
        else:
            print(f"Failed to deploy {chart_name}: {result.stderr}")
            return False
    
    def _decrypt_helm_secrets(self, secret_file: Path) -> Dict:
        """Decrypt Helm secrets using SOPS and transform to values format"""
        from Scripts.secret_manager import SecretManager
        sm = SecretManager(self.config)
        decrypted = sm.decrypt_secret(secret_file)
        
        # Check if this is a Kubernetes Secret resource and transform to values
        if isinstance(decrypted, dict) and decrypted.get('kind') == 'Secret':
            string_data = decrypted.get('stringData', {})
            
            # Transform secret data to Helm values format
            if 'authentik' in str(secret_file):
                return {
                    'authentik': {
                        'secretKey': string_data.get('secret_key', ''),
                    },
                    'postgresql': {
                        'auth': {
                            'password': string_data.get('postgresql_password', '')
                        }
                    },
                    'redis': {
                        'auth': {
                            'password': string_data.get('redis_password', '')
                        }
                    }
                }
            # Add more transformations for other charts as needed
            
        return decrypted
    
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
