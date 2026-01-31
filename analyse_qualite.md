# Analyse Qualité - SyncObsidian

**Date :** 30 janvier 2026
**Périmètre :** Backend Python (FastAPI) + Plugin TypeScript (Obsidian)
**Commits analysés :** 33 commits

---

## 1. Vue d'ensemble

| Composant | Fichiers | Lignes | Tests | Ratio Test/Code |
|-----------|----------|--------|-------|-----------------|
| Backend Python (`backend/app/`) | 10 | 1 695 | 5 318 | **3.1:1** |
| Plugin TypeScript (`obsidian-plugin/src/`) | 5 | 1 993 | 0 | **0:1** |
| **Total** | **15** | **3 688** | **5 318** | 1.4:1 |

---

## 2. Respect des conventions et standards

### Backend Python

| Critère | Statut | Détail |
|---------|--------|--------|
| Structure de projet | ⚠️ | Tous les modules à la racine de `app/` (pas de packages `services/`, `api/`, etc.) |
| Nommage fichiers | ✅ | snake_case respecté |
| Nommage fonctions/variables | ✅ | snake_case respecté |
| Typage Python | ✅ | Type hints présents sur toutes les signatures |
| Async/await | ✅ | Usage correct de SQLAlchemy async et aiofiles |
| Docstrings | ⚠️ | Présentes mais minimales, manquent sur certaines fonctions internes |
| PEP 8 | ✅ | Globalement respecté |
| Gestion des erreurs | ✅ | Try/except avec logging approprié |

### Plugin TypeScript

| Critère | Statut | Détail |
|---------|--------|--------|
| Structure de projet | ✅ | Séparation claire : `main.ts`, `sync-service.ts`, `api-client.ts`, `settings.ts`, `types.ts` |
| Nommage | ✅ | camelCase pour variables/fonctions, PascalCase pour classes/interfaces |
| Typage strict | ✅ | `noImplicitAny: true`, `strictNullChecks: true` dans tsconfig.json |
| Gestion async | ✅ | Utilisation correcte de async/await |
| Gestion des erreurs | ✅ | Try/catch avec fallbacks appropriés |
| Commentaires | ⚠️ | JSDoc partielles, certaines méthodes non documentées |

---

## 3. Maintenabilité et évolutivité

### Taille des fichiers (seuil SonarQube : 500 lignes)

| Fichier | Lignes | Verdict | Commentaire |
|---------|--------|---------|-------------|
| `backend/app/sync.py` | **774** | ⚠️ **Trop gros** | Contient toute la logique de sync (notes + attachments + compare). Candidat à extraction. |
| `obsidian-plugin/src/sync-service.ts` | **759** | ⚠️ **Trop gros** | Logique métier entière dans une classe. |
| `obsidian-plugin/src/settings.ts` | **668** | ⚠️ **Limite** | UI des settings + logique de formatage du rapport. |
| `backend/app/main.py` | 248 | ✅ | Acceptable pour un fichier de routes |
| `backend/app/schemas.py` | 228 | ✅ | DTOs Pydantic, taille justifiée |
| Autres fichiers | < 200 | ✅ | Conformes |

### Complexité et responsabilités

| Problème identifié | Fichier | Détail |
|-------------------|---------|--------|
| **Single Responsibility violé** | `sync.py` | Gère : notes sync, attachments sync, compare, parsing des références. 4 responsabilités distinctes. |
| **Single Responsibility violé** | `sync-service.ts` | Gère : collecte locale, push, pull, conflits, attachments, rapports. |
| **Single Responsibility violé** | `settings.ts` | Mélange UI des settings + génération de rapport + comparaison client/serveur. |
| **Code dupliqué** | `sync.py:270-346` vs `sync.py:632-725` | Logique push_notes et push_attachments quasi identique (structure try/except, gestion deleted, etc.) |
| **Code dupliqué** | `sync-service.ts:356-402` vs `sync-service.ts:404-466` | collectLocalNotes et collectLocalAttachments suivent le même pattern |

### Couplage et dépendances

| Aspect | Évaluation |
|--------|------------|
| Injection de dépendances | ✅ Backend utilise `Depends()` de FastAPI correctement |
| Couplage entre modules | ✅ Faible, modules indépendants |
| Couplage client/serveur | ✅ Contrat API bien défini via schemas Pydantic / types.ts |

### Code mort ou non utilisé

| Élément | Fichier | Ligne |
|---------|---------|-------|
| Commande "force-push" | `main.ts` | L.36-42 - Callback retourne "Fonction non implémentée" |
| Commande "force-pull" | `main.ts` | L.44-50 - Callback retourne "Fonction non implémentée" |

---

## 4. Couverture et typologie des tests

### Backend Python

