# Backlog du projet

## Qualité de code (technique)

| # | Priorité | Action | Description | Ce que ça corrige | Rétrocompatible | Dépendances additionnelles | Impact performance | Autres impacts / Risques | Commentaires / Stratégie de mitigation |
|---|----------|--------|-------------|-------------------|-----------------|---------------------------|-------------------|--------------------------|----------------------------------------|
| t1 | **P1 - CRITIQUE** | **Tests plugin TypeScript** | Ajouter une suite de tests pour le plugin Obsidian (1993 lignes non testées) | **Maintenabilité** : permet de refactorer sans régression, documente le comportement attendu | ✅ Oui | `vitest` ou `jest`, `@testing-library/dom` pour les composants UI | Aucun (tests exécutés en dev uniquement) | **Risque** : Courbe d'apprentissage testing Obsidian plugins. Mocking de l'API Obsidian nécessaire. | **Stratégie** : (1) Commencer par `api-client.ts` (facile à mocker). (2) Tester `sync-service.ts` avec mocks du vault. (3) `settings.ts` en dernier (UI complexe). Prioriser les TU sur la logique métier. |
| t2 | **P1 - CRITIQUE** | **Contrainte UNIQUE(user_id, path)** | Ajouter l'index unique manquant sur les tables `notes` et `attachments` dans `models.py` | **Intégrité données** : empêche les doublons en cas de requêtes concurrentes. Actuellement le code le gère mais sans garantie DB. | ⚠️ Migration requise | Aucune | Amélioration (les requêtes par path seront indexées) | **Risque** : Si des doublons existent déjà en prod, la migration échouera. | **Stratégie** : (1) Script de détection des doublons existants. (2) Nettoyage manuel si nécessaire. (3) Alembic migration avec `CREATE UNIQUE INDEX`. (4) TI : test de concurrence avec 2 requêtes simultanées. |
| t3 | **P1 - HAUTE** | **Refactoring sync.py** | Extraire le fichier `sync.py` (774 lignes) en 3 modules : `notes_sync.py`, `attachments_sync.py`, `compare_sync.py` | **Maintenabilité** : fichier trop gros, 4 responsabilités mélangées, hotspot git (9 modifications) | ✅ Oui | Aucune | Aucun | **Risque ÉLEVÉ** : Régression sur la logique de sync (cœur métier). Beaucoup de dépendances internes. | **Stratégie** : (1) **Tests first** : s'assurer que les 117 TI existants passent. (2) Extraire fonction par fonction avec commits atomiques. (3) Garder les imports dans `sync.py` comme facade temporaire. (4) Valider chaque extraction par les TI. Ne pas modifier la logique, juste déplacer. |
| t4 | **P2 - MOYENNE** | **Supprimer code mort** | Retirer ou implémenter les commandes `force-push` et `force-pull` dans `main.ts:36-50` qui affichent "Fonction non implémentée" | **UX** : évite la confusion utilisateur, réduit le code inutile | ✅ Oui | Aucune | Aucun | **Risque faible** : Aucun si on supprime. Si on implémente : risque de perte de données si mal utilisé. | **Stratégie** : Option A (recommandé) : Supprimer les commandes. Option B : Implémenter avec confirmation utilisateur + TI pour valider le comportement. |
| t5 | **P2 - MOYENNE** | **Tests unitaires backend** | Ajouter des TU pour les fonctions métier de `sync.py` : `process_sync`, `push_notes`, `compare_notes` | **Couverture** : les TI testent les endpoints mais pas la logique isolée. Facilite le refactoring. | ✅ Oui | Aucune (pytest déjà présent) | Aucun | **Risque** : Temps d'écriture. Les TI couvrent déjà bien les scénarios. | **Stratégie** : (1) Mocker `db` et `storage`. (2) Tester les cas limites non couverts par TI : hash collision, timezone edge cases, suppressions concurrentes. Prioriser après le refactoring t3. |
| t6 | **P2 - MOYENNE** | **Refactoring settings.ts** | Extraire la logique de formatage du rapport dans un fichier `report-formatter.ts` séparé de l'UI | **Maintenabilité** : `settings.ts` (668 lignes) mélange UI Obsidian et logique de formatage | ✅ Oui | Aucune | Aucun | **Risque modéré** : Régression sur l'affichage du rapport. Pas de tests actuels. | **Stratégie** : (1) **Tests first** : Écrire des TU pour `generateReportContent()` et `formatReportEntry()` AVANT extraction. (2) Extraire avec les tests comme filet de sécurité. (3) Tests manuels UI après. |
| t7 | **P3 - BASSE** | **Factoriser duplication push** | Créer une fonction générique pour `push_notes` et `push_attachments` dans `sync.py` (pattern quasi-identique L.270-346 vs L.632-725) | **Maintenabilité** : DRY, réduit le risque de divergence entre les deux implémentations | ✅ Oui | Aucune | Aucun | **Risque modéré** : Généralisation peut introduire des bugs subtils (notes = texte, attachments = binaire). | **Stratégie** : (1) Attendre le refactoring t3. (2) Créer `_push_items()` générique avec type hints. (3) TI existants doivent tous passer. (4) Ajouter TU spécifique pour la fonction générique. |
| t8 | **P3 - BASSE** | **Index sur modified_at** | Ajouter un index sur `notes.modified_at` et `attachments.modified_at` pour optimiser les requêtes filtrées | **Performance** : les requêtes `WHERE modified_at > X` seront plus rapides | ✅ Oui | Aucune | Amélioration (requêtes filtrées) | **Risque très faible** : Migration simple, pas de changement de code. | **Stratégie** : Migration Alembic simple. À faire si le volume de notes dépasse ~10 000 par utilisateur. Pas urgent actuellement. |
| t9 | **P3 - BASSE** | **Factoriser collectLocal*** | Créer une fonction générique pour `collectLocalNotes` et `collectLocalAttachments` dans `sync-service.ts` (pattern identique L.356-402 vs L.404-466) | **Maintenabilité** : DRY côté plugin | ✅ Oui | Aucune | Aucun | **Risque** : Sans tests plugin (t1), risque de régression. | **Stratégie** : **Prérequis** : Faire t1 (tests plugin) d'abord. Ensuite factoriser avec TU comme filet. |
| t10 | **P4 - OPTIONNEL** | **Enrichir docstrings** | Ajouter des docstrings détaillées sur les fonctions publiques de `sync.py` et JSDoc sur `sync-service.ts` | **Documentation** : facilite l'onboarding de nouveaux développeurs | ✅ Oui | Aucune | Aucun | Aucun risque. Temps d'écriture uniquement. | **Stratégie** : À faire lors du refactoring t3 et t6. Documenter au fil de l'eau plutôt qu'en batch. |

