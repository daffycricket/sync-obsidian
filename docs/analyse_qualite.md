# Analyse Qualité - SyncObsidian

**Date :** 1er février 2026
**Périmètre :** Backend Python (FastAPI) + Plugin TypeScript (Obsidian)

---

## 1. Vue d'ensemble

| Composant | Fichiers | Lignes | Tests | Ratio Test/Code |
|-----------|----------|--------|-------|-----------------|
| Backend Python (`backend/app/`) | 18 | 1 546 | 5 318 | **3.4:1** |
| Plugin TypeScript (`obsidian-plugin/src/`) | 6 | 2 000 | 1 338 | **0.67:1** |
| **Total** | **24** | **3 546** | **6 656** | 1.9:1 |

---

## 2. Respect des conventions et standards

### Backend Python

| Critère | Statut | Détail |
|---------|--------|--------|
| Structure de projet | ✅ | Packages bien organisés : `services/`, `routers/`, `core/` |
| Nommage fichiers | ✅ | snake_case respecté |
| Nommage fonctions/variables | ✅ | snake_case respecté |
| Typage Python | ✅ | Type hints présents sur toutes les signatures |
| Async/await | ✅ | Usage correct de SQLAlchemy async et aiofiles |
| PEP 8 | ✅ | Globalement respecté |
| Gestion des erreurs | ✅ | Try/except avec logging approprié |

### Plugin TypeScript

| Critère | Statut | Détail |
|---------|--------|--------|
| Structure de projet | ✅ | Séparation claire avec extraction du `report-formatter.ts` |
| Nommage | ✅ | camelCase pour variables/fonctions, PascalCase pour classes/interfaces |
| Typage strict | ✅ | `noImplicitAny: true`, `strictNullChecks: true` dans tsconfig.json |
| Gestion async | ✅ | Utilisation correcte de async/await |
| Gestion des erreurs | ✅ | Try/catch avec fallbacks appropriés |
| Tests | ✅ | Tests unitaires présents (1 338 lignes) |

---

## 3. Maintenabilité et évolutivité

### Taille des fichiers (seuil SonarQube : 500 lignes)

| Fichier | Lignes | Verdict | Commentaire |
|---------|--------|---------|-------------|
| `obsidian-plugin/src/sync-service.ts` | **759** | ⚠️ **Trop gros** | Candidat à extraction |
| `obsidian-plugin/src/settings.ts` | 475 | ✅ | Réduit après extraction de report-formatter |
| `backend/app/services/notes_sync.py` | 313 | ✅ | Conforme |
| `backend/app/services/compare_sync.py` | 263 | ✅ | Conforme |
| `backend/app/services/attachments_sync.py` | 165 | ✅ | Conforme |
| Autres fichiers | < 200 | ✅ | Conformes |

### Complexité et responsabilités

| Problème identifié | Fichier | Détail |
|-------------------|---------|--------|
| **Single Responsibility violé** | `sync-service.ts` | Gère : collecte locale, push, pull, conflits, attachments, rapports. Candidat à décomposition. |

### Couplage et dépendances

| Aspect | Évaluation |
|--------|------------|
| Injection de dépendances | ✅ Backend utilise `Depends()` de FastAPI correctement |
| Couplage entre modules | ✅ Faible, modules indépendants |
| Couplage client/serveur | ✅ Contrat API bien défini via schemas Pydantic / types.ts |

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
- ⚠️ Pas de tests unitaires isolés pour les fonctions métier
- ⚠️ Pas de tests de performance/charge

### Plugin TypeScript

| Catégorie | Fichiers | Lignes |
|-----------|----------|--------|
| Tests unitaires | 3 | 1 338 |

**Fichiers testés :**
- `api-client.test.ts` (509 lignes)
- `sync-service.test.ts` (516 lignes)
- `report-formatter.test.ts` (313 lignes)

**Constat :** ✅ Tests ajoutés, ratio test/code de 0.67:1

---

## 5. Architecture applicative et technique

### Backend

