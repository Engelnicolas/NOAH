#!/usr/bin/env python3
"""
NOAH Unified Security Manager
Comprehensive security management for NOAH infrastructure including:
- Secure password generation and rotation
- SOPS/Age encryption for git storage  
- Kubernetes secret management
- TLS certificate generation
- Security validation and compliance
"""

import os
import subprocess
import json
import secrets
import string
import base64
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

class NoahSecurityManager:
    """Unified security manager for NOAH infrastructure"""
    
    def __init__(self, config_loader=None, project_root=None):
        """Initialize the security manager
        
        Args:
            config_loader: Optional configuration loader (for backward compatibility)
            project_root: Project root directory (auto-detected if not provided)
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.config = config_loader
        
        # Directory structure
        self.secrets_dir = self.project_root / "Secrets"
        self.age_dir = self.project_root / "Age"
        self.helm_dir = self.project_root / "Helm"
        self.certs_dir = self.project_root / "Certificates"
        
        # Initialize directories
        for directory in [self.secrets_dir, self.age_dir, self.certs_dir]:
            directory.mkdir(exist_ok=True)
            
        # Configuration files
        self.age_key_file = self.age_dir / "keys.txt"
        self.sops_config = self.project_root / ".sops.yaml"
        
        # Ensure Age key exists
        if not self.age_key_file.exists():
            print("⚠️  Age key not found. Run 'initialize_encryption()' to set up SOPS/Age encryption.")

    # ================================
    # CORE PASSWORD GENERATION
    # ================================
    
    def generate_secure_password(self, length=32, include_special=True):
        """Generate a cryptographically secure password
        
        Args:
            length: Password length (default: 32)
            include_special: Include special characters (default: True)
            
        Returns:
            Secure random password string
        """
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
        
        # Ensure at least one character from each category
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase), 
            secrets.choice(string.digits)
        ]
        
        if include_special:
            password.append(secrets.choice("!@#$%^&*"))
            
        # Fill the rest randomly
        for _ in range(length - len(password)):
            password.append(secrets.choice(chars))
            
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def generate_password(self, length: int = 24) -> str:
        """Legacy method for backward compatibility (max 24 chars)"""
        return self.generate_secure_password(min(length, 24), include_special=True)

    # ================================
    # SERVICE-SPECIFIC SECRETS
    # ================================
    
    def generate_service_secrets(self, service_name):
        """Generate all required secrets for a service
        
        Args:
            service_name: Service name ('samba4', 'authentik', etc.)
            
        Returns:
            Dictionary of service-specific secrets
        """
        secrets_config = {
            'samba4': {
                'admin_password': self.generate_secure_password(24),
                'domain_admin_password': self.generate_secure_password(24),
                'service_account_password': self.generate_secure_password(24),
                'machine_account_password': self.generate_secure_password(32),
                'krb5_password': self.generate_secure_password(32),
                'dns_key': self.generate_secure_password(32, include_special=False),
            },
            'authentik': {
                'secret_key': self.generate_secure_password(50, include_special=False),
                'bootstrap_password': self.generate_secure_password(24),
                'bootstrap_token': self.generate_secure_password(50, include_special=False),
                'postgresql_password': self.generate_secure_password(32),
                'redis_password': self.generate_secure_password(32),
                'ldap_bind_password': self.generate_secure_password(24),
                'outpost_token': self.generate_secure_password(50, include_special=False),
                'session_secret': self.generate_secure_password(32),
            },
            'cilium': {
                'hubble_tls_key': self.generate_secure_password(32, include_special=False),
                'cluster_mesh_key': self.generate_secure_password(32, include_special=False),
                'ca_key_passphrase': self.generate_secure_password(24),
            }
        }
        
        return secrets_config.get(service_name, {})

    # ================================
    # KUBERNETES SECRET MANAGEMENT
    # ================================
    
    def create_kubernetes_secret_yaml(self, service_name, namespace="identity"):
        """Create Kubernetes secret YAML with secure passwords
        
        Args:
            service_name: Service name
            namespace: Kubernetes namespace
            
        Returns:
            Kubernetes Secret YAML dictionary
        """
        secrets = self.generate_service_secrets(service_name)
        
        # Service-specific formatting
        if service_name == 'samba4':
            # Create samba-user-config for dperson/samba format
            user_config = f"admin;{secrets['admin_password']}"
            secrets['samba_user_config'] = user_config
            
        # Convert to base64 for Kubernetes secret
        secret_data = {}
        for key, value in secrets.items():
            secret_data[key.replace('_', '-')] = base64.b64encode(value.encode()).decode()
        
        secret_yaml = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': f'{service_name}-security-secrets',
                'namespace': namespace,
                'labels': {
                    'app.kubernetes.io/name': service_name,
                    'noah.infra.com/component': 'security',
                    'noah.infra.com/managed-by': 'noah-security-manager'
                },
                'annotations': {
                    'noah.infra.com/generated-at': self._get_timestamp(),
                    'noah.infra.com/rotation-interval': '30d',
                    'noah.infra.com/secret-type': 'credentials'
                }
            },
            'type': 'Opaque',
            'data': secret_data
        }
        
        return secret_yaml
    
    def save_kubernetes_secret(self, service_name, namespace="identity"):
        """Save Kubernetes secret YAML to file
        
        Args:
            service_name: Service name
            namespace: Kubernetes namespace
            
        Returns:
            Path to saved secret file
        """
        secret_yaml = self.create_kubernetes_secret_yaml(service_name, namespace)
        
        # Save to secrets directory
        output_file = self.secrets_dir / f"{service_name}-security-secrets.yaml"
        with open(output_file, 'w') as f:
            yaml.dump(secret_yaml, f, default_flow_style=False, sort_keys=False)
            
        print(f"✅ Kubernetes secret saved: {output_file}")
        return output_file

    # ================================
    # SOPS/AGE ENCRYPTION (Git Storage)
    # ================================
    
    def initialize_encryption(self):
        """Initialize Age encryption for SOPS"""
        if self.age_key_file.exists():
            print(f"✅ Age key already exists at {self.age_key_file}")
            return self._get_public_key()
            
        try:
            # Generate new Age key
            result = subprocess.run(['age-keygen'], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.age_key_file.write_text(result.stdout)
                os.chmod(self.age_key_file, 0o600)
                print(f"✅ Age key generated: {self.age_key_file}")
                
                # Extract and return public key
                public_key = self._get_public_key()
                self.configure_sops()
                return public_key
            else:
                raise Exception(f"Failed to generate Age key: {result.stderr}")
        except FileNotFoundError:
            print("⚠️  Age not found. Install with: https://github.com/FiloSottile/age")
            return None
    
    def _get_public_key(self) -> str:
        """Extract public key from Age key file"""
        if not self.age_key_file.exists():
            raise Exception("Age key file not found. Run initialize_encryption() first.")
            
        content = self.age_key_file.read_text()
        for line in content.split('\n'):
            if line.startswith('# public key:'):
                return line.split(':')[1].strip()
        raise Exception("Could not find public key in Age key file")
    
    def configure_sops(self):
        """Configure SOPS with Age encryption"""
        try:
            public_key = self._get_public_key()
            
            sops_config = {
                'creation_rules': [
                    {
                        'path_regex': '.*\\.enc\\.yaml$',
                        'age': public_key
                    },
                    {
                        'path_regex': '.*\\.enc\\.json$', 
                        'age': public_key
                    }
                ]
            }
            
            with open(self.sops_config, 'w') as f:
                yaml.dump(sops_config, f)
            
            print(f"✅ SOPS configuration: {self.sops_config}")
        except Exception as e:
            print(f"⚠️  SOPS configuration failed: {e}")
    
    def create_encrypted_secret(self, service_name, namespace="identity"):
        """Create SOPS-encrypted secret file for git storage
        
        Args:
            service_name: Service name
            namespace: Kubernetes namespace
            
        Returns:
            Path to encrypted secret file
        """
        if not self.age_key_file.exists():
            print("⚠️  Initialize encryption first: manager.initialize_encryption()")
            return None
            
        # Generate secrets
        secrets = self.generate_service_secrets(service_name)
        
        # Create Helm values format
        helm_values = self._create_helm_values_format(service_name, secrets)
        
        # Save to Helm secrets directory
        service_secrets_dir = self.helm_dir / service_name / "secrets"
        service_secrets_dir.mkdir(parents=True, exist_ok=True)
        
        encrypted_file = service_secrets_dir / f"{service_name}-secrets.enc.yaml"
        temp_file = service_secrets_dir / f"{service_name}-secrets.temp.enc.yaml"
        
        try:
            # Write temporary unencrypted file
            with open(temp_file, 'w') as f:
                yaml.dump(helm_values, f, default_flow_style=False)
            
            # Encrypt with SOPS
            result = subprocess.run([
                'sops', '--encrypt', '--in-place', str(temp_file)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Move encrypted file to final location
                temp_file.rename(encrypted_file)
                print(f"✅ Encrypted secret created: {encrypted_file}")
                return encrypted_file
            else:
                temp_file.unlink(missing_ok=True)
                raise Exception(f"SOPS encryption failed: {result.stderr}")
                
        except FileNotFoundError:
            print("⚠️  SOPS not found. Install with: https://github.com/mozilla/sops")
            temp_file.unlink(missing_ok=True)
            return None
        except Exception as e:
            temp_file.unlink(missing_ok=True)
            print(f"❌ Encryption failed: {e}")
            return None

    def _create_helm_values_format(self, service_name, secrets):
        """Create Helm-compatible values format"""
        if service_name == 'samba4':
            return {
                'domain': {
                    'adminPassword': secrets['admin_password']
                },
                'secrets': {
                    'adminPassword': secrets['admin_password'],
                    'machinePassword': secrets['machine_account_password'],
                    'servicePassword': secrets['service_account_password']
                }
            }
        elif service_name == 'authentik':
            return {
                'authentik': {
                    'secretKey': secrets['secret_key'],
                    'bootstrap': {
                        'password': secrets['bootstrap_password'],
                        'token': secrets['bootstrap_token']
                    }
                },
                'postgresql': {
                    'auth': {
                        'password': secrets['postgresql_password']
                    }
                },
                'redis': {
                    'auth': {
                        'password': secrets['redis_password']
                    }
                }
            }
        else:
            return {'secrets': secrets}

    # ================================
    # SECRET ROTATION & MANAGEMENT
    # ================================
    
    def rotate_service_secrets(self, service_name, format_type="both", namespace="identity"):
        """Rotate all secrets for a service
        
        Args:
            service_name: Service to rotate secrets for
            format_type: "kubernetes", "encrypted", or "both"
            namespace: Kubernetes namespace
            
        Returns:
            List of created files
        """
        created_files = []
        
        if format_type in ["kubernetes", "both"]:
            # Create Kubernetes secret
            k8s_file = self.save_kubernetes_secret(service_name, namespace)
            created_files.append(k8s_file)
        
        if format_type in ["encrypted", "both"]:
            # Create encrypted secret for git
            enc_file = self.create_encrypted_secret(service_name, namespace)
            if enc_file:
                created_files.append(enc_file)
        
        return created_files
    
    def rotate_all_secrets(self, format_type="both", namespace="identity"):
        """Rotate secrets for all services
        
        Args:
            format_type: "kubernetes", "encrypted", or "both"
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary of service -> created files
        """
        services = ['samba4', 'authentik', 'cilium']
        rotated_services = {}
        
        print(f"🔐 Rotating secrets for all services...")
        
        for service in services:
            print(f"📝 Rotating {service} secrets...")
            files = self.rotate_service_secrets(service, format_type, namespace)
            rotated_services[service] = files
        
        self._print_rotation_summary(rotated_services, format_type)
        return rotated_services
    
    def _print_rotation_summary(self, rotated_services, format_type):
        """Print summary of secret rotation"""
        print(f"\n🔐 Secret rotation complete!")
        print(f"📁 Generated files:")
        
        for service, files in rotated_services.items():
            print(f"   {service}:")
            for file_path in files:
                print(f"     - {file_path}")
        
        print(f"\n⚠️  IMPORTANT NEXT STEPS:")
        if format_type in ["kubernetes", "both"]:
            print("1. Apply Kubernetes secrets: kubectl apply -f Secrets/")
            print("2. Restart deployments to use new credentials")
        if format_type in ["encrypted", "both"]:
            print("3. Commit encrypted secrets to git")
            print("4. Update Helm deployments to reference encrypted secrets")
        print("5. Store backup of old credentials securely")

    # ================================
    # UTILITY METHODS
    # ================================
    
    def _get_timestamp(self):
        """Get current timestamp for metadata"""
        return datetime.now().isoformat() + "Z"
    
    def decrypt_secret(self, secret_file: Path) -> Dict[str, Any]:
        """Decrypt a SOPS-encrypted file"""
        import subprocess
        import os
        result = subprocess.run(
            ['sops', '--decrypt', str(secret_file)],
            capture_output=True,
            text=True,
            env={**os.environ, 'SOPS_AGE_KEY_FILE': str(self.age_key_file)}
        )
        
        if result.returncode == 0:
            return yaml.safe_load(result.stdout)
        else:
            raise Exception(f"Failed to decrypt secret: {result.stderr}")
    
    def validate_age_setup(self):
        """Validate Age/SOPS encryption setup"""
        issues = []
        
        if not self.age_key_file.exists():
            issues.append("Age key file missing")
        if not self.sops_config.exists():
            issues.append("SOPS configuration missing")
            
        if issues:
            print(f"⚠️  Encryption setup issues: {', '.join(issues)}")
            print("   Run: manager.initialize_encryption()")
            return False
        
        print("✅ Age/SOPS encryption properly configured")
        return True
    
    def scan_security(self):
        """Scan for hardcoded passwords and security issues"""
        print("🔍 Scanning for security issues...")
        issues = []
        
        # Patterns that indicate potential hardcoded credentials
        dangerous_patterns = [
            r'password\s*[:=]\s*["\'][^"\']{3,}["\']',
            r'passwd\s*[:=]\s*["\'][^"\']{3,}["\']', 
            r'secret\s*[:=]\s*["\'][^"\']{8,}["\']',
            r'AdminPass123',
            r'postgres123',
            r'authentik.*password.*["\'][^"\']{3,}["\']',
            r'value:\s*["\'][^"\']*password[^"\']*["\']',
            r'USER.*value:\s*["\']admin;[^"\']+["\']'
        ]
        
        # Safe patterns (these are OK)
        safe_patterns = [
            r'password.*""',  # Empty passwords
            r'password.*lookup\(',  # Ansible password lookup
            r'lookup\(.*password.*\)',  # Ansible password lookup
            r'password.*\{\{.*\}\}',  # Template variables
            r'password.*valueFrom',  # Kubernetes secret references
            r'password.*existingSecret',  # External secret references
            r'existingSecret.*:',  # Secret references in YAML
            r'#.*password',  # Comments
            r'r["\'].*["\']',  # Regex patterns
            r'AdminPass123.*,',  # Regex pattern definitions
            r'postgres123.*,',  # Regex pattern definitions
            r'bind_password.*\$\{.*\}',  # Environment variable references
            r'\*\*.*Before.*\*\*:',  # Documentation before/after examples
            r'❌.*Before.*:',  # Documentation examples
            r'✅.*After.*:',  # Documentation examples
        ]
        
        # Get files to scan
        import glob
        import re
        extensions = ['*.py', '*.yaml', '*.yml', '*.json', '*.sh', '*.md']
        excluded_patterns = ['*.backup.*', '*.temp.*', '__pycache__', '.git', 'node_modules', '*.pyc']
        
        files = []
        for ext in extensions:
            files.extend(glob.glob(str(self.project_root / '**' / ext), recursive=True))
            
        # Filter out excluded patterns
        filtered_files = []
        for file_path in files:
            should_exclude = False
            for pattern in excluded_patterns:
                if pattern in file_path:
                    should_exclude = True
                    break
            if not should_exclude:
                filtered_files.append(file_path)
        
        # Scan files
        for file_path in filtered_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        # Skip if it matches safe patterns
                        is_safe = any(re.search(pattern, line, re.IGNORECASE) for pattern in safe_patterns)
                        if is_safe:
                            continue
                            
                        # Check for dangerous patterns
                        for pattern in dangerous_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                issues.append({
                                    'file': file_path,
                                    'line': line_num,
                                    'content': line.strip(),
                                    'type': 'hardcoded_credential'
                                })
            except Exception as e:
                print(f"⚠️  Error scanning {file_path}: {e}")
        
        if issues:
            print(f"🚨 Found {len(issues)} security issues:")
            for issue in issues:
                print(f"   {issue['file']}:{issue['line']} - {issue['content']}")
        else:
            print("✅ No hardcoded credentials found")
        
        return len(issues) == 0
    
    def list_secrets(self):
        """List all secret files in the project"""
        print("📁 NOAH Secret Files:")
        print(f"   Kubernetes secrets: {self.secrets_dir}")
        for file in self.secrets_dir.glob("*.yaml"):
            print(f"     - {file.name}")
            
        print(f"   Encrypted secrets:")
        for service_dir in self.helm_dir.glob("*/secrets"):
            print(f"     {service_dir.parent.name}:")
            for enc_file in service_dir.glob("*.enc.yaml"):
                print(f"       - {enc_file.name}")
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_files = list(self.project_root.glob("**/*.temp.*"))
        for temp_file in temp_files:
            temp_file.unlink()
            print(f"🗑️  Removed: {temp_file}")
        
        if temp_files:
            print(f"✅ Cleaned up {len(temp_files)} temporary files")
        else:
            print("✅ No temporary files to clean")


# ================================
# CLI INTERFACE
# ================================

def main():
    """Command-line interface for the security manager"""
    import sys
    
    manager = NoahSecurityManager()
    
    if len(sys.argv) < 2:
        print("""
