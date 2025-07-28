# 🔐 NOAH Security Guide

## Overview

This document outlines the security features, best practices, and configuration guidelines for the NOAH (Next Open-source Architecture Hub) platform.

## 🛡️ Security Architecture

### Authentication & Authorization
- **Keycloak**: Centralized identity provider with SSO
- **OAuth2 Proxy**: Authentication proxy for service protection
- **LDAP/Samba4**: Directory services for user management

### Network Security
- **Network Policies**: Kubernetes-native network segmentation
- **Ingress Controls**: TLS termination and traffic routing
- **Service Mesh**: Optional Istio integration for advanced security

## 🔑 Default Credentials

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
