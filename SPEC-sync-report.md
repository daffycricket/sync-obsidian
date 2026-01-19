# SPEC : Rapport de synchronisation dans les Settings

## Objectif

Afficher un rapport détaillé des synchronisations dans la page de paramètres du plugin Obsidian.

## Fonctionnalités

### 1. Historique des syncs

Afficher la liste des synchronisations avec :
- Date et heure
- Statut (✅ OK / ⚠️ WARNING / ❌ ERREUR)
- Liste complète des fichiers envoyés, reçus, supprimés
- Conflits détectés
- Durée et volume transféré

### 2. Paramètres configurables

| Paramètre | Type | Valeurs | Défaut |
|-----------|------|---------|--------|
| Mode historique | Radio | "Dernière sync" / "Historique (heures)" | Historique |
| Durée historique | Number | 1-168 (heures) | 24 |
| Afficher stack traces | Toggle | on/off | on |

### 3. Gestion des warnings

Statut ⚠️ WARNING si :
- **Conflits détectés** : des fichiers ont été modifiés sur plusieurs devices
- **Sync partielle** : certains fichiers n'ont pas pu être synchronisés (ex: le nom d'un des fichiers est invalide sur Android)

En cas de warning, afficher :
- Liste des conflits créés
- Liste des fichiers échoués avec raison

### 4. Gestion des erreurs

Statut ❌ ERREUR si :
- Échec complet de la sync (erreur serveur, réseau, auth...)

En cas d'erreur, afficher :
- Type d'erreur (serveur/locale)
- Message d'erreur
- Fichier concerné (si applicable)
- Détails contextuels
- Stack trace complète (si option activée)

## Format du rapport

```
───────────────────────────────────────────────────────
📅 19/01/2026 14:25:03                           ✅ OK
───────────────────────────────────────────────────────

↑ Envoyées (2) :
  • notes/projet-alpha.md
  • journal/2026-01-19.md

↓ Reçues (3) :
  • notes/documentation.md (+2.1 Ko)
  • notes/todo.md (+340 o)
  • inbox/note-réunion.md (+890 o)

🗑 Supprimées (0)

⚠️ Conflits (0)

⏱️ Durée : 1.8s | 📦 ↑1.2 Ko ↓3.3 Ko

───────────────────────────────────────────────────────
📅 19/01/2026 14:22:00                     ⚠️ WARNING
───────────────────────────────────────────────────────

↑ Envoyées (3) :
  • notes/projet-alpha.md
  • journal/2026-01-19.md
  • notes/réunion.md

↓ Reçues (2) :
  • notes/documentation.md (+1.2 Ko)
  • notes/todo.md (+340 o)

🗑 Supprimées (0)

⚠️ Conflits (1) :
  • notes/idées-partagées.md
    → Fichier créé : notes/idées-partagées (conflit 2026-01-19).md

⏱️ Durée : 2.1s | 📦 ↑2.4 Ko ↓1.5 Ko

───────────────────────────────────────────────────────
📅 19/01/2026 14:21:00                     ⚠️ WARNING
───────────────────────────────────────────────────────

Sync partielle : 5/6 fichiers synchronisés

↑ Envoyées (2) :
  • notes/projet.md
  • inbox/note.md

↓ Reçues (3) :
  • notes/doc.md (+500 o)
  • notes/guide.md (+1.1 Ko)
  • notes/faq.md (+200 o)

🗑 Supprimées (0)

⚠️ Conflits (0)

❌ Échecs (1) :
  • notes/projet:::test.md
    Erreur : Nom de fichier invalide sur ce système
    Caractères problématiques : :::

⏱️ Durée : 1.9s | 📦 ↑1.8 Ko ↓1.8 Ko

───────────────────────────────────────────────────────
📅 19/01/2026 14:20:01                      ❌ ERREUR
───────────────────────────────────────────────────────

Type : Erreur serveur (HTTP 500)

Message : Internal Server Error

Stack trace :
  POST https://sync.example.com/sync
  Status: 500
  Response: {"detail":"can't compare offset-naive and 
            offset-aware datetimes"}
  
  at ApiClient.sync (api-client.ts:45)
  at SyncService.sync (sync-service.ts:92)
  at async onClick (main.ts:61)

───────────────────────────────────────────────────────
📅 19/01/2026 14:15:02                      ❌ ERREUR
───────────────────────────────────────────────────────

Type : Erreur locale (écriture fichier)

Message : ENOENT: no such file or directory

Fichier concerné : notes/projet:::test.md

Détails :
  Le nom de fichier contient des caractères invalides
  sur ce système (Android).
  Caractères problématiques : :::

Stack trace :
  Error: ENOENT: no such file or directory, open 
         '/storage/.../notes/projet:::test.md'
  
  at Object.openSync (fs.js:498:3)
  at SyncService.pullNotes (sync-service.ts:215)
  at SyncService.sync (sync-service.ts:103)

───────────────────────────────────────────────────────
📅 19/01/2026 14:10:00                           ✅ OK
───────────────────────────────────────────────────────

↑ Envoyées (0)
↓ Reçues (0)
🗑 Supprimées (0)
⚠️ Conflits (0)

⏱️ Durée : 0.9s | Aucun changement

───────────────────────────────────────────────────────
📅 19/01/2026 09:45:12                           ✅ OK
───────────────────────────────────────────────────────

↑ Envoyées (5) :
  • journal/2026-01-19.md
  • notes/idées-projet.md
  • notes/réunion-équipe.md
  • inbox/capture-rapide.md
  • archives/2025/décembre/bilan.md

↓ Reçues (1) :
  • notes/todo.md (+120 o)

🗑 Supprimées (2) :
  • temp/brouillon-1.md
  • temp/brouillon-2.md

⚠️ Conflits (0)

⏱️ Durée : 2.4s | 📦 ↑8.5 Ko ↓120 o
```

