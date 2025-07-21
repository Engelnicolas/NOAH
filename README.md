# 🚀 NOAH - Next Open-source Architecture Hub

<div align="center">

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Kubernetes](https://img.shields.io/badge/Platform-Kubernetes-blueviolet.svg)](https://kubernetes.io/)
[![Version](https://img.shields.io/badge/Version-5.0.0-green.svg)](https://github.com/Engelnicolas/NOAH/releases)
[![Maintained](https://img.shields.io/badge/Maintained-Yes-brightgreen.svg)](https://github.com/Engelnicolas/NOAH/commits/main)
[![Code Quality](https://img.shields.io/badge/Code%20Quality-Linted-success.svg)](https://github.com/Engelnicolas/NOAH)

```
███    ██  ██████   █████  ██   ██
████   ██ ██    ██ ██   ██ ██   ██
██ ██  ██ ██    ██ ███████ ███████
██  ██ ██ ██    ██ ██   ██ ██   ██
██   ████  ██████  ██   ██ ██   ██

Next Open-source Architecture Hub
```

*Une plateforme d'infrastructure automatisée et sécurisée pour déployer des solutions open-source à l'échelle entreprise*

</div>

---

## ✨ Vue d'ensemble

**NOAH** (Next Open-source Architecture Hub) est une plateforme d'automatisation d'infrastructure moderne et évolutive qui déploie un écosystème complet de services open-source de niveau entreprise. Conçue pour les organisations souhaitant maintenir un contrôle total sur leurs données et leur infrastructure, NOAH fournit une solution unifiée alliant sécurité, observabilité et collaboration.

### 🏗️ Architecture & Composants

**NOAH** déploie une infrastructure complète composée de 11 charts Helm orchestrés via Ansible :

#### 🔐 Gestion des Identités
- **Samba4 Active Directory** : Annuaire centralisé avec authentification LDAP
- **Keycloak** : Fournisseur d'identité moderne avec SSO et fédération

#### 📦 Plateformes de Collaboration  
- **Nextcloud** : Partage de fichiers et collaboration sécurisés
- **Mattermost** : Messagerie d'équipe avec intégrations DevOps
- **GitLab** : Forge logicielle avec CI/CD intégré

#### 🛡️ Sécurité & Monitoring
- **Wazuh** : SIEM et détection d'intrusions
- **OpenEDR** : Détection et réponse aux menaces endpoint
- **OpenVPN** : Accès VPN sécurisé avec authentification AD
- **OAuth2 Proxy** : Reverse proxy avec authentification OAuth2

#### 📈 Observabilité
- **Prometheus** : Collecte de métriques et alerting
- **Grafana** : Visualisation et tableaux de bord avancés

---

## 🚀 Démarrage rapide

### 🔧 Prérequis
- **Kubernetes** : Cluster fonctionnel avec kubectl configuré
- **Helm** : Version 3.x installée
- **Python** : Version 3.8+ avec pip
- **Ressources** : 8GB+ RAM, 50GB+ stockage (voir [Exigences techniques](docs/TECHNICAL_REQUIREMENTS.md))

### ⚡ Installation Express (5 minutes)
```bash
# 1. Cloner le dépôt
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# 2. Activer l'environnement Python
source venv/bin/activate
# Alternative : make -f Makefile.python setup

# 3. Découvrir les commandes disponibles
./noah --help

# 4. Vérifier les prérequis système
./noah tech-requirements --check

# 5. Déployer la plateforme complète
./noah deploy --verbose

# 6. Surveiller le déploiement
./noah monitoring status
```

### 🎯 Accès aux services déployés
```bash
# Keycloak (Gestion des identités)
kubectl port-forward svc/keycloak 8080:8080
# http://localhost:8080

# Nextcloud (Collaboration)
kubectl port-forward svc/nextcloud 8081:80
# http://localhost:8081

# Mattermost (Communication)
kubectl port-forward svc/mattermost 8082:8065
# http://localhost:8082

# Grafana (Monitoring)
kubectl port-forward svc/grafana 3000:3000
# http://localhost:3000
```

---

## 💡 Fonctionnalités principales

### 🐍 CLI Python Intelligent

Le nouveau CLI NOAH offre une expérience utilisateur moderne et intuitive :

```bash
# Interface colorée et informative
./noah --help                    # Aide complète avec catégorisation
./noah --list                    # Liste détaillée de tous les scripts
./noah --version                 # Information de version

# Découverte automatique des scripts
./noah linter                    # Auto-détection des sous-commandes
./noah monitoring status         # Exécution intelligente avec validation

# Gestion automatique des privilèges
./noah deploy                    # Demande confirmation pour sudo si nécessaire
```

### 📊 Commandes disponibles par catégorie

#### 🏗️ Infrastructure
```bash
./noah deploy                    # Déploiement complet (11 charts Helm)
./noah setup                     # Configuration environnement développement
./noah tech-requirements         # Vérification prérequis système
```

#### 📈 Monitoring & Observabilité
```bash
./noah monitoring status         # État des services de monitoring
./noah monitoring deploy         # Déploiement Prometheus/Grafana
./noah monitoring teardown       # Suppression stack monitoring
```

#### 🔍 Qualité du code
```bash
./noah linter setup             # Configuration environnement linting
./noah linter lint --all        # Validation YAML/Ansible/Helm/Python
./noah linter precommit         # Exécution hooks pre-commit
./noah linter report --save     # Génération rapport qualité
```

#### 🔧 Gestion des dépendances
```bash
./noah deps-manager --check     # Vérification dépendances système
./noah deps-manager --install   # Installation packages requis
./noah deps-manager --update    # Mise à jour dépendances
```


## 🔧 Installation complète

### 📋 Prérequis détaillés

#### Environnement système
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv kubectl helm docker.io

# CentOS/RHEL
sudo yum install -y python3 python3-pip kubectl helm docker

# Validation
python3 --version    # >= 3.8
kubectl version      # Client et serveur
helm version         # >= 3.0
```

#### Cluster Kubernetes
- **Version** : 1.20+ (recommandé 1.24+)
- **Ressources** : 4 nodes minimum, 8GB RAM par node
- **StorageClass** : Classe de stockage par défaut configurée
- **Network Policy** : Support CNI (Calico, Flannel, etc.)

### 🏗️ Installation étape par étape

#### 1. Préparation de l'environnement
```bash
# Cloner et configurer
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Activer l'environnement virtuel Python
source venv/bin/activate

# Vérifier la configuration
./noah tech-requirements --report
./noah --list
```

#### 2. Configuration avancée
```bash
# Configuration personnalisée (optionnel)
cp script/values/values-minimal.yaml my-custom-values.yaml
# Éditer my-custom-values.yaml selon vos besoins

# Validation de la configuration
./noah linter setup
./noah linter lint --all
```

#### 3. Déploiement par phases

**Phase 1 : Infrastructure de base**
```bash
./noah deploy --profile minimal    # Seulement les services essentiels
./noah monitoring status           # Vérification état
```

**Phase 2 : Services collaboratifs**
```bash
./noah deploy --profile standard   # Ajout Nextcloud, Mattermost
kubectl get pods -n noah           # Validation déploiement
```

**Phase 3 : Sécurité et monitoring complets**
```bash
./noah deploy --profile complete   # Stack complète
./noah monitoring deploy           # Monitoring avancé
```

---

### 🎯 Cas d'usage principaux

#### 👤 Développeurs individuels
- Apprendre DevSecOps et pipelines d'automatisation
- Tester des outils d'entreprise dans un environnement sandbox
- Expérimenter avec des architectures cloud-native

#### 🧑‍💼 PME & Startups
- Remplacer les outils SaaS coûteux par des alternatives auto-hébergées
- Économies de 60-80% des coûts comparé aux solutions propriétaires
- Contrôle total des données et conformité RGPD

#### 🏢 Entreprises
- Infrastructure cloud hybride avec exigences de conformité
- Intégrations personnalisées et scalabilité enterprise
- Audit complet et traçabilité des opérations

#### 🏛️ Secteur public
- Infrastructure sécurisée et auditable
- Souveraineté des données et conformité réglementaire
- Déploiement on-premise avec contrôle total

---
### 📜 Licence

Ce projet est sous licence **GPL v3**. Voir [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

**Nicolas Engel**
📧 Email : [contact@nicolasengel.fr](mailto:contact@nicolasengel.fr)
🌐 Site web : [nicolasengel.fr](https://nicolasengel.fr)
💼 LinkedIn : [linkedin.com/in/nicolasengel](https://linkedin.com/in/nicolasengel)

*Passionné de cybersécurité, d'infrastructure open-source, DevSecOps, et de construction de solutions sécurisées et évolutives pour organisations de toutes tailles.*

---

## 🏆 Remerciements

Merci à la communauté open-source et aux mainteneurs de tous les outils qui rendent NOAH possible :

- **🐍 Python Software Foundation** pour le langage Python
- **☸️ CNCF** pour Kubernetes, Prometheus, et l'écosystème cloud-native
- **🔴 Red Hat** pour Ansible et l'automatisation infrastructure
- **🔑 Keycloak Team** pour la gestion des identités et accès
- **☁️ Nextcloud GmbH** pour les outils de collaboration sécurisée
- **💬 Mattermost** pour la communication d'équipe
- **📊 Grafana Labs** pour la visualisation et l'observabilité
- **🛡️ Wazuh** pour la surveillance sécuritaire
- **🐳 Docker** pour la conteneurisation
- **⎈ Helm** pour la gestion des applications Kubernetes
