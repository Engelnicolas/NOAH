# � Guide utilisateur NOAH v5.0.0 - Déploiement et utilisation complète

## 🎯 Vue d'ensemble

NOAH (Next Open-source Architecture Hub) v5.0.0 introduit une approche révolutionnaire pour le déploiement d'infrastructures open-source sécurisées et évolutives. Cette version apporte un CLI Python intelligent, une interface utilisateur modernisée, et une gestion automatisée des privilèges pour une expérience utilisateur optimale.

### 🌟 Nouveautés majeures v5.0.0

- **🐍 CLI Python unifié** : Remplacement complet de noah.sh par une interface Python moderne
- **🔍 Auto-découverte intelligente** : Détection automatique de tous les scripts et outils NOAH
- **🎨 Interface colorée** : Messages formatés et codes couleur pour une navigation intuitive
- **🔒 Gestion automatique des privilèges** : Élévation intelligente avec confirmation utilisateur
- **📚 Documentation intégrée** : Aide contextuelle complète avec exemples pratiques
- **⚡ Validation temps réel** : Vérification environnement et syntaxe avant exécution

---

## ⚡ Démarrage express (10 minutes)

### 🚀 Installation ultrarapide

```bash
# 1. Récupération du projet
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# 2. Activation environnement Python
source venv/bin/activate

# 3. Découverte des outils disponibles
./noah --help
./noah --list

# 4. Vérification prérequis système
./noah tech-requirements --check

# 5. Déploiement infrastructure complète
./noah deploy --verbose

# 6. Surveillance déploiement
./noah monitoring status

# 7. Accès aux services (dans des terminaux séparés)
kubectl port-forward svc/keycloak 8080:8080     # Gestion identités
kubectl port-forward svc/nextcloud 8081:80      # Collaboration
kubectl port-forward svc/mattermost 8082:8065   # Communication
kubectl port-forward svc/grafana 3000:3000      # Monitoring
```

### 🎯 Premiers accès

| Service | URL | Description |
|---------|-----|-------------|
| **Keycloak** | http://localhost:8080 | Gestion des identités et SSO |
| **Nextcloud** | http://localhost:8081 | Collaboration et partage de fichiers |
| **Mattermost** | http://localhost:8082 | Communication d'équipe |
| **Grafana** | http://localhost:3000 | Tableaux de bord et monitoring |

---

## 🐍 CLI Python moderne

### 🔧 Interface unifiée

Le nouveau CLI NOAH offre une expérience utilisateur révolutionnaire :

```bash
# Navigation intuitive avec aide contextuelle
./noah --help                    # Aide complète avec catégorisation
./noah --version                 # Information de version
./noah --list                    # Liste détaillée de tous les scripts

# Auto-découverte des sous-commandes
./noah linter                    # Affiche automatiquement les sous-commandes disponibles
./noah monitoring status         # Exécution directe avec validation
./noah deploy --dry-run          # Simulation sans modification

# Gestion intelligente des privilèges
./noah deploy                    # Demande confirmation sudo si nécessaire
sudo ./noah linter setup         # Exécution avec privilèges élevés
```

### 🎨 Interface visuelle moderne

**Codes couleur :**
- 🔵 **Bleu** : Messages informatifs
- 🟢 **Vert** : Opérations réussies
- 🟡 **Jaune** : Avertissements et confirmations
- 🔴 **Rouge** : Erreurs et problèmes
- 🟣 **Violet** : Catégories et titres

**Exemples visuels :**
```bash
[INFO] Vérification des prérequis système...
[SUCCESS] Kubernetes détecté ✓
[WARNING] La commande 'deploy' nécessite des privilèges root
[ERROR] Script non trouvé: noah-inexistant.py
```

### 📊 Commandes par catégorie

