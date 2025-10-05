# 🚀 NOAH  - Network Operations & Automation Hub

**NOAH** (Network Operations & Automation Hub) is a comprehensive Kubernetes infrastructure platform with integrated SSO, networking, and security automation.


## **What is NOAH?**

NOAH provides a complete infrastructure stack:

- **🔐 Authentik SSO** - Identity and access management
- **🌐 Cilium CNI** - Advanced networking with ingress
- **📊 Headlamp Dashboard** - Kubernetes web UI with SSO integration
- **🔒 Canonical Secrets Store** - Single authoritative encrypted secrets file (Age/SOPS protected)
- **🔄 Automated Deployment** - Single-command infrastructure setup
- **🧪 Testing Suite** - Built-in validation and health checks
- **🚀 CI/CD Ready** - GitHub Actions workflows included

## **Use Cases**

NOAH is designed for various infrastructure scenarios:

### **🏢 Small and Medium Enterprise & Organizations**
- **Corporate SSO** - Centralized authentication for all internal applications
- **Development Teams** - Rapid Kubernetes environment provisioning
- **IT Infrastructure** - Self-hosted identity provider with SSO integration
- **Security Compliance** - Encrypted secrets management and audit trails

### **🎓 Educational & Research**
- **Computer Science Labs** - Teaching Kubernetes, networking, and security
- **Research Projects** - Isolated, secure computing environments
- **Student Authentication** - Campus-wide SSO for academic applications
- **Lab Management** - Quick setup/teardown of experimental clusters

### **☁️ Cloud & DevOps**
- **Multi-Cloud Deployment** - Consistent infrastructure across providers
- **Development Environments** - Rapid dev/test cluster provisioning
- **CI/CD Integration** - Automated testing and deployment pipelines
- **Container Orchestration** - Production-ready Kubernetes with networking

## **Quick Start**

### **Single Command Deployment**
```bash

# Clone repository
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Install Python dependencies
pip install -r Scripts/requirements.txt

# Create the cluster
python noah.py cluster create --name your-cluster --domain your-domain.com

# Complete infrastructure deployment
python noah.py deploy core --domain your-domain.com

# Check status
python noah.py status

# Get credentials
python noah.py password show

# Test deployment
python noah.py test sso
```

## **Architecture Overview**

```
		  +-----------------------------+
		  |        End Users / Apps     |
		  +---------------+-------------+
				    |
				    v
			( HTTPS / OIDC / SSO )
				    |
	 +-----------------------+-----------------------+
	 |            Ingress & Network (Cilium)         |
	 |  - L7 routing  - TLS termination  - eBPF       |
	 +-----------------------+-----------------------+
				    |
				    v
		     +---------------------------+
		     |       Authentik SSO       |
		     |  Identity & Access Layer  |
		     +-----------+---------------+
				   |
		   +-------------+-------------+
		   |  PostgreSQL |    Redis    |
		   |  (State)    | (Sessions)  |
		   +------+------+-----+-------+
			   |            |
			   +-----+------+ 
				  |
		     +----------v-----------+
		     |   Kubernetes (K3s)   |
		     |  API / Scheduling    |
		     +----------+-----------+
				  |
		    Orchestrated Deployment
				  |
	 +----------+-----------+--------------+----------------+
	 |  NOAH CLI | Ansible   | Helm Charts  | Secrets Store  |
	 |  (Click)  | Playbooks | (Cilium,     | (Canonical)    |
	 |           |           |  Authentik)  | Age/SOPS YAML  |
	 +-----------+-----------+--------------+----------------+
				  |
			  Validation & Tests
			    (Health / DNS)
```

### Key Architectural Principles

- **Single Source of Truth for Secrets**: All sensitive material lives in a canonical encrypted YAML (metadata: `value`, `version`, `rotated_at`, plus integrity hash).
- **Deterministic Deployments**: `deploy core` funnels through one optimized Ansible playbook to ensure ordered, validated rollout (Cilium → Authentik → Headlamp → post‑checks).
- **Separation of Concerns**: Python CLI handles UX + secret prep; Ansible handles orchestration; Helm charts handle workload packaging.
- **Progressive Validation Modes**: `--validation-mode development|production` toggles depth (shortcuts vs full rollout + DNS/TLS checks + fail‑fast semantics).
- **Composable Security**: Secret generation and rotation isolated in `NoahSecurityManager` with versioned rotations and integrity verification.
- **Extensibility**: Add new services by defining required secrets, Helm values, and integrating into the playbook phases.
- **Safety in CI**: `NOAH_SKIP_ANSIBLE=true` allows fast credential/secrets path testing without a cluster.

### Runtime Flow (High-Level)
1. User invokes CLI (e.g., `python noah.py deploy core --domain example.com`).
2. Canonical secrets ensured (idempotent generation if missing).
3. Ansible playbook runs phased deployment (network → identity → dashboard → validation) with timing metrics.
4. DNS/TLS readiness & health probes surface environment status (production mode retries DNS & fails hard on phase errors).
5. Credentials displayed using canonical store (never scraped from Kubernetes secrets directly).
6. Tests / status commands provide post-deploy visibility.

### Future Enhancement Ideas
- Structured JSON summary artifact for CI pipelines.
- Ingress HTTP(S) probe with certificate validation.
- Watch-mode credentials command that waits for external IP + DNS.

## **Service Access**

After deployment, access services at:

- **Authentik SSO**: `https://auth.your-domain.com`
- **Headlamp Dashboard**: `https://headlamp.your-domain.com` (SSO via Authentik)
- **Cilium Hubble**: `https://hubble.your-domain.com`

Retrieve Authentik credentials via: `python noah.py password show`

**Note:** Headlamp uses Authentik for SSO authentication. Log in with your Authentik credentials to access the Kubernetes dashboard.

Rotate Authentik admin password (versioned with metadata):
```bash
python noah.py password new
# or during deployment
python noah.py deploy authentik --regenerate-password
```

Each secret carries metadata `{ value, version, rotated_at }` and an integrity hash is computed deterministically across services.

## **Requirements**

### **System**
- **OS**: Ubuntu 20.04+ (recommended)
- **Resources**: 4+ CPU cores, 8GB+ RAM, 50GB+ storage
- **Network**: Internet connectivity for component downloads

## **Testing & CI Shortcuts**

Lightweight test:
```bash
python Tests/test_noah.py
```

Mocked end-to-end secret generation without running real Ansible (useful in CI without Kubernetes):
```bash
NOAH_SKIP_ANSIBLE=true python Tests/test_deploy_core_secrets.py
```

Pytest example:
```bash
NOAH_SKIP_ANSIBLE=true python -m pytest Tests/test_deploy_core_secrets.py -q
```

Setting `NOAH_SKIP_ANSIBLE=true` causes the internal runner to skip invoking `ansible-playbook` while still performing canonical secret generation and CLI flow.

---
Made with ❤️