# NOAH Deployment Guide

**Version**: 0.0.7
**Last Updated**: March 2026

Deploy NOAH (Network Operations & Automation Hub) - a complete Kubernetes infrastructure with SSO authentication and web dashboards.

---

## Table of Contents

1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Quick Start](#quick-start)
4. [Detailed Steps](#detailed-steps)
5. [DNS Configuration](#dns-configuration)
6. [Accessing Services](#accessing-services)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### What is NOAH?

NOAH deploys a complete Kubernetes stack:

- **Kubernetes (K3s)** - Lightweight K8s distribution
- **Cilium CNI** - eBPF-based networking + Ingress
- **Authentik SSO** - Identity and access management
- **Headlamp Dashboard** - Kubernetes web UI with SSO
- **Hubble UI** - Network observability
- **External-DNS** - Optional automatic DNS (Cloudflare)

### Architecture

```
┌──────────────────────────────────────────────────┐
│  Users → https://auth.yourdomain.com            │
│         https://headlamp.yourdomain.com          │
│         https://hubble.yourdomain.com            │
└────────────────────┬─────────────────────────────┘
                     │ HTTPS/TLS
                     ▼
┌──────────────────────────────────────────────────┐
│         Cilium Ingress (LoadBalancer)            │
└────────┬──────────┬──────────┬───────────────────┘
         │          │          │
    ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐
    │Authentik│ │Headlamp│ │Hubble UI│
    │SSO/OIDC │◄┤(OIDC)  │ │         │
    └────┬────┘ └────────┘ └─────────┘
         │
    ┌────┴─────┬──────────┐
    │PostgreSQL│  │Redis │Cilium CNI│
    └──────────┴──┴──────┴──────────┘
───────────────────────────────────────
      Kubernetes (K3s) Cluster
───────────────────────────────────────
```

**Deployment Time**: ~25-45 minutes total

---

## Requirements

### System
- **OS**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
- **CPU**: 4 cores minimum (8+ recommended)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB free (100GB+ recommended)
- **Kernel**: Linux 5.10+ (for Cilium eBPF)
- **Network**: Internet connectivity

### Tools (auto-installed)
- Python 3.8+
- kubectl, helm, ansible
- age, sops (encryption)

### DNS Options
1. **Cloudflare** (automatic) - Requires API token
2. **Manual** - Any DNS provider with A record support
3. **Local** - /etc/hosts for testing

---

## Quick Start

```bash
# 1. Configure DNS (choose one):
# Option A: Automatic (Cloudflare) - set BEFORE deploy
export NOAH_EXTERNAL_DNS_ENABLED=true
export CLOUDFLARE_API_TOKEN='your-cloudflare-api-token'
# Option B: Manual - configure AFTER deploy (see DNS Configuration section)
# Option C: Local - add to /etc/hosts AFTER deploy

# 2. Clone repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# 3. Initialize environment
python3 noah.py setup initialize

# 4. Create cluster
python3 noah.py cluster create --name noah-cluster --domain yourdomain.com

# 5. Deploy stack
python3 noah.py deploy core --domain yourdomain.com

# 6. Get credentials
python3 noah.py password show
```

**Access services:**
- Authentik: `https://auth.yourdomain.com`
- Headlamp: `https://headlamp.yourdomain.com`
- Hubble: `https://hubble.yourdomain.com`

---

## Detailed Steps

### Step 1: Initialize Environment

```bash
python noah.py setup initialize
```

**What it does:**
- Checks Python 3.8+ version
- Creates virtual environment (`.venv/`)
- Installs Python dependencies
- Validates kernel for Cilium (BPF support)
- Installs system packages (age, kubectl, helm, ansible)
- Generates Age encryption keys
- Creates SOPS configuration
- **Runs the Cloudflare DNS wizard** (interactive — configure API token and DNS zone)

To skip the wizard (e.g. in CI or if you prefer manual DNS):
```bash
python noah.py setup initialize --skip-dns-wizard
```

**Verify:**
```bash
python noah.py setup doctor
```

---

### Step 2: Create Kubernetes Cluster

```bash
python noah.py cluster create --name noah-cluster --domain yourdomain.com
```

**What it does:**
- Generates TLS certificates (wildcard `*.yourdomain.com`)
- Installs K3s with optimized config
- Deploys local-path storage provisioner
- Creates namespaces (`identity`, `cilium-system`)
- Configures kubectl access (`~/.kube/config`)
- Validates cluster health (8 checks)

**Verify:**
```bash
kubectl get nodes  # Should show Ready
kubectl get pods -A  # Should show coredns, metrics-server running
```

---

### Step 3: Deploy Core Stack

```bash
python noah.py deploy core --domain yourdomain.com
```

**Deployment phases:**

#### Phase 0: External-DNS (Optional)
- **When**: If `NOAH_EXTERNAL_DNS_ENABLED=true` and `CLOUDFLARE_API_TOKEN` set
- **Duration**: ~2-3 minutes
- **What**: Deploys external-dns for automatic DNS record management

#### Phase 1: Cilium CNI
- **Duration**: ~5-7 minutes
- **Components**:
  - Cilium DaemonSet (eBPF networking)
  - Cilium Operator
  - Hubble Relay + UI
  - Cilium Ingress LoadBalancer

#### Phase 2: Authentik SSO
- **Duration**: ~7-10 minutes
- **Components**:
  - PostgreSQL (database)
  - Redis (cache)
  - Authentik Server (IAM)
  - Authentik Worker (background tasks)
- **Resources**: ~2GB RAM, ~1.1 CPU cores (requests)
- **Post-deploy**: Bootstrap token verified in canonical secrets store

#### Phase 3.5: Hubble UI SSO Provisioning (new in v0.0.7)
- **Duration**: ~1-2 minutes
- **What**: Calls `AuthentikProvisioner.provision_proxy_app()` to create a forward-auth proxy application in Authentik for Hubble UI, then applies nginx forward-auth ingress annotations automatically

#### Phase 4: Headlamp Dashboard
- **Duration**: ~3-5 minutes
- **Components**: Headlamp web UI with OIDC integration
- **Post-deploy**: Calls `AuthentikProvisioner.provision_oidc_app()` to register the Headlamp OIDC client in Authentik automatically

#### Phase 5: Validation
- **Duration**: ~1-2 minutes
- **Checks**: Pod readiness, service health, network connectivity

---

## DNS Configuration

### Option A: Automatic (Cloudflare)

**Prerequisites:**
- Domain on Cloudflare
- Cloudflare API token

**Configure BEFORE deployment:**
```bash
export NOAH_EXTERNAL_DNS_ENABLED=true
export CLOUDFLARE_API_TOKEN='your-cloudflare-api-token'
python noah.py deploy core --domain yourdomain.com
```

**Verify:**
```bash
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns
nslookup auth.yourdomain.com
```

---

### Option B: Manual DNS

**Configure AFTER deployment:**

**1. Get LoadBalancer IP:**
```bash
kubectl get svc -n kube-system cilium-ingress-lb
# Copy EXTERNAL-IP (e.g., 65.21.238.126)
```

**2. Create A records at your DNS provider:**
| Hostname | Type | Value |
|----------|------|-------|
| `auth.yourdomain.com` | A | `65.21.238.126` |
| `headlamp.yourdomain.com` | A | `65.21.238.126` |
| `hubble.yourdomain.com` | A | `65.21.238.126` |

**3. Verify:**
```bash
nslookup auth.yourdomain.com  # Should return LoadBalancer IP
```

---

### Option C: Local Testing

**Configure AFTER deployment:**
```bash
# Get LoadBalancer IP
EXTERNAL_IP=$(kubectl get svc -n kube-system cilium-ingress-lb -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add to /etc/hosts
echo "$EXTERNAL_IP auth.yourdomain.com" | sudo tee -a /etc/hosts
echo "$EXTERNAL_IP headlamp.yourdomain.com" | sudo tee -a /etc/hosts
echo "$EXTERNAL_IP hubble.yourdomain.com" | sudo tee -a /etc/hosts
```

---

## Accessing Services

### Get Credentials

```bash
python noah.py password show
```

**Example output:**
```
🔍 Current Authentik admin credentials:
==================================================
📍 URL:         https://auth.yourdomain.com
🌐 External IP: 65.21.238.126
👤 Username:    admin
📧 Email:       admin@localhost
🔑 Password:    test-password-abc123xyz
==================================================
```

### Login Flow

**1. Authentik SSO:**
- Open: `https://auth.yourdomain.com`
- Username: `admin`
- Password: (from `password show` command)

**2. Headlamp Dashboard:**
- Open: `https://headlamp.yourdomain.com`
- Click "Sign in with OIDC"
- Use same Authentik credentials
- View Kubernetes resources

**3. Hubble UI:**
- Open: `https://hubble.yourdomain.com`
- No authentication required
- View network flows

### Password Management

**Rotate password:**
```bash
python noah.py password new
python noah.py deploy authentik --regenerate-password
```

---

## Troubleshooting

### Quick Fixes

**Can't access services?**
```bash
# Check pods
kubectl get pods -A

# Check LoadBalancer IP
kubectl get svc -n kube-system cilium-ingress-lb

# Check DNS
nslookup auth.yourdomain.com

# Add to /etc/hosts if DNS not working
EXTERNAL_IP=<your-lb-ip>
echo "$EXTERNAL_IP auth.yourdomain.com" | sudo tee -a /etc/hosts
```

**Pods not starting?**
```bash
# Check events
kubectl get events -A --sort-by=.metadata.creationTimestamp

# Check logs
kubectl logs -n identity deployment/authentik-server
kubectl logs -n kube-system ds/cilium

# Restart pod
kubectl delete pod -n identity <pod-name>
```

**Certificate errors?**
```bash
# Accept self-signed cert in browser, or install CA:
sudo cp Certificates/ca.crt /usr/local/share/ca-certificates/noah-ca.crt
sudo update-ca-certificates
```

**Insufficient resources?**
```bash
# Check resources
kubectl top nodes
kubectl top pods -A

# Minimum required: 4 CPU, 8GB RAM, 50GB storage
```

### Complete Reset

```bash
# Backup credentials
python noah.py password show > backup-passwords.txt

# Destroy and recreate
python noah.py cluster destroy --force
python noah.py cluster create --name noah-cluster --domain yourdomain.com
python noah.py deploy core --domain yourdomain.com
```

### Common Issues

| Issue | Solution |
|-------|----------|
| DNS resolution fails | Add to `/etc/hosts` or wait 5-10min for propagation |
| Pods CrashLoopBackOff | Check logs: `kubectl logs <pod>` |
| Connection refused | Verify LoadBalancer IP: `kubectl get svc -A` |
| Permission denied | Fix kubeconfig: `chmod 600 ~/.kube/config` |
| Low memory | Need minimum 8GB RAM |
| Kernel too old | Need Linux 5.10+ for Cilium |

---

## Validation

### Check Status

```bash
python noah.py status
```

### Manual Verification

```bash
# All pods running
kubectl get pods -A

# Services accessible
curl -I https://auth.yourdomain.com
curl -I https://headlamp.yourdomain.com
curl -I https://hubble.yourdomain.com

# Resource usage
kubectl top nodes
kubectl top pods -A
```

### Success Checklist

- ✅ All pods `Running`: `kubectl get pods -A`
- ✅ LoadBalancer has EXTERNAL-IP
- ✅ DNS resolves to LoadBalancer IP
- ✅ HTTPS works (accept self-signed cert)
- ✅ Can login to Authentik
- ✅ Headlamp shows cluster resources
- ✅ Hubble UI shows network flows
- ✅ `python noah.py status` shows healthy

---

## Advanced Configuration

### Custom Subdomains

```bash
export NOAH_AUTHENTIK_SUBDOMAIN="sso"
export NOAH_HEADLAMP_SUBDOMAIN="k8s"
python noah.py deploy core --domain yourdomain.com
# Results: sso.yourdomain.com, k8s.yourdomain.com
```

### Development Mode

```bash
# Skip some validation for faster iteration
python noah.py deploy core --domain yourdomain.com --validation-mode development
```

### Resource Tuning

**For low-resource systems (8GB RAM):**
- Edit `Helm/authentik/values.yaml`
- Reduce PostgreSQL/Redis resource requests
- Redeploy: `python noah.py deploy authentik`

**For production (32GB+ RAM):**
- Increase resource limits
- Enable persistent storage
- Use production validation mode

---

## Maintenance

### Regular Operations

```bash
# Check status
python noah.py status

# View credentials
python noah.py password show

# Rotate password
python noah.py password new
python noah.py deploy authentik --regenerate-password

# Update NOAH
git pull origin main
python noah.py setup initialize --skip-tests
```

### Backup

```bash
# Backup critical files
tar -czf noah-backup-$(date +%Y%m%d).tar.gz \
  Age/ Certificates/ Config/canonical-secrets.yaml .sops.yaml

# Backup Kubernetes resources
kubectl get all -A -o yaml > k8s-backup-$(date +%Y%m%d).yaml
```

---

## Additional Resources

- **Troubleshooting**: [troubleshooting-guide.md](troubleshooting-guide.md)
- **DNS Management**: [DNS_MANAGEMENT_GUIDE.md](DNS_MANAGEMENT_GUIDE.md)
- **Headlamp Integration**: [HEADLAMP_INTEGRATION.md](HEADLAMP_INTEGRATION.md)

---

**Made with ❤️ by the NOAH Team**
