# Backlog du projet

## Qualité de code (technique)

| # | Priorité | Action | Description | Ce que ça corrige | Rétrocompatible | Dépendances additionnelles | Impact performance | Autres impacts / Risques | Commentaires / Stratégie de mitigation |
|---|----------|--------|-------------|-------------------|-----------------|---------------------------|-------------------|--------------------------|----------------------------------------|

## Sécurité

| # | Priorité | Action | Description | Ce que ça corrige | Rétrocompatible | Dépendances additionnelles | Impact performance | Autres impacts | Commentaires |
|---|----------|--------|-------------|-------------------|-----------------|---------------------------|-------------------|---------------|--------------|
| s1 | **P1 - HAUTE** | **Protection DDoS et brute force** | Ajouter rate limiting via Caddy : `/auth/login` 5 req/min, `/health` 20 req/min, autres 120 req/min | **DDoS + Brute force** : protège l'API contre les attaques par saturation et les tentatives de connexion automatisées | ✅ Oui | `caddy-ratelimit` (module Caddy) | Négligeable (vérification en mémoire) | Rebuild image Caddy nécessaire, ~30s interruption au déploiement | Spec complète : `docs/SPEC-rate-limiting.md`. Remplace s3 (approche plus complète au niveau reverse proxy). |
| s2 | **P2 - MOYENNE** | **Réduction expiration tokens** | Passer de 24h à 1-2h pour limiter l'exposition en cas de vol | **Sécurité des tokens** : réduit la fenêtre d'exploitation si un token est compromis | ⚠️ Impact UX | Aucune | Aucun | Les utilisateurs devront se reconnecter plus souvent (impact UX) | À équilibrer avec l'UX. |
| ~~s3~~ | ~~P3 - BASSE~~ | ~~Health check protégé~~ | ~~Ajouter un rate limit sur `/health`~~ | | | | | | **Remplacé par s1** (rate limiting Caddy plus complet) |
| s4 | **P4 - OPTIONNEL** | **Reset mot de passe** | Système d'email pour réinitialiser les mots de passe oubliés | **UX + Sécurité** : évite les comptes abandonnés avec mots de passe faibles | ✅ Oui | `aiosmtplib` ou service externe (SendGrid, etc.) | Négligeable (envoi asynchrone) | Nécessite un service email (SMTP ou API externe) et gestion de tokens de reset | Améliore l'expérience utilisateur. Nécessite une configuration email. |
| s5 | **P4 - OPTIONNEL** | **Validation de mot de passe** | Exiger minimum 12 caractères avec majuscule, minuscule, chiffre | **Sécurité des comptes** : réduit le risque de comptes compromis | ✅ Oui | Aucune (utilise `re` déjà présent) | Négligeable (< 1ms) | Aucun | Validation côté serveur. Les anciens comptes restent valides. |
| s6 | **P4 - OPTIONNEL** | **Workers multiples** | Passer de 1 à 4 workers uvicorn pour gérer la charge | **DDoS** : meilleure résistance à la charge, moins de blocages | ✅ Oui | Aucune (uvicorn supporte nativement) | Amélioration sous charge (meilleure parallélisation) | Consommation RAM multipliée par le nombre de workers (4x environ) | Améliore les performances sans changement client. |
| s7 | **P4 - OPTIONNEL** | **Validation MIME types** | Vérifier que les pièces jointes sont des types autorisés (images, PDF, etc.) | **Malware** : empêche l'upload de fichiers exécutables | ✅ Oui | `python-magic==0.4.27` (optionnel : `libmagic` système) | Léger (lecture des premiers bytes du fichier) | Nécessite `libmagic` installé sur le système (dépendance système) | Protection transparente. Le client reçoit une erreur claire si type refusé. |
| s8 | **P4 - OPTIONNEL** | **Logs d'audit fichiers** | Logger tous les accès aux fichiers (lecture/écriture) avec user_id et timestamp | **Traçabilité** : permet de détecter les accès suspects et de déboguer | ✅ Oui | Aucune (utilise `logging` déjà présent) | Négligeable (écriture asynchrone) | Augmentation de la taille des logs (rotation nécessaire) | Aucun impact client. Utile pour le debugging et la sécurité. |
| s9 | **P4 - OPTIONNEL** | **Monitoring métriques** | Ajouter des compteurs de requêtes, latence, erreurs (Prometheus ou simple) | **Observabilité** : détection précoce d'attaques ou de problèmes | ✅ Oui | `prometheus-client==0.19.0` (optionnel, peut être fait manuellement) | Négligeable (compteurs en mémoire) | Exposition d'un endpoint `/metrics` (optionnel) | Aucun impact client. Utile pour le monitoring. |
| s10 | **P4 - OPTIONNEL** | **Blacklist de tokens** | Permettre la révocation de tokens avant expiration (logout) | **Sécurité des sessions** : permet de déconnecter un utilisateur compromis | ✅ Oui | `redis` recommandé (ou stockage en mémoire) | Léger (vérification en mémoire ou Redis) | Nécessite un stockage persistant (Redis recommandé) ou perte au redémarrage | Améliore la sécurité mais pas critique pour une petite app. |

---

## Fonctionnel

| # | Priorité | Action | Description | Ce que ça corrige | Rétrocompatible | Dépendances additionnelles | Impact performance | Autres impacts | Commentaires |
|---|----------|--------|-------------|-------------------|-----------------|---------------------------|-------------------|---------------|--------------|
| | | | *(Aucun ticket fonctionnel pour l'instant)* | | | | | | |

---

## Légende

- ✅ Oui : Aucun changement client nécessaire
- ⚠️ À tester : Vérifier le comportement du client actuel
- ⚠️ Impact UX : Changement visible pour l'utilisateur (mais compatible)
- **tx** : Ticket technique (qualité de code)
- **sx** : Ticket sécurité
- **fx** : Ticket fonctionnel
