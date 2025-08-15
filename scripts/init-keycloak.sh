#!/bin/bash

echo "Waiting for Keycloak to be ready..."
kubectl wait --for=condition=ready pod -l app=keycloak -n noah-namespace --timeout=300s

echo "Getting Keycloak pod name..."
KEYCLOAK_POD=$(kubectl get pods -n noah-namespace -l app=keycloak -o jsonpath='{.items[0].metadata.name}')

echo "Importing realm configuration..."
kubectl exec -n noah-namespace $KEYCLOAK_POD -- bash -c '
  # Wait for Keycloak to fully start
  sleep 10
  
  # Authenticate and get token
  TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin" \
    -d "password=admin" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" | jq -r ".access_token")
  
  # Check if noah realm exists
  REALM_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8080/admin/realms/noah")
  
  if [ "$REALM_EXISTS" = "404" ]; then
    echo "Creating noah realm..."
    # Create realm using the imported config
    curl -X POST "http://localhost:8080/admin/realms" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"realm\":\"noah\",\"enabled\":true,\"sslRequired\":\"none\"}"
    
    # Create client
    curl -X POST "http://localhost:8080/admin/realms/noah/clients" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"clientId\":\"oauth2-proxy\",
        \"enabled\":true,
        \"publicClient\":false,
        \"secret\":\"your-client-secret-here\",
        \"redirectUris\":[\"*\"],
        \"webOrigins\":[\"*\"],
        \"standardFlowEnabled\":true,
        \"protocol\":\"openid-connect\"
      }"
    
    echo "Noah realm created successfully!"
  else
    echo "Noah realm already exists"
  fi
'

echo "Keycloak initialization complete!"
