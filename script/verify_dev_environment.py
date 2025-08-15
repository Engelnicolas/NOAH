#!/usr/bin/env python3
"""
NOAH Development Environment Verification
Verify that the development environment is properly set up
"""

import os
import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_file_exists(file_path: Path, description: str) -> bool:
    """Check if a file exists and has proper permissions"""
    if file_path.exists():
        stat = file_path.stat()
        permissions = oct(stat.st_mode)[-3:]
        console.print(f"✅ {description}: {file_path} (permissions: {permissions})")
        return True
    else:
        console.print(f"❌ {description}: {file_path} - NOT FOUND")
        return False


def verify_sops_encryption() -> bool:
    """Verify SOPS can decrypt the secrets file"""
    secrets_file = Path("ansible/vars/secrets.yml")
    age_key_file = Path("age/keys.txt")
    
    if not secrets_file.exists() or not age_key_file.exists():
        console.print("❌ SOPS verification failed: missing files")
        return False
    
    try:
        env = os.environ.copy()
        env['SOPS_AGE_KEY_FILE'] = str(age_key_file)
        
        result = subprocess.run(
            ["sops", "--decrypt", str(secrets_file)],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            console.print("✅ SOPS decryption test: SUCCESS")
            return True
        else:
            console.print(f"❌ SOPS decryption test: FAILED - {result.stderr}")
            return False
            
    except Exception as e:
        console.print(f"❌ SOPS verification error: {e}")
        return False


def verify_certificate() -> bool:
    """Verify the certificate has correct domains"""
    cert_file = Path("certs/tls.crt")
    
    if not cert_file.exists():
        console.print("❌ Certificate verification failed: file not found")
        return False
    
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_file), "-text", "-noout"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            cert_text = result.stdout
            if "noah.local" in cert_text and "keycloak.noah.local" in cert_text:
                console.print("✅ Certificate verification: SUCCESS")
                return True
            else:
                console.print("❌ Certificate verification: Missing expected domains")
                return False
        else:
            console.print(f"❌ Certificate verification: FAILED - {result.stderr}")
            return False
            
    except Exception as e:
        console.print(f"❌ Certificate verification error: {e}")
        return False


def verify_environment_variables() -> bool:
    """Verify environment variables file"""
    env_file = Path(".env.dev")
    
    if not env_file.exists():
        console.print("❌ Environment file not found: .env.dev")
        return False
    
    try:
        with open(env_file) as f:
            content = f.read()
        
        required_vars = [
            "SOPS_AGE_KEY_FILE",
            "NOAH_DOMAIN",
            "NOAH_ENV",
            "NOAH_TLS_CERT",
            "NOAH_TLS_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
        
        if missing_vars:
            console.print(f"❌ Environment variables missing: {', '.join(missing_vars)}")
            return False
        else:
            console.print("✅ Environment variables: ALL PRESENT")
            return True
            
    except Exception as e:
        console.print(f"❌ Environment variables verification error: {e}")
        return False


def main():
    """Main verification function"""
    console.print(Panel.fit(
        "🔍 NOAH Development Environment Verification",
        title="Verification Script"
    ))
    
    all_checks_passed = True
    
    # File existence checks
    console.print("\n📁 File Existence Checks:")
    checks = [
        (Path("age/keys.txt"), "Age private key"),
        (Path("certs/tls.crt"), "TLS certificate"),
        (Path("certs/tls.key"), "TLS private key"),
        (Path("ansible/vars/secrets.yml"), "Encrypted secrets"),
        (Path(".sops.yaml"), "SOPS configuration"),
        (Path(".env.dev"), "Environment variables"),
    ]
    
    for file_path, description in checks:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # Functional checks
    console.print("\n🔧 Functional Checks:")
    
    if not verify_sops_encryption():
        all_checks_passed = False
    
    if not verify_certificate():
        all_checks_passed = False
    
    if not verify_environment_variables():
        all_checks_passed = False
    
    # Summary
    console.print("\n" + "="*60)
    if all_checks_passed:
        console.print(Panel.fit(
            "[bold green]🎉 All verification checks PASSED![/bold green]\n\n"
            "Your NOAH development environment is ready!\n\n"
            "[bold cyan]Next steps:[/bold cyan]\n"
            "1. source .env.dev\n"
            "2. ./noah.py deploy --profile dev",
            title="✅ Verification SUCCESS"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ Some verification checks FAILED![/bold red]\n\n"
            "Please run the setup again:\n\n"
            "[bold cyan]./noah.py dev-setup --force[/bold cyan]",
            title="❌ Verification FAILED"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
