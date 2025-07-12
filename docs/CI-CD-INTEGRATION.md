# NOAH CI/CD Integration Guide

This document provides code examples and configurations for integrating NOAH Helm charts validation into various CI/CD systems.

## GitHub Actions

### Complete Workflow Example

The repository includes a complete GitHub Actions workflow at `.github/workflows/helm-validation.yml`. Key features:

- ✅ Automatic dependency building
- ✅ YAML syntax validation  
- ✅ Helm chart linting
- ✅ Template rendering tests
- ✅ Validation reporting

### Quick Integration Snippet

For existing workflows, add this step before your tests:

```yaml
- name: Build Helm dependencies
  run: |
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add elastic https://helm.elastic.co
    helm repo update
    for chart in Helm/*; do
      if [ -d "$chart" ] && [ -f "$chart/Chart.yaml" ]; then
        if grep -q "dependencies:" "$chart/Chart.yaml"; then
          helm dependency build "$chart" || exit 1
        fi
      fi
    done
```

## GitLab CI

### Complete Pipeline Example

```yaml
stages:
  - validate
  - test
  - deploy

variables:
  HELM_VERSION: "3.13.3"

.helm-base: &helm-base
  image: alpine/helm:$HELM_VERSION
  before_script:
    - apk add --no-cache bash python3 py3-pip
    - pip install yamllint

helm-validate:
  <<: *helm-base
  stage: validate
  script:
    - helm repo add bitnami https://charts.bitnami.com/bitnami
    - helm repo add elastic https://helm.elastic.co
    - helm repo update
    - ./Script/validate-charts.sh --verbose
  only:
    changes:
      - Helm/**/*
      - Script/.yamllint.yml
```

### Quick Integration Snippet

```yaml
build-dependencies:
  stage: validate
  script:
    - for chart in Helm/*; do
        if [ -d "$chart" ] && [ -f "$chart/Chart.yaml" ]; then
          helm dependency build "$chart" || exit 1
        fi
      done
```

## Jenkins Pipeline

### Declarative Pipeline Example

```groovy
pipeline {
    agent any
    
    environment {
        HELM_VERSION = '3.13.3'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    # Install Helm if not available
                    if ! command -v helm &> /dev/null; then
                        curl https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz | tar xz
                        sudo mv linux-amd64/helm /usr/local/bin/
                    fi
                    
                    # Install yamllint
                    pip install yamllint
                '''
            }
        }
        
        stage('Build Dependencies') {
            steps {
                sh '''
                    helm repo add bitnami https://charts.bitnami.com/bitnami
                    helm repo add elastic https://helm.elastic.co
                    helm repo update
                    
                    for chart in Helm/*; do
                        if [ -d "$chart" ] && [ -f "$chart/Chart.yaml" ]; then
                            if grep -q "dependencies:" "$chart/Chart.yaml"; then
                                echo "Building dependencies for $chart"
                                helm dependency build "$chart"
                            fi
                        fi
                    done
                '''
            }
        }
        
        stage('Validate Charts') {
            steps {
                sh './Script/validate-charts.sh --verbose'
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'Helm/*/Chart.lock', allowEmptyArchive: true
        }
    }
}
```

## Azure DevOps

### Pipeline Example

```yaml
trigger:
  branches:
    include:
      - main
      - develop
  paths:
    include:
      - Helm/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  helmVersion: '3.13.3'

stages:
- stage: Validate
  displayName: 'Validate Helm Charts'
  jobs:
  - job: HelmValidation
    displayName: 'Helm Validation'
    steps:
    - task: HelmInstaller@1
      displayName: 'Install Helm'
      inputs:
        helmVersionToInstall: $(helmVersion)
    
    - task: UsePythonVersion@0
      displayName: 'Setup Python'
      inputs:
        versionSpec: '3.11'
    
    - script: |
        pip install yamllint
        helm repo add bitnami https://charts.bitnami.com/bitnami
        helm repo add elastic https://helm.elastic.co
        helm repo update
      displayName: 'Setup dependencies'
    
    - script: |
        for chart in Helm/*; do
          if [ -d "$chart" ] && [ -f "$chart/Chart.yaml" ]; then
            if grep -q "dependencies:" "$chart/Chart.yaml"; then
              echo "Building dependencies for $chart"
              helm dependency build "$chart"
            fi
          fi
        done
      displayName: 'Build Helm dependencies'
    
    - script: ./Script/validate-charts.sh --verbose
      displayName: 'Validate Helm charts'
```

## CircleCI

### Configuration Example

```yaml
version: 2.1

orbs:
  helm: circleci/helm@2.0.1

jobs:
  validate-charts:
    docker:
      - image: cimg/base:stable
    steps:
      - checkout
      - helm/install-helm-client:
          version: v3.13.3
      - run:
          name: Install dependencies
          command: |
            sudo apt-get update
            sudo apt-get install -y python3-pip
            pip install yamllint
      - run:
          name: Setup Helm repositories
          command: |
            helm repo add bitnami https://charts.bitnami.com/bitnami
            helm repo add elastic https://helm.elastic.co
            helm repo update
      - run:
          name: Build Helm dependencies
          command: |
            for chart in Helm/*; do
              if [ -d "$chart" ] && [ -f "$chart/Chart.yaml" ]; then
                if grep -q "dependencies:" "$chart/Chart.yaml"; then
                  helm dependency build "$chart"
                fi
              fi
            done
      - run:
          name: Validate charts
          command: ./Script/validate-charts.sh --verbose

workflows:
  version: 2
  validate:
    jobs:
      - validate-charts:
          filters:
            branches:
              only: [main, develop]
```

## Local Development

### Using Make

```bash
# Full validation
make validate

# Build dependencies only
make deps

# Lint charts only  
make lint

# Test templates only
make template-test

# With automatic fixes
make validate-fix
```

### Using the validation script directly

```bash
# Basic validation
./Script/validate-charts.sh

# With verbose output
./Script/validate-charts.sh --verbose

# With automatic fixes
./Script/validate-charts.sh --fix
```

## Pre-commit Hooks

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: helm-validate
        name: Validate Helm Charts
        entry: ./Script/validate-charts.sh
        language: system
        files: ^Helm/.*\.(yaml|yml)$
        pass_filenames: false
```

## Docker Integration

### Dockerfile for validation

```dockerfile
FROM alpine/helm:3.13.3

RUN apk add --no-cache bash python3 py3-pip
RUN pip install yamllint

WORKDIR /workspace
COPY . .

RUN helm repo add bitnami https://charts.bitnami.com/bitnami && \
    helm repo add elastic https://helm.elastic.co && \
    helm repo update

CMD ["./Script/validate-charts.sh", "--verbose"]
```

### Docker Compose for validation

```yaml
version: '3.8'
services:
  helm-validate:
    build: .
    volumes:
      - .:/workspace
    command: ["./Script/validate-charts.sh", "--verbose"]
```

## Troubleshooting

### Common Issues

1. **Dependency build failures**: Ensure Helm repositories are added and updated
2. **Template rendering errors**: Check values.yaml for missing required fields
3. **YAML syntax errors**: Run `make yaml-lint` to identify specific issues

### Debug Commands

```bash
# Check Helm version
helm version

# List repositories
helm repo list

# Debug specific chart
helm template test-release Helm/chart-name --debug --dry-run

# Validate specific chart
helm lint Helm/chart-name --debug
```
