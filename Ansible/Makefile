# NOAH Ansible Makefile
# Provides convenient commands for deployment operations

.PHONY: help install-deps deploy deploy-parallel rollback scale backup validate clean

# Default target
help:
	@echo "NOAH Ansible Deployment Commands"
	@echo "======================================="
	@echo "install-deps    Install Ansible collections and dependencies"
	@echo "deploy          Deploy NOAH stack (sequential)"
	@echo "deploy-parallel Deploy NOAH stack (parallel where possible)"
	@echo "deploy-dev      Deploy to development environment"
	@echo "deploy-staging  Deploy to staging environment"
	@echo "deploy-prod     Deploy to production environment"
	@echo "rollback        Rollback deployment"
	@echo "rollback-force  Rollback with data removal (destructive)"
	@echo "scale           Scale services up/down"
	@echo "backup          Backup persistent data"
	@echo "validate        Run post-deployment validation"
	@echo "clean           Clean up logs and temporary files"
	@echo ""
	@echo "Example usage:"
	@echo "  make install-deps"
	@echo "  make deploy-dev"
	@echo "  make validate"

# Install required Ansible collections
install-deps:
	@echo "Installing Ansible collections..."
	ansible-galaxy collection install -r requirements.yml --force

# Standard deployment (sequential)
deploy:
	@echo "Deploying NOAH stack..."
	ansible-playbook -i inventory main.yml -v

# Parallel deployment where possible
deploy-parallel:
	@echo "Deploying NOAH stack (parallel mode)..."
	ansible-playbook -i inventory main.yml -e "parallel_deployment=true" -v

# Environment-specific deployments
deploy-dev:
	@echo "Deploying to development environment..."
	ansible-playbook -i inventory main.yml -l development -v

deploy-staging:
	@echo "Deploying to staging environment..."
	ansible-playbook -i inventory main.yml -l staging -v

deploy-prod:
	@echo "Deploying to production environment..."
	ansible-playbook -i inventory main.yml -l production -v

# Rollback operations
rollback:
	@echo "Rolling back NOAH deployment..."
	ansible-playbook -i inventory main.yml -e "rollback=true" --tags rollback -v

rollback-force:
	@echo "Rolling back with data removal (destructive operation)..."
	@read -p "Are you sure? This will delete all data! (y/N): " confirm && [ $$confirm = y ] || exit 1
	ansible-playbook -i inventory main.yml -e "rollback=true" -e "remove_data=true" -e "auto_confirm=true" --tags rollback -v

# Scaling operations
scale:
	@echo "Scaling NOAH services..."
	ansible-playbook -i inventory main.yml -e "scale_services=true" --tags scaling -v

# Backup operations
backup:
	@echo "Backing up NOAH data..."
	ansible-playbook -i inventory main.yml -e "backup_enabled=true" --tags backup -v

# Validation
validate:
	@echo "Running post-deployment validation..."
	ansible-playbook -i inventory main.yml --tags validation -v

# Cleanup
clean:
	@echo "Cleaning up temporary files..."
	rm -f /tmp/ansible-noah.log
	rm -f /tmp/noah_deployment_*.txt
	rm -rf /tmp/noah-backup/

# Check syntax
check:
	@echo "Checking Ansible syntax..."
	ansible-playbook -i inventory main.yml --syntax-check

# Dry run
dry-run:
	@echo "Performing dry run..."
	ansible-playbook -i inventory main.yml --check -v

# Show inventory
inventory:
	@echo "Showing inventory..."
	ansible-inventory -i inventory --list

# Install kubectl (helper)
install-kubectl:
	@echo "Installing kubectl..."
	curl -LO https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl
	chmod +x kubectl
	sudo mv kubectl /usr/local/bin/

# Install helm (helper)
install-helm:
	@echo "Installing Helm..."
	curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