| Catégorie | Fichiers | Tests | Couverture fonctionnelle |
|-----------|----------|-------|-------------------------|
| Tests d'intégration API | 14 | 117 | Endpoints /sync, /auth, /attachments |
| Tests unitaires purs | 0 | 0 | Aucun test unitaire isolé |
| Tests E2E | 0 | 0 | Aucun |
| Tests de sécurité | 2 | ~20 | Path traversal, sanitization |
| Tests multi-utilisateur | 1 | ~5 | Isolation des données |
| Tests edge cases | 1 | ~10 | Unicode, profondeur dossiers, etc. |

**Constats :**
- ✅ Excellente couverture des scénarios d'intégration (117 tests)
- ✅ Tests de sécurité présents (path traversal)
- ⚠️ **Pas de tests unitaires** : les fonctions `push_notes`, `process_sync`, `compare_notes` ne sont pas testées isolément
- ⚠️ Pas de tests de performance/charge

### Plugin TypeScript

| Catégorie | Fichiers | Tests |
|-----------|----------|-------|
| Tests unitaires | 0 | 0 |
| Tests d'intégration | 0 | 0 |
| Tests E2E | 0 | 0 |

**Constat critique :** ❌ **Aucun test côté plugin** (1993 lignes de code non testées)

---

## 5. Architecture applicative et technique

### Backend

```
backend/
├── app/
│   ├── main.py          # Routes FastAPI (controller)
│   ├── sync.py          # Logique métier (service)  ⚠️ monolithique
│   ├── storage.py       # Accès fichiers (repository)
│   ├── models.py        # Entités SQLAlchemy
│   ├── schemas.py       # DTOs Pydantic
│   ├── auth.py          # Authentification JWT
│   ├── database.py      # Config DB
│   └── config.py        # Settings
└── tests/               # 17 fichiers de tests
```

| Aspect | Évaluation | Commentaire |
|--------|------------|-------------|
| Séparation Controller/Service | ⚠️ Partielle | `main.py` délègue à `sync.py`, mais `sync.py` fait trop de choses |
| Pattern Repository | ✅ | `storage.py` isole l'accès fichiers |
| Injection de dépendances | ✅ | Via FastAPI `Depends()` |
| Gestion des transactions | ⚠️ | Commit par note dans `push_notes` (L.328), devrait être transactionnel par batch |

### Plugin TypeScript

```
obsidian-plugin/src/
├── main.ts              # Entry point plugin
├── sync-service.ts      # Service de synchronisation  ⚠️ monolithique
├── api-client.ts        # Client HTTP
├── settings.ts          # UI Settings + rapport  ⚠️ mélange UI/logique
└── types.ts             # Types/interfaces
```

| Aspect | Évaluation | Commentaire |
|--------|------------|-------------|
| Séparation des responsabilités | ⚠️ | `settings.ts` mélange UI et logique métier |
| Client HTTP | ✅ | `api-client.ts` bien isolé |
| Gestion d'état | ✅ | Via settings Obsidian standard |

---

## 6. Design de la base de données

### Schéma actuel (SQLite)

```sql
-- Table users
CREATE TABLE users (
    id INTEGER PRIMARY KEY,          -- ✅ Auto-increment
    username VARCHAR(50) UNIQUE,     -- ✅ Index unique
    email VARCHAR(100) UNIQUE,       -- ✅ Index unique
    hashed_password VARCHAR(255),
    created_at DATETIME,
    is_active BOOLEAN
);

-- Table notes
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),  -- ✅ FK
    path VARCHAR(500),                      -- ⚠️ Pas d'index unique (user_id, path)
    content_hash VARCHAR(64),
    modified_at DATETIME,
    synced_at DATETIME,
    is_deleted BOOLEAN
);

-- Table attachments
CREATE TABLE attachments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),  -- ✅ FK
    path VARCHAR(500),                      -- ⚠️ Pas d'index unique (user_id, path)
    content_hash VARCHAR(64),
    size INTEGER,
    mime_type VARCHAR(100),
    modified_at DATETIME,
    synced_at DATETIME,
    is_deleted BOOLEAN
);
```

### Analyse

| Critère | Statut | Problème identifié |
|---------|--------|-------------------|
| Clés primaires | ✅ | Auto-increment sur toutes les tables |
| Foreign keys | ✅ | Présentes avec cascade delete |
| Contraintes d'unicité | ❌ | **Manque** `UNIQUE(user_id, path)` sur `notes` et `attachments` |
| Index | ⚠️ | Pas d'index sur `modified_at` (filtres fréquents) |
| Types | ✅ | Appropriés |
| Normalisation | ✅ | 3NF respectée |

**Risque identifié :** Sans contrainte `UNIQUE(user_id, path)`, il est théoriquement possible d'avoir des doublons si deux requêtes concurrentes créent la même note. Le code gère ce cas via `get_note_by_path` + INSERT, mais une contrainte DB serait plus robuste.

