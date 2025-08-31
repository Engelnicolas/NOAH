# Nextcloud Helm Chart for NOAH Infrastructure

This Helm chart deploys Nextcloud file sharing and collaboration platform with integrated SSO authentication via Authentik and Traefik ingress.

## 🎯 Features

- **Complete Nextcloud Stack**: Files, calendar, contacts, and collaboration tools
- **SSO Integration**: Seamless authentication with Authentik OIDC
- **High Performance**: PostgreSQL database and Redis caching
- **Secure Access**: Automatic SSL/TLS via Traefik with security headers
- **Secret Management**: SOPS-encrypted secrets with automatic rotation
- **Scalable Storage**: Persistent volumes for data and configuration

## 📋 Components

### Core Application
- **Nextcloud Server**: Latest version with enhanced security
- **PostgreSQL**: Primary database for application data
- **Redis**: High-performance caching and session storage

### Security & Access
- **Traefik Ingress**: Load balancing with automatic SSL certificates
- **OIDC Integration**: Single Sign-On with Authentik provider
- **Security Middleware**: Custom headers and access controls
- **Encrypted Secrets**: SOPS-managed credentials and keys

## 🚀 Deployment

### Prerequisites
1. **NOAH Infrastructure**: Authentik and Traefik must be deployed
2. **Storage**: Persistent volume support in Kubernetes cluster
3. **Domain**: DNS pointing to cluster (cloud.noah-infra.com)
4. **Secrets**: Age/SOPS encryption initialized

### Quick Deploy
```bash
# Deploy with automatic secret generation
python noah.py deploy nextcloud --regenerate-secrets

# Deploy to custom namespace
python noah.py deploy nextcloud --namespace files --domain example.com

# Deploy with existing secrets
python noah.py deploy nextcloud
```

### Manual Deployment
```bash
# 1. Generate secrets
python Scripts/security_manager.py rotate nextcloud

# 2. Deploy chart
helm install nextcloud ./Helm/nextcloud \
  --namespace collaboration \
  --create-namespace \
  --values ./Helm/nextcloud/secrets/nextcloud-secrets.enc.yaml
```

## 🔐 Access Information

### Admin Access
- **URL**: https://cloud.noah-infra.com
- **Username**: nextcloud-admin
- **Password**: Auto-generated (displayed during deployment)

### SSO Access
- **Button**: "Log in with NOAH SSO"
- **Provider**: Authentik OIDC integration
- **Users**: All Authentik users can access with assigned permissions

## ⚙️ Configuration

### Main Configuration (`values.yaml`)
- **Host**: Domain configuration (cloud.noah-infra.com)
- **Persistence**: Storage sizes and classes
- **Resources**: CPU and memory limits
- **Ingress**: Traefik integration settings
- **Apps**: Additional Nextcloud applications

### Secret Configuration (`secrets/nextcloud-secrets.enc.yaml`)
- **Admin Password**: Nextcloud administrator credentials
- **OIDC Secret**: Authentik integration client secret
- **Database**: PostgreSQL root and user passwords
- **Redis**: Cache authentication password

### OIDC Configuration
Automatically configured for Authentik integration:
```php
'oidc_login_provider_url' => 'https://auth.noah-infra.com/application/o/nextcloud/',
'oidc_login_client_id' => 'nextcloud-oidc',
'oidc_login_button_text' => 'Log in with NOAH SSO',
'oidc_login_attributes' => [
    'id' => 'preferred_username',
    'name' => 'name', 
    'mail' => 'email',
    'groups' => 'groups'
]
```

## 🔄 Secret Management

### Automatic Rotation
Secrets are automatically rotated on each deployment when using `--regenerate-secrets`:
- Admin password
- Database passwords  
- Redis password
- OIDC client secret

### Manual Secret Operations
```bash
# Rotate all Nextcloud secrets
python Scripts/security_manager.py rotate nextcloud

# View encrypted secrets
sops -d Helm/nextcloud/secrets/nextcloud-secrets.enc.yaml

# Update specific secret
kubectl patch secret nextcloud-admin-secret -n collaboration --type merge -p '{"data":{"nextcloud-password":"bmV3LXBhc3N3b3Jk"}}'
```

## 🌐 Networking

### Ingress Configuration
- **Class**: traefik
- **Host**: cloud.noah-infra.com
- **TLS**: Automatic Let's Encrypt certificates
- **Middlewares**: Security headers and WebDAV redirects

### Security Headers
- Content Security Policy
- X-Frame-Options protection
- XSS protection
- HSTS enforcement
- WebDAV proper redirections

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Check deployment status
kubectl get pods -n collaboration

# Check ingress
kubectl get ingress -n collaboration

# Check secrets
kubectl get secrets -n collaboration
```

### Logs and Troubleshooting
```bash
# Nextcloud application logs
kubectl logs -n collaboration deployment/nextcloud-nextcloud

# Database logs  
kubectl logs -n collaboration deployment/nextcloud-postgresql

# Ingress logs
kubectl logs -n traefik deployment/traefik
```

### Common Issues
1. **OIDC Login Failed**: Check Authentik provider configuration
2. **Database Connection**: Verify PostgreSQL secret and connectivity
3. **File Upload Issues**: Check storage persistence and permissions
4. **SSL Certificate**: Verify Traefik certificate resolver

## 📈 Performance Tuning

### Storage Configuration
- **App Data**: 50Gi default (configurable)
- **User Files**: 100Gi default (configurable)
- **Database**: 20Gi default (configurable)
- **Redis**: 2Gi default (configurable)

### Resource Limits
- **Nextcloud**: 2 CPU cores, 2Gi RAM
- **PostgreSQL**: 1 CPU core, 1Gi RAM  
- **Redis**: 250m CPU, 256Mi RAM

### Caching Strategy
- **Local**: APCu for PHP opcache
- **Distributed**: Redis for sessions and file locking
- **Database**: PostgreSQL with connection pooling

## 🔧 Maintenance

### Backup Strategy
1. **Database**: PostgreSQL dumps via pg_dump
2. **Files**: Persistent volume snapshots
3. **Configuration**: SOPS-encrypted values
4. **Secrets**: Age-encrypted credential backup

### Update Process
1. Update chart dependencies: `helm dependency update`
2. Review changelog and breaking changes
3. Test in staging environment
4. Deploy with: `helm upgrade nextcloud ./Helm/nextcloud`
5. Verify functionality post-upgrade

## 📚 Additional Resources

- [Nextcloud Documentation](https://docs.nextcloud.com/)
- [OIDC User Backend](https://github.com/nextcloud/user_oidc)
- [Traefik Ingress](https://doc.traefik.io/traefik/providers/kubernetes-ingress/)
- [NOAH Security Manager](../Scripts/security_manager.py)
