# NOAH CI/CD Pipeline

This document describes the automated CI/CD pipeline for the NOAH project, based on Ansible, Kubespray, Helm, and GitHub Actions.

## 🏗️ Architecture

```
GitHub Actions (Orchestrator)
├── Ansible (Infrastructure & Config)
│   ├── Provision VMs (01-provision.yml)
│   ├── Install Kubernetes via Kubespray (02-install-k8s.yml)  
│   ├── Configure Cluster (03-configure-cluster.yml)
│   └── Deploy Apps via Helm (04-deploy-apps.yml)
└── Helm (Application Deployment)
    └── noah-chart (Main Chart)
```

## 🚀 Quick Start

1. **Initialize environment**
   ```bash
   ./script/setup-pipeline.sh
   ```

2. **Configure GitHub secrets**
   - `SSH_PRIVATE_KEY`: SSH private key to access servers
   - `ANSIBLE_VAULT_PASSWORD`: Password to decrypt Ansible secrets
   - `MASTER_HOST`: Master server IP/hostname for SSH configuration
   - `WORKER_HOSTS`: Worker server IPs/hostnames (comma-separated)

   **SSH Key Generation:**
   ```bash
   # Generate SSH key pair for deployment
   ssh-keygen -t ed25519 -C "noah-deployment@yourdomain.com" -f ~/.ssh/noah_deployment
   
   # Copy private key content to SSH_PRIVATE_KEY secret
   cat ~/.ssh/noah_deployment
   
   # Deploy public key to your servers
   ssh-copy-id -i ~/.ssh/noah_deployment.pub user@your-master-server
   ssh-copy-id -i ~/.ssh/noah_deployment.pub user@your-worker-servers
   ```

3. **Customize configuration**
   - Modify `ansible/inventory/mycluster/hosts.yaml` with your IPs
   - Adjust `values/values-prod.yaml` according to your needs
   - Update `ansible/vars/secrets.yml` with your secrets

4. **Trigger deployment**
   ```bash
   git push origin Ansible
   ```

## 📁 File Structure

```
.
├── .github/workflows/deploy.yml     # GitHub Actions workflow
├── ansible/
│   ├── ansible.cfg                  # Ansible configuration
│   ├── requirements.yml             # Required Ansible collections
│   ├── inventory/mycluster/
│   │   └── hosts.yaml              # Server inventory
│   ├── kubespray/                  # Kubespray submodule (auto-cloned)
│   ├── playbooks/
│   │   ├── 01-provision.yml        # Infrastructure provisioning
│   │   ├── 02-install-k8s.yml      # Kubernetes installation
│   │   ├── 03-configure-cluster.yml # Cluster configuration
│   │   ├── 04-deploy-apps.yml      # Application deployment
│   │   ├── 05-verify-deployment.yml # Deployment verification
│   │   └── 99-cleanup.yml          # Cleanup on failure
│   ├── templates/
│   │   ├── k8s-cluster.yml.j2      # Kubespray config template
│   │   └── deployment_report.j2    # Deployment report template
│   └── vars/
│       ├── global.yml              # Global variables
│       └── secrets.yml             # Secrets (encrypted with Vault)
├── helm/noah-chart/
│   ├── Chart.yaml                  # Main Helm chart
│   └── templates/                  # Kubernetes templates
├── script/
│   ├── setup-pipeline.sh           # Initialization script
│   ├── configure-pipeline.sh       # Configuration
│   ├── configure-ssh.sh            # Robust SSH configuration for CI/CD
│   ├── test-dependencies.sh        # Dependency validation
│   └── sops-secrets-manager.sh     # SOPS secrets management
└── values/
    └── values-prod.yaml            # Production configuration
```

## 🔄 Deployment Workflow

### 1. Infrastructure Provisioning
- VM creation on cloud provider
- Network and security configuration
- Master/worker role assignment

### 2. Kubernetes Installation
- Node preparation (packages, kernel modules, etc.)
- Using Kubespray to install K8s
- Network configuration with Calico
- Kubeconfig retrieval

### 3. Cluster Configuration
- Helm installation
- Ingress controller deployment (NGINX)
- Monitoring setup (Prometheus/Grafana)
- Namespaces and secrets creation

### 4. Application Deployment
- PostgreSQL (shared database)
- Keycloak (SSO authentication)
- GitLab (code management)
- Nextcloud (storage and collaboration)
- Mattermost (messaging)
- Grafana & Prometheus (monitoring)
- Wazuh & OpenEDR (security)
- OAuth2 Proxy (reverse proxy with auth)

### 5. Verification
- Connectivity tests
- Pod status verification
- Deployment report generation

## 🔐 Secrets Management

Secrets are managed with Ansible Vault:

```bash
# Encrypt secrets file
ansible-vault encrypt ansible/vars/secrets.yml

# Edit secrets
ansible-vault edit ansible/vars/secrets.yml

# Temporarily decrypt
ansible-vault decrypt ansible/vars/secrets.yml
```

## 🛠️ Customization

### Adding a New Application

1. Create a new Helm chart in `helm/`
2. Add configuration in `values/values-prod.yaml`
3. Integrate deployment in `ansible/playbooks/04-deploy-apps.yml`

### Modifying Kubernetes Configuration

1. Adjust variables in `ansible/vars/global.yml`
2. Modify template `ansible/templates/k8s-cluster.yml.j2`
3. Update inventory `ansible/inventory/mycluster/hosts.yaml`

### Changing Cloud Provider

1. Adapt tasks in `ansible/playbooks/01-provision.yml`
2. Add provider-specific Ansible modules
3. Update configuration variables

## 🔍 Troubleshooting

### Check Workflow Logs
```bash
# Via GitHub Actions interface
https://github.com/Engelnicolas/NOAH/actions

# Or locally
ansible-playbook ansible/playbooks/05-verify-deployment.yml -i ansible/inventory/mycluster/hosts.yaml
```

### Access Applications
```bash
# After deployment, configure /etc/hosts or DNS
echo "INGRESS_IP keycloak.noah.local" >> /etc/hosts
echo "INGRESS_IP gitlab.noah.local" >> /etc/hosts
echo "INGRESS_IP nextcloud.noah.local" >> /etc/hosts
echo "INGRESS_IP mattermost.noah.local" >> /etc/hosts
echo "INGRESS_IP grafana.noah.local" >> /etc/hosts
```

### Rollback on Issues
```bash
# Helm rollback
helm rollback <release-name> <revision> -n noah

# Or via Ansible
ansible-playbook ansible/playbooks/99-cleanup.yml -i ansible/inventory/mycluster/hosts.yaml
```

## 📊 Monitoring

The pipeline automatically deploys:
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **AlertManager**: Alert management

Access: https://grafana.noah.local (admin/configured_password)

## 🔒 Security

- All secrets encrypted with Ansible Vault
- TLS communications between components
- Kubernetes RBAC configured
- Ingress with OAuth2 authentication
- Security monitoring with Wazuh

## 🤝 Contributing

1. Create a branch for your changes
2. Test locally with `ansible-playbook --check`
3. Push and create a Pull Request
4. Pipeline runs automatically on merge

## 📞 Support

In case of issues:
1. Check GitHub Actions logs
2. Verify generated deployment report
3. Examine Kubernetes pod logs
4. Contact NOAH team
