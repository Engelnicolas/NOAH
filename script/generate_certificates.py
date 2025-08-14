#!/usr/bin/env python3
"""
NOAH Certificate Generator
Generate self-signed certificates for NOAH development environment
"""

import os
import subprocess
import tempfile
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
from rich.console import Console
from rich.panel import Panel

console = Console()


class CertificateGenerator:
    """Generate self-signed certificates for NOAH platform"""
    
    def __init__(self, domain: str = "noah.local", cert_dir: str = "./certs", 
                 days_valid: int = 365):
        self.domain = domain
        self.cert_dir = Path(cert_dir)
        self.days_valid = days_valid
        
        # NOAH platform subdomains
        self.subdomains = [
            self.domain,
            f"*.{self.domain}",
            f"keycloak.{self.domain}",
            f"grafana.{self.domain}",
            f"gitlab.{self.domain}",
            f"mattermost.{self.domain}",
            f"nextcloud.{self.domain}",
            f"prometheus.{self.domain}",
            f"alertmanager.{self.domain}",
            f"wazuh.{self.domain}",
            f"samba.{self.domain}"
        ]
    
    def generate_private_key(self) -> rsa.RSAPrivateKey:
        """Generate RSA private key"""
        console.print("🔑 Generating RSA private key (2048 bits)...")
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
    
    def create_certificate(self, private_key: rsa.RSAPrivateKey) -> x509.Certificate:
        """Create self-signed certificate with SAN"""
        console.print(f"📜 Creating self-signed certificate for {self.domain}...")
        
        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NOAH"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.domain),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, f"admin@{self.domain}"),
        ])
        
        # Create SAN (Subject Alternative Names)
        san_list = [x509.DNSName(subdomain) for subdomain in self.subdomains]
        
        # Build certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.now(datetime.timezone.utc)
        ).not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=self.days_valid)
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(private_key, hashes.SHA256())
        
        return cert
    
    def save_certificate_files(self, private_key: rsa.RSAPrivateKey, certificate: x509.Certificate):
        """Save private key and certificate to files"""
        # Create certificate directory
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Save private key
        key_path = self.cert_dir / "tls.key"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save certificate
        cert_path = self.cert_dir / "tls.crt"
        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))
        
        console.print(f"✅ Certificate files saved:")
        console.print(f"   Private Key: {key_path}")
        console.print(f"   Certificate: {cert_path}")
    
    def display_certificate_info(self):
        """Display certificate information"""
        cert_path = self.cert_dir / "tls.crt"
        if not cert_path.exists():
            console.print("[red]❌ Certificate file not found[/red]")
            return
        
        try:
            # Load and parse certificate
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            certificate = x509.load_pem_x509_certificate(cert_data)
            
            # Display certificate details
            console.print("\n📋 Certificate Information:")
            console.print(f"   Subject: {certificate.subject.rfc4514_string()}")
            console.print(f"   Valid from: {certificate.not_valid_before}")
            console.print(f"   Valid until: {certificate.not_valid_after}")
            
            # Display SAN
            try:
                san_ext = certificate.extensions.get_extension_for_oid(
                    ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                san_names = [name.value for name in san_ext.value]
                console.print(f"   Subject Alternative Names:")
                for name in san_names:
                    console.print(f"     - {name}")
            except x509.ExtensionNotFound:
                console.print("   No Subject Alternative Names found")
                
        except Exception as e:
            console.print(f"[red]❌ Error reading certificate: {e}[/red]")
    
    def generate(self) -> bool:
        """Generate complete certificate set"""
        try:
            console.print(Panel.fit(
                f"🔐 Generating Self-Signed Certificates\n"
                f"Domain: {self.domain}\nValid for: {self.days_valid} days",
                title="NOAH Certificate Generator"
            ))
            
            # Generate private key
            private_key = self.generate_private_key()
            
            # Create certificate
            certificate = self.create_certificate(private_key)
            
            # Save files
            self.save_certificate_files(private_key, certificate)
            
            # Display certificate info
            self.display_certificate_info()
            
            console.print("\n🔧 [bold green]Next steps:[/bold green]")
            console.print("   1. Run: [bold cyan]python script/update_tls_secrets.py[/bold cyan]")
            console.print("   2. Or manually update ansible/vars/secrets.yml with SOPS")
            console.print("   3. Deploy: [bold cyan]./noah.py deploy[/bold cyan]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Certificate generation failed: {e}[/red]")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate self-signed certificates for NOAH platform")
    parser.add_argument("--domain", default="noah.local", 
                       help="Primary domain name")
    parser.add_argument("--cert-dir", default="./certs", 
                       help="Certificate output directory")
    parser.add_argument("--days", type=int, default=365, 
                       help="Certificate validity in days")
    
    args = parser.parse_args()
    
    generator = CertificateGenerator(
        domain=args.domain,
        cert_dir=args.cert_dir,
        days_valid=args.days
    )
    
    success = generator.generate()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
