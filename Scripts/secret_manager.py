"""Secret management with SOPS and Age"""

import os
import subprocess
import json
import secrets
import string
import yaml
from pathlib import Path
from typing import Dict, Any
import base64

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
        
        with open(self.sops_config, 'w') as f:
            yaml.dump(sops_config, f)
        
        print(f"SOPS configuration written to {self.sops_config}")
    
    def generate_password(self, length: int = 24) -> str:
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_service_secrets(self, service: str, namespace: str):
        """Generate encrypted secrets for a service"""
        secrets_dir = Path(f"./Helm/{service}/secrets")
        secrets_dir.mkdir(parents=True, exist_ok=True)
        
        secret_file = secrets_dir / f"{service}-secrets.yaml"
        
        # Generate service-specific secrets
        service_secrets = self._generate_service_specific_secrets(service)
        
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
        
        # Write unencrypted file temporarily
        temp_file = secrets_dir / f"{service}-secrets.temp.yaml"
        with open(temp_file, 'w') as f:
            yaml.dump(k8s_secret, f)
        
        # Encrypt with SOPS
        encrypted_file = secrets_dir / f"{service}-secrets.enc.yaml"
        result = subprocess.run(
            ['sops', '--encrypt', '--age', self._get_public_key(), 
             str(temp_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            encrypted_file.write_text(result.stdout)
            temp_file.unlink()  # Remove temporary file
            print(f"Encrypted secrets saved to {encrypted_file}")
        else:
            raise Exception(f"Failed to encrypt secrets: {result.stderr}")
    
    def _generate_service_specific_secrets(self, service: str) -> Dict[str, str]:
        """Generate service-specific secrets"""
        if service == 'samba4':
            return {
                'admin_password': self.generate_password(),
                'domain_admin_password': self.generate_password(),
                'kerberos_password': self.generate_password()
            }
        elif service == 'authentik':
            return {
                'secret_key': secrets.token_urlsafe(50),
                'bootstrap_password': self.generate_password(),
                'bootstrap_token': secrets.token_urlsafe(50),
                'postgresql_password': self.generate_password(),
                'redis_password': self.generate_password()
            }
        elif service == 'cilium':
            return {
                'hubble_relay_client_cert': self._generate_self_signed_cert(),
                'hubble_relay_client_key': self._generate_private_key(),
                'identity_allocation_psk': secrets.token_hex(32)
            }
        else:
            return {
                'default_password': self.generate_password(),
                'api_key': secrets.token_urlsafe(50)
            }
    
    def _generate_self_signed_cert(self) -> str:
        """Generate a self-signed certificate"""
        # This is a placeholder - implement proper certificate generation
        return base64.b64encode(b"CERTIFICATE_PLACEHOLDER").decode()
    
    def _generate_private_key(self) -> str:
        """Generate a private key"""
        # This is a placeholder - implement proper key generation
        return base64.b64encode(b"PRIVATE_KEY_PLACEHOLDER").decode()
    
    def rotate_passwords(self, service: str):
        """Rotate passwords for a service"""
        print(f"Rotating passwords for {service}")
        namespace = 'identity' if service in ['samba4', 'authentik'] else 'kube-system'
        self.generate_service_secrets(service, namespace)
        print(f"Password rotation complete for {service}")
    
    def decrypt_secret(self, secret_file: Path) -> Dict[str, Any]:
        """Decrypt a SOPS-encrypted file"""
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
    
    def generate_tls_certificates(self, domain: str):
        """Generate self-signed TLS certificates for a domain"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
        
        certs_dir = Path("Certificates")
        certs_dir.mkdir(exist_ok=True)
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate CA certificate
        ca_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NOAH Infrastructure"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"NOAH CA for {domain}"),
        ])
        
        ca_cert = x509.CertificateBuilder().subject_name(
            ca_name
        ).issuer_name(
            ca_name
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
            ]),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).sign(private_key, hashes.SHA256())
        
        # Write CA certificate and key
        ca_cert_path = certs_dir / "ca.crt"
        ca_key_path = certs_dir / "ca.key"
        
        with open(ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(ca_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Generate wildcard certificate
        wildcard_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        wildcard_name = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NOAH Infrastructure"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"*.{domain}"),
        ])
        
        wildcard_cert = x509.CertificateBuilder().subject_name(
            wildcard_name
        ).issuer_name(
            ca_name
        ).public_key(
            wildcard_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write wildcard certificate and key
        wildcard_cert_path = certs_dir / f"*.{domain}.crt"
        wildcard_key_path = certs_dir / f"*.{domain}.key"
        
        with open(wildcard_cert_path, "wb") as f:
            f.write(wildcard_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(wildcard_key_path, "wb") as f:
            f.write(wildcard_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
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
