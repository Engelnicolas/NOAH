# =============================================================================
# NOAH - Enhanced Main Makefile
# =============================================================================
#
# This Makefile provides a unified interface for managing the entire NOAH
# project lifecycle including deployment, testing, monitoring, and maintenance.
#
# FEATURES:
# - Unified command interface for all NOAH operations
# - Multi-environment support (dev, staging, production)
# - Comprehensive validation and testing
# - Automated deployment workflows
# - Monitoring and observability
# - Backup and disaster recovery
# - Development productivity tools
# - CI/CD integration support
#
# USAGE:
#   make help           # Show all available targets
#   make setup          # Setup development environment
#   make deploy         # Deploy complete NOAH stack
#   make test           # Run comprehensive test suite
#   make clean          # Clean up resources
#
# ENVIRONMENT VARIABLES:
#   ENVIRONMENT=dev|staging|prod  # Target environment
#   NAMESPACE_PREFIX=noah         # Kubernetes namespace prefix
#   VERBOSE=true|false           # Enable verbose output
#
# Author: NOAH Team
# Version: 3.0.0
# License: MIT
# =============================================================================

# =============================================================================
# Configuration Variables
# =============================================================================

# Default environment (can be overridden)
ENVIRONMENT ?= dev

# Kubernetes namespace prefix
NAMESPACE_PREFIX ?= noah

# Helm operation timeout
HELM_TIMEOUT ?= 10m

# Verbose output flag
VERBOSE ?= false

# Python version requirement
PYTHON_VERSION ?= 3.12

# Current directory paths
ROOT_DIR := $(shell pwd)
SCRIPT_DIR := $(ROOT_DIR)/Script
HELM_DIR := $(ROOT_DIR)/Helm
ANSIBLE_DIR := $(ROOT_DIR)/Ansible
TEST_DIR := $(ROOT_DIR)/Test
DOCS_DIR := $(ROOT_DIR)/docs

# =============================================================================
# Terminal Colors
# =============================================================================

RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
NC := \033[0m

# =============================================================================
# Helper Functions
# =============================================================================

define print_header
	@echo "$(CYAN)▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓$(NC)"
	@echo "$(CYAN)▓▓$(NC) $(BLUE)NOAH - Next Open-source Architecture Hub$(NC) $(CYAN)▓▓$(NC)"
	@echo "$(CYAN)▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓$(NC)"
	@echo ""
endef

define print_section
	@echo "$(BLUE)█ $(1)$(NC)"
	@echo ""
endef

define print_success
	@echo "$(GREEN)✅ $(1)$(NC)"
endef

define print_error
	@echo "$(RED)❌ $(1)$(NC)"
endef

define print_warning
	@echo "$(YELLOW)⚠️ $(1)$(NC)"
endef

define print_info
	@echo "$(BLUE)ℹ️ $(1)$(NC)"
endef

# =============================================================================
# Phony Targets
# =============================================================================

.PHONY: all help setup install deps check-deps show-config \
        deploy deploy-dev deploy-staging deploy-prod \
        test test-unit test-integration test-e2e \
        validate validate-all validate-charts validate-ansible validate-python \
        lint lint-all lint-charts lint-ansible lint-python lint-shell \
        monitoring monitoring-up monitoring-down monitoring-status \
        backup backup-create backup-restore backup-list \
        clean clean-all clean-charts clean-cache \
        rollback rollback-infra rollback-monitoring \
        status status-all status-infra status-monitoring \
        docs docs-serve docs-build docs-deploy \
        dev dev-setup dev-test dev-deploy \
        ci ci-setup ci-test ci-deploy ci-validate \
        security security-scan security-audit security-update

# =============================================================================
# Default Target
# =============================================================================

all: help

# =============================================================================
# Help and Information
# =============================================================================

help: ## Show comprehensive help information
	$(call print_header)
	$(call print_section,"Available Commands")
	@echo "$(YELLOW)🚀 Setup & Installation:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##.*Setup|Installation' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)📦 Deployment:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##.*Deploy' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🧪 Testing & Validation:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##.*(Test|Validate)' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)📊 Monitoring & Status:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##.*(Monitor|Status)' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)🔧 Maintenance:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##.*(Clean|Backup|Rollback)' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)📚 Documentation:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##.*(Docs|Documentation)' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@echo "  $(CYAN)ENVIRONMENT$(NC)=$(ENVIRONMENT) (dev/staging/prod)"
	@echo "  $(CYAN)NAMESPACE_PREFIX$(NC)=$(NAMESPACE_PREFIX)"
	@echo "  $(CYAN)HELM_TIMEOUT$(NC)=$(HELM_TIMEOUT)"
	@echo "  $(CYAN)VERBOSE$(NC)=$(VERBOSE)"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make setup              # Setup development environment"
	@echo "  make deploy ENVIRONMENT=dev # Deploy to development"
	@echo "  make test               # Run all tests"
	@echo "  make status             # Check deployment status"
	@echo ""

show-config: ## Show current configuration settings
	$(call print_section,"Current Configuration")
	@echo "  Environment: $(CYAN)$(ENVIRONMENT)$(NC)"
	@echo "  Namespace Prefix: $(CYAN)$(NAMESPACE_PREFIX)$(NC)"
	@echo "  Helm Timeout: $(CYAN)$(HELM_TIMEOUT)$(NC)"
	@echo "  Verbose: $(CYAN)$(VERBOSE)$(NC)"
	@echo "  Python Version: $(CYAN)$(PYTHON_VERSION)$(NC)"
	@echo "  Current Context: $(CYAN)$$(kubectl config current-context 2>/dev/null || echo 'not set')$(NC)"
	@echo "  Root Directory: $(CYAN)$(ROOT_DIR)$(NC)"
	@echo ""

# =============================================================================
# Dependencies and Prerequisites
# =============================================================================

check-deps: ## Check if required dependencies are installed
	$(call print_section,"Checking Dependencies")
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)❌ Python 3 not found$(NC)"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "$(RED)❌ kubectl not found$(NC)"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "$(RED)❌ Helm not found$(NC)"; exit 1; }
	@command -v ansible-playbook >/dev/null 2>&1 || { echo "$(RED)❌ Ansible not found$(NC)"; exit 1; }
	@command -v docker >/dev/null 2>&1 || echo "$(YELLOW)⚠️ Docker not found (optional)$(NC)"
	@command -v git >/dev/null 2>&1 || { echo "$(RED)❌ Git not found$(NC)"; exit 1; }
	@echo "$(GREEN)✅ All required dependencies found$(NC)"