```
backend/
├── app/
│   ├── main.py              # Entry point FastAPI
│   ├── schemas.py           # DTOs Pydantic
│   ├── models.py            # Entités SQLAlchemy
│   ├── core/
│   │   ├── config.py        # Settings
│   │   ├── database.py      # Config DB
│   │   ├── security.py      # Auth JWT
│   │   ├── storage.py       # Accès fichiers
│   │   └── logging.py       # Configuration logs
│   ├── routers/
│   │   ├── auth.py          # Routes authentification
│   │   └── sync.py          # Routes synchronisation
│   └── services/
│       ├── notes_sync.py    # Logique sync notes
│       ├── attachments_sync.py  # Logique sync attachments
│       ├── compare_sync.py  # Logique comparaison
│       └── sync_utils.py    # Utilitaires partagés
└── tests/                   # 22 fichiers de tests
```

| Aspect | Évaluation | Commentaire |
|--------|------------|-------------|
| Séparation Controller/Service | ✅ | Routers délèguent aux services |
| Pattern Repository | ✅ | `storage.py` isole l'accès fichiers |
| Injection de dépendances | ✅ | Via FastAPI `Depends()` |
| Modularité | ✅ | Services bien découpés |

### Plugin TypeScript

```
obsidian-plugin/src/
├── main.ts              # Entry point plugin
├── sync-service.ts      # Service de synchronisation ⚠️ à décomposer
├── api-client.ts        # Client HTTP
├── settings.ts          # UI Settings
├── report-formatter.ts  # Formatage des rapports
├── types.ts             # Types/interfaces
└── __tests__/           # Tests unitaires
```

| Aspect | Évaluation | Commentaire |
|--------|------------|-------------|
| Séparation des responsabilités | ✅ | report-formatter extrait |
| Client HTTP | ✅ | `api-client.ts` bien isolé |
| Gestion d'état | ✅ | Via settings Obsidian standard |
| Tests | ✅ | Couverture présente |

---

## 6. Design de la base de données

### Schéma actuel (SQLite)

```sql
-- Table users
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255),
    created_at DATETIME,
    is_active BOOLEAN
);

-- Table notes
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    path VARCHAR(500),
    content_hash VARCHAR(64),
    modified_at DATETIME,              -- ✅ Index ajouté
    synced_at DATETIME,
    is_deleted BOOLEAN,
    UNIQUE(user_id, path)              -- ✅ Contrainte ajoutée
);

-- Table attachments
CREATE TABLE attachments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    path VARCHAR(500),
    content_hash VARCHAR(64),
    size INTEGER,
    mime_type VARCHAR(100),
    modified_at DATETIME,              -- ✅ Index ajouté
    synced_at DATETIME,
    is_deleted BOOLEAN,
    UNIQUE(user_id, path)              -- ✅ Contrainte ajoutée
);
```

### Analyse

| Critère | Statut | Détail |
|---------|--------|--------|
| Clés primaires | ✅ | Auto-increment sur toutes les tables |
| Foreign keys | ✅ | Présentes avec cascade delete |
| Contraintes d'unicité | ✅ | `UNIQUE(user_id, path)` sur `notes` et `attachments` |
| Index | ✅ | Index sur `modified_at` pour filtres fréquents |
| Types | ✅ | Appropriés |
| Normalisation | ✅ | 3NF respectée |

---

## 7. Points de vigilance sécurité

| Aspect | Statut | Détail |
|--------|--------|--------|
| Path traversal | ✅ | Protection via `sanitize_path()` dans `storage.py` |
| Authentification | ✅ | JWT avec bcrypt, tokens expirables |
| Injection SQL | ✅ | SQLAlchemy ORM protège des injections |
| CORS | ⚠️ | `allow_origins=["*"]` dans `main.py:60` - trop permissif pour la prod |
| Secrets | ✅ | Via variables d'environnement (.env) |
| Limite upload | ✅ | 25 Mo pour les attachments |

---

## 8. Synthèse des points critiques

### Priorité Haute