## Structure de données

### SyncReportEntry (à stocker dans settings)

```typescript
interface SyncReportEntry {
    timestamp: string;           // ISO 8601
    status: "success" | "warning" | "error";
    duration_ms: number;
    
    // Succès / Warning partiel
    sent: SyncFileInfo[];
    received: SyncFileInfo[];
    deleted: string[];
    conflicts: SyncConflictInfo[];
    failed: SyncFailedFile[];     // Fichiers échoués (sync partielle)
    bytes_up: number;
    bytes_down: number;
    
    // Erreur complète
    error_type?: "server" | "local" | "network" | "auth";
    error_message?: string;
    error_file?: string;
    error_details?: string;
    stack_trace?: string;
}

interface SyncFileInfo {
    path: string;
    size_delta?: number;  // en octets
}

interface SyncConflictInfo {
    path: string;
    conflict_file: string;  // chemin du fichier conflit créé
}

interface SyncFailedFile {
    path: string;
    error: string;          // message d'erreur court
    details?: string;       // détails (ex: caractères problématiques)
}
```

### Règles de détermination du statut

```typescript
function determineStatus(report: SyncReportEntry): "success" | "warning" | "error" {
    // Erreur complète (sync échouée)
    if (report.error_type) {
        return "error";
    }
    
    // Warning si conflits ou échecs partiels
    if (report.conflicts.length > 0 || report.failed.length > 0) {
        return "warning";
    }
    
    // Succès
    return "success";
}
```

### Settings additionnels

```typescript
interface SyncObsidianSettings {
    // ... existants ...
    
    // Rapport
    reportMode: "last" | "history";
    reportHistoryHours: number;      // défaut: 24
    reportShowStackTrace: boolean;   // défaut: true
    syncHistory: SyncReportEntry[];  // liste des rapports
}
```

## UI des Settings

