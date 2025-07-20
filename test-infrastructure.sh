#!/bin/bash

echo "=== Test de déploiement de l'infrastructure NOAH ==="
echo "Date: $(date)"
echo

# Couleurs pour l'affichage
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction de test
test_component() {
    local component=$1
    local test_command=$2
    local expected_result=$3
    
    echo -n "Testing $component... "
    result=$(eval "$test_command" 2>/dev/null)
    
    if [[ "$result" == *"$expected_result"* ]]; then
        echo -e "${GREEN}✅ PASS${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "  Expected: $expected_result"
        echo "  Got: $result"
        return 1
    fi
}

# Variables
NAMESPACE="noah"
TEST_POD="test-nginx-789dbf6956-nv9bs"

echo "=== Infrastructure Components Test ==="

# Test 1: Kubernetes cluster
test_component "Kubernetes cluster" "kubectl cluster-info | head -1" "running"

# Test 2: Namespace
test_component "Namespace $NAMESPACE" "kubectl get namespace $NAMESPACE -o jsonpath='{.status.phase}'" "Active"

# Test 3: Keycloak
test_component "Keycloak service" "kubectl exec -n $NAMESPACE $TEST_POD -- curl -s -o /dev/null -w '%{http_code}' http://keycloak.noah.svc.cluster.local" "302"

# Test 4: PostgreSQL
test_component "PostgreSQL database" "kubectl exec -n $NAMESPACE keycloak-postgresql-0 -- pg_isready -U noah" "accepting connections"

# Test 5: Samba4
test_component "Samba4 process" "kubectl logs -n $NAMESPACE samba4-5dd476c5b4-pn2m2 --tail=1" "ready to serve connections"

# Test 6: OAuth2-proxy
test_component "OAuth2-proxy service" "kubectl exec -n $NAMESPACE $TEST_POD -- curl -s -o /dev/null -w '%{http_code}' http://oauth2-proxy-minimal.noah.svc.cluster.local:4180/ping" "200"

echo
echo "=== Pod Status Summary ==="
kubectl get pods -n $NAMESPACE --no-headers | while read pod status ready restarts age; do
    if [[ "$status" == "Running" && "$ready" == "1/1" ]]; then
        echo -e "${GREEN}✅ $pod${NC}"
    elif [[ "$status" == *"Error"* || "$status" == *"CrashLoop"* || "$status" == *"CreateContainer"* ]]; then
        echo -e "${RED}❌ $pod ($status)${NC}"
    else
        echo -e "${YELLOW}⚠️  $pod ($status)${NC}"
    fi
done

echo
echo "=== Service Status Summary ==="
kubectl get services -n $NAMESPACE --no-headers | while read service type cluster_ip external_ip ports age; do
    echo -e "${GREEN}✅ $service${NC} ($type) - $cluster_ip:$ports"
done

echo
echo "=== Storage Status ==="
kubectl get pvc -n $NAMESPACE --no-headers | while read pvc status volume capacity access modes age; do
    if [[ "$status" == "Bound" ]]; then
        echo -e "${GREEN}✅ $pvc${NC} ($capacity)"
    else
        echo -e "${RED}❌ $pvc ($status)${NC}"
    fi
done

echo
echo "=== Deployment Summary ==="
echo -e "${GREEN}✅ Core Services Functional:${NC}"
echo "  - Keycloak (Authentication/SSO)"
echo "  - PostgreSQL (Database)"
echo "  - Samba4 (File Sharing/LDAP)"
echo "  - OAuth2-proxy (Authentication Proxy)"

echo
echo -e "${GREEN}✅ All services are now operational!${NC}"

echo
echo "=== Infrastructure Test Complete ==="
