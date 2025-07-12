# NOAH Helm Charts Makefile
# =========================
# Provides convenient commands for validating and managing Helm charts

.PHONY: help validate validate-fix validate-verbose deps lint yaml-lint template-test template-validate quick-template-test clean

# Default target
help:
	@echo "NOAH Helm Charts Management"
	@echo "=========================="
	@echo ""
	@echo "Available targets:"
	@echo "  help           Show this help message"
	@echo "  validate       Run full validation (dependencies, lint, templates)"
	@echo "  validate-fix   Run validation with automatic fixes"
	@echo "  validate-verbose Run validation with verbose output"
	@echo "  deps           Build Helm chart dependencies only"
	@echo "  lint           Run Helm chart linting only"
	@echo "  yaml-lint      Run YAML syntax validation only"
	@echo "  template-test  Test template rendering only"
	@echo "  template-validate Advanced template validation with multiple scenarios"
	@echo "  quick-template-test Quick template rendering test"
	@echo "  clean          Clean up dependency files"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Helm 3.x"
	@echo "  - yamllint (pip install yamllint)"
	@echo ""

# Run full validation
validate:
	@echo "🚀 Running full Helm charts validation..."
	@./Script/validate-charts.sh

# Run validation with fixes
validate-fix:
	@echo "🔧 Running validation with automatic fixes..."
	@./Script/validate-charts.sh --fix

# Run validation with verbose output
validate-verbose:
	@echo "📝 Running validation with verbose output..."
	@./Script/validate-charts.sh --verbose

# Build dependencies only
deps:
	@echo "📦 Building Helm chart dependencies..."
	@helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
	@helm repo add elastic https://helm.elastic.co 2>/dev/null || true
	@helm repo update
	@for chart in Helm/*; do \
		if [ -d "$$chart" ] && [ -f "$$chart/Chart.yaml" ]; then \
			if grep -q "dependencies:" "$$chart/Chart.yaml" 2>/dev/null; then \
				echo "Building dependencies for $$chart..."; \
				helm dependency build "$$chart" || exit 1; \
			fi; \
		fi; \
	done
	@echo "✅ Dependencies built successfully"

# Lint charts only
lint:
	@echo "🔍 Linting Helm charts..."
	@failed_charts=(); \
	for chart in Helm/*; do \
		if [ -d "$$chart" ] && [ -f "$$chart/Chart.yaml" ]; then \
			echo "Linting $$chart..."; \
			if ! helm lint "$$chart"; then \
				failed_charts+=($$chart); \
			fi; \
		fi; \
	done; \
	if [ $${#failed_charts[@]} -ne 0 ]; then \
		echo "❌ Failed charts: $${failed_charts[*]}"; \
		exit 1; \
	else \
		echo "✅ All charts passed linting"; \
	fi

# YAML syntax validation only
yaml-lint:
	@echo "📄 Validating YAML syntax..."
	@yamllint --config-file=Script/.yamllint.yml Helm/*/values.yaml Helm/*/Chart.yaml
	@echo "✅ YAML syntax validation passed"

# Test template rendering only
template-test:
	@echo "🎨 Testing template rendering..."
	@failed_charts=(); \
	for chart in Helm/*; do \
		if [ -d "$$chart" ] && [ -f "$$chart/Chart.yaml" ]; then \
			chart_name=$$(basename "$$chart"); \
			echo "Testing template rendering for $$chart_name..."; \
			if ! helm template "test-$$chart_name" "$$chart" --debug --dry-run >/dev/null 2>&1; then \
				failed_charts+=($$chart_name); \
			fi; \
		fi; \
	done; \
	if [ $${#failed_charts[@]} -ne 0 ]; then \
		echo "❌ Failed charts: $${failed_charts[*]}"; \
		exit 1; \
	else \
		echo "✅ All charts rendered successfully"; \
	fi

# Clean up generated files
clean:
	@echo "🧹 Cleaning up dependency files..."
	@find Helm -name "Chart.lock" -delete
	@find Helm -name "charts" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed"

# CI/CD friendly target (no interactive output)
ci-validate:
	@helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
	@helm repo add elastic https://helm.elastic.co >/dev/null 2>&1 || true
	@helm repo update >/dev/null 2>&1
	@for chart in Helm/*; do \
		if [ -d "$$chart" ] && [ -f "$$chart/Chart.yaml" ]; then \
			if grep -q "dependencies:" "$$chart/Chart.yaml" 2>/dev/null; then \
				helm dependency build "$$chart" || exit 1; \
			fi; \
		fi; \
	done
	@yamllint --config-file=Script/.yamllint.yml Helm/*/values.yaml Helm/*/Chart.yaml
	@for chart in Helm/*; do \
		if [ -d "$$chart" ] && [ -f "$$chart/Chart.yaml" ]; then \
			helm lint "$$chart" || exit 1; \
		fi; \
	done
	@for chart in Helm/*; do \
		if [ -d "$$chart" ] && [ -f "$$chart/Chart.yaml" ]; then \
			chart_name=$$(basename "$$chart"); \
			helm template "test-$$chart_name" "$$chart" --debug --dry-run >/dev/null || exit 1; \
		fi; \
	done

# Advanced template validation with multiple scenarios
template-validate:
	@echo "🔬 Running advanced template validation..."
	@../Script/validate-templates.sh

# Quick template rendering test
quick-template-test:
	@echo "🧪 Running quick template test..."
	@../Script/quick-template-test.sh
