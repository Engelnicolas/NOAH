# NOAH Encrypted Password System

## Overview

NOAH now uses SOPS (Secrets OPerationS) encryption with Age keys to securely store all passwords and sensitive configuration data. This replaces the previous unencrypted `.env` file system.

## Security Features

✅ **SOPS Encryption**: All sensitive data encrypted using industry-standard SOPS
✅ **Age Key Management**: Uses Age keys for secure encryption/decryption 
✅ **No Plain Text Secrets**: All passwords stored encrypted at rest
✅ **Environment Variable Compatibility**: Seamless integration with existing code
✅ **Git Security**: `.gitignore` updated to prevent accidental plain text commits

## Files

### Encrypted Configuration
- `config.enc.yaml` - Main encrypted configuration file (SOPS encrypted)
- `Age/keys.txt` - Age encryption keys (existing)
- `.sops.yaml` - SOPS configuration rules

### Security Implementation  
- `Scripts/secure_env_loader.py` - SecureEnvLoader class for handling encrypted configs
- Updated `noah.py` - Now uses SecureEnvLoader instead of dotenv

### Removed Files (Security)
- ❌ `.env` - Removed (was unencrypted)
- ❌ `.env.secure` - Removed (was unencrypted)

## Configuration Structure

The `config.enc.yaml` file contains all configuration in YAML format:

```yaml
noah:
  version: "0.0.1"
  domain: "noah-infra.com"

authentik:
  secret_key: "encrypted_value"
  bootstrap_password: "encrypted_value"
  postgresql_password: "encrypted_value"
  # ... other secrets

kubernetes:
  cluster_name: "noah-cluster"
  # ... other config

# ... other sections
```

## Usage

### Automatic Loading
The system automatically loads encrypted configuration when `noah.py` runs:

```python
from Scripts.secure_env_loader import SecureEnvLoader
secure_loader = SecureEnvLoader()
secure_loader.load_secure_env(Path("config.enc.yaml"))
```

### Manual Decryption
To view the configuration manually:

```bash
# Decrypt and view config
sops -d config.enc.yaml

# Edit encrypted config
sops config.enc.yaml
```

### Environment Variables
The YAML structure is flattened to environment variables:

- `noah.version` → `NOAH_VERSION`
- `authentik.secret_key` → `AUTHENTIK_SECRET_KEY`
- `kubernetes.cluster_name` → `KUBERNETES_CLUSTER_NAME`

## Security Benefits

1. **Encryption at Rest**: All sensitive data encrypted using SOPS/Age
2. **Version Control Safe**: Only encrypted files committed to git
3. **Access Control**: Requires Age private key for decryption
4. **Audit Trail**: SOPS provides cryptographic signatures
5. **Industry Standard**: Uses established SOPS/Age encryption tools

## Migration Complete

✅ All unencrypted password files removed
✅ Strong random passwords generated for all services  
✅ SOPS encryption successfully implemented
✅ Environment variable compatibility maintained
✅ Git security enhanced with updated .gitignore
✅ All existing functionality preserved

The NOAH system now uses encrypted passwords throughout, significantly improving security posture while maintaining full operational compatibility.
