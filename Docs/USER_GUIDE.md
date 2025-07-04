# USER_GUIDE.md

## 🏁 Initial Setup Guide

This guide explains how to provision and validate a full test environment using Terraform, Ansible, Kubernetes, Helm, and GitLab CI.

---

### Prerequisites

Make sure the following tools are installed:

- Docker
- Terraform >= 1.3
- Ansible >= 2.12
- Helm >= 3.10
- Git >= 2.30
- GitLab Runner or GitHub Actions (optional)
- A Linux host (Fedora/Ubuntu recommended) or Docker container

---

### 1. Provision Infrastructure with Terraform

```bash
cd terraform
terraform init
terraform apply -auto-approve
```

This will provision virtual machines, networks, and DNS.

---

### 2. Deploy Infrastructure with Ansible

```bash
cd ../ansible
ansible-playbook -i inventory/dev/hosts.yml playbooks/deploy_all.yml
```

This installs all services (Keycloak, Nextcloud, Wazuh, etc.) and configures identity federation.

---

### 3. Validate Variable Setup

```bash
ansible-playbook -i inventory/dev/hosts.yml -e check_mode=true playbooks/deploy_all.yml
```

Runs Ansible in dry-run mode to catch missing or misconfigured variables.

---

### 4. Add Users to Samba AD

```bash
ansible-playbook -i inventory/dev/hosts.yml -t samba_ad
```

Users are created using the inventory-defined `user_list.yml`.

---

### 5. Import OIDC Clients to Keycloak

```bash
ansible-playbook -i inventory/dev/hosts.yml -t keycloak
```

OIDC clients for Nextcloud, Mattermost, Wazuh, and OpenEDR are imported.

---

### 6. Kubernetes Optional: Deploy with Helm

```bash
helm install keycloak ./helm/keycloak
helm install nextcloud ./helm/nextcloud
helm install mattermost ./helm/mattermost
helm install wazuh ./helm/wazuh
```

Set up your `kubeconfig` context before running this.

---

### 7. Run Post-Deployment Tests

```bash
ansible-playbook -i inventory/dev/hosts.yml playbooks/test_post_deploy.yml
```

This validates:
- Network (ping)
- Service availability (HTTP 200)
- LDAP port (389)
- Samba user presence
- OIDC metadata

---

### 8. Use GitLab CI (Optional)

```bash
gitlab-runner exec shell test_deployment
```

OR use the built-in `.gitlab-ci.yml` or `.github/workflows/ci.yml` for full automation.

---

### 9. Rollback (Optional)

```bash
ansible-playbook -i inventory/dev/hosts.yml playbooks/rollback.yml
```

This removes services and cleans up hosts in the event of a failure.

---

### 🔐 Final Notes

- All environments (`dev`, `staging`, `prod`) are supported through inventory switching.
- DNS updates are dynamic via `nsupdate`.
- Email/Slack alerts are enabled in CI/CD.