#### 🏗️ Infrastructure
```bash
./noah deploy               # Déploiement complet (11 charts Helm)
./noah deploy --profile minimal     # Configuration allégée
./noah deploy --only keycloak       # Déploiement sélectif
./noah setup                # Configuration environnement développement
./noah tech-requirements    # Vérification prérequis système
```

#### 📈 Monitoring & Observabilité
```bash
./noah monitoring status    # État des services de monitoring
./noah monitoring deploy    # Déploiement Prometheus/Grafana
./noah monitoring watch     # Surveillance temps réel
./noah monitoring teardown  # Suppression stack monitoring
```

#### 🔍 Qualité du code
```bash
./noah linter setup         # Configuration environnement linting
./noah linter lint --all    # Validation YAML/Ansible/Helm/Python
./noah linter precommit     # Exécution hooks pre-commit
./noah linter report        # Génération rapport qualité
```

#### 🔧 Gestion des dépendances
```bash
./noah deps-manager --check    # Vérification dépendances système
./noah deps-manager --install  # Installation packages requis
./noah deps-manager --update   # Mise à jour dépendances
```

---

## 📋 Prérequis et installation

### 🖥️ Exigences système

#### Configuration minimale (Développement)
- **OS** : Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **CPU** : 4 cœurs minimum
- **RAM** : 8GB minimum (recommandé 12GB)
- **Stockage** : 100GB SSD disponible
- **Réseau** : 25 Mbps stable
- **Python** : 3.8+ obligatoire

#### Configuration production
- **OS** : Linux avec support containers
- **CPU** : 16+ cœurs (32+ recommandés)
- **RAM** : 32GB minimum (64GB+ recommandés)
- **Stockage** : 500GB+ SSD NVMe
- **Réseau** : 100+ Mbps dédié
- **Cluster** : Kubernetes 1.20+ avec 3+ nodes

### 🔧 Prérequis logiciels

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
                    kubectl helm docker.io git curl

# CentOS/RHEL/Fedora
sudo dnf install -y python3 python3-pip \
                    kubectl helm docker git curl

# Validation
python3 --version    # >= 3.8
kubectl version      # Client et serveur connectés
helm version         # >= 3.0
docker --version     # Service actif
```

### ☸️ Configuration Kubernetes

#### Cluster de développement
```bash
# Minikube (recommandé pour développement)
minikube start --memory=8192 --cpus=4 --disk-size=100GB
kubectl cluster-info

# Kind (alternative)
kind create cluster --config=kind-config.yaml
```

#### Cluster de production
- **Nodes** : 3+ nodes minimum (1 master + 2+ workers)
- **CNI** : Calico, Flannel, ou Weave Net
- **Storage** : StorageClass par défaut configurée
- **LoadBalancer** : MetalLB ou cloud provider
- **Monitoring** : Cluster metrics disponible
```yaml
# Cluster multi-nœuds recommandé
nodes:
  master: 3 (configuration HA)
  worker: 2+ (minimum)
resources:
  cpu: 8-16 cœurs par nœud
  memory: 16-32GB par nœud
  storage: 200-500GB par nœud
```

### Logiciels requis

**Outils principaux :**
```bash
# Vérifier si les outils sont installés
./noah tech-requirements --check

