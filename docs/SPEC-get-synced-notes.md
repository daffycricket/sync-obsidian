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
- [x] Exposer dans le plugin Obsidian : voir section dédiée ci-dessous
- [x] Endpoint de comparaison client/serveur : voir section dédiée ci-dessous

---

## Feature : Visualisation dans le Plugin Obsidian

### Objectif

Permettre à l'utilisateur de voir la liste des notes synchronisées directement dans le plugin Obsidian, sans avoir à ouvrir le navigateur.

### Décisions

| Aspect | Décision |
|--------|----------|
| Emplacement UI | Onglet dédié dans les Settings du plugin |
| Interaction | Lecture seule (affichage uniquement) |
| Pagination | Oui (50 notes/page) |
| Contenu | Tableau simplifié : Path, Modified, Size |

### Spécification UI

**Onglet "Synced Notes" dans Settings :**

```
┌─────────────────────────────────────────────────────────────┐
│ SyncObsidian Settings                                       │
├──────────┬──────────────────────────────────────────────────┤
│ General  │                                                  │
│ Account  │  📊 Notes synchronisées : 425                    │
│ > Synced │  📦 Taille totale : 12.3 MB                      │
│          │                                                  │
│          │  ┌─────────────────────────────────────────────┐ │
│          │  │ 🔍 Filtrer par chemin...                    │ │
│          │  └─────────────────────────────────────────────┘ │
│          │                                                  │
│          │  Path                      Modified      Size    │
│          │  ─────────────────────────────────────────────── │
│          │  Daily/2026-01-29.md       29/01 14:00   138 B  │
│          │  Projects/README.md        29/01 10:30   1.2 KB │
│          │  ...                                            │
│          │                                                  │
│          │  ◀ Précédent    Page 1/9    Suivant ▶           │
│          │                                                  │
│          │  [Ouvrir dans le navigateur ↗]                  │
└──────────┴──────────────────────────────────────────────────┘
```

**Fonctionnalités :**
- Stats en haut : nombre de notes, taille totale
- Champ de filtre par path (debounce 300ms)
- Tableau avec colonnes : Path, Modified, Size
- Pagination : boutons + indicateur de page
- Lien pour ouvrir sync-viewer dans le navigateur (avec token auto-injecté)

### Plan d'Implémentation

1. **Créer l'onglet Settings** (`plugin/src/settings/SyncedNotesTab.ts`)
   - Étendre `PluginSettingTab`
   - Ajouter onglet "Synced Notes"

2. **Service API** (`plugin/src/api/syncedNotes.ts`)
   - Fonction `getSyncedNotes(page, pageSize, pathFilter)`
   - Gestion des erreurs et loading state

3. **Composant tableau** (`plugin/src/ui/NotesTable.ts`)
   - Rendu du tableau avec les données
   - Gestion de la pagination

4. **Tests**
   - Test du service API (mock)
   - Test du rendu UI

---

## Feature : Endpoint de Comparaison Client/Serveur

### Objectif

Permettre de comparer l'état des notes entre le client (plugin) et le serveur pour identifier les différences et faciliter le diagnostic des problèmes de sync.

### Décisions

| Aspect | Décision |
|--------|----------|
| Périmètre | Notes uniquement (pas les attachments) |
| Déclenchement | Manuel (bouton dans settings) |
| Format sortie | Liste catégorisée par action |

### Nouvelle Route API

```
POST /sync/compare
```

**Authentification** : JWT requis

**Body (envoyé par le client)** :
```json
{
  "notes": [
    {
      "path": "folder/note.md",
      "content_hash": "abc123...",
      "modified_at": "2026-01-29T10:30:00Z"
    }
  ]
}
```

**Réponse** :
```json
{
  "server_time": "2026-01-29T15:00:00Z",
  "summary": {
    "total_client": 150,
    "total_server": 148,
    "to_push": 5,
    "to_pull": 3,
    "conflicts": 1,
    "identical": 142,
    "deleted_on_server": 2
  },
  "to_push": [
    {
      "path": "new-note.md",
      "reason": "not_on_server",
      "client_modified": "2026-01-29T14:00:00Z"
    }
  ],
  "to_pull": [
    {
      "path": "updated-note.md",
      "reason": "server_newer",
      "client_modified": "2026-01-28T10:00:00Z",
      "server_modified": "2026-01-29T12:00:00Z"
    }
  ],
  "conflicts": [
    {
      "path": "conflict-note.md",
      "reason": "both_modified",
      "client_hash": "abc...",
      "server_hash": "def...",
      "client_modified": "2026-01-29T10:00:00Z",
      "server_modified": "2026-01-29T10:05:00Z"
    }
  ],
  "deleted_on_server": [
    {
      "path": "old-note.md",
      "deleted_at": "2026-01-28T09:00:00Z"
    }
  ]
}
```

### Catégories de Différences

| Catégorie | Condition | Action suggérée |
|-----------|-----------|-----------------|
| `to_push` | Note existe côté client mais pas serveur, ou client plus récent | Push vers serveur |
| `to_pull` | Note existe côté serveur mais pas client, ou serveur plus récent | Pull depuis serveur |
| `conflicts` | Les deux modifiés depuis le dernier sync, hash différents | Résolution manuelle |
| `deleted_on_server` | Note supprimée sur serveur, encore présente sur client | Supprimer localement ou re-push |
| `identical` | Même hash des deux côtés | Aucune action |

### Plan d'Implémentation

1. **Schema** (`backend/app/schemas.py`)
   - `CompareRequest` : liste des notes client
   - `CompareResponse` : résultat catégorisé

2. **Service** (`backend/app/sync.py`)
   - Fonction `compare_notes(db, user, client_notes)`
   - Logique de comparaison hash + timestamps

3. **Endpoint** (`backend/app/main.py`)
   - Route `POST /sync/compare`
   - Validation et appel service

4. **Plugin UI** (`plugin/src/settings/`)
   - Bouton "Comparer avec le serveur"
   - Modal affichant le résultat
   - Stats + listes dépliables par catégorie

5. **Tests**
   - Scénarios : nouveau client, nouveau serveur, conflit, identique
   - Tests d'intégration API