**Preuve :** `backend/app/models.py:34-37` - Le commentaire mentionne un index unique mais il n'est pas implémenté :
```python
__table_args__ = (
    # Index unique sur user_id + path
    {"sqlite_autoincrement": True},
)
```

---

## 7. Hotspots Git (fichiers les plus modifiés)

| Fichier | Nb modifications | Risque |
|---------|-----------------|--------|
| `backend/app/sync.py` | 9 | ⚠️ **Élevé** - Point de fragilité, contient la logique critique |
| `obsidian-plugin/src/sync-service.ts` | 5 | ⚠️ Moyen |
| `backend/app/schemas.py` | 4 | Faible (évolutions API) |
| `backend/app/main.py` | 4 | Faible (ajout routes) |
| `obsidian-plugin/src/types.ts` | 4 | Faible (évolutions types) |
| `obsidian-plugin/src/settings.ts` | 3 | Faible |

**Analyse :** Les fichiers `sync.py` et `sync-service.ts` concentrent les modifications car ils contiennent toute la logique métier. Une décomposition en modules plus petits réduirait les risques de régression.

---

## 8. Points de vigilance sécurité

| Aspect | Statut | Détail |
|--------|--------|--------|
| Path traversal | ✅ | Protection via `sanitize_path()` dans `storage.py` |
| Authentification | ✅ | JWT avec bcrypt, tokens expirables |
| Injection SQL | ✅ | SQLAlchemy ORM protège des injections |
| CORS | ⚠️ | `allow_origins=["*"]` en dur dans `main.py:58` - trop permissif pour la prod |
| Secrets | ✅ | Via variables d'environnement (.env) |
| Limite upload | ✅ | 25 Mo pour les attachments |

---

## 9. Synthèse des points critiques

### Priorité Haute

| # | Problème | Impact | Action recommandée |
|---|----------|--------|-------------------|
| 1 | **Aucun test plugin TypeScript** | Risque régressions, maintenabilité | Ajouter tests unitaires avec Jest/Vitest |
| 2 | **Index unique manquant** `(user_id, path)` | Intégrité données | Ajouter contrainte dans models.py |
| 3 | **sync.py trop gros** (774 lignes) | Difficulté maintenance | Extraire `notes_sync.py`, `attachments_sync.py`, `compare.py` |

### Priorité Moyenne

| # | Problème | Impact | Action recommandée |
|---|----------|--------|-------------------|
| 4 | Fonctions "force-push/pull" non implémentées | UX confuse | Implémenter ou supprimer les commandes |
| 5 | CORS trop permissif | Sécurité prod | Configurer les origines autorisées en prod |
| 6 | Pas de tests unitaires backend | Couverture partielle | Ajouter tests unitaires pour fonctions métier |
| 7 | settings.ts mélange UI et logique | Maintenabilité | Extraire `report-formatter.ts` |

### Priorité Basse

| # | Problème | Impact | Action recommandée |
|---|----------|--------|-------------------|
| 8 | Duplication code push notes/attachments | Maintenabilité | Factoriser avec fonction générique |
| 9 | Pas d'index sur modified_at | Performance | Ajouter index si volume important |
| 10 | Docstrings minimales | Documentation | Enrichir si onboarding prévu |

---

## 10. Conclusion

### Forces du projet

- ✅ **Excellente couverture tests backend** (ratio 3:1)
- ✅ **Typage strict** des deux côtés (Python hints + TypeScript strict)
- ✅ **Sécurité correcte** (path traversal, JWT, bcrypt)
- ✅ **Architecture simple** adaptée à la taille du projet
- ✅ **Contrat API bien défini** (schemas Pydantic miroir des types TS)

### Faiblesses du projet

- ❌ **Aucun test côté plugin** (1993 lignes non couvertes)
- ⚠️ **Fichiers centraux trop gros** (sync.py, sync-service.ts > 700 lignes)
- ⚠️ **Contrainte d'unicité manquante** en base de données
- ⚠️ **Code mort** (commandes non implémentées)

### Verdict global

| Critère | Note |
|---------|------|
| Qualité du code | **B** |
| Maintenabilité | **B-** |
| Testabilité backend | **A** |
| Testabilité plugin | **F** |
| Sécurité | **B+** |
| Architecture | **B** |

**Le projet est viable et de qualité correcte pour un projet personnel/small team.** Pour un passage à l'échelle ou un onboarding de nouveaux développeurs, les chantiers prioritaires sont :

1. **Ajouter des tests au plugin TypeScript**
2. **Corriger la contrainte d'unicité en BDD**
3. **Refactorer les fichiers > 500 lignes**

---

*Rapport généré par analyse statique du code source.*
