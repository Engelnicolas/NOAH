#!/usr/bin/env python3
"""
Script de test pour un déploiement simple.
"""

import subprocess
import sys
from pathlib import Path

def test_simple_deployment():
    """Test avec un déploiement nginx simple."""
    
    # Création d'un manifest nginx simple
    nginx_manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-nginx
  namespace: noah
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test-nginx
  template:
    metadata:
      labels:
        app: test-nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: test-nginx
  namespace: noah
spec:
  selector:
    app: test-nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
"""

    try:
        # Appliquer le manifest
        result = subprocess.run(
            ["kubectl", "apply", "-f", "-"],
            input=nginx_manifest,
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode == 0:
            print("✅ Déploiement nginx test réussi")
            print(result.stdout)
            
            # Vérifier le status des pods
            status_result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "noah", "-l", "app=test-nginx"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            
            if status_result.returncode == 0:
                print("📊 Status des pods:")
                print(status_result.stdout)
            
            return True
        else:
            print("❌ Échec du déploiement nginx test")
            print(f"Erreur: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def cleanup():
    """Nettoyer le déploiement de test."""
    try:
        result = subprocess.run(
            ["kubectl", "delete", "deployment,service", "-n", "noah", "-l", "app=test-nginx"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode == 0:
            print("🧹 Nettoyage terminé")
        else:
            print(f"⚠️  Problème de nettoyage: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Erreur lors du nettoyage: {e}")

if __name__ == "__main__":
    print("🧪 Test de déploiement simple avec nginx...")
    
    if test_simple_deployment():
        print("\n✅ Test réussi! Le système de déploiement fonctionne.")
        
        # Attendre un peu puis nettoyer
        import time
        print("⏳ Attente de 10 secondes avant nettoyage...")
        time.sleep(10)
        cleanup()
    else:
        print("\n❌ Test échoué. Problème avec le déploiement Kubernetes.")
        sys.exit(1)
