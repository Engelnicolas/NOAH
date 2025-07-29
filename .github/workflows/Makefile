# =============================================================================
# NOAH - Makefile
# =============================================================================
#
# A streamlined interface for NOAH project management
#
# USAGE:
#   make help       # Show available targets
#   make setup      # Setup development environment
#   make deploy     # Deploy complete NOAH stack
#   make test       # Run tests
#   make clean      # Clean up resources
#
# Author: NOAH Team
# Version: 0.3.0 
# License: MIT
# =============================================================================

# Default environment
ENVIRONMENT ?= dev
NAMESPACE_PREFIX ?= noah

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m

# Phony targets
.PHONY: all help setup deploy test clean status validate

# Default target
all: help

# =============================================================================
# Help
# =============================================================================

help: ## Show available commands
	@echo "$(CYAN)NOAH - Network Operations & Automation Hub$(NC)"
	@echo ""
	@echo "$(YELLOW)Available Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Environment:$(NC) $(ENVIRONMENT)"
	@echo ""

# =============================================================================
# Main Commands
# =============================================================================

setup: ## Setup development environment
	@echo "$(BLUE)Setting up NOAH development environment...$(NC)"
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)Python 3 required$(NC)"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "$(RED)kubectl required$(NC)"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "$(RED)helm required$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Environment ready$(NC)"

deploy: ## Deploy NOAH stack
	@echo "$(BLUE)Deploying NOAH stack ($(ENVIRONMENT))...$(NC)"
	@cd ../.. && ./noah deploy --profile $(ENVIRONMENT)
	@echo "$(GREEN)✅ Deployment complete$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	@cd ../.. && ./noah test
	@echo "$(GREEN)✅ Tests complete$(NC)"

status: ## Check deployment status
	@echo "$(BLUE)Checking NOAH status...$(NC)"
	@cd ../.. && ./noah status --all
	@echo "$(GREEN)✅ Status check complete$(NC)"

validate: ## Validate configuration
	@echo "$(BLUE)Validating configuration...$(NC)"
	@cd ../.. && ./noah validate
	@echo "$(GREEN)✅ Validation complete$(NC)"

clean: ## Clean up resources
	@echo "$(BLUE)Cleaning up...$(NC)"
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

# =============================================================================
# Environment-specific shortcuts
# =============================================================================

dev: ENVIRONMENT=dev
dev: deploy ## Deploy to development

prod: ENVIRONMENT=prod
prod: ## Deploy to production (with confirmation)
	@echo "$(RED)⚠️  WARNING: Production deployment$(NC)"
	@echo "$(YELLOW)Continue? [y/N]$(NC)" && read ans && [ $${ans:-N} = y ]
	@$(MAKE) deploy ENVIRONMENT=prod

version: ## Show version information
	@echo "$(CYAN)NOAH Makefile v4.0.0 (Simplified)$(NC)"
	@echo "$(BLUE)Environment: $(ENVIRONMENT)$(NC)"
	@kubectl version --client --short 2>/dev/null || echo "kubectl: not available"
	@helm version --short 2>/dev/null || echo "helm: not available"


