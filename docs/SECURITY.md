# 🔐 NOAH v0.2.1 - Security Guide

## 🛡️ Security Architecture

### Authentication & Authorization
- **Keycloak**: Centralized identity provider with SSO/SAML/OIDC
- **OAuth2 Proxy**: Authentication proxy for service protection
- **Kubernetes RBAC**: Granular access controls

### Network Security
- **TLS/SSL**: Automatic encryption with cert-manager
- **Network Policies**: Native Kubernetes network segmentation
- **Ingress Controller**: TLS termination and secure routing

### Data Security
- **Ansible Vault**: Encryption of secrets and configurations
- **Kubernetes Secrets**: Secure credential management
- **Encrypted Volumes**: Secure persistent storage

## 🔑 Default Accounts

⚠️ **IMPORTANT**: Change these passwords after deployment!

| Service | Username | Default Password |
|---------|----------|------------------|
| Keycloak | `admin` | `Keycl0ak_Admin_789!Strong` |
| GitLab | `root` | `GitL@b_Root_Password_012!` |
| Nextcloud | `admin` | `N3xtcloud_Admin_345!Safe` |
| Grafana | `admin` | `Gr@fana_Monitoring_678!View` |

## 🔧 Secure Configuration

### Change Passwords
```bash
# Decrypt and edit secrets
ansible-vault edit ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass

# Or via CLI
./noah configure --secrets
```

### Configure HTTPS
```bash
# SSL certificates are automatically managed by cert-manager
# For custom domains, edit:
nano helm/noah-common/values.yaml
```

### Audit and Logging
```bash
# View security logs
kubectl logs -n noah -l app=keycloak
kubectl logs -n kube-system -l app=audit-policy-controller
```

## 🚨 Best Practices

1. **Passwords**: Change all default passwords
2. **Network**: Use Network Policies to isolate services
3. **Access**: Configure appropriate Kubernetes RBAC
4. **Monitoring**: Monitor authentication logs
5. **Updates**: Keep components up to date

## 🔍 Security Verification

```bash
# Verify TLS configuration
./noah test --security

# Audit permissions
kubectl auth can-i --list

# Certificate status
kubectl get certificates -n noah
```

## 🔒 Security Features

### Data Protection
- **Encryption at Rest**: Persistent volumes encrypted
- **Encryption in Transit**: TLS 1.3 for all communications
- **Secret Management**: Kubernetes secrets with RBAC

### Access Control
- **RBAC**: Role-based access control for Kubernetes
- **Multi-factor Authentication**: Optional MFA via Keycloak
- **Session Management**: Configurable session timeouts

### Monitoring & Auditing
- **Wazuh SIEM**: Security information and event management
- **OpenEDR**: Endpoint detection and response
- **Audit Logs**: Comprehensive logging for all services

## ⚙️ Security Configuration

### Minimal Profile (Development)
```yaml
security:
  tls:
    enabled: false          # HTTP only for development
  networkPolicies:
    enabled: false          # No network restrictions
  podSecurityPolicy:
    enabled: false          # Permissive security context
```

### Root Profile (Production)
```yaml
security:
  tls:
    enabled: true           # HTTPS enforced
    certificate: "letsencrypt"
  networkPolicies:
    enabled: true           # Network segmentation
  podSecurityPolicy:
    enabled: true           # Strict security context
```

## 🚨 Security Monitoring

### Real-time Alerts
- Failed authentication attempts
- Privilege escalation attempts
- Network policy violations
- Resource abuse detection

### Log Sources
- Kubernetes API server
- Application logs
- Network traffic
- System events

## 🔧 Hardening Checklist

### Pre-deployment
- [ ] Change all default passwords
- [ ] Configure TLS certificates
- [ ] Set up network policies
- [ ] Enable audit logging
- [ ] Configure backup encryption

### Post-deployment
- [ ] Verify authentication flows
- [ ] Test network isolation
- [ ] Validate monitoring alerts
- [ ] Review access permissions
- [ ] Update security documentation

## 🆘 Incident Response

### Security Incident Workflow
1. **Detection**: Automated alerts via Wazuh/Prometheus
2. **Assessment**: Severity classification and impact analysis
3. **Containment**: Isolate affected components
4. **Eradication**: Remove threats and vulnerabilities
5. **Recovery**: Restore services and validate security
6. **Lessons Learned**: Update procedures and documentation

## 📚 Security Resources

### Documentation
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Keycloak Security Guide](https://www.keycloak.org/docs/latest/securing_apps/)
- [OWASP Kubernetes Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Kubernetes_Security_Cheat_Sheet.html)
- [Wazuh Documentation](https://documentation.wazuh.com/current/index.html)
