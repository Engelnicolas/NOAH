# Authentik Helm Chart for Samba 4 SSO Integration

This Helm chart deploys Authentik with Samba 4 Active Directory integration for Single Sign-On (SSO) capabilities.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- Samba 4 AD DC already deployed and running
- PV provisioner support in the underlying infrastructure

## Installation

1. Add the Bitnami repository for dependencies:
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

2. Update the dependencies:
```bash
helm dependency update
```

3. Configure your values in `custom-values.yaml`:
```yaml
authentik:
  ldap:
    enabled: true
    baseDn: "dc=noah-infra,dc=com"
    bindDn: "cn=Administrator,cn=Users,dc=noah-infra,dc=com"
    bindPassword: ""  # Set from secure secrets
    serverUri: "ldap://samba4.identity.svc.cluster.local:389"

ingress:
  hosts:
    - host: sso.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
```

4. Install the chart:
```bash
helm install authentik . -f custom-values.yaml
```

## Post-Installation Steps

1. Access Authentik at https://sso.yourdomain.com
2. Complete initial setup with admin user
3. Configure LDAP source for Samba 4 integration
4. Create applications and configure SSO providers

## Samba 4 Integration

The chart automatically configures:
- LDAP outpost for authentication
- LDAP source configuration for Samba 4 AD
- User and group synchronization

## Configuration

Key configuration options:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `authentik.ldap.enabled` | Enable LDAP integration | `true` |
| `authentik.ldap.serverUri` | Samba 4 LDAP server URI | `ldap://samba-dc.default.svc.cluster.local` |
| `authentik.ldap.baseDn` | LDAP Base DN | `dc=example,dc=com` |
| `authentik.ldap.bindDn` | LDAP Bind DN | `cn=Administrator,cn=Users,dc=example,dc=com` |
| `authentik.outposts.ldap.enabled` | Enable LDAP outpost | `true` |

## Uninstalling

```bash
helm uninstall authentik
```
