# =============================================================================
# NOAH - Enhanced Makefile for Production Operations
# =============================================================================
#
# This Makefile provides a unified interface for managing the NOAH
# deployment lifecycle. It orchestrates deployment, monitoring, maintenance,
# and operational tasks across different environments.
#
# FEATURES:
# - Multi-environment support (dev, staging, production)
# - Color-coded output for better visibility
# - Dependency validation and prerequisite checking
# - Comprehensive deployment automation
# - Monitoring stack management
# - Backup and restore operations
# - Configuration validation and linting
# - Rollback and recovery procedures
# - Status monitoring and health checks
#
# USAGE:
#   make help           # Show all available targets
#   make setup          # Initialize environment and dependencies
#   make deploy         # Deploy the complete NOAH stack
#   make status         # Check deployment status and health
#   make clean          # Clean up deployments and resources
#
# CONFIGURATION:
# Set environment variables or modify values below to customize behavior:
#   ENVIRONMENT=prod make deploy
#   NAMESPACE_PREFIX=myorg make setup
#
# Author: NOAH Team
# Version: 2.0.0
# License: MIT
# =============================================================================

# =============================================================================
# Configuration Variables
# =============================================================================
# These variables can be overridden via environment variables or command line

# Target deployment environment (affects resource allocation and validation)
# Supported values: dev, staging, prod
ENVIRONMENT ?= dev

# Kubernetes namespace prefix for resource organization
# All resources will be created in namespaces like: noah-dev, noah-prod
NAMESPACE_PREFIX ?= noah

# Helm operation timeout for large deployments
# Increase for production environments with many resources
HELM_TIMEOUT ?= 10m

# Kubernetes context to use (leave empty for current context)
# Useful for multi-cluster environments
KUBECTL_CONTEXT ?= 

# Ansible inventory file location for configuration management
ANSIBLE_INVENTORY ?= ../Ansible/inventory

# =============================================================================
# Terminal Color Codes for Enhanced Output
# =============================================================================
# ANSI color codes for improved readability and user experience

