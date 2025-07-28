# 🔐 NOAH v2.0 - Guide de Sécurité

## 🛡️ Architecture de Sécurité

### Authentification & Autorisation
- **Keycloak** : Fournisseur d'identité centralisé avec SSO/SAML/OIDC
- **OAuth2 Proxy** : Proxy d'authentification pour protection des services
- **RBAC Kubernetes** : Contrôles d'accès granulaires

### Sécurité Réseau
- **TLS/SSL** : Chiffrement automatique avec cert-manager
- **Network Policies** : Segmentation réseau native Kubernetes
- **Ingress Controller** : Terminaison TLS et routage sécurisé

### Sécurité des Données
- **Ansible Vault** : Chiffrement des secrets et configurations
- **Secrets Kubernetes** : Gestion sécurisée des credentials
- **Volumes chiffrés** : Stockage persistant sécurisé

## � Comptes par Défaut

⚠️ **IMPORTANT** : Changez ces mots de passe après le déploiement !

| Service | Utilisateur | Mot de passe par défaut |
|---------|-------------|-------------------------|
| Keycloak | `admin` | `Keycl0ak_Admin_789!Strong` |
| GitLab | `root` | `GitL@b_Root_Password_012!` |
| Nextcloud | `admin` | `N3xtcloud_Admin_345!Safe` |
| Grafana | `admin` | `Gr@fana_Monitoring_678!View` |

## 🔧 Configuration Sécurisée

### Changer les mots de passe
```bash
# Décrypter et éditer les secrets
ansible-vault edit ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass

# Ou via le CLI
./noah.sh configure --secrets
```

### Configurer HTTPS
```bash
# Les certificats SSL sont automatiquement gérés par cert-manager
# Pour domaines personnalisés, éditer :
nano helm/noah-common/values.yaml
```

### Audit et Logs
```bash
# Consulter les logs de sécurité
kubectl logs -n noah -l app=keycloak
kubectl logs -n kube-system -l app=audit-policy-controller
```

## 🚨 Bonnes Pratiques

1. **Mots de passe** : Changez tous les mots de passe par défaut
2. **Réseau** : Utilisez des Network Policies pour isoler les services
3. **Accès** : Configurez RBAC Kubernetes approprié
4. **Monitoring** : Surveillez les logs d'authentification
5. **Mises à jour** : Maintenez les composants à jour

## 🔍 Vérification de Sécurité

```bash
# Vérifier la configuration TLS
./noah.sh test --security

# Audit des permissions
kubectl auth can-i --list

# État des certificats
kubectl get certificates -n noah
```

⚠️ **Important**: Change all default passwords before production deployment.

### Keycloak Admin
- **Username**: `admin`
- **Password**: `noah-admin-2024`
- **URL**: `https://keycloak.noah.local/admin`

### Database Access
- **PostgreSQL**: Auto-generated passwords stored in Kubernetes secrets
- **Redis**: Authentication via secret keys

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