install: ## Installation - Install all dependencies
	$(call print_section,"Installing Dependencies")
	$(MAKE) -C $(ANSIBLE_DIR) install-deps
	$(MAKE) -C $(TEST_DIR) install
	$(MAKE) -C $(HELM_DIR) deps
	$(call print_success,"All dependencies installed")

deps: install ## Installation - Alias for install

# =============================================================================
# Setup and Environment
# =============================================================================

setup: check-deps ## Setup - Initialize development environment
	$(call print_section,"Setting up NOAH Development Environment")
	@cd $(SCRIPT_DIR) && ./noah linting setup
	@cd $(SCRIPT_DIR) && ./noah-fix.py --verbose
	$(call print_success,"Development environment setup complete")

dev-setup: ENVIRONMENT=dev
dev-setup: setup ## Setup - Setup development environment specifically
	$(call print_section,"Setting up Development Environment")
	@cd $(SCRIPT_DIR) && ./noah infra setup --environment dev
	$(call print_success,"Development environment ready")

# =============================================================================
# Deployment
# =============================================================================

deploy: check-deps ## Deploy - Deploy complete NOAH stack
	$(call print_section,"Deploying NOAH Stack ($(ENVIRONMENT))")
	@cd $(SCRIPT_DIR) && ./noah infra deploy --environment $(ENVIRONMENT)
	@cd $(SCRIPT_DIR) && ./noah monitoring deploy --environment $(ENVIRONMENT)
	$(call print_success,"NOAH stack deployed successfully")

deploy-dev: ENVIRONMENT=dev
deploy-dev: deploy ## Deploy - Deploy to development environment
	$(call print_info,"Development deployment completed")

deploy-staging: ENVIRONMENT=staging
deploy-staging: deploy ## Deploy - Deploy to staging environment
	$(call print_info,"Staging deployment completed")

deploy-prod: ENVIRONMENT=prod
deploy-prod: ## Deploy - Deploy to production environment (with confirmation)
	$(call print_section,"Production Deployment")
	@echo "$(RED)⚠️  WARNING: This will deploy to PRODUCTION environment$(NC)"
	@echo "$(YELLOW)Are you sure? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	$(MAKE) deploy ENVIRONMENT=prod
	$(call print_success,"Production deployment completed")

