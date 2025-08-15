#!/bin/bash

# Automated deployment script for NOAH with OAuth2 secrets generation
set -e

NAMESPACE="noah-namespace"

echo "🚀 Starting automated NOAH deployment with OAuth2 secrets generation..."

# Step 1: Generate OAuth2 secrets
echo "📝 Generating OAuth2 secrets..."
./scripts/generate-oauth2-secrets.sh

# Step 2: Apply Kubernetes configuration
echo "⚙️  Applying Kubernetes configuration..."
kubectl apply -k k8s/base/

# Step 3: Wait for deployments to be ready
echo "⏳ Waiting for Keycloak to be ready..."
kubectl wait --for=condition=ready pod -l app=keycloak -n $NAMESPACE --timeout=300s

echo "⏳ Waiting for OAuth2-proxy to be ready..."
kubectl wait --for=condition=ready pod -l app=oauth2-proxy -n $NAMESPACE --timeout=300s

# Step 4: Verify deployment
echo "✅ Verifying deployment..."
echo "Pods status:"
kubectl get pods -n $NAMESPACE

echo "Services status:"
kubectl get services -n $NAMESPACE

echo "Secrets status:"
kubectl get secrets -n $NAMESPACE

# Step 5: Test OAuth2 connectivity
echo "🔍 Testing OAuth2 connectivity..."
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n $NAMESPACE -- \
  curl -s http://keycloak:8080/realms/noah/.well-known/openid-configuration > /dev/null && \
  echo "✅ Keycloak noah realm is accessible" || \
  echo "❌ Keycloak noah realm is not accessible"

echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "- Namespace: $NAMESPACE"
echo "- Keycloak: Available at http://keycloak.${NAMESPACE}.svc.cluster.local:8080"
echo "- OAuth2-proxy: Available at http://oauth2-proxy.${NAMESPACE}.svc.cluster.local:4180"
echo "- Secrets: Automatically generated and stored in 'oauth2-proxy-secrets'"
echo ""
echo "🔑 To view generated secrets:"
echo "kubectl get secret oauth2-proxy-secrets -n $NAMESPACE -o yaml"
