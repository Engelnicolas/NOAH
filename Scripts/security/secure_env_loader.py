#!/usr/bin/env python3
"""
NOAH Secure Environment Loader
Loads environment variables from encrypted .env files using SOPS
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging
import yaml

from Scripts.utils.paths import NOAH_PATHS  # centralized path resolution
from Scripts.utils.dict_utils import flatten_mapping  # shared flatten helper
from Scripts.security.sops_client import SopsClient, SopsError

logger = logging.getLogger(__name__)

class SecureEnvLoader:
    """Load environment variables from SOPS-encrypted files.

    Parameters
    -----------
    noah_root : Path | None
        Base directory for NOAH repository. Defaults to NOAH_PATHS['root_dir'].
    age_key_file : Path | None
        Override path to Age keys file.
    sops_config : Path | None
        Override path to SOPS config file.
    """

    def __init__(
        self,
        noah_root: Optional[Path] = None,
        age_key_file: Optional[Path] = None,
        sops_config: Optional[Path] = None,
    ):
        root = noah_root or NOAH_PATHS['root_dir']
        self.noah_root = Path(root)
        self.sops_config = sops_config or Path(NOAH_PATHS['sops_config'])
        self.age_key_file = age_key_file or Path(NOAH_PATHS['age_key_file'])
        
    def check_sops_available(self) -> bool:
        """Check if SOPS is available in the system."""
        return SopsClient.is_available()

    def check_age_key_available(self) -> bool:
        """Check if Age key file exists and is readable"""
        return self.age_key_file.exists() and self.age_key_file.is_file()
    
    def decrypt_env_file(self, encrypted_file: Path) -> Optional[Dict[str, str]]:
        """Decrypt a SOPS-encrypted YAML env file and return flattened key-value pairs."""
        if not encrypted_file.exists():
            logger.warning("Encrypted file not found: %s", encrypted_file)
            return None

        try:
            with SopsClient(self.age_key_file, self.sops_config) as sops:
                raw = sops.decrypt_to_string(encrypted_file)
        except SopsError as e:
            logger.error("SOPS decryption failed for %s: %s", encrypted_file, e)
            return None

        config = yaml.safe_load(raw) or {}
        if not isinstance(config, dict):
            logger.error("Decrypted content is not a mapping")
            return None

        env_vars = flatten_mapping(config)
        logger.info("Successfully loaded %d environment variables from YAML", len(env_vars))
        return env_vars
    
    def read_secure_env(self, encrypted_file: Optional[Path] = None) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """Return decrypted environment mapping without mutating os.environ.

        Returns (env_dict, error_message). On success error_message is None.
        """
        if encrypted_file is None:
            # Search default candidates
            for candidate in (
                self.noah_root / ".env.enc",
                self.noah_root / "config.env.enc",
                self.noah_root / "secrets.env.enc",
            ):
                if candidate.exists():
                    encrypted_file = candidate
                    break
            else:
                return None, "No encrypted environment file found"

        env_vars = self.decrypt_env_file(encrypted_file)
        if env_vars is None:
            return None, f"Failed to decrypt: {encrypted_file}"
        return env_vars, None

    def load_secure_env(self, encrypted_file: Optional[Path] = None) -> bool:
        """Load environment variables from encrypted file into os.environ."""
        env_vars, error = self.read_secure_env(encrypted_file)
        if env_vars is None:
            logger.warning(error)
            return False
        
        # Load into environment
        for key, value in env_vars.items():
            os.environ[key] = value
        
        logger.info(f"Loaded secure environment from {encrypted_file}")
        return True
    
    def create_encrypted_env(self, source_file: Path, target_file: Path) -> bool:
        """Encrypt a plain .env file using SOPS."""
        if not source_file.exists():
            logger.error("Source file not found: %s", source_file)
            return False

        from Scripts.security.sops_client import SopsEncryptionError
        try:
            with SopsClient(self.age_key_file, self.sops_config) as sops:
                sops.encrypt_to(source_file, target_file)
            logger.info("Successfully encrypted %s to %s", source_file, target_file)
            return True
        except SopsEncryptionError as e:
            logger.error("SOPS encryption failed: %s", e)
            return False

# Convenience functions for NOAH
def load_noah_secure_env(noah_root: Optional[Path] = None, *, return_mapping: bool = False):
    """Load NOAH secure environment variables.

    If return_mapping=True, returns (mapping | None, success_bool) without mutating
    the environment when mapping is None.
    """
    loader = SecureEnvLoader(noah_root)
    if return_mapping:
        mapping, err = loader.read_secure_env()
        return mapping, err is None
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
