# Pipeline CI/CD NO3. **Initialisation**
   ```bash
   ./script/setup-pipeline.sh
   ```Ce document décrit le pipeline CI/CD automatisé pour le projet NOAH, basé sur Ansible, Kubespray, Helm et GitHub Actions.

## 🏗️ Architecture

```
GitHub Actions (Orchestrateur)
├── Ansible (Infrastructure & Config)
│   ├── Provision VMs (01-provision.yml)
│   ├── Install Kubernetes via Kubespray (02-install-k8s.yml)  
│   ├── Configure Cluster (03-configure-cluster.yml)
│   └── Deploy Apps via Helm (04-deploy-apps.yml)
└── Helm (Déploiement applicatif)
    └── noah-chart (Chart principal)
```

## 🚀 Démarrage rapide

1. **Initialiser l'environnement**
   ```bash
   ./setup-pipeline.sh
   ```

2. **Configurer les secrets GitHub**
   - `SSH_PRIVATE_KEY` : Clé privée SSH pour accéder aux serveurs
   - `ANSIBLE_VAULT_PASSWORD` : Mot de passe pour décrypter les secrets Ansible
   - `MASTER_HOST` : IP du serveur master pour la configuration SSH

3. **Personnaliser la configuration**
   - Modifier `ansible/inventory/mycluster/hosts.yaml` avec vos IPs
   - Ajuster `values/values-prod.yaml` selon vos besoins
   - Mettre à jour `ansible/vars/secrets.yml` avec vos secrets

4. **Déclencher le déploiement**
   ```bash
   git push origin Ansible
   ```

## 📁 Structure des fichiers

```
.
├── .github/workflows/deploy.yml     # Workflow GitHub Actions
├── ansible/
│   ├── ansible.cfg                  # Configuration Ansible
│   ├── requirements.yml             # Collections Ansible requises
│   ├── inventory/mycluster/
│   │   └── hosts.yaml              # Inventaire des serveurs
│   ├── kubespray/                  # Submodule Kubespray (auto-cloné)
│   ├── playbooks/
│   │   ├── 01-provision.yml        # Provision infrastructure
│   │   ├── 02-install-k8s.yml      # Installation Kubernetes
│   │   ├── 03-configure-cluster.yml # Configuration cluster
│   │   ├── 04-deploy-apps.yml      # Déploiement applications
│   │   ├── 05-verify-deployment.yml # Vérification déploiement
│   │   └── 99-cleanup.yml          # Nettoyage en cas d'échec
│   ├── templates/
│   │   ├── k8s-cluster.yml.j2      # Template config Kubespray
│   │   └── deployment_report.j2    # Template rapport déploiement
│   └── vars/
│       ├── global.yml              # Variables globales
│       └── secrets.yml             # Secrets (chiffrés avec Vault)
├── helm/noah-chart/
│   ├── Chart.yaml                  # Chart Helm principal
│   └── templates/                  # Templates Kubernetes
├── script/
│   ├── setup-pipeline.sh           # Script d'initialisation
│   ├── configure-pipeline.sh       # Configuration
│   └── generate-ssh-keys.sh        # Génération clés SSH
└── values/
    └── values-prod.yaml            # Configuration production
```

## 🔄 Workflow de déploiement

### 1. Provision de l'infrastructure
- Création des VMs sur le cloud provider
- Configuration réseau et sécurité
- Attribution des rôles master/worker

### 2. Installation Kubernetes
- Préparation des nœuds (packages, kernel modules, etc.)
- Utilisation de Kubespray pour installer K8s
- Configuration du réseau avec Calico
- Récupération du kubeconfig

### 3. Configuration du cluster
- Installation de Helm
- Déploiement d'un ingress controller (NGINX)
- Configuration du monitoring (Prometheus/Grafana)
- Création des namespaces et secrets

### 4. Déploiement des applications
- PostgreSQL (base de données partagée)
- Keycloak (authentification SSO)
- GitLab (gestion de code)
- Nextcloud (stockage et collaboration)
- Mattermost (messagerie)
- Grafana & Prometheus (monitoring)
- Wazuh & OpenEDR (sécurité)
- OAuth2 Proxy (reverse proxy avec auth)

### 5. Vérification
- Tests de connectivité
- Vérification de l'état des pods
- Génération d'un rapport de déploiement

## 🔐 Gestion des secrets

Les secrets sont gérés avec Ansible Vault :

```bash
# Chiffrer le fichier de secrets
ansible-vault encrypt ansible/vars/secrets.yml

# Éditer les secrets
ansible-vault edit ansible/vars/secrets.yml

# Décrypter temporairement
ansible-vault decrypt ansible/vars/secrets.yml
```

## 🛠️ Personnalisation

### Ajouter une nouvelle application

1. Créer un nouveau chart Helm dans `helm/`
2. Ajouter la configuration dans `values/values-prod.yaml`
3. Intégrer le déploiement dans `ansible/playbooks/04-deploy-apps.yml`

### Modifier la configuration Kubernetes

1. Ajuster les variables dans `ansible/vars/global.yml`
2. Modifier le template `ansible/templates/k8s-cluster.yml.j2`
3. Mettre à jour l'inventaire `ansible/inventory/mycluster/hosts.yaml`

### Changer le provider cloud

1. Adapter les tâches dans `ansible/playbooks/01-provision.yml`
2. Ajouter les modules Ansible spécifiques au provider
3. Mettre à jour les variables de configuration

## 🔍 Dépannage

### Vérifier les logs du workflow
```bash
# Via l'interface GitHub Actions
https://github.com/Engelnicolas/NOAH/actions

# Ou localement
ansible-playbook ansible/playbooks/05-verify-deployment.yml -i ansible/inventory/mycluster/hosts.yaml
```

### Accéder aux applications
```bash
# Après déploiement, configurer /etc/hosts ou DNS
echo "INGRESS_IP keycloak.noah.local" >> /etc/hosts
echo "INGRESS_IP gitlab.noah.local" >> /etc/hosts
echo "INGRESS_IP nextcloud.noah.local" >> /etc/hosts
echo "INGRESS_IP mattermost.noah.local" >> /etc/hosts
echo "INGRESS_IP grafana.noah.local" >> /etc/hosts
```

### Rollback en cas de problème
```bash
# Rollback Helm
helm rollback <release-name> <revision> -n noah

# Ou via Ansible
ansible-playbook ansible/playbooks/99-cleanup.yml -i ansible/inventory/mycluster/hosts.yaml
```

## 📊 Monitoring

Le pipeline déploie automatiquement :
- **Prometheus** : Collecte des métriques
- **Grafana** : Visualisation des métriques
- **AlertManager** : Gestion des alertes

Accès : https://grafana.noah.local (admin/mot_de_passe_configuré)

## 🔒 Sécurité

- Tous les secrets sont chiffrés avec Ansible Vault
- Communications TLS entre les composants
- RBAC Kubernetes configuré
- Ingress avec authentification OAuth2
- Monitoring de sécurité avec Wazuh

## 🤝 Contribution

1. Créer une branche pour vos modifications
2. Tester localement avec `ansible-playbook --check`
3. Pousser et créer une Pull Request
4. Le pipeline s'exécute automatiquement sur merge

## 📞 Support

En cas de problème :
1. Consulter les logs GitHub Actions
2. Vérifier le rapport de déploiement généré
3. Examiner les logs des pods Kubernetes
4. Contacter l'équipe NOAH
