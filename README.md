# 🚀 NOAH - Network Operations & Automation Hub

<div align="center">

[![Ansible](https://img.shields.io/badge/Ansible-2.16+-red.svg)](https://www.ansible.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Kubernetes](https://img.shields.io/badge/Platform-Kubernetes-blueviolet.svg)](https://kubernetes.io/)
[![Version](https://img.shields.io/badge/Version-0.2.1-green.svg)](https://github.com/Engelnicolas/NOAH/releases)
[![Maintained](https://img.shields.io/badge/Maintained-Yes-brightgreen.svg)](https://github.com/Engelnicolas/NOAH/commits/main)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blue.svg)](https://github.com/features/actions)

*Plateforme d'infrastructure moderne avec pipelines CI/CD Ansible/Helm pour déployer des solutions open-source à l'échelle entreprise*

</div>

---

## ✨ Vue d'ensemble

**NOAH v0.2** est une plateforme d'automatisation d'infrastructure de nouvelle génération qui utilise des **pipelines CI/CD modernes** pour déployer un écosystème complet de services open-source de niveau entreprise. 

### 🏗️ Architecture & Composants

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
- **OAuth2 Proxy** : Reverse proxy avec authentification OAuth2

#### 📈 Observabilité
- **Prometheus** : Collecte de métriques et alerting
- **Grafana** : Visualisation et tableaux de bord avancés

#### ⚙️ Infrastructure Moderne
- **Ansible + Kubespray** : Déploiement automatisé de Kubernetes v1.28.2
- **GitHub Actions** : Pipeline CI/CD avec déploiement automatique
- **Helm 3.13+** : Gestion applicative cloud-native

---

## 🚀 Démarrage rapide (5 minutes)

### 🔧 Prérequis
- **Serveurs** : 2+ serveurs Ubuntu 20.04+ (8GB RAM, 50GB disque)
- **Accès** : SSH avec sudo sans mot de passe
- **GitHub** : Repository avec Actions activé
- **Local** : Git, Ansible 2.16+, kubectl (optionnel)

### ⚡ Installation Express

#### 1. Configuration automatique
```bash
# Cloner et configurer
git clone https://github.com/Engelnicolas/NOAH.git
cd NOAH

# Configuration automatique avec valeurs par défaut
./script/configure-pipeline.sh --auto

# Ou mode interactif pour personnaliser
./script/configure-pipeline.sh
```

#### 2. Configuration GitHub Actions
Copiez les valeurs affichées par le script dans les **secrets GitHub** :

| Secret | Valeur par défaut | Description |
|--------|-------------------|-------------|
| `SSH_PRIVATE_KEY` | *Affichée par le script* | Clé privée SSH pour accès serveurs |
| `ANSIBLE_VAULT_PASSWORD` | `N0ah_V4ult_P@ssw0rd_2025!SecureK8s#` | Mot de passe Ansible Vault |
| `MASTER_HOST` | `192.168.1.10` | IP du serveur master |

#### 3. Déploiement des clés SSH
```bash
# Copiez la clé publique sur vos serveurs
ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@192.168.1.10
ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@192.168.1.12
```

#### 4. Lancement du pipeline
```bash
git add .
git commit -m "Configure NOAH pipeline with defaults"
git push origin Ansible
```

Le pipeline GitHub Actions se lance automatiquement et déploie :
1. **Provision** d'infrastructure
2. **Installation** de Kubernetes avec Kubespray
3. **Configuration** du cluster (ingress, storage, monitoring)
4. **Déploiement** des applications via Helm

### 🎯 Configuration par défaut

#### Serveurs
- **Master**: `192.168.1.10`
- **Worker**: `192.168.1.12`
- **Ingress**: `192.168.1.10`

#### Domaines
- **Base**: `noah.local`
- **Keycloak**: `keycloak.noah.local`
- **GitLab**: `gitlab.noah.local`
- **Nextcloud**: `nextcloud.noah.local`
- **Mattermost**: `mattermost.noah.local`
- **Grafana**: `grafana.noah.local`

#### Comptes par défaut
| Service | Utilisateur | Mot de passe |
|---------|-------------|--------------|
| Keycloak | `admin` | `Keycl0ak_Admin_789!Strong` |
| GitLab | `root` | `GitL@b_Root_Password_012!` |
| Nextcloud | `admin` | `N3xtcloud_Admin_345!Safe` |
| Grafana | `admin` | `Gr@fana_Monitoring_678!View` |

### 🌐 Configuration DNS locale

Ajoutez à votre `/etc/hosts` :
```bash
192.168.1.10 keycloak.noah.local
192.168.1.10 gitlab.noah.local
192.168.1.10 nextcloud.noah.local
192.168.1.10 mattermost.noah.local
192.168.1.10 grafana.noah.local
```

### ✅ Accès aux services déployés

- **🔐 Keycloak**: https://keycloak.noah.local
- **🦊 GitLab**: https://gitlab.noah.local  
- **☁️ Nextcloud**: https://nextcloud.noah.local
- **💬 Mattermost**: https://mattermost.noah.local
- **📊 Grafana**: https://grafana.noah.local

---

## 🛠️ CLI NOAH v0.2

### Commandes principales
```bash
# Nouveau CLI moderne et rapide
./noah.sh --help                    # Aide complète
./noah.sh --version                 # Version: v0.2.1

# Gestion du déploiement
./noah.sh init                      # Initialiser l'environnement
./noah.sh configure --auto          # Configuration automatique
./noah.sh deploy --profile prod     # Déploiement production
./noah.sh status --all              # État complet du système

# Gestion des services
./noah.sh start                     # Démarrer tous les services
./noah.sh stop                      # Arrêter tous les services
./noah.sh restart                   # Redémarrer tous les services
./noah.sh logs --service keycloak   # Logs d'un service

# Validation et tests
./noah.sh validate                  # Valider la configuration
./noah.sh test                      # Tests de connectivité
./noah.sh health                    # Santé du système
```

### Monitoring et debugging
```bash
# Vérification de l'état
kubectl get pods -n noah
kubectl get ingress -n noah

# Consulter les logs
kubectl logs -n noah deployment/keycloak
kubectl logs -n noah deployment/gitlab

## 🔧 Personnalisation

### Changer les IPs serveurs
```bash
# Éditer l'inventaire
nano ansible/inventory/mycluster/hosts.yaml

# Ou utiliser le script de configuration
MASTER_IP=10.0.0.10 WORKER_IP=10.0.0.11 ./script/configure-pipeline.sh --auto
```

### Changer le domaine
```bash
# Éditer les values Helm
nano helm/noah-common/values.yaml

# Changer la ligne : domain: noah.local
# Par exemple : domain: noah.mycompany.com
```

### Modifier les secrets
```bash
# Décrypter et éditer avec Ansible Vault
ansible-vault edit ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass
```

### Ajouter des applications
```bash
# Créer un nouveau chart Helm
helm create helm/mon-app

# Ajouter au playbook de déploiement
nano ansible/playbooks/04-deploy-apps.yml
```

---

## 🆘 Dépannage

### Pipeline échoue sur la provision
```bash
# Vérifier la connectivité SSH
ansible all -m ping -i ansible/inventory/mycluster/hosts.yaml

# Vérifier les clés SSH
ssh -i ~/.ssh/noah_pipeline ubuntu@192.168.1.10
```

### Applications inaccessibles
```bash
# Vérifier l'ingress controller
kubectl get ingress -n noah
kubectl get svc -n ingress-nginx

# Vérifier DNS local
nslookup keycloak.noah.local
```

### Pods en CrashLoopBackOff
```bash
# Voir les logs détaillés
kubectl logs -n noah -l app=keycloak --tail=100

# Redémarrer un deployment
kubectl rollout restart deployment/keycloak -n noah

# Vérifier les ressources
kubectl describe pod -n noah -l app=keycloak
```

### Problèmes de certificats SSL
```bash
# Vérifier cert-manager
kubectl get certificates -n noah
kubectl logs -n cert-manager deployment/cert-manager

# Forcer renouvellement
kubectl delete certificate -n noah --all
```

---

## 🎯 Cas d'usage principaux

### 👤 Développeurs & DevOps
- **Apprentissage** : Maîtriser DevSecOps et pipelines d'automatisation
- **Sandbox** : Tester des outils d'entreprise dans un environnement sécurisé
- **Prototypage** : Expérimenter avec des architectures cloud-native

### 🧑‍💼 PME & Startups
- **Économies** : 60-80% d'économie vs solutions SaaS propriétaires
- **Contrôle** : Maîtrise totale des données et conformité RGPD
- **Évolutivité** : Infrastructure qui grandit avec l'entreprise

### 🏢 Entreprises
- **Hybride** : Infrastructure cloud hybride avec exigences de conformité
- **Intégrations** : Personnalisations et connecteurs sur mesure
- **Gouvernance** : Audit complet et traçabilité des opérations

### 🏛️ Secteur public
- **Souveraineté** : Contrôle total des données et infrastructure
- **Conformité** : Respect des réglementations sectorielles
- **Sécurité** : Architecture sécurisée et auditée

---

## 📚 Documentation

- **[Pipeline CI/CD](docs/PIPELINE_CI_CD.md)** : Architecture des pipelines modernes
- **[CLI v0.2](docs/NOAH_CLI_v2.md)** : Guide complet du nouveau CLI
- **[Configuration domaine](docs/DOMAIN_CONFIGURATION.md)** : DNS et certificats SSL
- **[Sécurité](docs/SECURITY.md)** : Guide de sécurisation et bonnes pratiques

---

## 📜 Licence

Ce projet est sous licence **GPL v3**. Voir [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

**Nicolas Engel**  
📧 Email : [contact@nicolasengel.fr](mailto:contact@nicolasengel.fr)  
🌐 Site web : [nicolasengel.fr](https://nicolasengel.fr)  
💼 LinkedIn : [nicolas-engel-france](https://www.linkedin.com/in/nicolas-engel-france/)

*Expert en cybersécurité, infrastructure cloud-native, et DevSecOps. Passionné de solutions open-source sécurisées et évolutives.*

---

## 🏆 Remerciements

Merci à la communauté open-source et aux mainteneurs des outils qui rendent NOAH possible :

- **� Ansible** pour l'automatisation infrastructure
- **☸️ CNCF** pour Kubernetes, Prometheus, et l'écosystème cloud-native
- **⎈ Helm** pour la gestion des applications Kubernetes
- **🔐 Keycloak** pour la gestion des identités et accès
- **☁️ Nextcloud** pour la collaboration sécurisée
- **💬 Mattermost** pour la communication d'équipe
- **📊 Grafana** pour la visualisation et l'observabilité
- **🛡️ Wazuh** pour la surveillance sécuritaire
- **� GitHub** pour les pipelines CI/CD

---