### Ordre recommandé d'exécution

```
t2 (contrainte UNIQUE) ──► t1 (tests plugin) ──► t3 (refacto sync.py) ──► t5 (TU backend)
                                    │
                                    ▼
                          t6 (refacto settings.ts) ──► t9 (factoriser collectLocal)
                                    │
                                    ▼
                          t4 (code mort) ──► t7 (factoriser push)
```

**Rationale** :
- t2 est un quick win critique (intégrité données)
- t1 est le prérequis pour tout refactoring plugin
- t3 doit être fait avec les TI existants comme filet
- Les factorisations (t7, t9) viennent après les tests

---

## Sécurité

| # | Priorité | Action | Description | Ce que ça corrige | Rétrocompatible | Dépendances additionnelles | Impact performance | Autres impacts | Commentaires |
|---|----------|--------|-------------|-------------------|-----------------|---------------------------|-------------------|---------------|--------------|
| s2 | **P2 - MOYENNE** | **Réduction expiration tokens** | Passer de 24h à 1-2h pour limiter l'exposition en cas de vol | **Sécurité des tokens** : réduit la fenêtre d'exploitation si un token est compromis | ⚠️ Impact UX | Aucune | Aucun | Les utilisateurs devront se reconnecter plus souvent (impact UX) | À équilibrer avec l'UX. |
| s3 | **P3 - BASSE** | **Health check protégé** | Ajouter un rate limit ou une authentification basique sur `/health` | **DDoS** : empêche le flood du health check | ⚠️ À vérifier | Aucune (utilise `slowapi` existant) | Négligeable | Si un monitoring externe utilise `/health`, s'assurer qu'il reste accessible | Protection simple. |
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
