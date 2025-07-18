#!/usr/bin/env python3
"""
Script de test pour le CLI NOAH
Vérifie que toutes les commandes principales fonctionnent correctement
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, expect_error=False):
    """Exécuter une commande et vérifier le résultat."""
    print(f"🧪 Test: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if expect_error:
            if result.returncode != 0:
                print("  ✅ Erreur attendue détectée")
                return True
            else:
                print("  ❌ Erreur attendue mais commande réussie")
                return False
        else:
            if result.returncode == 0:
                print("  ✅ Commande exécutée avec succès")
                return True
            else:
                print(f"  ❌ Échec de la commande (code: {result.returncode})")
                print(f"     stdout: {result.stdout[:200]}")
                print(f"     stderr: {result.stderr[:200]}")
                return False
    except subprocess.TimeoutExpired:
        print("  ⏰ Timeout - commande trop longue")
        return False
    except Exception as e:
        print(f"  💥 Erreur d'exécution: {e}")
        return False


def main():
    """Test principal du CLI NOAH."""
    print("🚀 Tests du CLI NOAH v5.0.0")
    print("=" * 50)
    
    # Changer vers le répertoire NOAH
    noah_dir = Path(__file__).parent
    
    tests = [
        # Tests de base
        (["./noah", "--version"], False),
        (["./noah", "--help"], False),
        (["./noah", "--list"], False),
        
        # Tests de commandes sans sous-commandes (devraient échouer)
        (["./noah", "linter"], True),
        (["./noah", "monitoring"], True),
        
        # Tests avec sous-commandes (peuvent nécessiter des privilèges)
        (["./noah", "linter", "help"], False),
        (["./noah", "setup", "--help"], False),
        (["./noah", "deps-manager", "--help"], False),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, expect_error in tests:
        if run_command(cmd, expect_error):
            passed += 1
        print()
    
    print("📊 Résultats des tests")
    print("=" * 50)
    print(f"Tests réussis: {passed}/{total}")
    print(f"Taux de réussite: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 Tous les tests sont réussis !")
        return 0
    else:
        print("⚠️  Certains tests ont échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())
