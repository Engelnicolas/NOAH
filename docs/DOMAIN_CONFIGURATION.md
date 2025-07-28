# Domain Configuration for NOAH
# This file helps you configure your domains according to your environment

## 🏠 Local/Development Environment Configuration

### Option 1: .local domains (recommended for dev)
```yaml
global:
  domain: noah.local
  
# Applications accessible via:
# - https://keycloak.noah.local
# - https://gitlab.noah.local  
# - https://nextcloud.noah.local
# - https://mattermost.noah.local
# - https://grafana.noah.local
```

### Option 2: IP-based domains (for quick testing)
```yaml
global:
  domain: 192-168-1-100.nip.io    # Replace 192-168-1-100 with your ingress IP
  
# Applications accessible via:
# - https://keycloak.192-168-1-100.nip.io
# - https://gitlab.192-168-1-100.nip.io
```

## 🌐 Production Environment Configuration

### Option 3: Corporate domain
```yaml
global:
  domain: noah.mycompany.com
  
# Applications accessible via:
# - https://keycloak.noah.mycompany.com
# - https://gitlab.noah.mycompany.com
# - https://nextcloud.noah.mycompany.com
```

### Option 4: Separate subdomains
```yaml
# In this case, configure each service individually:
keycloak:
  ingress:
    hostname: auth.mycompany.com
    
gitlab:
  global:
    hosts:
      gitlab:
        name: git.mycompany.com
        
nextcloud:
  nextcloud:
    host: files.mycompany.com
```

## 🔧 Required DNS Configuration

### For .local domains (development)
Add to your /etc/hosts:
```bash
# Replace INGRESS_IP with your ingress controller IP
INGRESS_IP keycloak.noah.local
INGRESS_IP gitlab.noah.local
INGRESS_IP nextcloud.noah.local
INGRESS_IP mattermost.noah.local
INGRESS_IP grafana.noah.local
```

### For public domains (production)
Configure your DNS records:
```
Type  | Name                   | Value
------|------------------------|------------------
A     | keycloak.noah.company  | INGRESS_IP
A     | gitlab.noah.company    | INGRESS_IP
A     | nextcloud.noah.company | INGRESS_IP
A     | mattermost.noah.company| INGRESS_IP
A     | grafana.noah.company   | INGRESS_IP
```

## 🔐 SSL/TLS Configuration

### Automatic Let's Encrypt (recommended)
```yaml
# Already configured in values-prod.yaml
annotations:
  cert-manager.io/cluster-issuer: letsencrypt-prod
```

### Custom certificates
```yaml
# Store your certificates in Ansible Vault (secrets.yml)
vault_tls_cert: |
  -----BEGIN CERTIFICATE-----
  Your SSL certificate here
  -----END CERTIFICATE-----
  
vault_tls_key: |
  -----BEGIN PRIVATE KEY-----
  Your SSL private key here  
  -----END PRIVATE KEY-----
```

## 🚀 Quick Configuration Script

To automatically configure your domains:

```bash
#!/bin/bash
# NOAH domains quick configuration

DOMAIN="noah.local"                    # 🔧 Change according to your needs
INGRESS_IP="192.168.1.100"            # 🔧 Your ingress controller IP

echo "Configuring domains for $DOMAIN..."

# Update values file
sed -i "s/domain: noah.local/domain: $DOMAIN/g" values/values-prod.yaml

# Update /etc/hosts for local dev
if [[ "$DOMAIN" == *.local ]]; then
    echo "Adding local DNS entries..."
    sudo tee -a /etc/hosts << EOF
$INGRESS_IP keycloak.$DOMAIN
$INGRESS_IP gitlab.$DOMAIN
$INGRESS_IP nextcloud.$DOMAIN
$INGRESS_IP mattermost.$DOMAIN
$INGRESS_IP grafana.$DOMAIN
EOF
fi

echo "✅ Configuration completed for $DOMAIN"
```