| # | Problème | Impact | Action recommandée |
|---|----------|--------|-------------------|
| 1 | **sync-service.ts trop gros** (759 lignes) | Difficulté maintenance | Extraire `notes-sync.ts`, `attachments-sync.ts`, `conflict-resolver.ts` |

### Priorité Moyenne

| # | Problème | Impact | Action recommandée |
|---|----------|--------|-------------------|
| 2 | CORS trop permissif | Sécurité prod | Configurer les origines autorisées via variable d'environnement |
| 3 | Pas de tests unitaires isolés backend | Couverture partielle | Ajouter tests unitaires pour fonctions métier critiques |

### Priorité Basse

| # | Problème | Impact | Action recommandée |
|---|----------|--------|-------------------|
| 4 | Pas de tests de performance | Scalabilité | Ajouter tests de charge si volume important prévu |

---

## 9. Évolutions depuis la dernière analyse (30 janvier 2026)

### Corrections effectuées

| Problème initial | Statut | Détail |
|------------------|--------|--------|
| Aucun test plugin TypeScript | ✅ **Corrigé** | 3 fichiers de tests ajoutés (1 338 lignes) |
| Index unique manquant (user_id, path) | ✅ **Corrigé** | `UniqueConstraint` ajouté dans `models.py` |
| Index manquant sur modified_at | ✅ **Corrigé** | `index=True` ajouté sur les colonnes |
| sync.py trop gros (774 lignes) | ✅ **Corrigé** | Décomposé en 4 modules (notes_sync, attachments_sync, compare_sync, sync_utils) |
| Code mort force-push/pull | ✅ **Corrigé** | Commandes supprimées |
| settings.ts mélange UI et logique | ✅ **Corrigé** | `report-formatter.ts` extrait |
| Structure backend monolithique | ✅ **Corrigé** | Réorganisé avec packages (services/, routers/, core/) |

### Améliorations des métriques

| Métrique | Avant | Après | Évolution |
|----------|-------|-------|-----------|
| Ratio test/code global | 1.4:1 | 1.9:1 | +36% |
| Ratio test/code plugin | 0:1 | 0.67:1 | ∞ |
| Fichiers backend > 500 lignes | 1 | 0 | -100% |
| Fichiers plugin > 500 lignes | 2 | 1 | -50% |

---

## 10. Conclusion

### Forces du projet

- ✅ **Excellente couverture tests backend** (ratio 3.4:1)
- ✅ **Tests plugin ajoutés** (ratio 0.67:1)
- ✅ **Typage strict** des deux côtés (Python hints + TypeScript strict)
- ✅ **Sécurité correcte** (path traversal, JWT, bcrypt)
- ✅ **Architecture modulaire backend** avec séparation claire des responsabilités
- ✅ **Intégrité BDD renforcée** (contraintes d'unicité, index)
- ✅ **Contrat API bien défini** (schemas Pydantic miroir des types TS)

### Faiblesses résiduelles

- ⚠️ **sync-service.ts toujours trop gros** (759 lignes)
- ⚠️ **CORS trop permissif** pour environnement de production

### Verdict global

| Critère | Note précédente | Note actuelle | Évolution |
|---------|-----------------|---------------|-----------|
| Qualité du code | B | **A-** | ↑ |
| Maintenabilité | B- | **B+** | ↑ |
| Testabilité backend | A | **A** | = |
| Testabilité plugin | F | **B** | ↑↑ |
| Sécurité | B+ | **B+** | = |
| Architecture | B | **A-** | ↑ |

**Le projet a significativement progressé.** Les 7 corrections majeures apportées depuis la dernière analyse ont résolu les problèmes d'intégrité BDD, amélioré la modularité backend et ajouté une couverture de tests au plugin.

**Actions restantes pour atteindre l'excellence :**
1. Décomposer `sync-service.ts` (759 → ~3 fichiers de 250 lignes)
2. Configurer CORS pour la production

---

*Rapport mis à jour après analyse du code source - 1er février 2026*
