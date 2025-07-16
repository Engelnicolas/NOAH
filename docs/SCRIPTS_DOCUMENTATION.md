# NOAH Scripts Documentation

## Vue d'ensemble

Ce document décrit précisément ce que fait chaque script dans le projet NOAH et comment ils s'articulent.

## Architecture CLI

```
noah (CLI principal)
├── noah-deploy.py (déploiement infrastructure)
├── noah-monitoring.py (stack monitoring)
├── noah-linter.py (validation code)
└── noah-fix.py (correction automatique)
```

## Scripts détaillés

### 1. `noah` (CLI Principal)
**Type:** Bash script
**Rôle:** Point d'entrée unique pour toutes les opérations NOAH
**Version:** 4.0.0 (nouvelle version)

**Fonctionnalités:**
- Interface CLI unifiée avec routage de commandes
- Validation et exécution des scripts spécialisés
- Système d'aide intégré avec documentation complète
- Gestion des erreurs centralisée
- Support multi-méthodes d'exécution (Python 3, Bash, direct)

**Améliorations apportées:**
- Documentation exhaustive avec exemples
- Banner coloré avec identité visuelle
- Mappage des commandes avec descriptions
- Validation automatique des scripts
- Support des options globales (-v, --help, --version)

### 2. `noah-deploy.py` 
**Type:** Python script
**Rôle:** Gestion complète de l'infrastructure
**Lignes de code:** 692 lignes

**Fonctionnalités principales:**
- **Setup:** Initialisation des prérequis (kubectl, helm, minikube)
- **Deploy:** Déploiement de 11 charts Helm en 3 phases
- **Status:** Vérification de l'état des déploiements
- **Teardown:** Suppression propre de l'infrastructure

**Charts déployés (11 au total):**
```
Phase 1 (Foundation):
- noah-common (configurations communes)
- samba4 (authentification)
- keycloak (SSO)
- oauth2-proxy (authentification)

Phase 2 (Applications):
- nextcloud (stockage/collaboration)
- mattermost (communication)
- gitlab (développement)

Phase 3 (Monitoring):
- prometheus (métriques)
- grafana (visualisation)
- wazuh (sécurité)
- openedr (détection)
```

### 3. `noah-monitoring.py`
**Type:** Python script
**Rôle:** Gestion du stack de monitoring
**Statut:** Récemment migré de bash vers Python

**Fonctionnalités:**
- **Deploy:** Déploiement Prometheus + Grafana
- **Status:** Vérification santé du monitoring
- **Teardown:** Suppression du stack monitoring
- **Configuration:** Gestion des dashboards et datasources

**Avantages de la migration Python:**
- Meilleure gestion d'erreurs
- Logging structuré
- Validation des configurations
- Intégration avec l'API Kubernetes

### 4. `noah-linter.py`
**Type:** Python script
**Rôle:** Validation et linting du code
**Statut:** Unifie setup-linting.sh et run-super-linter.sh

**Fonctionnalités:**
- **Setup:** Configuration de l'environnement de linting
- **Lint:** Exécution des validations avec Super-Linter
- **Report:** Génération de rapports détaillés
- **Precommit:** Validation pre-commit hooks

**Outils intégrés:**
- YAML Lint (.yamllint.yml)
- Markdown Lint (.markdownlint.yml)
- Shell Check (bash/sh)
- Python flake8/black
- Ansible Lint

### 5. `noah-fix.py`
**Type:** Python script
**Rôle:** Correction automatique des problèmes
**Fonctionnalités:**
- **YAML Fix:** Correction formatage YAML
- **Shell Fix:** Correction scripts shell
- **Auto-repair:** Réparations intelligentes
- **Validation:** Vérification post-correction

## Flux d'exécution

```bash
# Exemple de déploiement complet
./noah infra setup      # Initialise l'environnement
./noah infra deploy     # Déploie les 11 charts
./noah monitoring deploy # Déploie le monitoring
```

## Améliorations apportées

### 1. Migration Python
- **Avant:** Scripts bash difficiles à maintenir
- **Après:** Scripts Python avec gestion d'erreurs robuste

### 2. CLI Unifié
- **Avant:** Multiples scripts disparates
- **Après:** Interface cohérente avec routage centralisé

### 3. Documentation
- **Avant:** Aide minimaliste
- **Après:** Documentation complète avec exemples

### 4. Validation
- **Avant:** Validation manuelle
- **Après:** Validation automatique des scripts

## Makefile intégré

Le Makefile v3.0.0 provide des raccourcis pour les opérations courantes :

```makefile
make deploy          # Déploiement complet
make monitoring      # Stack monitoring
make validate        # Validation projet
make lint           # Linting code
make clean          # Nettoyage
```

## Prochaines étapes

1. **Implémentation noah-validate:** Script de validation manquant
2. **Amélioration noah-backup:** Fonctionnalité de sauvegarde
3. **Tests automatisés:** Validation CI/CD
4. **Documentation API:** Documentation technique approfondie

## Conclusion

Le projet NOAH dispose maintenant d'une architecture CLI moderne et maintenable avec :
- Scripts Python robustes et bien documentés
- Interface CLI unifiée et intuitive
- Validation automatique et correction d'erreurs
- Monitoring et logging intégrés
- Documentation complète et exemples pratiques
