# Spécification : Synchronisation des Pièces Jointes (Attachments)

## Contexte

Les notes synchronisées peuvent référencer des pièces jointes (images, PDFs, ZIPs, etc.) via la syntaxe Obsidian `![[fichier.png]]` ou `[[fichier.pdf]]`. Actuellement, seules les notes sont synchronisées - les attachments référencés sont listés comme "manquants" sur le serveur.

## Objectif

Implémenter la synchronisation complète des pièces jointes entre les devices, en utilisant l'infrastructure existante (modèle `Attachment`, fonctions `storage.py`).

---

## Décisions Techniques

| Aspect | Choix | Justification |
|--------|-------|---------------|
| **Transport** | Base64 dans JSON | Simplicité, même pattern que les notes |
| **Stockage** | Filesystem | Déjà implémenté, adapté à l'usage personnel |
| **Limite taille** | 25 Mo par fichier | Couvre 99% des cas (photos, PDFs) |
| **Stratégie sync** | Uniquement les référencés | Évite les fichiers orphelins |
| **Gestion conflits** | Immutable | Un attachment ne change pas après création |
| **Ordre sync** | Notes puis attachments | Cohérence des références |

---

## Architecture

### Flux de synchronisation

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYNC FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. POST /sync (notes metadata + attachments metadata)           │
│     ├─ Client envoie : notes[], attachments[]                    │
│     └─ Serveur répond : notes_to_push/pull, attachments_to_push/pull │
│                                                                  │
│  2. POST /sync/push (notes content)                              │
│     └─ Inchangé                                                  │
│                                                                  │
│  3. POST /sync/pull (notes content)                              │
│     └─ Inchangé                                                  │
│                                                                  │
│  4. POST /sync/attachments/push (NEW)                            │
│     └─ Client envoie les fichiers demandés (base64)              │
│                                                                  │
│  5. POST /sync/attachments/pull (NEW)                            │
│     └─ Serveur retourne les fichiers demandés (base64)           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Backend

### Schémas (à ajouter dans `schemas.py`)

```python
class AttachmentMetadata(BaseModel):
    """Métadonnées d'un attachment pour la comparaison."""
    path: str                    # Chemin relatif (ex: "attachments/image.png")
    content_hash: str            # SHA256 du contenu
    size: int                    # Taille en octets
    modified_at: datetime
    is_deleted: bool = False


class AttachmentContent(BaseModel):
    """Contenu complet d'un attachment pour push/pull."""
    path: str
    content_base64: str          # Contenu encodé en base64
    content_hash: str
    size: int
    mime_type: Optional[str]     # Ex: "image/png", "application/pdf"
    modified_at: datetime
    is_deleted: bool = False


class PushAttachmentsRequest(BaseModel):
    attachments: List[AttachmentContent]


class PushAttachmentsResponse(BaseModel):
    success: List[str]           # Paths des attachments sauvegardés
    failed: List[str]            # Paths des attachments en échec


class PullAttachmentsRequest(BaseModel):
    paths: List[str]             # Paths des attachments à récupérer


class PullAttachmentsResponse(BaseModel):
    attachments: List[AttachmentContent]
```

### Modification de `SyncRequest` et `SyncResponse`

```python
# SyncRequest existant - vérifier que attachments est bien utilisé
class SyncRequest(BaseModel):
    last_sync: Optional[datetime]
    notes: List[NoteMetadata]
    attachments: List[AttachmentMetadata]  # <- Actuellement ignoré


# SyncResponse existant - déjà prévu mais vide
class SyncResponse(BaseModel):
    server_time: datetime
    notes_to_pull: List[NoteMetadata]
    notes_to_push: List[str]
    conflicts: List[NoteMetadata]
    attachments_to_pull: List[AttachmentMetadata]  # <- À implémenter
    attachments_to_push: List[str]                  # <- À implémenter
```

### Nouveaux Endpoints (dans `main.py`)

```python
@app.post("/sync/attachments/push", response_model=PushAttachmentsResponse)
async def sync_attachments_push(
    request: PushAttachmentsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reçoit les pièces jointes à pousser vers le serveur."""
    success, failed = await push_attachments(db, current_user, request.attachments)
    return PushAttachmentsResponse(success=success, failed=failed)


@app.post("/sync/attachments/pull", response_model=PullAttachmentsResponse)
async def sync_attachments_pull(
    request: PullAttachmentsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne les pièces jointes demandées."""
    attachments = await pull_attachments(db, current_user, request.paths)
    return PullAttachmentsResponse(attachments=attachments)
```

### Nouvelles Fonctions (dans `sync.py`)