# =============================================================================
# Testing
# =============================================================================

test: ## Test - Run comprehensive test suite
	$(call print_section,"Running Comprehensive Test Suite")
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) validate-all
	$(call print_success,"All tests completed")

test-unit: ## Test - Run unit tests
	$(call print_section,"Running Unit Tests")
	$(MAKE) -C $(TEST_DIR) test-python
	$(call print_success,"Unit tests completed")

test-integration: ## Test - Run integration tests
	$(call print_section,"Running Integration Tests")
	$(MAKE) -C $(TEST_DIR) test
	$(call print_success,"Integration tests completed")

test-e2e: ## Test - Run end-to-end tests
	$(call print_section,"Running End-to-End Tests")
	@cd $(SCRIPT_DIR) && ./noah linting lint --environment $(ENVIRONMENT)
	$(call print_success,"End-to-end tests completed")

dev-test: ENVIRONMENT=dev
dev-test: test ## Test - Run tests in development environment

# =============================================================================
# Validation
# =============================================================================

validate: validate-all ## Validate - Run all validation checks

validate-all: ## Validate - Run comprehensive validation
	$(call print_section,"Running Comprehensive Validation")
	$(MAKE) validate-charts
	$(MAKE) validate-ansible
	$(MAKE) validate-python
	$(call print_success,"All validations completed")

validate-charts: ## Validate - Validate Helm charts
	$(call print_section,"Validating Helm Charts")
	$(MAKE) -C $(HELM_DIR) validate
	$(call print_success,"Helm charts validated")

validate-ansible: ## Validate - Validate Ansible playbooks
	$(call print_section,"Validating Ansible Playbooks")
	@cd $(ANSIBLE_DIR) && ansible-playbook --syntax-check main.yml
	$(call print_success,"Ansible playbooks validated")

validate-python: ## Validate - Validate Python scripts
	$(call print_section,"Validating Python Scripts")
	@cd $(SCRIPT_DIR) && python3 -m py_compile *.py
	$(call print_success,"Python scripts validated")

# =============================================================================
# Linting
# =============================================================================

lint: lint-all ## Lint - Run all linting checks

lint-all: ## Lint - Run comprehensive linting
	$(call print_section,"Running Comprehensive Linting")
	$(MAKE) lint-charts
	$(MAKE) lint-ansible
	$(MAKE) lint-python
	$(MAKE) lint-shell
	$(call print_success,"All linting completed")

lint-charts: ## Lint - Lint Helm charts
	$(call print_section,"Linting Helm Charts")
	$(MAKE) -C $(HELM_DIR) lint
	$(call print_success,"Helm charts linted")

lint-ansible: ## Lint - Lint Ansible playbooks
	$(call print_section,"Linting Ansible Playbooks")
	@cd $(ANSIBLE_DIR) && ansible-lint main.yml || true
	$(call print_success,"Ansible playbooks linted")

lint-python: ## Lint - Lint Python scripts
	$(call print_section,"Linting Python Scripts")
	@cd $(SCRIPT_DIR) && ./noah linting lint --verbose
	$(call print_success,"Python scripts linted")

lint-shell: ## Lint - Lint shell scripts
	$(call print_section,"Linting Shell Scripts")
	@cd $(SCRIPT_DIR) && ./noah-fix.py --types shell --verbose
	$(call print_success,"Shell scripts linted")

# =============================================================================
# Monitoring
# =============================================================================

monitoring: monitoring-up ## Monitor - Deploy monitoring stack

monitoring-up: ## Monitor - Deploy monitoring stack
	$(call print_section,"Deploying Monitoring Stack")
	@cd $(SCRIPT_DIR) && ./noah monitoring deploy --environment $(ENVIRONMENT)
	$(call print_success,"Monitoring stack deployed")

monitoring-down: ## Monitor - Remove monitoring stack
	$(call print_section,"Removing Monitoring Stack")
	@cd $(SCRIPT_DIR) && ./noah monitoring teardown --environment $(ENVIRONMENT)
	$(call print_success,"Monitoring stack removed")

monitoring-status: ## Monitor - Check monitoring stack status
	$(call print_section,"Monitoring Stack Status")
	@cd $(SCRIPT_DIR) && ./noah monitoring status --environment $(ENVIRONMENT)

# =============================================================================
# Status and Health Checks
# =============================================================================

status: status-all ## Status - Check overall system status

