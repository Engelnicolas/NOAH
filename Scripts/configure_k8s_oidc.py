#!/usr/bin/env python3
"""
Kubernetes API Server OIDC Configuration Generator
This script generates the necessary configuration for integrating 
Kubernetes API server with Authentik OIDC provider
"""

import os
import sys
from pathlib import Path
import tempfile
import yaml


class KubernetesOIDCConfigurator:
    def __init__(self, authentik_domain=None, client_id=None, username_claim=None, 
                 groups_claim=None, signing_algs=None):
        """Initialize OIDC configurator with customizable parameters"""
        self.authentik_domain = authentik_domain or os.getenv('AUTHENTIK_DOMAIN', 'auth.noah-infra.com')
        self.oidc_issuer_url = f"https://{self.authentik_domain}/application/o/kubernetes/"
        self.oidc_client_id = client_id or os.getenv('OIDC_CLIENT_ID', 'kubernetes-cluster')
        self.oidc_username_claim = username_claim or os.getenv('OIDC_USERNAME_CLAIM', 'preferred_username')
        self.oidc_groups_claim = groups_claim or os.getenv('OIDC_GROUPS_CLAIM', 'groups')
        self.oidc_signing_algs = signing_algs or os.getenv('OIDC_SIGNING_ALGS', 'RS256')
        
        # Output directory
        self.output_dir = Path(tempfile.gettempdir())
        
    def generate_apiserver_config(self) -> Path:
        """Generate kube-apiserver OIDC configuration"""
        config = {
            'apiVersion': 'v1',
            'kind': 'Pod',
            'metadata': {
                'name': 'kube-apiserver',
                'namespace': 'kube-system'
            },
            'spec': {
                'containers': [{
                    'name': 'kube-apiserver',
                    'image': 'registry.k8s.io/kube-apiserver:v1.28.0',
                    'command': [
                        'kube-apiserver',
                        # Existing flags would go here...
                        # OIDC flags:
                        f'--oidc-issuer-url={self.oidc_issuer_url}',
                        f'--oidc-client-id={self.oidc_client_id}',
                        f'--oidc-username-claim={self.oidc_username_claim}',
                        f'--oidc-groups-claim={self.oidc_groups_claim}',
                        f'--oidc-signing-algs={self.oidc_signing_algs}',
                        # Optional: Certificate validation (for production)
                        # '--oidc-ca-file=/etc/ssl/certs/authentik-ca.crt',
                        # '--oidc-username-prefix=oidc:',
                        # '--oidc-groups-prefix=oidc:'
                    ]
                }]
            }
        }
        
        output_file = self.output_dir / 'kube-apiserver-oidc.yaml'
        
        with open(output_file, 'w') as f:
            f.write("# Add these flags to your kube-apiserver configuration\n")
            f.write("# Example: /etc/kubernetes/manifests/kube-apiserver.yaml (for kubeadm)\n\n")
            yaml.dump(config, f, default_flow_style=False)
            
        return output_file
    
    def generate_kubectl_config(self) -> Path:
        """Generate kubectl OIDC configuration"""
        config = {
            'apiVersion': 'v1',
            'kind': 'Config',
            'clusters': [{
                'cluster': {
                    'server': 'https://your-k8s-api-server:6443',
                    # 'certificate-authority': '/path/to/ca.crt'
                },
                'name': 'noah-cluster'
            }],
            'contexts': [{
                'context': {
                    'cluster': 'noah-cluster',
                    'user': 'oidc-user'
                },
                'name': 'noah-oidc'
            }],
            'current-context': 'noah-oidc',
            'users': [{
                'name': 'oidc-user',
                'user': {
                    'exec': {
                        'apiVersion': 'client.authentication.k8s.io/v1beta1',
                        'command': 'kubectl',
                        'args': [
                            'oidc-login',
                            'get-token',
                            f'--oidc-issuer-url={self.oidc_issuer_url}',
                            f'--oidc-client-id={self.oidc_client_id}',
                            '--oidc-extra-scope=groups'
                        ]
                    }
                }
            }]
        }
        
        output_file = self.output_dir / 'kubectl-oidc-config.yaml'
        
        with open(output_file, 'w') as f:
            f.write("# kubectl configuration for OIDC authentication\n")
            f.write("# Use this with: kubectl config set-credentials oidc-user --exec-command=kubectl --exec-arg=oidc-login\n\n")
            yaml.dump(config, f, default_flow_style=False)
            
        return output_file
    
    def generate_rbac_examples(self) -> Path:
        """Generate RBAC policy examples"""
        rbac_configs = [
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'ClusterRole',
                'metadata': {
                    'name': 'authentik-admins'
                },
                'rules': [{
                    'apiGroups': ['*'],
                    'resources': ['*'],
                    'verbs': ['*']
                }]
            },
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'ClusterRoleBinding',
                'metadata': {
                    'name': 'authentik-admins-binding'
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'ClusterRole',
                    'name': 'authentik-admins'
                },
                'subjects': [
                    {
                        'kind': 'User',
                        'name': f'{self.oidc_username_claim}:admin@noah-infra.com',
                        'apiGroup': 'rbac.authorization.k8s.io'
                    },
                    {
                        'kind': 'Group',
                        'name': f'{self.oidc_groups_claim}:authentik Admins',
                        'apiGroup': 'rbac.authorization.k8s.io'
                    }
                ]
            },
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'Role',
                'metadata': {
                    'namespace': 'development',
                    'name': 'developer'
                },
                'rules': [{
                    'apiGroups': ['', 'apps', 'extensions'],
                    'resources': ['pods', 'deployments', 'services', 'configmaps', 'secrets'],
                    'verbs': ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']
                }]
            },
            {
                'apiVersion': 'rbac.authorization.k8s.io/v1',
                'kind': 'RoleBinding',
                'metadata': {
                    'name': 'developer-binding',
                    'namespace': 'development'
                },
                'roleRef': {
                    'apiGroup': 'rbac.authorization.k8s.io',
                    'kind': 'Role',
                    'name': 'developer'
                },
                'subjects': [{
                    'kind': 'Group',
                    'name': f'{self.oidc_groups_claim}:developers',
                    'apiGroup': 'rbac.authorization.k8s.io'
                }]
            }
        ]
        
        output_file = self.output_dir / 'kubernetes-rbac-examples.yaml'
        
        with open(output_file, 'w') as f:
            f.write("# Example RBAC configurations for OIDC users/groups\n")
            for i, config in enumerate(rbac_configs):
                if i > 0:
                    f.write("---\n")
                if config['kind'] == 'ClusterRole':
                    f.write("# ClusterRole for Authentik administrators\n")
                elif config['kind'] == 'ClusterRoleBinding':
                    f.write("# ClusterRoleBinding for Authentik administrators\n")
                elif config['kind'] == 'Role':
                    f.write("# Role for developers (namespace-scoped)\n")
                elif config['kind'] == 'RoleBinding':
                    f.write("# RoleBinding for developers\n")
                yaml.dump(config, f, default_flow_style=False)
                f.write("\n")
                
        return output_file
    
    def generate_all_configs(self) -> dict:
        """Generate all configuration files"""
        print("🔧 Generating Kubernetes API Server OIDC Configuration...")
        print(f"   Issuer URL: {self.oidc_issuer_url}")
        print(f"   Client ID: {self.oidc_client_id}")
        
        files = {
            'apiserver_config': self.generate_apiserver_config(),
            'kubectl_config': self.generate_kubectl_config(),
            'rbac_examples': self.generate_rbac_examples()
        }
        
        print("✅ Generated configuration files:")
        print(f"   📄 {files['apiserver_config']} - API server configuration")
        print(f"   📄 {files['kubectl_config']} - kubectl client configuration")
        print(f"   📄 {files['rbac_examples']} - RBAC examples")
        print("")
        print("📋 Next Steps:")
        print("   1. Deploy Authentik with: python noah.py deploy authentik")
        print("   2. Configure OIDC provider in Authentik admin interface")
        print("   3. Apply API server configuration (requires cluster restart)")
        print("   4. Set up RBAC policies for your users/groups")
        print("   5. Test OIDC authentication with kubectl")
        
        return files


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Kubernetes OIDC configuration for Authentik')
    parser.add_argument('--domain', default='auth.noah-infra.com', 
                       help='Authentik domain (default: auth.noah-infra.com)')
    parser.add_argument('--client-id', default='kubernetes-cluster',
                       help='OIDC client ID (default: kubernetes-cluster)')
    parser.add_argument('--username-claim', default='preferred_username',
                       help='OIDC username claim (default: preferred_username)')
    parser.add_argument('--groups-claim', default='groups',
                       help='OIDC groups claim (default: groups)')
    parser.add_argument('--signing-algs', default='RS256',
                       help='OIDC signing algorithms (default: RS256)')
    
    args = parser.parse_args()
    
    configurator = KubernetesOIDCConfigurator(
        authentik_domain=args.domain,
        client_id=args.client_id,
        username_claim=args.username_claim,
        groups_claim=args.groups_claim,
        signing_algs=args.signing_algs
    )
    
    configurator.generate_all_configs()


if __name__ == '__main__':
    main()