```python
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25 Mo


async def process_attachments_sync(
    db: AsyncSession,
    user: User,
    client_attachments: List[AttachmentMetadata]
) -> Tuple[List[AttachmentMetadata], List[str]]:
    """
    Compare les attachments client/serveur.
    Retourne (attachments_to_pull, attachments_to_push).

    Logique simplifiée (attachments immutables) :
    - Si client a, serveur n'a pas -> to_push
    - Si serveur a, client n'a pas -> to_pull
    - Si les deux ont avec même hash -> rien
    - Si les deux ont avec hash différent -> conflit (garder serveur, log warning)
    """
    pass  # À implémenter


async def push_attachments(
    db: AsyncSession,
    user: User,
    attachments: List[AttachmentContent]
) -> Tuple[List[str], List[str]]:
    """
    Sauvegarde les attachments reçus du client.
    Vérifie la taille max (25 Mo).
    Retourne (success, failed).
    """
    pass  # À implémenter


async def pull_attachments(
    db: AsyncSession,
    user: User,
    paths: List[str]
) -> List[AttachmentContent]:
    """
    Retourne le contenu des attachments demandés (encodé base64).
    """
    pass  # À implémenter
```

---

## Plugin Obsidian

### Modifications dans `sync-service.ts`

#### 1. Collecte des attachments locaux

```typescript
private async collectLocalAttachments(): Promise<{
    attachments: AttachmentMetadata[];
    failed: SyncFailedFile[];
}> {
    const attachments: AttachmentMetadata[] = [];
    const failed: SyncFailedFile[] = [];

    // Récupérer tous les fichiers non-markdown
    const allFiles = this.app.vault.getFiles();
    const nonMdFiles = allFiles.filter(f => !f.path.endsWith('.md'));

    for (const file of nonMdFiles) {
        try {
            // Vérifier la taille (25 Mo max)
            if (file.stat.size > 25 * 1024 * 1024) {
                failed.push({
                    path: file.path,
                    error: "Fichier trop volumineux (max 25 Mo)"
                });
                continue;
            }

            const content = await this.app.vault.readBinary(file);
            const hash = await this.computeBinaryHash(content);

            attachments.push({
                path: file.path,
                content_hash: hash,
                size: file.stat.size,
                modified_at: new Date(file.stat.mtime).toISOString(),
                is_deleted: false
            });
        } catch (error) {
            failed.push({
                path: file.path,
                error: error.message
            });
        }
    }

    return { attachments, failed };
}
```

#### 2. Push des attachments

```typescript
private async pushAttachments(paths: string[]): Promise<{
    sent: SyncFileInfo[];
    failed: SyncFailedFile[];
    bytesUp: number;
}> {
    const attachmentsToSend: AttachmentContent[] = [];
    const sent: SyncFileInfo[] = [];
    const failed: SyncFailedFile[] = [];
    let bytesUp = 0;

    for (const path of paths) {
        try {
            const file = this.app.vault.getAbstractFileByPath(path);
            if (file instanceof TFile) {
                const content = await this.app.vault.readBinary(file);
                const base64 = arrayBufferToBase64(content);
                const hash = await this.computeBinaryHash(content);

                attachmentsToSend.push({
                    path: path,
                    content_base64: base64,
                    content_hash: hash,
                    size: file.stat.size,
                    mime_type: this.getMimeType(path),
                    modified_at: new Date(file.stat.mtime).toISOString(),
                    is_deleted: false
                });

                bytesUp += file.stat.size;
                sent.push({ path, size_delta: file.stat.size });
            }
        } catch (error) {
            failed.push({ path, error: error.message });
        }
    }

    if (attachmentsToSend.length > 0) {
        await this.apiClient.pushAttachments({ attachments: attachmentsToSend });
    }

    return { sent, failed, bytesUp };
}
```

#### 3. Pull des attachments

```typescript
private async pullAttachments(paths: string[]): Promise<{
    received: SyncFileInfo[];
    failed: SyncFailedFile[];
    bytesDown: number;
}> {
    const received: SyncFileInfo[] = [];
    const failed: SyncFailedFile[] = [];
    let bytesDown = 0;

    if (paths.length === 0) {
        return { received, failed, bytesDown };
    }

    const response = await this.apiClient.pullAttachments({ paths });

    for (const att of response.attachments) {
        try {
            const content = base64ToArrayBuffer(att.content_base64);
            bytesDown += att.size;

            // Créer le dossier parent si nécessaire
            const folder = att.path.substring(0, att.path.lastIndexOf("/"));
            if (folder && !this.app.vault.getAbstractFileByPath(folder)) {
                await this.app.vault.createFolder(folder);
            }

            // Créer ou écraser le fichier
            const existingFile = this.app.vault.getAbstractFileByPath(att.path);
            if (existingFile instanceof TFile) {
                await this.app.vault.modifyBinary(existingFile, content);
            } else {
                await this.app.vault.createBinary(att.path, content);
            }

            received.push({ path: att.path, size_delta: att.size });
        } catch (error) {
            failed.push({ path: att.path, error: error.message });
        }
    }

    return { received, failed, bytesDown };
}
```

