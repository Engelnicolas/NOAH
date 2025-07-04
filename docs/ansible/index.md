# Ansible Documentation

This section contains documentation for the Ansible automation included in the N.O.A.H project.

## Overview

The Ansible automation provides:
- **Infrastructure Configuration**: Automated setup of core services
- **Service Deployment**: Orchestrated rollout of all platform components  
- **Identity Management**: LDAP/OIDC integration and user management
- **Security Configuration**: Network policies, monitoring, and compliance

## Structure

```
Ansible/
├── main.yml                 # Master playbook
├── inventory               # Host and group definitions
├── ansible.cfg            # Ansible configuration
├── requirements.yml        # Required collections and roles
├── vars/
│   └── global.yml          # Global variables
├── roles/                  # Custom roles
└── templates/              # Jinja2 templates
```

## Available Roles

### Core Infrastructure
- **`ldap_samba4`** - Samba4 Active Directory deployment
- **`keycloak`** - Identity provider configuration
- **`oauth2_proxy`** - Authentication proxy setup

### Collaboration Services
- **`collab_platforms`** - Nextcloud and Mattermost deployment
- **`gitlab`** - GitLab CE installation and configuration

### Security & Monitoring
- **`wazuh`** - SIEM deployment and configuration
- **`openedr`** - Endpoint detection setup
- **`monitoring`** - Prometheus and Grafana stack
- **`ufw`** - Firewall configuration
- **`openvpn`** - VPN server setup

### Integration
- **`federation`** - OIDC federation between services
- **`openvpn_auth`** - VPN authentication with LDAP

## Usage

### Basic Deployment
```bash
cd Ansible
ansible-playbook main.yml -i inventory
```

### Environment-Specific Deployment
```bash
# Development environment
ansible-playbook main.yml -i inventory --limit development

# Production with specific tags
ansible-playbook main.yml -i inventory --tags "phase1,phase2"
```

### Configuration

#### Global Variables
Edit `vars/global.yml` to customize:
- Domain names and certificates
- Service credentials
- Resource limits
- Feature toggles

#### Inventory
The inventory file defines:
- Target environments (local, dev, staging, prod)
- Environment-specific variables
- Host groups and connectivity

### Advanced Features

#### Parallel Deployment
Enable parallel deployment for faster rollouts:
```yaml
parallel_deployment: true
```

#### Validation and Testing
Enable comprehensive validation:
```yaml
run_validation: true
```

#### Rollback Support
Automated rollback on critical failures with state tracking.

## Development Guidelines

### Role Development
- Follow Ansible best practices
- Use descriptive task names
- Include proper error handling
- Test with different environments

### Variable Management
- Use group_vars and host_vars appropriately
- Encrypt sensitive data with ansible-vault
- Document all variables in defaults/main.yml

### Testing
- Syntax validation: `ansible-playbook --syntax-check`
- Dry run: `ansible-playbook --check`
- Integration tests in Test/ directory

For detailed role documentation, see the individual role directories under `roles/`.
