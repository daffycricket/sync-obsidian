# TODO - Déploiement SyncObsidian


## 7. 🔄 Installer le plugin sur les devices

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
docker compose -f docker-compose.prod.yml logs caddy
```
Vérifier que :
- Le port 20443 est bien ouvert sur la Freebox
- Le token DuckDNS est correct dans `.env`
- L'image Caddy a été reconstruite avec le plugin DNS

### L'API ne répond pas
```bash
docker compose -f docker-compose.prod.yml logs syncobsidian
```

### DuckDNS ne pointe pas vers la bonne IP
```bash
nslookup mon-vault.duckdns.org
docker compose -f docker-compose.prod.yml restart duckdns
```