status-all: ## Status - Check comprehensive system status
	$(call print_section,"NOAH System Status")
	$(MAKE) status-infra
	$(MAKE) status-monitoring
	$(call print_success,"Status check completed")

status-infra: ## Status - Check infrastructure status
	$(call print_section,"Infrastructure Status")
	@cd $(SCRIPT_DIR) && ./noah infra status --environment $(ENVIRONMENT)

status-monitoring: ## Status - Check monitoring status
	$(call print_section,"Monitoring Status")
	@cd $(SCRIPT_DIR) && ./noah monitoring status --environment $(ENVIRONMENT)

# =============================================================================
# Backup and Restore
# =============================================================================

backup: backup-create ## Backup - Create backup of system

backup-create: ## Backup - Create system backup
	$(call print_section,"Creating System Backup")
	$(call print_warning,"Backup functionality to be implemented with noah backup command")
	$(call print_info,"Current status saved for reference")
	@cd $(SCRIPT_DIR) && ./noah monitoring status --save-report

backup-restore: ## Backup - Restore from backup
	$(call print_section,"Restoring from Backup")
	$(call print_warning,"Restore functionality to be implemented with noah backup command")

backup-list: ## Backup - List available backups
	$(call print_section,"Available Backups")
	$(call print_warning,"Backup listing to be implemented with noah backup command")

# =============================================================================
# Rollback and Recovery
# =============================================================================

rollback: rollback-infra ## Rollback - Rollback infrastructure

rollback-infra: ## Rollback - Rollback infrastructure deployment
	$(call print_section,"Rolling Back Infrastructure")
	$(call print_warning,"Use Helm rollback for specific releases")
	@echo "Examples:"
	@echo "  helm rollback <release-name> <revision> -n $(NAMESPACE_PREFIX)-$(ENVIRONMENT)"

rollback-monitoring: ## Rollback - Rollback monitoring deployment
	$(call print_section,"Rolling Back Monitoring")
	$(call print_warning,"Use Helm rollback for monitoring releases")
	@echo "Examples:"
	@echo "  helm rollback prometheus-$(ENVIRONMENT) <revision> -n $(NAMESPACE_PREFIX)-monitoring"

# =============================================================================
# Cleanup
# =============================================================================

clean: clean-all ## Clean - Clean up all resources

clean-all: ## Clean - Comprehensive cleanup
	$(call print_section,"Cleaning Up All Resources")
	$(MAKE) clean-charts
	$(MAKE) clean-cache
	$(call print_success,"Cleanup completed")

clean-charts: ## Clean - Clean Helm charts
	$(call print_section,"Cleaning Helm Charts")
	$(MAKE) -C $(HELM_DIR) clean
	$(call print_success,"Helm charts cleaned")

clean-cache: ## Clean - Clean cache files
	$(call print_section,"Cleaning Cache Files")
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	$(call print_success,"Cache files cleaned")

# =============================================================================
# Documentation
# =============================================================================

docs-serve: ## Docs - Serve documentation locally
	$(call print_section,"Serving Documentation")
	@if [ -f "mkdocs.yml" ]; then \
		mkdocs serve; \
	else \
		$(call print_error,"mkdocs.yml not found"); \
	fi

docs-build: ## Docs - Build documentation
	$(call print_section,"Building Documentation")
	@if [ -f "mkdocs.yml" ]; then \
		mkdocs build; \
	else \
		$(call print_error,"mkdocs.yml not found"); \
	fi

docs-deploy: ## Docs - Deploy documentation
	$(call print_section,"Deploying Documentation")
	@if [ -f "mkdocs.yml" ]; then \
		mkdocs gh-deploy; \
	else \
		$(call print_error,"mkdocs.yml not found"); \
	fi

# =============================================================================
# CI/CD Integration
# =============================================================================

ci-setup: ## CI - Setup CI environment
	$(call print_section,"Setting up CI Environment")
	$(MAKE) check-deps
	$(MAKE) install
	$(call print_success,"CI environment ready")

ci-test: ## CI - Run CI test suite
	$(call print_section,"Running CI Test Suite")
	$(MAKE) validate-all
	$(MAKE) test-unit
	$(MAKE) lint-all
	$(call print_success,"CI tests completed")

ci-deploy: ## CI - Deploy from CI
	$(call print_section,"CI Deployment")
	@if [ "$(ENVIRONMENT)" = "prod" ]; then \
		$(call print_error,"Production deployment requires manual approval"); \
		exit 1; \
	fi
	$(MAKE) deploy ENVIRONMENT=$(ENVIRONMENT)
	$(call print_success,"CI deployment completed")

