# DNS Management Guide for NOAH

Configure DNS for NOAH infrastructure with automatic or manual DNS management.

---

## Table of Contents

1. [Overview](#overview)
2. [Cloudflare Setup](#cloudflare-setup)
3. [Automatic DNS (External-DNS)](#automatic-dns-external-dns)
4. [Manual DNS Configuration](#manual-dns-configuration)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Configuration](#advanced-configuration)

---

## Overview

### DNS Options

NOAH supports three DNS management approaches:

1. **Automatic (Cloudflare)** - External-DNS auto-creates/updates DNS records
2. **Manual** - Manually configure DNS records at any provider
3. **Local** - /etc/hosts for development/testing

### DNS Architecture

```
┌─────────────────────────────────────────┐
│  Kubernetes Cluster                     │
│  ┌────────────────────────────────────┐ │
│  │  external-dns (optional)           │ │
│  │  Watches Ingress → Updates DNS     │ │
│  └────────────────┬───────────────────┘ │
│                   │ API Calls            │
│  ┌────────────────▼───────────────────┐ │
│  │  Ingress Resources                 │ │
│  │  • auth.yourdomain.com             │ │
│  │  • headlamp.yourdomain.com         │ │
│  │  • hubble.yourdomain.com           │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Cloudflare DNS / Your DNS Provider     │
│  auth.yourdomain.com → 65.21.238.126    │
│  headlamp.yourdomain.com → same IP      │
│  hubble.yourdomain.com → same IP        │
└─────────────────────────────────────────┘
                   │
                   ▼
              End Users
```

### Default Service Domains

| Service | Subdomain | Full Domain |
|---------|-----------|-------------|
| Authentik SSO | `auth` | `auth.yourdomain.com` |
| Headlamp Dashboard | `headlamp` | `headlamp.yourdomain.com` |
| Hubble UI | `hubble` | `hubble.yourdomain.com` |

---

## Cloudflare Setup

### Why Cloudflare?

- **Free tier** with unlimited DNS
- **Fast** global network (< 20ms)
- **Excellent API** for automation
- **DDoS protection** included

### Quick Setup

**1. Create account:**
- Go to [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
- Verify email

**2. Add domain:**
- Click "Add a Site"
- Enter: `yourdomain.com`
- Select **Free plan**
- Update nameservers at your registrar to Cloudflare's provided nameservers

**3. Create API token:**
- Profile → **API Tokens** → **Create Token**
- Template: **"Edit zone DNS"**
- Permissions:
  - Zone → DNS → Edit
  - Zone → Zone → Read
- Zone Resources: Include → Specific zone → `yourdomain.com`
- **Copy token** (won't be shown again!)

**Example token:** `vPQP9K4jqZxJ7q6DXxxxxxxxxxxxxxXXXXXXXXXXX`

**4. Store token:**
```bash
export CLOUDFLARE_API_TOKEN='your-token-here'

# Make persistent
echo "export CLOUDFLARE_API_TOKEN='your-token-here'" >> ~/.bashrc
source ~/.bashrc
```

---

## Automatic DNS (External-DNS)

### Deployment Timing

**⚠️ IMPORTANT:** Set environment variables **BEFORE** running `deploy core`

External-DNS deploys in **Phase 0** (before Cilium, Authentik, Headlamp).

### Deploy with Core Stack

```bash
# Set BEFORE deployment
export NOAH_EXTERNAL_DNS_ENABLED=true
export CLOUDFLARE_API_TOKEN='your-token-here'

# Deploy (External-DNS will be deployed in Phase 0)
python noah.py deploy core --domain yourdomain.com
```

### Deploy Standalone

```bash
# Deploy external-dns separately
export CLOUDFLARE_API_TOKEN='your-token-here'
python noah.py deploy dns --domain yourdomain.com
```

### How It Works

1. External-DNS watches Kubernetes Ingress resources
2. Reads annotations: `external-dns.alpha.kubernetes.io/hostname`
3. Gets LoadBalancer IP from service
4. Creates/updates DNS records in Cloudflare automatically

### Verify Deployment

```bash
# Check pod status
kubectl get pods -n kube-system -l app.kubernetes.io/name=external-dns

# View logs
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns -f

# Expected output:
# level=info msg="Applying provider record filter for domains: [yourdomain.com]"
# level=info msg="Desired change: CREATE auth.yourdomain.com A"
# level=info msg="3 record(s) in zone yourdomain.com were successfully updated"
```

### DNS Propagation

- **Cloudflare network**: < 1 second
- **Local cache**: 5-15 minutes
- **Global**: 15-30 minutes

**Check resolution:**
```bash
nslookup auth.yourdomain.com
dig auth.yourdomain.com +short
```

### DNS Policy

**upsert-only** (Default - Recommended):
- Creates new DNS records
- Updates existing DNS records
- **Never deletes** DNS records
- Safe for production

---

## Manual DNS Configuration

### When to Configure

**Configure AFTER deployment completes** (needs LoadBalancer IP).

### Step 1: Get LoadBalancer IP

```bash
kubectl get svc -n kube-system cilium-ingress-lb

# Example output:
# NAME                TYPE           EXTERNAL-IP
# cilium-ingress-lb   LoadBalancer   65.21.238.126
```

### Step 2: Create DNS Records

At your DNS provider, create these A records:

| Hostname | Type | Value | TTL |
|----------|------|-------|-----|
| `auth.yourdomain.com` | A | `65.21.238.126` | 300 |
| `headlamp.yourdomain.com` | A | `65.21.238.126` | 300 |
| `hubble.yourdomain.com` | A | `65.21.238.126` | 300 |

### Step 3: Verify

```bash
# Test DNS (wait 5-10 minutes for propagation)
nslookup auth.yourdomain.com

# Test HTTPS access
curl -I https://auth.yourdomain.com
```

### Local Testing (/etc/hosts)

For development without real DNS:

```bash
# Get IP
EXTERNAL_IP=$(kubectl get svc -n kube-system cilium-ingress-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add to /etc/hosts
echo "$EXTERNAL_IP auth.yourdomain.com" | sudo tee -a /etc/hosts
echo "$EXTERNAL_IP headlamp.yourdomain.com" | sudo tee -a /etc/hosts
echo "$EXTERNAL_IP hubble.yourdomain.com" | sudo tee -a /etc/hosts

# Test
curl -I https://auth.yourdomain.com

# Remove when done
sudo sed -i '/yourdomain.com/d' /etc/hosts
```

---

## Troubleshooting

### DNS Records Not Created

**Check pod status:**
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=external-dns
```

**Check logs:**
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns

# Common errors:
# "authentication error" → Invalid API token
# "permission denied" → Token lacks permissions
```

**Verify API token:**
```bash
# Check secret
kubectl get secret external-dns-cloudflare -n kube-system -o yaml

# Decode token
kubectl get secret external-dns-cloudflare -n kube-system \
  -o jsonpath='{.data.cloudflare_api_token}' | base64 -d
```

**Solution:** Recreate token with correct permissions (DNS Edit + Zone Read)

---

### DNS Not Resolving

**Check nameservers:**
```bash
dig NS yourdomain.com +short

# Should show Cloudflare nameservers (if using Cloudflare):
# anya.ns.cloudflare.com
# todd.ns.cloudflare.com
```

**Clear DNS cache:**
```bash
# Linux
sudo systemd-resolve --flush-caches

# macOS
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

**Test from external DNS:**
```bash
dig @8.8.8.8 auth.yourdomain.com +short
dig @1.1.1.1 auth.yourdomain.com +short
```

**Solution:** Wait 15-30 minutes for full propagation

---

### Authentication Errors (401)

**Symptom:** `level=error msg="authentication error"`

**Solution:**
1. Create new API token in Cloudflare
2. Update secret:
```bash
kubectl delete secret external-dns-cloudflare -n kube-system
python noah.py deploy dns --domain yourdomain.com --api-token 'new-token'
```

---

### Permission Errors (403)

**Symptom:** `level=error msg="Permission denied"`

**Solution:** Ensure API token has:
- Zone → DNS → Edit
- Zone → Zone → Read

Edit token in Cloudflare dashboard and redeploy.

---

### Wrong Domain Filter

**Check domain filter:**
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns | grep "domain filter"

# Should show:
# level=info msg="Applying provider record filter for domains: [yourdomain.com]"
```

**Ensure Ingress annotations match:**
```yaml
# ✅ Correct
external-dns.alpha.kubernetes.io/hostname: "auth.yourdomain.com"

# ❌ Wrong - different domain
external-dns.alpha.kubernetes.io/hostname: "auth.otherdomain.com"
```

---

## Advanced Configuration

### Custom Subdomains

```bash
export NOAH_DOMAIN="yourdomain.com"
export NOAH_AUTHENTIK_SUBDOMAIN="sso"      # Default: auth
export NOAH_HEADLAMP_SUBDOMAIN="k8s"       # Default: headlamp

python noah.py deploy core --domain yourdomain.com

# Results:
# sso.yourdomain.com → Authentik
# k8s.yourdomain.com → Headlamp
# hubble.yourdomain.com → Hubble (default)
```

### Different Domain per Service

```bash
export NOAH_DOMAIN="internal.yourdomain.com"
export NOAH_AUTHENTIK_DOMAIN="auth.external.com"

# Results:
# auth.external.com → Authentik (public)
# headlamp.internal.yourdomain.com → Headlamp (internal)
# hubble.internal.yourdomain.com → Hubble (internal)
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `NOAH_DOMAIN` | `noah-infra.com` | Global domain for all services |
| `NOAH_EXTERNAL_DNS_ENABLED` | `false` | Enable automatic DNS |
| `NOAH_EXTERNAL_DNS_POLICY` | `upsert-only` | DNS policy |
| `CLOUDFLARE_API_TOKEN` | - | Cloudflare API token |
| `NOAH_AUTHENTIK_SUBDOMAIN` | `auth` | Authentik subdomain |
| `NOAH_HEADLAMP_SUBDOMAIN` | `headlamp` | Headlamp subdomain |
| `NOAH_CILIUM_SUBDOMAIN` | `hubble` | Hubble subdomain |

---

## Migration from Manual to Automatic

### Step 1: Deploy External-DNS (Safe)

```bash
# Deploy with upsert-only (won't delete existing records)
export CLOUDFLARE_API_TOKEN='your-token-here'
python noah.py deploy dns --domain yourdomain.com --policy upsert-only
```

### Step 2: Verify

```bash
# Check logs for success
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns -f

# Should see:
# level=info msg="2 record(s) in zone yourdomain.com were successfully updated"
```

### Step 3: Compare Records

- Check Cloudflare dashboard
- Manual A records should still exist
- New TXT records appear (for ownership tracking)

### Step 4: Remove Manual Records (Optional)

Once confident external-dns works:
- Delete manual A records in Cloudflare
- External-DNS will recreate them automatically

---

## Best Practices

1. ✅ Use **upsert-only** policy (prevents deletions)
2. ✅ Store API tokens securely (environment variables)
3. ✅ Use **scoped tokens** (never Global API keys)
4. ✅ Monitor external-dns logs
5. ✅ Test in staging first
6. ✅ Rotate API tokens every 90 days
7. ✅ Set TTL to 300s (5 minutes) for dynamic environments
8. ✅ Document custom domain overrides

---

## Related Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Main deployment guide
- [troubleshooting-guide.md](troubleshooting-guide.md) - Quick fixes
- [README.md](README.md) - Project overview
- [External-DNS Documentation](https://github.com/kubernetes-sigs/external-dns)
- [Cloudflare API Docs](https://api.cloudflare.com/)

---

**Made with ❤️ by the NOAH Team**
