#!/usr/bin/env python3
"""
NOAH Secure Environment Loader
Loads environment variables from encrypted .env files using SOPS
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SecureEnvLoader:
    """Load environment variables from SOPS-encrypted files"""
    
    def __init__(self, noah_root: Optional[Path] = None):
        self.noah_root = noah_root or Path.cwd()
        self.sops_config = self.noah_root / ".sops.yaml"
        self.age_key_file = self.noah_root / "Age" / "keys.txt"
        
    def check_sops_available(self) -> bool:
        """Check if SOPS is available in the system"""
        try:
            result = subprocess.run(['sops', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def check_age_key_available(self) -> bool:
        """Check if Age key file exists and is readable"""
        return self.age_key_file.exists() and self.age_key_file.is_file()
    
    def decrypt_env_file(self, encrypted_file: Path) -> Optional[Dict[str, str]]:
        """Decrypt a SOPS-encrypted .env file and return key-value pairs"""
        if not encrypted_file.exists():
            logger.warning(f"Encrypted file not found: {encrypted_file}")
            return None
        
        if not self.check_sops_available():
            logger.error("SOPS not available - cannot decrypt environment file")
            return None
        
        if not self.check_age_key_available():
            logger.error(f"Age key file not found: {self.age_key_file}")
            return None
        
        try:
            # Set Age key file for SOPS
            env = os.environ.copy()
            env['SOPS_AGE_KEY_FILE'] = str(self.age_key_file)
            
            # Decrypt the file
            result = subprocess.run(
                ['sops', '--decrypt', str(encrypted_file)],
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"SOPS decryption failed: {result.stderr}")
                return None
            
            # Parse the decrypted content as YAML format
            import yaml
            config = yaml.safe_load(result.stdout)
            
            # Flatten the nested YAML structure into environment variables
            env_vars = {}
            
            def flatten_dict(d, parent_key='', sep='_'):
                """Recursively flatten nested dictionary"""
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key.upper(), sep).items())
                    else:
                        items.append((new_key.upper(), str(v)))
                return dict(items)
            
            env_vars = flatten_dict(config)
            
            logger.info(f"Successfully loaded {len(env_vars)} environment variables from YAML")
            return env_vars
            
        except Exception as e:
            logger.error(f"Error decrypting environment file: {e}")
            return None
    
    def load_secure_env(self, encrypted_file: Optional[Path] = None) -> bool:
        """Load environment variables from encrypted file into os.environ"""
        if encrypted_file is None:
            # Try default locations
            possible_files = [
                self.noah_root / ".env.enc",
                self.noah_root / "config.env.enc",
                self.noah_root / "secrets.env.enc"
            ]
            
            for file_path in possible_files:
                if file_path.exists():
                    encrypted_file = file_path
                    break
            else:
                logger.warning("No encrypted environment file found")
                return False
        
        env_vars = self.decrypt_env_file(encrypted_file)
        if env_vars is None:
            return False
        
        # Load into environment
        for key, value in env_vars.items():
            os.environ[key] = value
        
        logger.info(f"Loaded secure environment from {encrypted_file}")
        return True
    
    def create_encrypted_env(self, source_file: Path, target_file: Path) -> bool:
        """Encrypt a plain .env file using SOPS"""
        if not source_file.exists():
            logger.error(f"Source file not found: {source_file}")
            return False
        
        if not self.check_sops_available():
            logger.error("SOPS not available - cannot encrypt environment file")
            return False
        
        try:
            # Set Age key file for SOPS
            env = os.environ.copy()
            env['SOPS_AGE_KEY_FILE'] = str(self.age_key_file)
            
            # Encrypt the file
            result = subprocess.run(
                ['sops', '--encrypt', '--output', str(target_file), str(source_file)],
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                logger.error(f"SOPS encryption failed: {result.stderr}")
                return False
            
            logger.info(f"Successfully encrypted {source_file} to {target_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error encrypting environment file: {e}")
            return False

# Convenience functions for NOAH
def load_noah_secure_env(noah_root: Optional[Path] = None) -> bool:
    """Load NOAH secure environment variables"""
    loader = SecureEnvLoader(noah_root)
    return loader.load_secure_env()

def create_noah_encrypted_env(source_env: Optional[Path] = None, 
                             target_name: str = ".env.enc") -> bool:
    """Create encrypted environment file for NOAH"""
    noah_root = Path.cwd()
    if source_env is None:
        source_env = noah_root / ".env"
    
    target_file = noah_root / target_name
    loader = SecureEnvLoader(noah_root)
    return loader.create_encrypted_env(source_env, target_file)

if __name__ == "__main__":
    # CLI usage for testing
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="NOAH Secure Environment Loader")
    parser.add_argument("--encrypt", metavar="SOURCE", 
                       help="Encrypt a .env file")
    parser.add_argument("--decrypt", metavar="ENCRYPTED", 
                       help="Decrypt and display a .env.enc file")
    parser.add_argument("--load", action="store_true",
                       help="Load encrypted environment into current process")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(levelname)s: %(message)s')
    
    loader = SecureEnvLoader()
    
    if args.encrypt:
        source = Path(args.encrypt)
        target = source.parent / f"{source.name}.enc"
        if loader.create_encrypted_env(source, target):
            print(f"✅ Encrypted {source} → {target}")
            sys.exit(0)
        else:
            print(f"❌ Failed to encrypt {source}")
            sys.exit(1)
    
    elif args.decrypt:
        encrypted = Path(args.decrypt)
        env_vars = loader.decrypt_env_file(encrypted)
        if env_vars:
            print("# Decrypted environment variables:")
            for key, value in env_vars.items():
                print(f"{key}={value}")
            sys.exit(0)
        else:
            print(f"❌ Failed to decrypt {encrypted}")
            sys.exit(1)
    
    elif args.load:
        if loader.load_secure_env():
            print("✅ Secure environment loaded successfully")
            sys.exit(0)
        else:
            print("❌ Failed to load secure environment")
            sys.exit(1)
    
    else:
        parser.print_help()
