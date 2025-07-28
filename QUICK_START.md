# 🚀 Guide de démarrage rapide - Pipeline NOAH

Ce guide vous permet de déployer le pipeline NOAH en quelques minutes avec des valeurs par défaut.

## ⚡ Démarrage express (5 minutes)

### 1. Configuration automatique
```bash
# Lancer la configuration automatique
./configure-pipeline.sh --auto

# Ou en mode interactif pour personnaliser
./configure-pipeline.sh
```

### 2. Configuration GitHub Actions
Copiez les valeurs affichées par le script dans les secrets GitHub :

| Secret | Valeur | Description |
|--------|--------|-------------|
| `SSH_PRIVATE_KEY` | *Affichée par le script* | Clé privée SSH pour accès serveurs |
| `ANSIBLE_VAULT_PASSWORD` | `N0ah_V4ult_P@ssw0rd_2025!SecureK8s#` | Mot de passe Ansible Vault |
| `MASTER_HOST` | `192.168.1.10` | IP du serveur master |

### 3. Déploiement des clés SSH
```bash
# Copiez la clé publique sur vos serveurs
ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@192.168.1.10
ssh-copy-id -i ~/.ssh/noah_pipeline.pub ubuntu@192.168.1.12
```

### 4. Lancement du pipeline
```bash
git add .
git commit -m "Configure NOAH pipeline with defaults"
git push origin Ansible
```

## 🔧 Configuration par défaut

### Serveurs
- **Master**: `192.168.1.10`
- **Worker**: `192.168.1.12`
- **Ingress**: `192.168.1.10`

### Domaines
- **Base**: `noah.local`
- **Keycloak**: `keycloak.noah.local`
- **GitLab**: `gitlab.noah.local`
- **Nextcloud**: `nextcloud.noah.local`
- **Mattermost**: `mattermost.noah.local`
- **Grafana**: `grafana.noah.local`

### Comptes par défaut
| Service | Utilisateur | Mot de passe |
|---------|-------------|--------------|
| Keycloak | `admin` | `Keycl0ak_Admin_789!Strong` |
| GitLab | `root` | `GitL@b_Root_Password_012!` |
| Nextcloud | `admin` | `N3xtcloud_Admin_345!Safe` |
| Grafana | `admin` | `Gr@fana_Monitoring_678!View` |

## 🌐 Configuration DNS locale

Ajoutez à votre `/etc/hosts` :
```bash
192.168.1.10 keycloak.noah.local
192.168.1.10 gitlab.noah.local
192.168.1.10 nextcloud.noah.local
192.168.1.10 mattermost.noah.local
192.168.1.10 grafana.noah.local
```

## ✅ Vérification du déploiement

### 1. Vérifier l'état des pods
```bash
kubectl get pods -n noah
```

### 2. Accéder aux applications
- **Keycloak**: https://keycloak.noah.local
- **GitLab**: https://gitlab.noah.local
- **Nextcloud**: https://nextcloud.noah.local
- **Mattermost**: https://mattermost.noah.local
- **Grafana**: https://grafana.noah.local

### 3. Consulter les logs
```bash
# Logs du workflow GitHub Actions
# Disponible dans l'onglet Actions de votre repo

# Logs des applications
kubectl logs -n noah deployment/keycloak
kubectl logs -n noah deployment/gitlab
```

## 🔧 Personnalisation

### Changer les IPs
```bash
# Éditer l'inventaire
nano ansible/inventory/mycluster/hosts.yaml

# Ou utiliser le script de configuration
MASTER_IP=10.0.0.10 WORKER_IP=10.0.0.11 ./configure-pipeline.sh --auto
```

### Changer le domaine
```bash
# Éditer les values
nano values/values-prod.yaml

# Changer la ligne : domain: noah.local
# Par exemple : domain: noah.mycompany.com
```

### Modifier les secrets
```bash
# Décrypter et éditer
ansible-vault edit ansible/vars/secrets.yml --vault-password-file ansible/.vault_pass
```

## 🆘 Dépannage rapide

### Problème : Pipeline échoue sur la provision
```bash
# Vérifier la connectivité SSH
ansible all -m ping -i ansible/inventory/mycluster/hosts.yaml
```

### Problème : Applications inaccessibles
```bash
# Vérifier l'ingress controller
kubectl get ingress -n noah
kubectl get svc -n ingress-nginx

# Vérifier DNS local
nslookup keycloak.noah.local
```

### Problème : Pods en CrashLoopBackOff
```bash
# Voir les logs
kubectl logs -n noah -l app=keycloak --tail=100

# Redémarrer un deployment
kubectl rollout restart deployment/keycloak -n noah
```

## 📞 Support

1. **Logs détaillés** : Consultez le rapport de déploiement généré automatiquement
2. **GitHub Actions** : Vérifiez les logs dans l'onglet Actions
3. **Documentation** : Consultez `docs/PIPELINE_CI_CD.md` pour plus de détails

---

🎉 **Félicitations !** Votre plateforme NOAH devrait maintenant être opérationnelle !
