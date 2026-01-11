# TODO - Déploiement SyncObsidian

## 1. ⬜ Mettre le code sur GitHub

```bash
# Créer un repo sur github.com, puis :
cd ~/syncobsidian
git remote add origin git@github.com:ton-username/syncobsidian.git
git branch -M main
git push -u origin main
```

---

## 2. ⬜ Récupérer le code sur le Raspberry Pi

```bash
# Sur le Raspberry Pi
ssh pi@192.168.x.x

# Installer Git et Docker si pas fait
sudo apt update && sudo apt install -y git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Se déconnecter/reconnecter

# Cloner le repo
git clone https://github.com/ton-username/syncobsidian.git
cd syncobsidian/backend
```

---

## 3. ⬜ Créer le fichier .env sur le serveur

```bash
cd ~/syncobsidian/backend
nano .env
```

Contenu :
```env
# Générer avec : python3 -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=ta-cle-secrete-generee

# DuckDNS (depuis https://www.duckdns.org)
DUCKDNS_SUBDOMAIN=nico-vault
DUCKDNS_TOKEN=ton-token-duckdns

# Domaine
DOMAIN=nico-vault.duckdns.org
```

⚠️ **Ne jamais commiter ce fichier !**

---

## 4. ⬜ Ouvrir les ports sur la Freebox

1. Aller sur **http://mafreebox.freebox.fr**
2. Se connecter (mot de passe admin Freebox)
3. **Paramètres de la Freebox** → **Gestion des ports**
4. Ajouter :

| Port externe | Port interne | IP destination | Protocole |
|--------------|--------------|----------------|-----------|
| 80           | 80           | IP du Raspberry | TCP      |
| 443          | 443          | IP du Raspberry | TCP      |

💡 Pour trouver l'IP du Raspberry : `hostname -I` (ex: 192.168.1.42)

---

## 5. ⬜ Lancer les services sur le Raspberry

```bash
cd ~/syncobsidian/backend
docker-compose -f docker-compose.prod.yml up -d

# Vérifier que tout tourne
docker ps
docker-compose -f docker-compose.prod.yml logs -f
```

Tester l'accès :
```bash
curl https://nico-vault.duckdns.org/health
# Doit retourner : {"status":"healthy","service":"syncobsidian"}
```

---

## 6. ⬜ Créer un compte utilisateur

```bash
curl -X POST https://nico-vault.duckdns.org/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "nico", "email": "nico@example.com", "password": "mot-de-passe-fort"}'
```

---

## 7. ⬜ Installer le plugin sur les devices

### Desktop (Mac/Windows/Linux)

1. Compiler le plugin :
```bash
cd ~/syncobsidian/obsidian-plugin
npm install
npm run build
```

2. Copier dans Obsidian :
```bash
# Trouver ton vault Obsidian, puis :
mkdir -p "/chemin/vers/vault/.obsidian/plugins/syncobsidian"
cp main.js manifest.json "/chemin/vers/vault/.obsidian/plugins/syncobsidian/"
```

3. Dans Obsidian : **Paramètres** → **Plugins tiers** → Activer "SyncObsidian"

### Android

1. Copier `main.js` et `manifest.json` sur le téléphone
2. Utiliser un gestionnaire de fichiers pour les placer dans :
   ```
   /storage/emulated/0/Documents/Obsidian/MonVault/.obsidian/plugins/syncobsidian/
   ```
3. Redémarrer Obsidian
4. Activer le plugin dans les paramètres

**Alternative** : Utiliser un cloud (Google Drive, Syncthing) pour sync le dossier `.obsidian/plugins/`

### iOS

1. Ouvrir l'app **Fichiers**
2. Naviguer vers : **Sur mon iPhone** → **Obsidian** → **MonVault** → **.obsidian** → **plugins**
3. Créer un dossier `syncobsidian`
4. Copier `main.js` et `manifest.json` dedans (via AirDrop, iCloud, ou câble)
5. Redémarrer Obsidian
6. Activer le plugin

**Alternative** : Utiliser iCloud pour sync le dossier plugins depuis le Mac

---

## 8. ⬜ Configurer le plugin sur chaque device

Dans les paramètres du plugin SyncObsidian :

| Champ | Valeur |
|-------|--------|
| URL du serveur | `https://nico-vault.duckdns.org` |
| Nom d'utilisateur | `nico` |
| Mot de passe | `ton-mot-de-passe` |

Cliquer sur **Se connecter**, puis **Synchroniser**.

---

## 9. ⬜ Vérifier le problème de refresh token

### État actuel

Le système utilise un **token JWT avec expiration de 24h**, sans refresh token.

### Problèmes potentiels

| Problème | Impact |
|----------|--------|
| Token expire après 24h | L'utilisateur doit se reconnecter |
| Pas de refresh automatique | Interruption de la sync après 24h |

### Solutions possibles

**Option A : Augmenter la durée du token** (simple)
```env
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 jours
```

**Option B : Implémenter un refresh token** (plus sécurisé)
- Ajouter un endpoint `/auth/refresh`
- Le plugin appelle ce endpoint avant expiration
- Nécessite modification du plugin + backend

### Recommandation

Pour un usage personnel, **Option A** (token 30 jours) est suffisante.
Si tu veux plus de sécurité, demande-moi d'implémenter les refresh tokens.

---

## ✅ Checklist finale

- [ ] Code sur GitHub
- [ ] Code cloné sur Raspberry Pi
- [ ] Fichier `.env` créé sur le serveur
- [ ] Ports 80/443 ouverts sur Freebox
- [ ] Services Docker lancés
- [ ] Compte utilisateur créé
- [ ] Plugin installé sur Mac
- [ ] Plugin installé sur Android
- [ ] Plugin installé sur iOS
- [ ] Sync testé entre tous les devices
- [ ] Décision sur refresh token

---

## 🆘 Dépannage

### Le certificat HTTPS ne marche pas
```bash
docker-compose -f docker-compose.prod.yml logs caddy
```
Vérifier que les ports 80/443 sont bien ouverts.

### L'API ne répond pas
```bash
docker-compose -f docker-compose.prod.yml logs syncobsidian
```

### DuckDNS ne pointe pas vers la bonne IP
```bash
nslookup nico-vault.duckdns.org
docker-compose -f docker-compose.prod.yml restart duckdns
```
