# Spécification : Route "Get Synced Notes"

## Contexte & Problème

Lors de la synchronisation entre plusieurs appareils, certaines notes ne se synchronisent pas correctement. Il est actuellement difficile de diagnostiquer ces problèmes car il n'existe pas de moyen de visualiser l'état des fichiers côté serveur indépendamment des clients.

## Objectif

Créer une route API permettant de lister toutes les notes synchronisées sur le serveur pour un utilisateur donné, avec leurs métadonnées, afin de faciliter le diagnostic des problèmes de synchronisation.

---

## Solution Proposée

### Nouvelle Route API

```
GET /api/sync/notes
```

**Authentification** : JWT requis (utilisateur connecté)

### Réponse (paginée)

```json
{
  "total_count": 425,
  "page": 1,
  "page_size": 50,
  "total_pages": 9,
  "notes": [
    {
      "path": "folder/note.md",
      "content_hash": "sha256:abc123...",
      "modified_at": "2025-01-29T10:30:00Z",
      "synced_at": "2025-01-29T10:35:00Z",
      "is_deleted": false,
      "size_bytes": 1234
    }
  ],
  "attachments": [
    {
      "path": "attachments/image.png",
      "content_hash": "sha256:def456...",
      "modified_at": "2025-01-29T09:00:00Z",
      "synced_at": "2025-01-29T09:05:00Z",
      "is_deleted": false,
      "size_bytes": 45678
    }
  ]
}
```

### Paramètres de Query

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `page` | int | non | Numéro de page (défaut: `1`) |
| `page_size` | int | non | Nombre d'éléments par page (défaut: `50`, max: `200`) |
| `include_deleted` | bool | non | Inclure les notes marquées comme supprimées (défaut: `false`) |
| `path_filter` | string | non | Filtrer par préfixe de chemin (ex: `folder/`) |
| `modified_after` | datetime | non | Notes modifiées après cette date |
| `modified_before` | datetime | non | Notes modifiées avant cette date |

---

## Plan d'Implémentation

### Étape 1 : Créer le schéma de réponse
**Fichier** : `backend/app/schemas/sync.py`

- Ajouter `SyncedNoteInfo` : schéma pour une note individuelle
- Ajouter `SyncedNotesResponse` : schéma pour la réponse complète

### Étape 2 : Créer la fonction service
**Fichier** : `backend/app/services/sync.py`

- Ajouter fonction `get_synced_notes(db, user, filters)`
- Récupérer toutes les notes de l'utilisateur depuis la DB
- Appliquer les filtres optionnels
- Calculer la taille des fichiers depuis le storage

### Étape 3 : Créer l'endpoint API
**Fichier** : `backend/app/api/sync.py`

- Ajouter route `GET /sync/notes`
- Parser les query parameters
- Appeler le service
- Retourner la réponse formatée

### Étape 4 : Page HTML de visualisation
**Fichier** : `backend/app/static/sync-viewer.html`

Page HTML statique autonome (single file) pour visualiser les notes :

**Fonctionnalités UI :**
- Tableau avec colonnes : Path, Hash (tronqué), Modified, Synced, Deleted, Size
- Pagination : boutons Précédent/Suivant + sélecteur de page
- Tri par colonne (clic sur header)
- Filtres : champ texte pour path, checkbox "include deleted"
- Indicateur de chargement
- Affichage du total de notes

**Implémentation :**
- HTML/CSS/JS vanilla (pas de framework)
- Fetch API pour appeler `GET /api/sync/notes`
- Token JWT passé via URL (`?token=xxx`), stocké en variable JS
- Design simple et fonctionnel (CSS minimal inline ou Pico.css)
- Refresh : manuel via F5 / refresh navigateur (pas de bouton dédié)

**Accès :**
- Route : `GET /sync-viewer` ou fichier statique servi par FastAPI
- Authentification : token passé en query param `?token=xxx`
  - Le token est lu au chargement et stocké en mémoire (variable JS)
  - Si pas de token : afficher un message "Token manquant, ajoutez ?token=votre_jwt"
  - Simple et suffisant pour un outil de debug

### Étape 5 : Tests
**Fichier** : `backend/tests/test_sync_notes.py`

- Test avec utilisateur authentifié
- Test de la pagination
- Test des filtres
- Test avec notes supprimées
- Test sans notes

---

## Considérations Techniques

### Performance
- Pagination obligatoire (défaut 50, max 200 par page)
- Index DB sur `user_id` déjà présent
- COUNT query séparée pour le total (éviter de charger toutes les notes)

### Sécurité
- Authentification JWT obligatoire
- Un utilisateur ne voit que SES notes
- Pas d'exposition du contenu des notes (uniquement métadonnées)
- Page HTML : gestion sécurisée du token (pas d'exposition dans l'URL)

### Extensibilité Future (hors scope initial)
- Endpoint `GET /sync/notes/{path}` pour le détail d'une note
- Comparaison automatique client/serveur
- Export CSV des données
- Intégration dans le plugin Obsidian

---

## Utilisation pour le Debug

Cette route permettra de :

1. **Lister les notes serveur** : Voir exactement ce qui est stocké côté serveur
2. **Comparer avec le client** : Identifier les notes manquantes ou désynchronisées
3. **Vérifier les timestamps** : Comprendre l'ordre des modifications
4. **Détecter les suppressions** : Voir si une note a été marquée supprimée

### Exemple de workflow de debug

```
1. Device A : Lister les notes locales
2. Appeler GET /api/sync/notes
3. Comparer les deux listes
4. Identifier les différences (path, hash, timestamps)
```

---

## Décisions

- [x] Pagination : **Oui**, incluse dès le départ (50 items/page par défaut)
- [x] Page HTML de visualisation : **Oui**, tableau avec pagination
- [x] Authentification page HTML : **Token via query param** (`?token=xxx`)
- [x] Refresh : **Manuel** (F5 / refresh navigateur)
- [ ] Exposer dans le plugin Obsidian : **Plus tard**
- [ ] Endpoint de comparaison client/serveur : **Plus tard**
