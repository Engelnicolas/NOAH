#!/bin/bash

# Helm-based deployment script for NOAH with OAuth2
set -e

NAMESPACE="noah-namespace"
CHART_PATH="helm/noah-chart"

echo "🚀 Starting Helm-based NOAH deployment..."

# Step 1: Update Helm dependencies
echo "📦 Updating Helm dependencies..."
cd "$CHART_PATH"
helm dependency update
cd - > /dev/null

# Step 2: Create namespace if it doesn't exist
echo "🏗️  Creating namespace..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Generate and install secrets using Helm hooks
echo "🔐 Installing NOAH with Helm (includes secret generation)..."
helm upgrade --install noah "$CHART_PATH" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --wait \
  --timeout=600s

# Step 4: Verify deployment
echo "✅ Verifying deployment..."
echo "Pods status:"
kubectl get pods -n "$NAMESPACE"

echo "Services status:"
kubectl get services -n "$NAMESPACE"

echo "Secrets status:"
kubectl get secrets -n "$NAMESPACE" | grep oauth2

# Step 5: Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=keycloak -n "$NAMESPACE" --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=oauth2-proxy -n "$NAMESPACE" --timeout=300s

# Step 6: Test connectivity
echo "🔍 Testing OAuth2 connectivity..."
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n "$NAMESPACE" -- \
  curl -s http://noah-keycloak:8080/realms/noah/.well-known/openid-configuration > /dev/null && \
  echo "✅ Keycloak noah realm is accessible" || \
  echo "❌ Keycloak noah realm is not accessible"

echo "🎉 Helm deployment completed successfully!"
echo ""
echo "📋 Summary:"
echo "- Chart: $CHART_PATH"
echo "- Namespace: $NAMESPACE"
echo "- Release: noah"
echo ""
echo "🔧 Management commands:"
echo "- Update: helm upgrade noah $CHART_PATH -n $NAMESPACE"
echo "- Rollback: helm rollback noah -n $NAMESPACE"
echo "- Uninstall: helm uninstall noah -n $NAMESPACE"
echo "- Status: helm status noah -n $NAMESPACE"
