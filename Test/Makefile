# N.O.A.H Simple Test Makefile
# ============================

.PHONY: help install test test-charts test-shell clean

# Default target
help:
	@echo "N.O.A.H Test Commands"
	@echo "===================="
	@echo ""
	@echo "  install      Install dependencies"
	@echo "  test         Run all tests (Python + Shell)"
	@echo "  test-python  Run Python tests only"
	@echo "  test-shell   Run shell tests only"
	@echo "  test-charts  Run Helm chart tests only"
	@echo "  clean        Clean test artifacts"
	@echo "  check-deps   Check dependencies"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Run all tests
test:
	@echo "Running comprehensive test suite..."
	./unified_tests.sh

# Run Python tests only
test-python:
	@echo "Running Python tests..."
	python3 noah_test.py -v

# Run shell tests only  
test-shell:
	@echo "Running shell tests..."
	./unified_tests.sh --python-only

# Run only chart tests
test-charts:
	@echo "Running Helm chart tests..."
	./unified_tests.sh --helm-only

# Clean artifacts
clean:
	@echo "Cleaning test artifacts..."
	rm -rf __pycache__/
	rm -f *.json
	rm -f *.html
	rm -f *.log
	rm -f /tmp/noah_test*

# Check dependencies
check-deps:
	@echo "Checking dependencies..."
	./unified_tests.sh --deps-only