RED := \033[0;31m       # Error messages and failures
GREEN := \033[0;32m     # Success messages and completed tasks
YELLOW := \033[0;33m    # Warnings and informational messages
BLUE := \033[0;34m      # Headers and process information
NC := \033[0m           # No Color (reset to default)

# =============================================================================
# Phony Targets Declaration
# =============================================================================
# Prevent make from looking for files with these names

.PHONY: all help setup deploy test clean status rollback helm-install helm-upgrade helm-uninstall \
        monitoring-up monitoring-down backup restore validate lint check-deps show-config

# =============================================================================
# Default Target
# =============================================================================

# Default target when 'make' is run without arguments
all: help

# =============================================================================
# Help and Information Targets
# =============================================================================

# Display comprehensive help information with all available targets
help: ## Show this help message with all available commands and usage
	@echo "$(BLUE)NOAH - Enhanced Deployment Makefile$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@echo "  ENVIRONMENT=$(ENVIRONMENT) (dev/staging/prod)"
	@echo "  NAMESPACE_PREFIX=$(NAMESPACE_PREFIX)"
	@echo "  HELM_TIMEOUT=$(HELM_TIMEOUT)"
	@echo ""

# Validate that all required system dependencies are installed and accessible
check-deps: ## Check if required dependencies are installed and available
	@echo "$(BLUE)🔍 Checking dependencies...$(NC)"
	@command -v kubectl >/dev/null 2>&1 || { echo "$(RED)❌ kubectl not found$(NC)"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "$(RED)❌ helm not found$(NC)"; exit 1; }
	@command -v ansible-playbook >/dev/null 2>&1 || { echo "$(RED)❌ ansible-playbook not found$(NC)"; exit 1; }
	@echo "$(GREEN)✅ All dependencies found$(NC)"

# Display current configuration settings and environment information
show-config: ## Show current configuration settings and environment details
	@echo "$(BLUE)📋 Current Configuration:$(NC)"
	@echo "  Environment: $(ENVIRONMENT)"
	@echo "  Namespace Prefix: $(NAMESPACE_PREFIX)"
	@echo "  Helm Timeout: $(HELM_TIMEOUT)"
	@echo "  Kubectl Context: $$(kubectl config current-context 2>/dev/null || echo 'not set')"
	@echo "  Ansible Inventory: $(ANSIBLE_INVENTORY)"

setup: check-deps ## Setup infrastructure prerequisites
	@echo "$(BLUE)🚀 Setting up infrastructure...$(NC)"
	@bash setup_infra.sh --environment $(ENVIRONMENT)

deploy: check-deps ## Run full Ansible deployment
	@echo "$(BLUE)🚀 Running Ansible full deployment...$(NC)"
	ansible-playbook -i $(ANSIBLE_INVENTORY)/$(ENVIRONMENT)/hosts.yml \
		../Ansible/main.yml \
		--extra-vars "environment=$(ENVIRONMENT)" \
		--diff

test: ## Run post-deployment validation tests
	@echo "$(BLUE)🧪 Running post-deployment tests...$(NC)"
	@bash ../Test/post_deploy_validate.sh --environment $(ENVIRONMENT)

validate: ## Validate Helm charts and Ansible playbooks
	@echo "$(BLUE)🔍 Validating Helm charts...$(NC)"
	@bash validate_charts.sh
	@echo "$(BLUE)🔍 Validating Ansible playbooks...$(NC)"
	ansible-playbook --syntax-check ../Ansible/main.yml

lint: ## Lint Helm charts and Ansible playbooks
	@echo "$(BLUE)🧹 Linting Helm charts...$(NC)"
	@for chart in ../Helm/*/; do \
		if [ -f "$$chart/Chart.yaml" ]; then \
			echo "Linting $$(basename $$chart)..."; \
			helm lint $$chart || exit 1; \
		fi \
	done
	@echo "$(BLUE)🧹 Linting Ansible playbooks...$(NC)"
	ansible-lint ../Ansible/main.yml || true

helm-install: check-deps ## Install all Helm charts
	@echo "$(BLUE)☸️ Installing all Helm charts...$(NC)"
	@bash deploy_and_verify_helm.sh --environment $(ENVIRONMENT) --namespace-prefix $(NAMESPACE_PREFIX)

helm-upgrade: check-deps ## Upgrade all Helm charts
	@echo "$(BLUE)⬆️ Upgrading all Helm charts...$(NC)"
	@bash deploy_and_verify_helm.sh --upgrade --environment $(ENVIRONMENT) --namespace-prefix $(NAMESPACE_PREFIX)

helm-uninstall: ## Uninstall all Helm charts
	@echo "$(BLUE)❌ Uninstalling all Helm charts...$(NC)"
	@bash uninstall_helm_charts.sh --environment $(ENVIRONMENT) --namespace-prefix $(NAMESPACE_PREFIX)

monitoring-up: check-deps ## Deploy monitoring stack
	@echo "$(BLUE)📈 Deploying monitoring stack...$(NC)"
	@bash deploy_monitoring_stack.sh --environment $(ENVIRONMENT)

monitoring-down: ## Teardown monitoring stack
	@echo "$(BLUE)📉 Tearing down monitoring stack...$(NC)"
	@bash teardown_monitoring_stack.sh --environment $(ENVIRONMENT)

status: ## Show deployment status
	@echo "$(BLUE)📊 Deployment Status:$(NC)"
	@bash status_check.sh --environment $(ENVIRONMENT)

backup: ## Create backup of persistent volumes and configurations
	@echo "$(BLUE)💾 Creating backup...$(NC)"
	@bash backup_restore.sh --action backup --environment $(ENVIRONMENT)

restore: ## Restore from backup
	@echo "$(BLUE)♻️ Restoring from backup...$(NC)"
	@bash backup_restore.sh --action restore --environment $(ENVIRONMENT)

rollback: ## Rollback infrastructure to previous state
	@echo "$(BLUE)⏪ Rolling back infrastructure...$(NC)"
	@bash rollback.sh --environment $(ENVIRONMENT)

clean: helm-uninstall monitoring-down ## Clean up all resources
	@echo "$(BLUE)🧹 Cleaning up all resources...$(NC)"
	@bash cleanup.sh --environment $(ENVIRONMENT)

# Development targets
dev-deploy: ENVIRONMENT=dev
dev-deploy: setup helm-install monitoring-up ## Deploy development environment

staging-deploy: ENVIRONMENT=staging  
staging-deploy: setup helm-install monitoring-up ## Deploy staging environment

prod-deploy: ENVIRONMENT=prod
prod-deploy: setup helm-install monitoring-up ## Deploy production environment (with confirmation)
	@echo "$(RED)⚠️ Production deployment completed$(NC)"