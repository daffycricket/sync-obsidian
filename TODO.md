# TODO - Déploiement SyncObsidian

# Actions de Sécurisation Priorisées

## Tableau des Actions

| # | Priorité | Action | Description | Ce que ça corrige | Rétrocompatible | Dépendances additionnelles | Impact performance | Autres impacts | Commentaires |
|---|----------|--------|-------------|-------------------|-----------------|---------------------------|-------------------|---------------|--------------|
| 6 | **P1 - HAUTE** | **Timeouts sur requêtes** | Timeout de 30s max par requête pour éviter les connexions bloquantes | **DDoS** : empêche l'accumulation de connexions ouvertes | ✅ Oui | Aucune | Aucun (timeout passif) | Les requêtes longues (> 30s) échoueront avec erreur 408. | Protection transparente. Les requêtes normales ne sont pas affectées. |
| 3 | **P1 - HAUTE** | **Limites de taille de fichier** | Limiter la taille des uploads (ex: 50MB par fichier, 1GB total par utilisateur) | **DDoS** : empêche la saturation disque et les attaques par gros fichiers | ✅ Oui | Aucune | Négligeable (vérification de `len()`) | Nécessite un calcul d'espace disque par utilisateur (scan initial possible) | Limite côté serveur uniquement. Erreur claire au client si dépassement. |
| 8 | **P1 - HAUTE** | **Workers multiples** | Passer de 1 à 4 workers uvicorn pour gérer la charge | **DDoS** : meilleure résistance à la charge, moins de blocages | ✅ Oui | Aucune (uvicorn supporte nativement) | Amélioration sous charge (meilleure parallélisation) | Consommation RAM multipliée par le nombre de workers (4x environ) | Améliore les performances sans changement client. |
| 9 | **P2 - MOYENNE** | **Réduction expiration tokens** | Passer de 24h à 1-2h pour limiter l'exposition en cas de vol | **Sécurité des tokens** : réduit la fenêtre d'exploitation si un token est compromis | ⚠️ Impact UX | Aucune | Aucun | Les utilisateurs devront se reconnecter plus souvent (impact UX) | À équilibrer avec l'UX. |
| 10 | **P3 - BASSE** | **Validation MIME types** | Vérifier que les pièces jointes sont des types autorisés (images, PDF, etc.) | **Malware** : empêche l'upload de fichiers exécutables | ✅ Oui | `python-magic==0.4.27` (optionnel : `libmagic` système) | Léger (lecture des premiers bytes du fichier) | Nécessite `libmagic` installé sur le système (dépendance système) | Protection transparente. Le client reçoit une erreur claire si type refusé. |
| 11 | **P3 - BASSE** | **Logs d'audit fichiers** | Logger tous les accès aux fichiers (lecture/écriture) avec user_id et timestamp | **Traçabilité** : permet de détecter les accès suspects et de déboguer | ✅ Oui | Aucune (utilise `logging` déjà présent) | Négligeable (écriture asynchrone) | Augmentation de la taille des logs (rotation nécessaire) | Aucun impact client. Utile pour le debugging et la sécurité. |
| 12 | **P3 - BASSE** | **Health check protégé** | Ajouter un rate limit ou une authentification basique sur `/health` | **DDoS** : empêche le flood du health check | ⚠️ À vérifier | Aucune (utilise `slowapi` existant) | Négligeable | Si un monitoring externe utilise `/health`, s'assurer qu'il reste accessible | Protection simple. |
| 13 | **P3 - BASSE** | **Monitoring métriques** | Ajouter des compteurs de requêtes, latence, erreurs (Prometheus ou simple) | **Observabilité** : détection précoce d'attaques ou de problèmes | ✅ Oui | `prometheus-client==0.19.0` (optionnel, peut être fait manuellement) | Négligeable (compteurs en mémoire) | Exposition d'un endpoint `/metrics` (optionnel) | Aucun impact client. Utile pour le monitoring. |
| 14 | **P4 - OPTIONNEL** | **Blacklist de tokens** | Permettre la révocation de tokens avant expiration (logout) | **Sécurité des sessions** : permet de déconnecter un utilisateur compromis | ✅ Oui | `redis` recommandé (ou stockage en mémoire) | Léger (vérification en mémoire ou Redis) | Nécessite un stockage persistant (Redis recommandé) ou perte au redémarrage | Améliore la sécurité mais pas critique pour une petite app. |
| 15 | **P4 - OPTIONNEL** | **Reset mot de passe** | Système d'email pour réinitialiser les mots de passe oubliés | **UX + Sécurité** : évite les comptes abandonnés avec mots de passe faibles | ✅ Oui | `aiosmtplib` ou service externe (SendGrid, etc.) | Négligeable (envoi asynchrone) | Nécessite un service email (SMTP ou API externe) et gestion de tokens de reset | Améliore l'expérience utilisateur. Nécessite une configuration email. |
| 16 | **P4 - OPTIONNEL** | **Circuit breaker** | Arrêter temporairement un endpoint si trop d'erreurs | **Résilience** : évite la cascade de pannes si un composant plante | ✅ Oui | `pybreaker==1.0.1` (optionnel, peut être fait manuellement) | Négligeable | Complexité de code supplémentaire | Protection avancée. Utile si l'app grandit. |
| 4 | **P4 - OPTIONNEL** | **Validation de mot de passe** | Exiger minimum 12 caractères avec majuscule, minuscule, chiffre | **Sécurité des comptes** : réduit le risque de comptes compromis | ✅ Oui | Aucune (utilise `re` déjà présent) | Négligeable (< 1ms) | Aucun | Validation côté serveur. Les anciens comptes restent valides. |
| 5 | **P4 - OPTIONNEL** | **CORS restrictif** | Remplacer `allow_origins=["*"]` par une liste de domaines autorisés | **CSRF/Attaques cross-origin** : empêche les requêtes depuis des sites malveillants | ⚠️ À tester | Aucune | Aucun | Configuration à maintenir si nouveaux clients. | Si le plugin Obsidian fait des requêtes depuis `file://` ou un domaine spécifique, l'adapter. |


## Légende

- ✅ Oui : Aucun changement client nécessaire
- ⚠️ À tester : Vérifier le comportement du client actuel
- ⚠️ Impact UX : Changement visible pour l'utilisateur (mais compatible)

## Résumé des Dépendances Additionnelles

### Obligatoires (P0)
- `slowapi==0.1.9` (pour actions #2 et #7)

### Optionnelles (P3)
- `python-magic==0.4.27` + `libmagic` système (pour action #10)
- `prometheus-client==0.19.0` (pour action #13)

### Optionnelles (P4)
- `redis` (pour action #14 - blacklist distribuée)
- `aiosmtplib` (pour action #15 - reset password)
- `pybreaker==1.0.1` (pour action #16)

## Notes Importantes

1. **`slowapi`** est la seule dépendance obligatoire pour les protections critiques (P0-P2).
2. Les impacts de performance sont généralement **négligeables** (< 1ms par requête).
3. **`libmagic`** est une dépendance système (pas Python) pour la validation MIME.
4. **Redis** n'est nécessaire que pour des fonctionnalités avancées (blacklist distribuée, rate limiting multi-instances).


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