# Outils requis (auto-validés par noah tech-requirements) :
- Docker >= 20.10
- Kubernetes (kubectl) >= 1.24
- Helm >= 3.10
- Python >= 3.8
- Git >= 2.30
- Make >= 4.2
```

**Outils optionnels (fonctionnalités avancées) :**
```bash
# Infrastructure as Code
- Terraform >= 1.3 (pour le provisionnement d'infrastructure)
- Ansible >= 2.12 (pour la gestion de configuration)

# Monitoring et observabilité
- Prometheus >= 2.40 (collecte de métriques)
- Grafana >= 9.0 (visualisation)

# Intégration CI/CD
- GitLab Runner >= 15.0
- Jenkins >= 2.400
```

### Environnement Python (Nouveau v5.0.0)

**Configuration automatique :**
```bash
# Méthode 1 : Makefile Python (recommandé)
make -f Makefile.python setup

# Méthode 2 : Manuelle
python3 -m venv venv
source venv/bin/activate
pip install -r script/requirements.txt

# Méthode 3 : Script de développement
python dev.py setup
```

**Dépendances Python principales :**
```txt
# Contenu de script/requirements.txt
pytest>=7.0.0           # Tests unitaires
black>=23.0.0           # Formatage de code
isort>=5.12.0           # Tri des imports
flake8>=6.0.0           # Linting
mypy>=1.0.0             # Vérification de types
bandit>=1.7.0           # Analyse sécurité
pre-commit>=3.0.0       # Hooks pré-commit
rich>=13.0.0            # Interface colorée
pyyaml>=6.0.0           # Parsing YAML
requests>=2.28.0        # HTTP client
click>=8.0.0            # CLI framework
```
### Exigences de stockage

**Profil développement :**
```yaml
# Stockage éphémère (pas de persistance)
persistence:
  enabled: false
  size: 1Gi

# Stockage total nécessaire : ~10-20GB (conteneurs + logs)
```

**Profil production :**
```yaml
# Stockage persistant requis
persistence:
  enabled: true
  size: 20Gi        # Par service principal

# Stockage base de données
postgresql:
  persistence:
    size: 10Gi      # Données de base de données

# Stockage cache
redis:
  persistence:
    size: 5Gi       # Données de cache

# Stockage total nécessaire : ~200-500GB (données + sauvegardes + logs)
```

---

## 🛠️ CLI Python moderne (Version 5.0.0)

### Découverte automatique des scripts

Le nouveau CLI Python découvre automatiquement tous les scripts NOAH disponibles :

```bash
# Lister tous les scripts disponibles avec descriptions
./noah --list

# Sortie exemple :
# Scripts NOAH disponibles:
#
#   deploy               NOAH - Next Open-source Architecture Hub Deployment Script (Fixed Version)
#     └─ noah-deploy.py (python) [ROOT]
#
#   deps-manager         Script exécutable: noah-deps-manager
#     └─ noah-deps-manager (executable)
#
#   linter               NOAH Linting Validator
#     └─ noah-linter.py (python) [ROOT] (now in tests/)
#
#   monitoring           NOAH Monitoring Management
#     └─ noah-monitoring.py (python) [ROOT]
```

### Système d'aide avancé

```bash
# Aide générale avec exemples et catégories
./noah --help

# Aide spécifique pour une commande
./noah deploy --help
./noah monitoring --help
./noah linter --help

# Version et informations système
./noah --version
```

### Gestion automatique des privilèges

Le CLI détecte automatiquement les commandes nécessitant des privilèges root :

```bash
# Le système demande sudo automatiquement si nécessaire
./noah deploy

# Sortie exemple :
# [WARNING] La commande 'deploy' nécessite des privilèges root
# [INFO] Les opérations suivantes nécessitent des privilèges administrateur :
# [INFO]   • Installation de packages système
# [INFO]   • Configuration de services réseau
# [INFO]   • Gestion des conteneurs Docker/Kubernetes
# [INFO]   • Modification des configurations système
#
# Voulez-vous continuer avec sudo ? [y/N]
```

### Validation et exécution sécurisée

```bash
# Validation automatique avant exécution
./noah deploy --dry-run        # Voir ce qui serait exécuté
./noah linter --check-only     # Validation sans modification

# Exécution avec logs détaillés
./noah deploy --verbose
./noah monitoring --debug
```

---

## 🚀 Guide de déploiement étape par étape

### Étape 1 : Préparation de l'environnement

```bash
# 1. Cloner et configurer
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# 2. Configurer l'environnement Python
source venv/bin/activate  # ou make -f Makefile.python setup

# 3. Vérifier les prérequis
./noah tech-requirements --check --verbose

# 4. Configuration initiale
./noah setup --dev  # pour développement
# OU
./noah setup --prod # pour production
```

### Étape 2 : Validation pré-déploiement

```bash
# Vérifier la qualité du code et configuration
./noah linter --all --strict

---

## 🏗️ Déploiement avancé

### 🎯 Profils de déploiement

NOAH propose trois profils prédéfinis pour différents cas d'usage :

#### 📱 Profil Minimal (Développement)
```bash
./noah deploy --profile minimal
```
**Composants inclus :**
- Keycloak (Gestion identités)
- Nextcloud (Collaboration)
- Monitoring de base (Prometheus)

**Ressources requises :**
- RAM : 8GB minimum
- CPU : 4 cœurs
- Stockage : 100GB

#### 🏢 Profil Standard (PME)
```bash
./noah deploy --profile standard
```
**Composants inclus :**
- Profil minimal +
- Mattermost (Communication)
- GitLab (DevOps)
- Grafana (Visualisation)
- OpenVPN (Accès distant)

**Ressources requises :**
- RAM : 16GB minimum
- CPU : 8 cœurs
- Stockage : 300GB

#### 🏭 Profil Complet (Entreprise)
```bash
./noah deploy --profile complete
```
**Composants inclus :**
- Profil standard +
- Wazuh (SIEM)
- OpenEDR (Protection endpoint)
- OAuth2 Proxy (Sécurité)
- Monitoring avancé

**Ressources requises :**
- RAM : 32GB minimum
- CPU : 16 cœurs
- Stockage : 500GB+

### 🔧 Options de déploiement avancées

#### Déploiement sélectif
```bash
# Déployer uniquement certains services
./noah deploy --only keycloak,nextcloud

# Exclure des services spécifiques
./noah deploy --exclude wazuh,openedr

# Déploiement par namespace
./noah deploy --namespace noah-prod
```

#### Configuration personnalisée
```bash
# Utiliser un fichier de valeurs personnalisé
./noah deploy --values my-custom-values.yaml

# Override de valeurs spécifiques
./noah deploy --set keycloak.replicas=3

# Mode dry-run pour validation
./noah deploy --dry-run --verbose
```

#### Déploiement par phases
```bash
# Phase 1 : Infrastructure de base
./noah deploy --phase infrastructure

# Phase 2 : Services applicatifs
./noah deploy --phase applications

# Phase 3 : Sécurité et monitoring
./noah deploy --phase security
```

---

## 📊 Monitoring et observabilité

### 🔍 Surveillance en temps réel

```bash
# État général de la plateforme
./noah monitoring status

# Surveillance détaillée avec métriques
./noah monitoring status --detailed

# Monitoring en temps réel
./noah monitoring watch

# Logs en direct
./noah monitoring logs --follow
```

### 📈 Métriques et alertes

#### Configuration Prometheus
```bash
# Déployer stack monitoring complète
./noah monitoring deploy

# Configurer les règles d'alertes
./noah monitoring alerts --configure

# Test des alertes
./noah monitoring alerts --test
```

#### Tableaux de bord Grafana
```bash
# Importer tableaux de bord prédéfinis
./noah monitoring dashboards --import

# Créer tableau de bord personnalisé
./noah monitoring dashboards --create noah-custom

# Exporter configuration
./noah monitoring dashboards --export
```

### 🚨 Gestion des alertes

```bash
# Configurer notifications Slack
./noah monitoring alerts --slack-webhook https://hooks.slack.com/...

# Configurer notifications email
./noah monitoring alerts --email admin@company.com

# Test des notifications
./noah monitoring alerts --test-notifications
```

---

## 🔐 Sécurité et gestion des identités

### 👤 Configuration Keycloak

#### Accès initial
```bash
# Port-forward pour accès local
kubectl port-forward svc/keycloak 8080:8080

# URL : http://localhost:8080
# Identifiants par défaut (À CHANGER !) :
# Username: admin
# Password: voir les secrets Kubernetes
kubectl get secret keycloak-admin -o jsonpath='{.data.password}' | base64 -d
```

#### Configuration SSO
1. **Créer un Realm** : `NOAH-Enterprise`
2. **Configurer les clients** : Nextcloud, Mattermost, Grafana
3. **Gérer les utilisateurs** : Créer groupes et rôles
4. **Activer MFA** : TOTP et WebAuthn

### 🛡️ Sécurité réseau

#### Policies réseau
```bash
# Appliquer les policies de sécurité
kubectl apply -f ansible/templates/network-policies.yaml

# Vérifier les policies actives
kubectl get networkpolicy -n noah
```

#### OpenVPN
```bash
# Générer certificats clients
./noah openvpn --generate-client username

# Télécharger configuration client
./noah openvpn --download-config username
```

---

## 🔧 Maintenance et opérations

### 📦 Gestion des mises à jour

#### Mise à jour des charts Helm
```bash
# Vérifier les mises à jour disponibles
./noah update --check

# Mise à jour sélective
./noah update --component keycloak

# Mise à jour complète avec sauvegarde
./noah update --all --backup
```

#### Rolling updates
```bash
# Mise à jour progressive sans interruption
./noah deploy --rolling-update

# Rollback vers version précédente
./noah rollback --to-revision 2
```

### 💾 Sauvegardes

#### Sauvegarde automatique
```bash
# Configurer sauvegarde quotidienne
./noah backup --schedule daily --retention 30d

# Sauvegarde manuelle complète
./noah backup --all --output /backup/noah-$(date +%Y%m%d)

# Sauvegarde sélective
./noah backup --components keycloak,nextcloud
```

#### Restauration
```bash
# Lister les sauvegardes disponibles
./noah backup --list

# Restaurer depuis sauvegarde
./noah restore --from /backup/noah-20250115

# Restauration sélective
./noah restore --components keycloak --from backup-file.tar.gz
```

### 🔍 Diagnostics et dépannage

#### Vérifications santé
```bash
# Check santé complet
./noah health --comprehensive

# Diagnostic réseau
./noah health --network

# Test connectivité services
./noah health --connectivity
```

#### Logs et debugging
```bash
# Logs agrégés de tous les services
./noah logs --all --since 1h

# Logs spécifiques avec filtrage
./noah logs --component keycloak --level error

# Export logs pour support
./noah logs --export --output noah-logs-$(date +%Y%m%d).tar.gz
```

---

## 🚀 Cas d'usage et exemples

### 💼 Scénario PME

**Contexte :** Entreprise 50 personnes, migration depuis Google Workspace

```bash
# 1. Déploiement configuration PME
./noah deploy --profile standard

# 2. Configuration domaine entreprise
./noah configure --domain company.local

# 3. Migration utilisateurs
./noah users --import-csv users.csv

# 4. Configuration SSO
./noah sso --configure --domain company.local
```

### 🏛️ Scénario administration publique

**Contexte :** Organisme public, exigences RGPD strictes

```bash
# 1. Déploiement sécurisé complet
./noah deploy --profile complete --security-hardened

# 2. Configuration audit et conformité
./noah compliance --enable-audit-logs
./noah compliance --gdpr-mode

# 3. Sécurisation réseau
./noah security --enable-network-policies
./noah security --configure-wazuh
```

### 🎓 Scénario éducatif

**Contexte :** Université, 1000+ étudiants

```bash
# 1. Déploiement multi-tenant
./noah deploy --profile complete --multi-tenant

# 2. Intégration LDAP existant
./noah ldap --integrate --server ldap.university.edu

# 3. Configuration par facultés
./noah tenants --create informatique
./noah tenants --create medecine
```

---

## 🛠️ Dépannage et FAQ

### ❓ Problèmes fréquents

#### Erreur : "Insufficient resources"
```bash
# Vérifier ressources disponibles
kubectl top nodes
kubectl describe nodes

# Solution : Ajuster les requêtes de ressources
./noah deploy --profile minimal --reduce-resources
```

#### Erreur : "ImagePullBackOff"
```bash
# Vérifier connectivité registre
docker pull keycloak/keycloak:latest

# Solution : Configurer proxy ou registre local
./noah configure --registry-proxy proxy.company.com
```

#### Services inaccessibles
```bash
# Vérifier services et endpoints
kubectl get svc,endpoints -n noah

# Vérifier policies réseau
kubectl get networkpolicy -n noah

# Solution : Port-forward temporaire
kubectl port-forward svc/SERVICE_NAME 8080:8080
```

### 📞 Support et communauté

- **🐛 Issues GitHub** : [github.com/Engelnicolas/NOAH/issues](https://github.com/Engelnicolas/NOAH/issues)
- **💬 Discussions** : [github.com/Engelnicolas/NOAH/discussions](https://github.com/Engelnicolas/NOAH/discussions)
- **📖 Wiki** : [github.com/Engelnicolas/NOAH/wiki](https://github.com/Engelnicolas/NOAH/wiki)
- **📧 Contact** : noah-support@project.org

### 🔗 Ressources utiles

- **[Guide de migration](MIGRATION_GUIDE.md)** : Migration depuis versions antérieures
- **[Guide sécurité](SECURITY_GUIDE.md)** : Bonnes pratiques sécuritaires
- **[API Documentation](API_REFERENCE.md)** : Référence API complète
- **[Troubleshooting](TROUBLESHOOTING.md)** : Guide de résolution de problèmes

---

<div align="center">

**🎉 Félicitations ! Vous maîtrisez maintenant NOAH v5.0.0**

*Pour toute question ou amélioration, n'hésitez pas à contribuer au projet !*

[⬆️ Retour au sommaire](#-guide-utilisateur-noah-v500---déploiement-et-utilisation-complète)

</div>
./noah deploy --phase monitoring

# Mise à jour sélective
./noah deploy --update-only keycloak,nextcloud

# Rollback en cas de problème
./noah deploy --rollback --version previous
```

### Monitoring et observabilité

```bash
# Status complet du système
./noah monitoring status --all --json

# Métriques détaillées
./noah monitoring metrics --export-prometheus

# Logs centralisés
./noah monitoring logs --component keycloak --tail 100

# Alertes et notifications
./noah monitoring alerts --configure --slack-webhook URL
```

### Maintenance et mise à jour

```bash
# Sauvegarde avant maintenance
./noah backup --all --destination /backup/noah

# Mise à jour des composants
./noah update --check-versions
./noah update --component kubernetes,helm

# Nettoyage et optimisation
./noah cleanup --unused-images --old-logs
./noah optimize --resources --performance
```

---

## 🐛 Dépannage

### Problèmes courants

**1. Problèmes de privilèges :**
```bash
# Solution : Utiliser sudo explicitement
sudo ./noah deploy

# Ou configurer sudoers pour l'utilisateur
echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/noah
```

**2. Erreurs Python :**
```bash
# Réinstaller l'environnement
rm -rf venv/
make -f Makefile.python setup

# Vérifier les dépendances
python dev.py check
```

**3. Problèmes Kubernetes :**
```bash
# Vérifier la connectivité
kubectl cluster-info
kubectl get nodes

# Réinitialiser si nécessaire
kubectl delete namespace noah
./noah deploy --clean-install
```

### Logs et diagnostics

```bash
# Logs du CLI
./noah --debug COMMAND

# Logs des applications
kubectl logs -n noah -l app=keycloak
kubectl logs -n noah -l app=nextcloud

# Diagnostics complets
./noah monitoring diagnostics --export-report
```

Pour plus d'informations, consultez la [documentation complète](https://github.com/Engelnicolas/NOAH/wiki).