🔐 NOAH Security Manager

Usage:
  python3 security_manager.py <command> [options]

Commands:
  init                     - Initialize Age/SOPS encryption
  rotate <service>         - Rotate secrets for specific service
  rotate-all              - Rotate secrets for all services  
  kubernetes <service>     - Generate Kubernetes secret only
  encrypted <service>      - Generate encrypted secret only
  list                    - List all secret files
  validate                - Validate encryption setup
  scan                    - Scan for hardcoded passwords
  cleanup                 - Clean up temporary files

Examples:
  python3 security_manager.py init
  python3 security_manager.py rotate samba4
  python3 security_manager.py rotate-all
  python3 security_manager.py kubernetes authentik
        """)
        return
    
    command = sys.argv[1]
    
    if command == "init":
        manager.initialize_encryption()
    elif command == "rotate":
        if len(sys.argv) > 2:
            service = sys.argv[2]
            manager.rotate_service_secrets(service)
        else:
            print("Usage: rotate <service>")
    elif command == "rotate-all":
        manager.rotate_all_secrets()
    elif command == "kubernetes":
        if len(sys.argv) > 2:
            service = sys.argv[2]
            manager.rotate_service_secrets(service, "kubernetes")
        else:
            print("Usage: kubernetes <service>")
    elif command == "encrypted":
        if len(sys.argv) > 2:
            service = sys.argv[2]
            manager.rotate_service_secrets(service, "encrypted")
        else:
            print("Usage: encrypted <service>")
    elif command == "list":
        manager.list_secrets()
    elif command == "validate":
        manager.validate_age_setup()
    elif command == "scan":
        manager.scan_security()
    elif command == "cleanup":
        manager.cleanup_temp_files()
    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see usage.")

if __name__ == "__main__":
    main()