```
┌─────────────────────────────────────────────────────┐
│  Rapport de synchronisation                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Historique affiché                                 │
│  ┌─────────────────────────────────────────────┐   │
│  │ ○ Dernière sync uniquement                  │   │
│  │ ● Historique (heures) : [24____]            │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ☑ Afficher les stack traces en cas d'erreur       │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │  [RAPPORT AFFICHÉ ICI - zone scrollable]    │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Implémentation

### Prérequis : corriger la gestion des erreurs fichier par fichier

**Problème actuel** : Le code actuel s'arrête dès qu'un fichier pose problème. Si un fichier échoue, les fichiers suivants ne sont jamais traités.

#### Comportement actuel (à corriger)

| Méthode | Problème |
|---------|----------|
| `collectLocalNotes()` | Pas de try/catch dans la boucle. Si `vault.read()` échoue sur un fichier, toute la sync s'arrête. |
| `pushNotes()` | Pas de try/catch. Si `vault.read()` échoue sur un fichier, les fichiers suivants ne sont pas envoyés. |
| `pullNotes()` | Pas de try/catch. Si `vault.create()` échoue (ex: nom invalide sur Android), les fichiers suivants ne sont pas reçus. |
| `handleConflicts()` | Pas de try/catch. Un conflit qui échoue arrête le traitement des conflits suivants. |

#### Scénario typique sur Android

1. Le serveur renvoie 10 fichiers à pull
2. Les fichiers 1-5 sont traités OK
3. Le fichier 6 a un nom avec `:::` → `vault.create()` échoue
4. **Fichiers 7-10 ne sont jamais traités**
5. L'erreur remonte au try/catch global dans `sync()`
6. L'utilisateur voit "Erreur de synchronisation"
7. Au prochain sync, même échec au même endroit (blocage)

#### Modifications requises dans `sync-service.ts`

```typescript
// Pattern à appliquer dans chaque méthode
private async pullNotes(paths: string[]): Promise<SyncFailedFile[]> {
    const failed: SyncFailedFile[] = [];
    
    for (const note of response.notes) {
        try {
            if (note.is_deleted) {
                await this.app.vault.delete(file);
            } else {
                await this.app.vault.create(note.path, note.content);
            }
        } catch (error) {
            // Capturer l'erreur, continuer avec les autres fichiers
            failed.push({
                path: note.path,
                error: error.message,
                details: this.extractErrorDetails(error)
            });
        }
    }
    
    return failed;  // Retourner les échecs pour le rapport
}
```

| Méthode | Modification |
|---------|--------------|
| `collectLocalNotes()` | Ajouter try/catch, ignorer fichiers illisibles, les lister dans le rapport |
| `pushNotes()` | Ajouter try/catch, retourner `SyncFailedFile[]` |
| `pullNotes()` | Ajouter try/catch, retourner `SyncFailedFile[]` |
| `handleConflicts()` | Ajouter try/catch, retourner `SyncFailedFile[]` |
| `sync()` | Agréger tous les `failed[]`, créer le rapport avec le bon statut |

### Fichiers à modifier

| Fichier | Modifications |
|---------|---------------|
| `types.ts` | Ajouter interfaces `SyncReportEntry`, `SyncFileInfo`, `SyncConflictInfo`, `SyncFailedFile` |
| `types.ts` | Ajouter settings rapport dans `SyncObsidianSettings` |
| `sync-service.ts` | Ajouter try/catch fichier par fichier (voir ci-dessus) |
| `sync-service.ts` | Collecter les infos de sync et créer le rapport |
| `sync-service.ts` | Capturer les erreurs avec stack trace |
| `settings.ts` | Ajouter section "Rapport de synchronisation" |
| `settings.ts` | Afficher le rapport formaté |
| `settings.ts` | Ajouter les paramètres de configuration |

### Détection des erreurs fichier

#### Erreurs typiques à capturer

| Erreur | Cause | Détails à extraire |
|--------|-------|-------------------|
| `ENOENT` | Fichier/dossier inexistant | Path concerné |
| `EINVAL` | Nom de fichier invalide | Caractères problématiques |
| `EACCES` | Permission refusée | Path concerné |
| `ENOSPC` | Espace disque insuffisant | Taille requise vs disponible |

#### Caractères problématiques par OS

| OS | Caractères interdits |
|----|---------------------|
| Android | `: * ? " < > \|` |
| Windows | `\ / : * ? " < > \|` |
| iOS | `:` (rare mais possible) |
| macOS | `:` (affiché comme `/`) |

#### Fonction utilitaire suggérée

```typescript
private extractErrorDetails(error: Error, path: string): string | undefined {
    const invalidChars = /[:\\*?"<>|]/g;
    const matches = path.match(invalidChars);
    
    if (matches) {
        return `Caractères problématiques : ${[...new Set(matches)].join(' ')}`;
    }
    
    return undefined;
}
```

### Gestion du volume

- Rotation automatique : supprimer les entrées > `reportHistoryHours`
- Nettoyage au démarrage du plugin
- Estimation : ~500 octets/sync OK, ~1.5 Ko/sync erreur
- 24h à 5 min d'intervalle : ~288 syncs → ~150 Ko max

## Tests automatiques

### Tests unitaires plugin (TypeScript)

Fichier : `obsidian-plugin/src/__tests__/sync-service.test.ts`

#### Sync partielle (gestion erreurs fichier par fichier)

| Test | Description | Assertion |
|------|-------------|-----------|
| `pullNotes_continues_after_file_error` | Un fichier échoue à l'écriture, les suivants sont traités | Fichiers 1,2,4,5 créés, fichier 3 dans `failed[]` |
| `pullNotes_returns_all_failed_files` | Plusieurs fichiers échouent | Tous les échecs listés dans `failed[]` |
| `pushNotes_continues_after_read_error` | Un fichier ne peut pas être lu | Autres fichiers envoyés, échec dans `failed[]` |
| `collectLocalNotes_skips_unreadable_files` | Fichier corrompu/inaccessible | Les autres fichiers sont collectés |
| `handleConflicts_continues_after_error` | Création fichier conflit échoue | Autres conflits traités |

#### Détermination du statut

