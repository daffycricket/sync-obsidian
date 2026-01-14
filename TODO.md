# TODO - Déploiement SyncObsidian

## 🔥 Prochaine action : Appliquer les modifications DNS-01

Le certificat HTTPS échoue car la Freebox bloque les ports < 16000.
Solution : utiliser le **challenge DNS-01** au lieu de HTTP-01.

### Sur le Raspberry Pi :

```bash
cd ~/syncobsidian/backend

# Récupérer les modifications
git pull

# Reconstruire l'image Caddy avec le plugin DuckDNS
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache caddy

# Relancer
docker-compose -f docker-compose.prod.yml up -d

# Vérifier que le certificat s'obtient
docker-compose -f docker-compose.prod.yml logs -f caddy
```

Vous devriez voir :
```
"msg":"certificate obtained successfully","identifier":"mon-vault.duckdns.org"
```

---

## 4. ⬜ Mettre à jour le port forwarding Freebox

Modifier la règle existante (ou supprimer 80/443 et ajouter) :

| Port externe | Port interne | IP destination  | Protocole |
|--------------|--------------|-----------------|-----------|
| 20443        | 443          | IP du Raspberry | TCP       |

> ⚠️ Le port 80 n'est plus nécessaire grâce au challenge DNS-01

---

## 5. ⬜ Vérifier que HTTPS fonctionne

```bash
curl https://mon-vault.duckdns.org:20443/health
# Doit retourner : {"status":"healthy","service":"syncobsidian"}
```

---

## 6. ⬜ Créer un compte utilisateur

```bash
curl -X POST https://mon-vault.duckdns.org:20443/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "monuser", "email": "email@example.com", "password": "mot-de-passe-fort"}'
```

---

## 7. 🔄 Installer le plugin sur les devices

### ✅ Desktop (Mac/Windows/Linux) - FAIT

### ⬜ Android

1. Copier `main.js` et `manifest.json` sur le téléphone
2. Utiliser un gestionnaire de fichiers pour les placer dans :
   ```
   /storage/emulated/0/Documents/Obsidian/MonVault/.obsidian/plugins/syncobsidian/
   ```
3. Redémarrer Obsidian
4. Activer le plugin dans les paramètres

**Alternative** : Utiliser un cloud (Google Drive, Syncthing) pour sync le dossier `.obsidian/plugins/`

### ⬜ iOS

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
| URL du serveur | `https://mon-vault.duckdns.org:20443` |
| Nom d'utilisateur | `monuser` |
| Mot de passe | `ton-mot-de-passe` |

> 💡 N'oubliez pas le port `:20443` dans l'URL !

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

- [x] Code sur GitHub
- [x] Code cloné sur Raspberry Pi
- [x] Fichier `.env` créé sur le serveur
- [ ] Port 20443 ouvert sur Freebox
- [ ] Modifications DNS-01 appliquées sur le Raspberry
- [ ] Services Docker relancés avec certificat HTTPS OK
- [ ] Compte utilisateur créé
- [x] Plugin installé sur Mac
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
Vérifier que :
- Le port 20443 est bien ouvert sur la Freebox
- Le token DuckDNS est correct dans `.env`
- L'image Caddy a été reconstruite avec le plugin DNS

### L'API ne répond pas
```bash
docker-compose -f docker-compose.prod.yml logs syncobsidian
```

### DuckDNS ne pointe pas vers la bonne IP
```bash
nslookup mon-vault.duckdns.org
docker-compose -f docker-compose.prod.yml restart duckdns
```

---

# ✅ DONE

## 1. ✅ Mettre le code sur GitHub

```bash
cd ~/syncobsidian
git remote add origin git@github.com:ton-username/syncobsidian.git
git branch -M main
git push -u origin main
```

---

## 2. ✅ Récupérer le code sur le Raspberry Pi

```bash
ssh pi@192.168.x.x

# Installer Git et Docker
sudo apt update && sudo apt install -y git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Cloner le repo
git clone https://github.com/ton-username/syncobsidian.git
cd syncobsidian/backend
```

---

## 3. ✅ Créer le fichier .env sur le serveur

```bash
cd ~/syncobsidian/backend
nano .env
```

Contenu :
```env
SECRET_KEY=ta-cle-secrete-generee
DUCKDNS_SUBDOMAIN=mon-vault
DUCKDNS_TOKEN=ton-token-duckdns
DOMAIN=mon-vault.duckdns.org
```

---

## Problème identifié : Ports Freebox bloqués

**Constat** : La Freebox bloque les ports < 16000, impossible d'utiliser 80/443.

**Solution appliquée** : 
- Utilisation du port 20443 au lieu de 443
- Challenge DNS-01 pour Let's Encrypt (pas besoin du port 80)
- Fichiers modifiés : `Caddyfile`, `docker-compose.prod.yml`, `Dockerfile.caddy`