#### 4. Modification de `sync()` principal

```typescript
async sync(): Promise<void> {
    // ... code existant ...

    // 1. Collecter notes ET attachments
    const { notes: localNotes, failed: collectNotesFailed } = await this.collectLocalNotes();
    const { attachments: localAttachments, failed: collectAttFailed } = await this.collectLocalAttachments();

    report.failed.push(...collectNotesFailed, ...collectAttFailed);

    // 2. Envoyer au serveur pour comparaison
    const syncResponse = await this.apiClient.sync({
        last_sync: this.settings.lastSync,
        notes: localNotes,
        attachments: localAttachments,  // <- Maintenant rempli !
    });

    // 3. Push/Pull notes (existant)
    // ...

    // 4. Push attachments demandés par le serveur
    if (syncResponse.attachments_to_push.length > 0) {
        const { sent, failed, bytesUp } = await this.pushAttachments(syncResponse.attachments_to_push);
        report.sent.push(...sent);
        report.failed.push(...failed);
        report.bytes_up += bytesUp;
    }

    // 5. Pull attachments depuis le serveur
    if (syncResponse.attachments_to_pull.length > 0) {
        const paths = syncResponse.attachments_to_pull.map(a => a.path);
        const { received, failed, bytesDown } = await this.pullAttachments(paths);
        report.received.push(...received);
        report.failed.push(...failed);
        report.bytes_down += bytesDown;
    }

    // ... reste du code ...
}
```

---

## Plan d'Implémentation

### Phase 1 : Backend (estimé : ~2h)

| # | Tâche | Fichier |
|---|-------|---------|
| 1.1 | Ajouter schémas `AttachmentContent`, `PushAttachmentsRequest/Response`, `PullAttachmentsResponse` | `schemas.py` |
| 1.2 | Implémenter `process_attachments_sync()` | `sync.py` |
| 1.3 | Implémenter `push_attachments()` | `sync.py` |
| 1.4 | Implémenter `pull_attachments()` | `sync.py` |
| 1.5 | Ajouter endpoints `/sync/attachments/push` et `/sync/attachments/pull` | `main.py` |
| 1.6 | Modifier `process_sync()` pour appeler `process_attachments_sync()` | `sync.py` |
| 1.7 | Tests unitaires | `tests/test_attachments_sync.py` |

### Phase 2 : Plugin (estimé : ~2h)

| # | Tâche | Fichier |
|---|-------|---------|
| 2.1 | Ajouter types `AttachmentMetadata`, `AttachmentContent` | `types.ts` |
| 2.2 | Ajouter méthodes `pushAttachments()`, `pullAttachments()` | `api-client.ts` |
| 2.3 | Implémenter `collectLocalAttachments()` | `sync-service.ts` |
| 2.4 | Implémenter `pushAttachments()`, `pullAttachments()` | `sync-service.ts` |
| 2.5 | Modifier `sync()` pour inclure les attachments | `sync-service.ts` |
| 2.6 | Build et test manuel | - |

### Phase 3 : Tests d'intégration (estimé : ~1h)

| # | Test |
|---|------|
| 3.1 | Mac 1 crée note + attachment -> sync -> Mac 2 sync -> attachment présent |
| 3.2 | Attachment > 25 Mo -> erreur claire |
| 3.3 | Attachment supprimé sur Mac 1 -> propagé sur Mac 2 |
| 3.4 | Même attachment sur les deux -> pas de re-transfert (hash identique) |

---

## Validation

### Critères d'acceptation

- [ ] Un attachment référencé dans une note est synchronisé automatiquement
- [ ] Les attachments > 25 Mo sont rejetés avec message clair
- [ ] Le sync-viewer affiche les attachments comme "présents" (plus "manquants")
- [ ] Les attachments non référencés ne sont PAS synchronisés
- [ ] La suppression d'un attachment est propagée entre devices
- [ ] Tous les tests existants continuent de passer

---

## Risques et Mitigations

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Timeout sur gros fichiers | Sync échoue | Augmenter timeout côté plugin (60s), chunking futur |
| Mémoire sur Raspberry Pi | OOM crash | Limite 25 Mo, traitement séquentiel |
| Bande passante saturée | Sync lent | Compression GZip déjà active |
| Conflits de noms | Perte données | Hash comparison, log warning |

---

## Évolutions Futures (hors scope)

- Upload chunké pour fichiers > 25 Mo
- Streaming pour éviter tout charger en mémoire
- Synchronisation sélective par dossier
- Déduplication cross-users (même hash = même fichier)