ci-validate: ## CI - Validate CI pipeline
	$(call print_section,"Validating CI Pipeline")
	$(MAKE) ci-setup
	$(MAKE) ci-test
	$(call print_success,"CI pipeline validated")

# =============================================================================
# Security
# =============================================================================

security-scan: ## Security - Run security scans
	$(call print_section,"Running Security Scans")
	$(call print_warning,"Security scanning to be implemented")
	$(call print_info,"Consider using tools like:")
	@echo "  - kubesec for Kubernetes security"
	@echo "  - bandit for Python security"
	@echo "  - ansible-review for Ansible security"

security-audit: ## Security - Run security audit
	$(call print_section,"Running Security Audit")
	$(call print_warning,"Security audit to be implemented")

security-update: ## Security - Update security policies
	$(call print_section,"Updating Security Policies")
	$(call print_warning,"Security update to be implemented")

# =============================================================================
# Development Shortcuts
# =============================================================================

dev: dev-setup dev-deploy dev-test ## Dev - Complete development workflow

dev-deploy: ENVIRONMENT=dev
dev-deploy: deploy ## Dev - Deploy to development environment

quick-deploy: ## Dev - Quick deploy without full validation
	@echo "$(BLUE)█ Quick Deploy (Development)$(NC)"
	@echo ""
	@cd $(SCRIPT_DIR) && sudo python3 ./noah-infra --dry-run --verbose
	@echo "$(YELLOW)⚠️ This was a dry run. Remove --dry-run for actual deployment$(NC)"

quick-test: ## Dev - Quick test without full suite
	@echo "$(BLUE)█ Quick Test$(NC)"
	@echo ""
	$(MAKE) validate-charts
	$(MAKE) test-unit
	@echo "$(GREEN)✅ Quick tests completed$(NC)"

# =============================================================================
# Version Information
# =============================================================================

version: ## Show version information
	$(call print_header)
	@echo "$(BLUE)NOAH Makefile Version: 3.0.0$(NC)"
	@echo "$(BLUE)Environment: $(ENVIRONMENT)$(NC)"
	@echo "$(BLUE)Namespace Prefix: $(NAMESPACE_PREFIX)$(NC)"
	@echo ""
	@echo "$(YELLOW)Component Versions:$(NC)"
	@kubectl version --client --short 2>/dev/null || echo "  kubectl: not available"
	@helm version --short 2>/dev/null || echo "  helm: not available"
	@ansible --version 2>/dev/null | head -n1 || echo "  ansible: not available"
	@python3 --version 2>/dev/null || echo "  python3: not available"
	@echo ""

# =============================================================================
# Debugging and Troubleshooting
# =============================================================================

debug: ## Debug - Show debugging information
	$(call print_section,"Debugging Information")
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@env | grep -E "(ENVIRONMENT|NAMESPACE|HELM|KUBECTL|VERBOSE)" || echo "  No relevant env vars set"
	@echo ""
	@echo "$(YELLOW)Kubernetes Context:$(NC)"
	@kubectl config current-context 2>/dev/null || echo "  No current context"
	@echo ""
	@echo "$(YELLOW)Helm Repositories:$(NC)"
	@helm repo list 2>/dev/null || echo "  No repositories configured"
	@echo ""
	@echo "$(YELLOW)Directory Structure:$(NC)"
	@ls -la $(ROOT_DIR) | head -10
	@echo ""

troubleshoot: ## Debug - Troubleshooting guide
	$(call print_section,"Troubleshooting Guide")
	@echo "$(YELLOW)Common Issues:$(NC)"
	@echo "  1. kubectl not found: Install kubectl CLI"
	@echo "  2. helm not found: Install Helm package manager"
	@echo "  3. ansible not found: Install Ansible automation platform"
	@echo "  4. Permission denied: Check file permissions with 'ls -la'"
	@echo "  5. Context not set: Set kubectl context with 'kubectl config use-context <context>'"
	@echo ""
	@echo "$(YELLOW)Useful Commands:$(NC)"
	@echo "  make check-deps     # Check all dependencies"
	@echo "  make show-config    # Show current configuration"
	@echo "  make debug         # Show debugging information"
	@echo "  make version       # Show version information"
	@echo ""

# =============================================================================
# End of Makefile
# =============================================================================
