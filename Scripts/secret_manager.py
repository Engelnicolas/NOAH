"""Secret management with SOPS and Age"""

import os
import subprocess
import json
import secrets
import string
from pathlib import Path
from typing import Dict, Any, Optional
import base64

# Optional imports with graceful fallbacks
yaml: Optional[Any] = None
try:
    import yaml  # type: ignore
except ImportError:
    pass

class SecretManager:
    def __init__(self, config_loader):
        self.config = config_loader
        self.age_key_file = Path(self.config.get('AGE_KEY_FILE', './Age/keys.txt'))
        self.sops_config = Path('.sops.yaml')
        
    def initialize_age(self):
        """Initialize Age encryption keys"""
        # Create Age directory if it doesn't exist
        self.age_key_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.age_key_file.exists():
            # Generate new Age key
            result = subprocess.run(
                ['age-keygen'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.age_key_file.write_text(result.stdout)
                os.chmod(self.age_key_file, 0o600)
                print(f"Age key generated and saved to {self.age_key_file}")
                
                # Extract public key
                for line in result.stdout.split('\n'):
                    if line.startswith('# public key:'):
                        public_key = line.split(':')[1].strip()
                        print(f"Public key: {public_key}")
                        return public_key
            else:
                raise Exception(f"Failed to generate Age key: {result.stderr}")
        else:
            print(f"Age key already exists at {self.age_key_file}")
            return self._get_public_key()
    
    def _get_public_key(self) -> str:
        """Extract public key from Age key file"""
        content = self.age_key_file.read_text()
        for line in content.split('\n'):
            if line.startswith('# public key:'):
                return line.split(':')[1].strip()
        raise Exception("Could not find public key in Age key file")
    
    def configure_sops(self):
        """Configure SOPS with Age"""
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
        
        if yaml is None:
            raise Exception("PyYAML is required for SOPS configuration. Install with: pip install PyYAML")
        
        with open(self.sops_config, 'w') as f:
            yaml.dump(sops_config, f)
        
        print(f"SOPS configuration written to {self.sops_config}")
    
    def generate_password(self, length: int = 24) -> str:
        """Generate a secure random password (max 24 characters)"""
        # Ensure we never exceed 24 characters
        max_length = min(length, 24)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(max_length))
    
    def generate_service_secrets(self, service: str, namespace: str):
        """Generate encrypted secrets for a service with password coordination"""
        secrets_dir = Path(f"./Helm/{service}/secrets")
        secrets_dir.mkdir(parents=True, exist_ok=True)
        
        secret_file = secrets_dir / f"{service}-secrets.yaml"
        
        # Check if secrets already exist and reuse passwords if they do
        existing_passwords = self._get_existing_passwords(service, secrets_dir)
        
        # Generate service-specific secrets, reusing existing passwords where possible
        service_secrets = self._generate_service_specific_secrets(service, existing_passwords)
        
        # Create Kubernetes secret manifest
        k8s_secret = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {
                'name': f'{service}-secrets',
                'namespace': namespace
            },
            'type': 'Opaque',
            'stringData': service_secrets
        }
        
        # Write encrypted file directly
        encrypted_file = secrets_dir / f"{service}-secrets.enc.yaml"
        
        if yaml is None:
            raise Exception("PyYAML is required for secret generation. Install with: pip install PyYAML")
        
        with open(encrypted_file, 'w') as f:
            yaml.dump(k8s_secret, f)
        
        # Encrypt with SOPS in-place
        result = subprocess.run(
            ['sops', '--encrypt', '--in-place', str(encrypted_file)],
            capture_output=True,
            text=True,
            env={**os.environ, 'SOPS_AGE_KEY_FILE': str(self.age_key_file)}
        )
        
        if result.returncode == 0:
            print(f"Encrypted secrets saved to {encrypted_file}")
            # Also create a values file for immediate use
            self._create_helm_values_file(service, service_secrets, secrets_dir)
        else:
            raise Exception(f"Failed to encrypt secrets: {result.stderr}")
    
    def _get_existing_passwords(self, service: str, secrets_dir: Path) -> Dict[str, str]:
        """Get existing passwords from encrypted secrets to maintain consistency"""
        encrypted_file = secrets_dir / f"{service}-secrets.enc.yaml"
        
        if not encrypted_file.exists():
            return {}
        
        try:
            decrypted = self.decrypt_secret(encrypted_file)
            if isinstance(decrypted, dict) and decrypted.get('kind') == 'Secret':
                return decrypted.get('stringData', {})
        except Exception as e:
            print(f"Warning: Could not decrypt existing secrets: {e}")
            return {}
        
        return {}
    
    def _create_helm_values_file(self, service: str, secrets: Dict[str, str], secrets_dir: Path):
        """Create a Helm values file with the correct password structure"""
        if service == 'authentik':
            values = {
                'authentik': {
                    'secretKey': secrets.get('secret_key', ''),
                },
                'postgresql': {
                    'auth': {
                        'password': secrets.get('postgresql_password', ''),
                        'username': 'authentik',
                        'database': 'authentik'
                    }
                },
                'redis': {
                    'auth': {
                        'enabled': True,
                        'password': secrets.get('redis_password', '')
                    }
                }
            }
            
            values_file = secrets_dir / f"{service}-values.yaml"
            if yaml is None:
                raise Exception("PyYAML is required for values file creation. Install with: pip install PyYAML")
            
            with open(values_file, 'w') as f:
                yaml.dump(values, f)
            
            print(f"Helm values file created at {values_file}")
    
    def _generate_service_specific_secrets(self, service: str, existing: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate service-specific secrets (all ≤ 24 characters), reusing existing passwords"""
        if existing is None:
            existing = {}
            
        if service == 'samba4':
            return {
                'admin_password': existing.get('admin_password', self.generate_password(24)),
                'domain_admin_password': existing.get('domain_admin_password', self.generate_password(24)),
                'kerberos_password': existing.get('kerberos_password', self.generate_password(24))
            }
        elif service == 'authentik':
            return {
                'secret_key': existing.get('secret_key', self.generate_password(24)),
                'bootstrap_password': existing.get('bootstrap_password', self.generate_password(24)),
                'bootstrap_token': existing.get('bootstrap_token', self.generate_password(24)),
                'postgresql_password': existing.get('postgresql_password', self.generate_password(24)),
                'redis_password': existing.get('redis_password', self.generate_password(24))
            }
        elif service == 'cilium':
            return {
                'hubble_relay_client_cert': existing.get('hubble_relay_client_cert', self._generate_self_signed_cert()),
                'hubble_relay_client_key': existing.get('hubble_relay_client_key', self._generate_private_key()),
                'identity_allocation_psk': existing.get('identity_allocation_psk', self.generate_password(24))
            }
        else:
            return {
                'default_password': existing.get('default_password', self.generate_password(24)),
                'api_key': existing.get('api_key', self.generate_password(24))
            }
    
    def _generate_self_signed_cert(self) -> str:
        """Generate a self-signed certificate (≤24 chars for demo)"""
        # For demo purposes, generate a short placeholder
        # In production, this would be a proper certificate
        return self.generate_password(24)
    
    def _generate_private_key(self) -> str:
        """Generate a private key (≤24 chars for demo)"""
        # For demo purposes, generate a short placeholder  
        # In production, this would be a proper private key
        return self.generate_password(24)
    
    def rotate_passwords(self, service: str):
        """Rotate passwords for a service"""
        print(f"Rotating passwords for {service}")
        namespace = 'identity' if service in ['samba4', 'authentik'] else 'kube-system'
        self.generate_service_secrets(service, namespace)
        print(f"Password rotation complete for {service}")
    
    def validate_service_secrets(self, service: str, namespace: str) -> bool:
        """Validate that all secrets for a service are consistent"""
        try:
            if service == 'authentik':
                return self._validate_authentik_secrets(namespace)
            elif service == 'samba4':
                return self._validate_samba4_secrets(namespace)
            else:
                print(f"[INFO] No validation implemented for service: {service}")
                return True
        except Exception as e:
            print(f"[ERROR] Secret validation failed for {service}: {e}")
            return False
    
    def _validate_authentik_secrets(self, namespace: str) -> bool:
        """Validate that authentik secrets are consistent across all components"""
        import subprocess
        import base64
        
        try:
            # Get passwords from different sources
            secrets = {}
            
            # Get from main authentik secret
            result = subprocess.run([
                'kubectl', 'get', 'secret', 'authentik-secret', '-n', namespace,
                '-o', 'jsonpath={.data}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                secrets['authentik_postgresql'] = base64.b64decode(data.get('postgresql-password', '')).decode()
                secrets['authentik_redis'] = base64.b64decode(data.get('redis-password', '')).decode()
            
            # Get from postgresql secret
            result = subprocess.run([
                'kubectl', 'get', 'secret', 'authentik-postgresql', '-n', namespace,
                '-o', 'jsonpath={.data.password}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                secrets['postgresql_actual'] = base64.b64decode(result.stdout).decode()
            
            # Get from redis secret
            result = subprocess.run([
                'kubectl', 'get', 'secret', 'authentik-redis', '-n', namespace,
                '-o', 'jsonpath={.data.redis-password}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                secrets['redis_actual'] = base64.b64decode(result.stdout).decode()
            
            # Validate consistency
            validation_results = []
            
            if 'authentik_postgresql' in secrets and 'postgresql_actual' in secrets:
                pg_match = secrets['authentik_postgresql'] == secrets['postgresql_actual']
                validation_results.append(('PostgreSQL passwords', pg_match))
                if not pg_match:
                    print(f"[ERROR] PostgreSQL password mismatch: authentik-secret vs authentik-postgresql")
            
            if 'authentik_redis' in secrets and 'redis_actual' in secrets:
                redis_match = secrets['authentik_redis'] == secrets['redis_actual']
                validation_results.append(('Redis passwords', redis_match))
                if not redis_match:
                    print(f"[ERROR] Redis password mismatch: authentik-secret vs authentik-redis")
            
            all_valid = all(result[1] for result in validation_results)
            
            if all_valid:
                print(f"[SUCCESS] All authentik secrets are consistent")
            else:
                print(f"[ERROR] Authentik secret validation failed")
                for name, valid in validation_results:
                    status = "✅" if valid else "❌"
                    print(f"  {status} {name}")
            
            return all_valid
            
        except Exception as e:
            print(f"[ERROR] Failed to validate authentik secrets: {e}")
            return False
    
    def _validate_samba4_secrets(self, namespace: str) -> bool:
        """Validate samba4 secrets (placeholder for future implementation)"""
        print(f"[INFO] Samba4 secret validation not yet implemented")
        return True

    def decrypt_secret(self, secret_file: Path) -> Dict[str, Any]:
        """Decrypt a SOPS-encrypted file"""
        result = subprocess.run(
            ['sops', '--decrypt', str(secret_file)],
            capture_output=True,
            text=True,
            env={**os.environ, 'SOPS_AGE_KEY_FILE': str(self.age_key_file)}
        )
        
        if result.returncode == 0:
            if yaml is None:
                raise Exception("PyYAML is required for secret decryption. Install with: pip install PyYAML")
            return yaml.safe_load(result.stdout)
        else:
            raise Exception(f"Failed to decrypt secret: {result.stderr}")
    
    def generate_tls_certificates(self, domain: str):
        """Generate self-signed TLS certificates for a domain using openssl"""
        certs_dir = Path("Certificates")
        certs_dir.mkdir(exist_ok=True)
        
        ca_cert_path = certs_dir / "ca.crt"
        ca_key_path = certs_dir / "ca.key"
        wildcard_cert_path = certs_dir / f"*.{domain}.crt"
        wildcard_key_path = certs_dir / f"*.{domain}.key"
        
        # Check if openssl is available
        try:
            subprocess.run(['openssl', 'version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("OpenSSL is required for TLS certificate generation. Please install OpenSSL.")
        
        # Generate CA private key
        subprocess.run([
            'openssl', 'genrsa', '-out', str(ca_key_path), '2048'
        ], check=True, capture_output=True)
        
        # Generate CA certificate
        subprocess.run([
            'openssl', 'req', '-new', '-x509', '-key', str(ca_key_path),
            '-out', str(ca_cert_path), '-days', '3650', '-subj',
            f'/C=FR/ST=FR/L=LYON/O=NOAH Infrastructure/CN=NOAH CA for {domain}'
        ], check=True, capture_output=True)
        
        # Generate wildcard private key
        subprocess.run([
            'openssl', 'genrsa', '-out', str(wildcard_key_path), '2048'
        ], check=True, capture_output=True)
        
        # Generate wildcard certificate signing request
        csr_path = certs_dir / f"*.{domain}.csr"
        subprocess.run([
            'openssl', 'req', '-new', '-key', str(wildcard_key_path),
            '-out', str(csr_path), '-subj',
            f'/C=FR/ST=FR/L=LYON/O=NOAH Infrastructure/CN=*.{domain}'
        ], check=True, capture_output=True)
        
        # Generate wildcard certificate signed by CA
        subprocess.run([
            'openssl', 'x509', '-req', '-in', str(csr_path),
            '-CA', str(ca_cert_path), '-CAkey', str(ca_key_path),
            '-CAcreateserial', '-out', str(wildcard_cert_path),
            '-days', '365', '-extensions', 'v3_req'
        ], check=True, capture_output=True)
        
        # Clean up CSR
        csr_path.unlink(missing_ok=True)
        
        print(f"✓ TLS certificates generated for {domain}")
        print(f"  - CA Certificate: {ca_cert_path}")
        print(f"  - CA Key: {ca_key_path}")
        print(f"  - Wildcard Certificate: {wildcard_cert_path}")
        print(f"  - Wildcard Key: {wildcard_key_path}")
    
    def list_certificates(self):
        """List existing TLS certificates"""
        certs_dir = Path("Certificates")
        if not certs_dir.exists():
            print("No certificates directory found")
            return
        
        cert_files = list(certs_dir.glob("*.crt"))
        if not cert_files:
            print("No certificates found")
            return
        
        print("Found certificates:")
        for cert_file in cert_files:
            print(f"  - {cert_file.name}")
    
    def cleanup_local_secrets(self):
        """Clean up local secrets and certificates"""
        print("Cleaning up local secrets and certificates...")
        
        # Remove Age keys
        age_dir = Path("Age")
        if age_dir.exists():
            for file in age_dir.iterdir():
                file.unlink()
            age_dir.rmdir()
            print("  - Removed Age keys")
        
        # Remove certificates
        certs_dir = Path("Certificates")
        if certs_dir.exists():
            for file in certs_dir.iterdir():
                file.unlink()
            certs_dir.rmdir()
            print("  - Removed TLS certificates")
        
        # Remove SOPS config
        sops_config = Path(".sops.yaml")
        if sops_config.exists():
            sops_config.unlink()
            print("  - Removed SOPS configuration")
        
        print("Local secrets cleanup complete")