| Test | Description | Assertion |
|------|-------------|-----------|
| `status_success_when_no_errors` | Sync sans erreur ni conflit | `status === "success"` |
| `status_warning_when_conflicts` | Sync avec conflits | `status === "warning"` |
| `status_warning_when_partial_failure` | Sync avec fichiers échoués | `status === "warning"` |
| `status_warning_when_conflicts_and_failures` | Conflits ET fichiers échoués | `status === "warning"` |
| `status_error_when_network_failure` | Erreur réseau/serveur | `status === "error"` |
| `status_error_when_auth_failure` | Token expiré/invalide | `status === "error"` |

#### Rapport de sync

| Test | Description | Assertion |
|------|-------------|-----------|
| `report_includes_sent_files` | Fichiers envoyés listés | `report.sent` contient les paths |
| `report_includes_received_files_with_size` | Fichiers reçus avec delta taille | `report.received[].size_delta` défini |
| `report_includes_deleted_files` | Fichiers supprimés listés | `report.deleted` contient les paths |
| `report_includes_conflicts_with_created_file` | Conflits avec fichier créé | `report.conflicts[].conflict_file` défini |
| `report_includes_failed_with_error` | Échecs avec message | `report.failed[].error` défini |
| `report_includes_duration` | Durée mesurée | `report.duration_ms > 0` |
| `report_includes_bytes_transferred` | Volume transféré | `report.bytes_up >= 0`, `report.bytes_down >= 0` |

#### Gestion de l'historique

| Test | Description | Assertion |
|------|-------------|-----------|
| `history_adds_new_report` | Nouvelle sync ajoutée | `syncHistory.length` incrémenté |
| `history_rotation_removes_old_entries` | Entrées > reportHistoryHours supprimées | Entrées anciennes absentes |
| `history_respects_mode_last` | Mode "last" | Seule la dernière sync conservée |
| `history_respects_mode_history` | Mode "history" | Toutes les syncs dans la fenêtre conservées |

#### Extraction des détails d'erreur

| Test | Description | Assertion |
|------|-------------|-----------|
| `extractErrorDetails_detects_invalid_chars` | Path avec `:::` | Retourne "Caractères problématiques : :" |
| `extractErrorDetails_detects_multiple_chars` | Path avec `*?:` | Retourne tous les caractères |
| `extractErrorDetails_returns_undefined_for_valid_path` | Path valide | Retourne `undefined` |

### Tests d'intégration backend (Python)

Fichier : `backend/tests/test_sync_report.py`

Note : Le backend ne gère pas directement le rapport (c'est côté plugin), mais on peut tester les cas qui génèrent des conflits.

| Test | Description | Assertion |
|------|-------------|-----------|
| `sync_conflict_returns_conflict_metadata` | Client et serveur ont modifié | `conflicts[]` contient le path |
| `sync_conflict_server_content_preserved` | Pull après conflit | Contenu serveur accessible |

### Tests E2E (optionnel, si infra de test)

| Test | Description |
|------|-------------|
| `e2e_partial_sync_android_invalid_filename` | Sync avec fichier au nom invalide sur Android |
| `e2e_conflict_creates_conflict_file` | Conflit crée fichier avec suffixe date |
| `e2e_report_displayed_in_settings` | Rapport visible dans les settings |

### Mocking requis

Pour les tests unitaires du plugin :

```typescript
// Mock du vault Obsidian
const mockVault = {
    read: jest.fn(),
    create: jest.fn(),
    modify: jest.fn(),
    delete: jest.fn(),
    createFolder: jest.fn(),
    getMarkdownFiles: jest.fn(),
    getAbstractFileByPath: jest.fn(),
};

// Mock de l'API client
const mockApiClient = {
    sync: jest.fn(),
    pushNotes: jest.fn(),
    pullNotes: jest.fn(),
};

// Simulation d'erreur fichier
mockVault.create.mockImplementation((path: string) => {
    if (path.includes(':::')) {
        throw new Error('EINVAL: invalid filename');
    }
    return Promise.resolve();
});
```

## Tests manuels

### Statuts

- [ ] Sync réussie → ✅ OK, rapport affiché correctement
- [ ] Sync sans changement → ✅ OK, "Aucun changement" affiché
- [ ] Sync avec conflit → ⚠️ WARNING, conflit listé avec fichier créé
- [ ] Sync partielle (fichier échoué) → ⚠️ WARNING, fichier et erreur affichés
- [ ] Erreur serveur 500 → ❌ ERREUR, stack trace visible
- [ ] Erreur réseau → ❌ ERREUR, message approprié
- [ ] Erreur locale (fichier) → ❌ ERREUR, fichier concerné affiché

### Paramètres

- [ ] Basculer "Dernière sync" → historique masqué
- [ ] Changer durée historique → anciennes entrées supprimées
- [ ] Désactiver stack traces → masquées dans le rapport
