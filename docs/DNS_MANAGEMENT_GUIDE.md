# DNS Management Guide for NOAH

This guide explains how to configure and manage DNS for the NOAH infrastructure automation platform.

## Table of Contents

1. [Overview](#overview)
2. [DNS Architecture](#dns-architecture)
3. [Cloudflare Setup (Recommended)](#cloudflare-setup-recommended)
4. [External-DNS Deployment](#external-dns-deployment)
5. [Manual DNS Configuration](#manual-dns-configuration)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Overview

NOAH supports two DNS management approaches:

1. **Automatic DNS Management (Recommended)**: Using external-dns with Cloudflare
2. **Manual DNS Management**: Manually configure DNS records at your registrar

### Why Use Automatic DNS Management?

- **Zero-touch DNS updates**: DNS records are created/updated automatically
- **Infrastructure as Code**: DNS configuration lives in Kubernetes manifests
- **Dynamic IP support**: Automatically updates when LoadBalancer IPs change
- **Consistent configuration**: Reduces human error in DNS management

---

## DNS Architecture

### Current NOAH DNS Structure

```
┌─────────────────────────────────────────────────┐
│          Kubernetes Cluster (NOAH)              │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  external-dns Pod (optional)             │  │
│  │  - Watches Ingress resources             │  │
│  │  - Reads annotations                     │  │
│  │  - Syncs to Cloudflare API               │  │
│  └──────────────────────────────────────────┘  │
│                    │                            │
│                    │ Creates/Updates DNS        │
│                    ▼                            │
│  ┌──────────────────────────────────────────┐  │
│  │  Ingress Resources                       │  │
│  │  • auth.noah-infra.com                   │  │
│  │  • hubble.noah-infra.com                 │  │
│  │  • headlamp.noah-infra.com               │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  CoreDNS (Internal DNS)                  │  │
│  │  • *.svc.cluster.local                   │  │
│  │  • Internal service discovery            │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                     │
                     │ API Calls
                     ▼
┌─────────────────────────────────────────────────┐
│       Cloudflare DNS (Free Tier)                │
│                                                 │
│  auth.noah-infra.com     → 65.21.238.126       │
│  hubble.noah-infra.com   → 65.21.238.126       │
│  headlamp.noah-infra.com → 65.21.238.126       │
└─────────────────────────────────────────────────┘
                     │
                     │ DNS Queries
                     ▼
              End Users / Clients
```

### DNS Hierarchy in NOAH

NOAH uses a hierarchical domain configuration system:

```yaml
# Global domain (default: noah-infra.com)
NOAH_DOMAIN="yourdomain.com"

# Service-specific overrides
NOAH_AUTHENTIK_DOMAIN="custom-auth-domain.com"
NOAH_AUTHENTIK_SUBDOMAIN="sso"  # Default: auth

# Result: sso.custom-auth-domain.com
```

### Default Service FQDNs

| Service | Default Subdomain | Default FQDN |
|---------|------------------|--------------|
| Authentik SSO | `auth` | `auth.noah-infra.com` |
| Cilium Hubble UI | `hubble` | `hubble.noah-infra.com` |
| Headlamp Dashboard | `headlamp` | `headlamp.noah-infra.com` |
| Nextcloud (future) | `cloud` | `cloud.noah-infra.com` |
| Grafana (future) | `monitoring` | `monitoring.noah-infra.com` |

---

## Cloudflare Setup (Recommended)

### Why Cloudflare?

- **Free tier with unlimited DNS**: No cost for DNS hosting
- **Global anycast network**: Fast DNS resolution worldwide (< 20ms)
- **Excellent API**: Perfect for automation with external-dns
- **Built-in DDoS protection**: Included in free tier
- **Free SSL certificates**: Universal SSL at no cost

### Step 1: Create Cloudflare Account

1. Go to [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
2. Create a free account
3. Verify your email address

### Step 2: Add Your Domain

#### Option A: Transfer Domain to Cloudflare (Easiest)

1. In Cloudflare dashboard, click **"Add a Site"**
2. Enter your domain name (e.g., `yourdomain.com`)
3. Select **Free plan**
4. Cloudflare will scan existing DNS records
5. Review and import records
6. Update nameservers at your registrar:
   ```
   anya.ns.cloudflare.com
   todd.ns.cloudflare.com
   ```
   (Your nameservers will be different - use the ones Cloudflare provides)

#### Option B: Use Existing Domain with Cloudflare DNS

1. Keep domain at current registrar
2. Point nameservers to Cloudflare (provided during setup)
3. Wait 24-48 hours for nameserver propagation

### Step 3: Create API Token

1. In Cloudflare dashboard, click your profile icon → **My Profile**
2. Go to **API Tokens** section
3. Click **Create Token**
4. Use **"Edit zone DNS"** template or create custom token with:
   - **Permissions**:
     - Zone → DNS → Edit
     - Zone → Zone → Read
   - **Zone Resources**:
     - Include → Specific zone → `yourdomain.com`
   - **Client IP Address Filtering** (optional): Add your cluster's public IP for extra security

5. Click **Continue to summary**
6. Click **Create Token**
7. **COPY THE TOKEN** - you won't see it again!

Example token format:
```
vPQP9K4jqZxJ7q6DXxxxxxxxxxxxxxXXXXXXXXXXX
```

### Step 4: Store API Token Securely

#### Option 1: Environment Variable (Recommended)

```bash
export CLOUDFLARE_API_TOKEN='your-token-here'
```

Add to your shell profile for persistence:
```bash
# Add to ~/.bashrc or ~/.zshrc
echo "export CLOUDFLARE_API_TOKEN='your-token-here'" >> ~/.bashrc
source ~/.bashrc
```

#### Option 2: NOAH Configuration File

Add to `Config/config.enc.yaml` (will be encrypted by SOPS):
```yaml
cloudflare:
  api_token: "your-token-here"
```

Then reload configuration:
```bash
python noah.py config reload
```

---

## External-DNS Deployment

### Automatic Deployment (via noah.py deploy core)

External-DNS can be automatically deployed during core stack deployment:

```bash
# Enable external-dns in environment
export NOAH_EXTERNAL_DNS_ENABLED=true
export CLOUDFLARE_API_TOKEN='your-token-here'

# Deploy complete stack with DNS automation
python noah.py deploy core --domain yourdomain.com
```

External-DNS will be deployed in **Phase 0** (before Cilium, Authentik, Headlamp).

### Manual Deployment (standalone)

Deploy external-dns independently:

```bash
# Set Cloudflare API token
export CLOUDFLARE_API_TOKEN='your-token-here'

# Deploy external-dns
python noah.py deploy dns --domain yourdomain.com

# Or with all options
python noah.py deploy dns \
  --domain yourdomain.com \
  --provider cloudflare \
  --namespace kube-system \
  --policy upsert-only \
  --api-token 'your-token-here'
```

### Deployment Options

| Option | Default | Description |
|--------|---------|-------------|
| `--domain` | `noah-infra.com` | Domain to manage DNS for |
| `--provider` | `cloudflare` | DNS provider (only cloudflare supported) |
| `--namespace` | `kube-system` | Kubernetes namespace for external-dns |
| `--policy` | `upsert-only` | DNS record policy (see below) |
| `--api-token` | `$CLOUDFLARE_API_TOKEN` | Cloudflare API token |

### DNS Policies

**upsert-only** (Recommended):
- Creates new DNS records
- Updates existing DNS records
- **Never deletes** DNS records
- Safe for production - prevents accidental deletions

**sync**:
- Creates new DNS records
- Updates existing DNS records
- **Deletes DNS records** when Ingress/Service is removed
- Use with caution - can delete records not managed by external-dns

### Verify Deployment

```bash
# Check external-dns pod status
kubectl get pods -n kube-system -l app.kubernetes.io/name=external-dns

# View external-dns logs
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns -f

# Expected log output:
# time="..." level=info msg="Applying provider record filter for domains: [yourdomain.com]"
# time="..." level=info msg="Desired change: CREATE auth.yourdomain.com A"
# time="..." level=info msg="2 record(s) in zone yourdomain.com were successfully updated"
```

### How External-DNS Works

External-DNS watches for Kubernetes Ingress resources with annotations:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: authentik-ingress
  annotations:
    external-dns.alpha.kubernetes.io/hostname: "auth.yourdomain.com"
spec:
  rules:
    - host: auth.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: authentik-server
                port:
                  number: 80
```

When external-dns detects this Ingress:
1. Extracts the hostname from annotation: `auth.yourdomain.com`
2. Gets the LoadBalancer IP from the service: `65.21.238.126`
3. Creates/updates Cloudflare DNS record: `auth.yourdomain.com A 65.21.238.126`

### DNS Record Propagation

After deployment:
- **Cloudflare network**: < 1 second
- **Your location**: 5-15 minutes (DNS TTL: 300s)
- **Global propagation**: 15-30 minutes

Check DNS propagation:
```bash
# Check if record exists
nslookup auth.yourdomain.com

# Check from multiple locations
dig auth.yourdomain.com @8.8.8.8
dig auth.yourdomain.com @1.1.1.1
```

---

## Manual DNS Configuration

If not using external-dns, you must manually create DNS records.

### Step 1: Get LoadBalancer IP

```bash
# Get Cilium Ingress LoadBalancer IP
kubectl get svc -n kube-system cilium-ingress-lb

# Expected output:
# NAME                TYPE           CLUSTER-IP      EXTERNAL-IP      PORT(S)
# cilium-ingress-lb   LoadBalancer   10.43.123.45    65.21.238.126    80:30080/TCP,443:30443/TCP
```

Copy the `EXTERNAL-IP` value (e.g., `65.21.238.126`).

### Step 2: Create DNS A Records

In your DNS provider's control panel, create these A records:

| Hostname | Type | Value | TTL |
|----------|------|-------|-----|
| `auth.yourdomain.com` | A | `65.21.238.126` | 300 |
| `hubble.yourdomain.com` | A | `65.21.238.126` | 300 |
| `headlamp.yourdomain.com` | A | `65.21.238.126` | 300 |

### Step 3: Verify DNS Resolution

```bash
# Test DNS resolution
nslookup auth.yourdomain.com
nslookup hubble.yourdomain.com
nslookup headlamp.yourdomain.com

# Or use dig
dig auth.yourdomain.com +short
```

### Step 4: Test HTTPS Access

```bash
# Wait 5-10 minutes for DNS propagation, then test
curl -I https://auth.yourdomain.com
curl -I https://hubble.yourdomain.com
curl -I https://headlamp.yourdomain.com
```

---

## Troubleshooting

### Issue: DNS Records Not Created

**Symptom**: External-DNS deployed but no DNS records appear in Cloudflare

**Check 1**: Verify external-dns pod is running
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=external-dns
```

**Check 2**: View external-dns logs for errors
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns

# Look for errors like:
# level=error msg="Failed to list records: authentication error"
# level=error msg="Cloudflare API error: Invalid API token"
```

**Check 3**: Verify API token secret
```bash
kubectl get secret external-dns-cloudflare -n kube-system -o yaml

# Decode the token
kubectl get secret external-dns-cloudflare -n kube-system -o jsonpath='{.data.cloudflare_api_token}' | base64 -d
```

**Check 4**: Verify Ingress annotations
```bash
kubectl get ingress -n identity authentik-ingress -o yaml | grep external-dns
```

**Solution**: Ensure API token has correct permissions (DNS Edit + Zone Read)

---

### Issue: DNS Records Not Resolving

**Symptom**: DNS records exist in Cloudflare but don't resolve

**Check 1**: Verify nameservers are set correctly
```bash
dig NS yourdomain.com +short

# Expected output (Cloudflare nameservers):
# anya.ns.cloudflare.com
# todd.ns.cloudflare.com
```

**Check 2**: Clear DNS cache
```bash
# Linux
sudo systemd-resolve --flush-caches

# macOS
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder

# Windows (PowerShell as Admin)
Clear-DnsClientCache
```

**Check 3**: Test from external DNS server
```bash
# Google DNS
dig @8.8.8.8 auth.yourdomain.com +short

# Cloudflare DNS
dig @1.1.1.1 auth.yourdomain.com +short
```

**Solution**: Wait 15-30 minutes for full DNS propagation

---

### Issue: 401 Unauthorized Error

**Symptom**: External-DNS logs show authentication errors

```
level=error msg="Failed to list records: authentication error"
```

**Cause**: Invalid or expired API token

**Solution**:
1. Create a new API token in Cloudflare dashboard
2. Update the secret:
   ```bash
   kubectl delete secret external-dns-cloudflare -n kube-system
   python noah.py deploy dns --domain yourdomain.com --api-token 'new-token'
   ```

---

### Issue: 403 Forbidden Error

**Symptom**: External-DNS logs show permission errors

```
level=error msg="Cloudflare API error: Permission denied"
```

**Cause**: API token lacks required permissions

**Solution**:
1. Edit API token in Cloudflare dashboard
2. Ensure permissions include:
   - Zone → DNS → Edit
   - Zone → Zone → Read
3. Update the secret with corrected token

---

### Issue: External-DNS Not Watching Services

**Symptom**: Only some Ingresses are managed, others are ignored

**Check**: Verify domain filter matches
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns | grep "domain filter"

# Expected:
# level=info msg="Applying provider record filter for domains: [yourdomain.com]"
```

**Solution**: Ensure Ingress hostname matches domain filter:
```yaml
# ❌ Wrong - subdomain doesn't match filter
external-dns.alpha.kubernetes.io/hostname: "auth.otherdomain.com"

# ✅ Correct - matches domain filter
external-dns.alpha.kubernetes.io/hostname: "auth.yourdomain.com"
```

---

### Issue: DNS Records Multiplying (Duplicates)

**Symptom**: Multiple A records for same hostname

**Cause**: Multiple external-dns instances or conflicting DNS providers

**Check**: Verify only one external-dns pod exists
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=external-dns

# Should show only 1 pod
```

**Solution**:
1. Delete duplicate deployments:
   ```bash
   kubectl delete deployment external-dns -n kube-system
   ```
2. Redeploy single instance:
   ```bash
   python noah.py deploy dns --domain yourdomain.com
   ```

---

### Testing DNS with /etc/hosts Override

For testing before DNS is configured:

```bash
# Get LoadBalancer IP
EXTERNAL_IP=$(kubectl get svc -n kube-system cilium-ingress-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add to /etc/hosts (requires sudo)
echo "$EXTERNAL_IP auth.yourdomain.com" | sudo tee -a /etc/hosts
echo "$EXTERNAL_IP hubble.yourdomain.com" | sudo tee -a /etc/hosts
echo "$EXTERNAL_IP headlamp.yourdomain.com" | sudo tee -a /etc/hosts

# Test access
curl -I https://auth.yourdomain.com

# Remove entries when DNS is working
sudo sed -i '/auth.yourdomain.com/d' /etc/hosts
sudo sed -i '/hubble.yourdomain.com/d' /etc/hosts
sudo sed -i '/headlamp.yourdomain.com/d' /etc/hosts
```

---

## Advanced Configuration

### Custom Subdomains

Override default subdomains via environment variables:

```bash
export NOAH_DOMAIN="yourdomain.com"
export NOAH_AUTHENTIK_SUBDOMAIN="sso"      # Default: auth
export NOAH_CILIUM_SUBDOMAIN="network"     # Default: hubble
export NOAH_HEADLAMP_SUBDOMAIN="k8s"       # Default: headlamp

# Deploy with custom subdomains
python noah.py deploy core --domain yourdomain.com

# Results:
# - sso.yourdomain.com → Authentik
# - network.yourdomain.com → Hubble UI
# - k8s.yourdomain.com → Headlamp
```

### Multiple Domains per Service

Override entire domain for specific service:

```bash
export NOAH_DOMAIN="internal.yourdomain.com"
export NOAH_AUTHENTIK_DOMAIN="auth.external.com"  # Different domain for Authentik

# Results:
# - auth.external.com → Authentik (public-facing)
# - hubble.internal.yourdomain.com → Hubble UI (internal)
# - headlamp.internal.yourdomain.com → Headlamp (internal)
```

### Zone ID Filtering

Limit external-dns to specific Cloudflare zones:

```yaml
# In Helm values or via environment variable
NOAH_DNS_ZONE_ID_FILTER="zone-id-1,zone-id-2"
```

Get zone IDs from Cloudflare:
```bash
# Using Cloudflare API
curl -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json"
```

### Custom TTL Values

Modify DNS record TTL in external-dns deployment:

```yaml
# Edit Helm values
externalDns:
  extraArgs:
    - --cloudflare-dns-records-per-page=100
    - --txt-cache-interval=300s
```

### Annotation Filtering

Only manage Ingresses with specific annotation:

```yaml
externalDns:
  annotationFilter: "external-dns.enabled=true"
```

Then add annotation to Ingresses you want managed:
```yaml
metadata:
  annotations:
    external-dns.enabled: "true"
    external-dns.alpha.kubernetes.io/hostname: "auth.yourdomain.com"
```

---

## DNS Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NOAH_DOMAIN` | `noah-infra.com` | Global domain for all services |
| `NOAH_DNS_PROVIDER` | `cloudflare` | DNS provider (only cloudflare supported) |
| `NOAH_EXTERNAL_DNS_ENABLED` | `false` | Enable automatic DNS management |
| `NOAH_EXTERNAL_DNS_NAMESPACE` | `kube-system` | Namespace for external-dns |
| `NOAH_EXTERNAL_DNS_POLICY` | `upsert-only` | DNS record policy |
| `CLOUDFLARE_API_TOKEN` | - | Cloudflare API token (required for automation) |
| `CLOUDFLARE_API_KEY` | - | Legacy Cloudflare auth (not recommended) |
| `CLOUDFLARE_EMAIL` | - | Legacy Cloudflare auth (not recommended) |

### Service-Specific Overrides

| Variable | Service | Default Subdomain |
|----------|---------|-------------------|
| `NOAH_AUTHENTIK_SUBDOMAIN` | Authentik SSO | `auth` |
| `NOAH_AUTHENTIK_DOMAIN` | Authentik SSO | `$NOAH_DOMAIN` |
| `NOAH_CILIUM_SUBDOMAIN` | Cilium Hubble | `hubble` |
| `NOAH_CILIUM_DOMAIN` | Cilium Hubble | `$NOAH_DOMAIN` |
| `NOAH_HEADLAMP_SUBDOMAIN` | Headlamp | `headlamp` |
| `NOAH_HEADLAMP_DOMAIN` | Headlamp | `$NOAH_DOMAIN` |

### ConfigLoader DNS Methods

Python API for DNS configuration:

```python
from Scripts.utils.config_loader import ConfigLoader

config = ConfigLoader()

# DNS provider configuration
provider = config.get_dns_provider()  # Returns: 'cloudflare'
api_token = config.get_cloudflare_api_token()
policy = config.get_external_dns_policy()  # Returns: 'upsert-only'

# DNS validation
issues = config.validate_dns_configuration()
if issues:
    for issue in issues:
        print(f"DNS Config Issue: {issue}")
```

---

## Migration from Manual to Automatic DNS

If you're currently using manual DNS and want to migrate to automatic:

### Step 1: Deploy External-DNS (No Changes Yet)

```bash
# Deploy with upsert-only policy (safe - won't delete anything)
export CLOUDFLARE_API_TOKEN='your-token-here'
python noah.py deploy dns --domain yourdomain.com --policy upsert-only
```

### Step 2: Verify External-DNS is Working

```bash
# Check logs
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns -f

# Look for successful record updates:
# level=info msg="2 record(s) in zone yourdomain.com were successfully updated"
```

### Step 3: Compare DNS Records

```bash
# Check Cloudflare dashboard - you should see:
# - Original manual records (unchanged)
# - New TXT records created by external-dns (for ownership tracking)
```

### Step 4: Remove Manual Records (Optional)

Once confident external-dns is working:
1. Delete manual A records in Cloudflare dashboard
2. external-dns will recreate them automatically
3. TXT records are used for ownership tracking

---

## Best Practices

1. **Use upsert-only policy**: Prevents accidental DNS record deletion
2. **Store API tokens securely**: Use environment variables or encrypted config
3. **Monitor external-dns logs**: Set up alerting for authentication failures
4. **Use scoped API tokens**: Never use Global API keys
5. **Test in staging first**: Verify DNS automation before production
6. **Document custom domains**: Keep track of service-specific domain overrides
7. **Rotate API tokens regularly**: Every 90 days recommended
8. **Enable Cloudflare proxy carefully**: Can break some services (e.g., LDAP)
9. **Use TXT record ownership**: Prevents conflicts with other DNS managers
10. **Set appropriate TTLs**: 300s (5 minutes) is good for dynamic environments

---

## Support

For issues or questions:

- **NOAH Issues**: [https://github.com/your-org/noah/issues](https://github.com/your-org/noah/issues)
- **external-dns Documentation**: [https://github.com/kubernetes-sigs/external-dns](https://github.com/kubernetes-sigs/external-dns)
- **Cloudflare Support**: [https://support.cloudflare.com](https://support.cloudflare.com)

---

## Related Documentation

- [NOAH README](../README.md)
- [Headlamp Integration Guide](HEADLAMP_INTEGRATION.md)
- [Troubleshooting Guide](troubleshooting-guide.md)
- [Security Best Practices](../Security/README.md)
