# TLS Configuration Options for NOAH Platform

## Overview

The NOAH platform requires TLS certificates for secure communication. You have three main options:

## Option 1: Self-Signed Certificates (Development) ⚡

**Best for:** Development, testing, local environments

**Pros:**
- ✅ Quick setup (< 5 minutes)
- ✅ No external dependencies
- ✅ Works offline
- ✅ No rate limits

**Cons:**
- ❌ Browser warnings ("Not Secure")
- ❌ Not suitable for production
- ❌ Manual certificate management

**Implementation:**
```bash
# Generate self-signed certificates
python script/generate_certificates.py

# Update SOPS secrets
python script/update_tls_secrets.py

# Deploy
./noah.py deploy
```

## Option 2: Cert-Manager + Let's Encrypt (Recommended) 🏆

**Best for:** Production, staging, public-facing deployments

**Pros:**
- ✅ Automatic certificate management
- ✅ Trusted by browsers
- ✅ Auto-renewal
- ✅ Production-ready

**Cons:**
- ❌ Requires public domain
- ❌ Internet connectivity needed
- ❌ Let's Encrypt rate limits

**Implementation:**
```bash
# Configure TLS interactively
python script/configure_tls.py

# Deploy with automatic certificates
./noah.py deploy
```

## Option 3: Manual Certificate Management (Enterprise)

**Best for:** Enterprise environments with existing PKI

**Pros:**
- ✅ Full control over certificates
- ✅ Compliance with corporate policies
- ✅ Custom certificate authorities

**Cons:**
- ❌ Manual management required
- ❌ Complex setup
- ❌ Need existing PKI infrastructure

## Quick Start Recommendation

### For Development:
```bash
python script/generate_certificates.py && python script/update_tls_secrets.py
```

### For Production:
1. Configure a public domain pointing to your cluster
2. Run: `python script/configure_tls.py` and choose option 2
3. Deploy with automatic Let's Encrypt certificates

## Technical Details

### Current Configuration Issue
The deployment fails because `vault_tls_cert` and `vault_tls_key` variables are undefined in `ansible/vars/secrets.yml`.

### Solution Architecture
```
Browser → NGINX Ingress → TLS Termination → Services
                ↓
        Certificate Source:
        - Self-signed (dev)
        - Let's Encrypt (prod)
        - Custom CA (enterprise)
```

### Security Considerations
- Self-signed certificates should only be used in development
- Let's Encrypt certificates are automatically renewed
- Always use TLS 1.2+ with strong cipher suites
- Consider certificate pinning for high-security environments
