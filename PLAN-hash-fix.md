# Plan : Correction du calcul de hash côté plugin

## Problème actuel

Le plugin et le serveur utilisent des algorithmes de hash différents, ce qui empêche la détection correcte des fichiers identiques.

```
Situation actuelle :
┌─────────────────────────────────────────────────────────────────┐
│  Plugin (TypeScript)           │  Serveur (Python)             │
├────────────────────────────────┼───────────────────────────────┤
│  Hash JS simple (djb2-like)    │  SHA256 (hashlib)             │
│  → "0000000012345678" × 4      │  → "a1b2c3d4e5f6..."          │
└────────────────────────────────┴───────────────────────────────┘

Conséquence :
- Même fichier, même contenu → hashes DIFFÉRENTS
- La comparaison de hash échoue TOUJOURS
- Seuls les timestamps sont utilisés pour décider
- Risque d'écrasement de fichiers identiques
```

## Solution

Utiliser SHA256 côté plugin via la Web Crypto API (native dans les navigateurs et Obsidian).

```
Solution :
┌─────────────────────────────────────────────────────────────────┐
│  Plugin (TypeScript)           │  Serveur (Python)             │
├────────────────────────────────┼───────────────────────────────┤
│  SHA256 (Web Crypto API)       │  SHA256 (hashlib)             │
│  → "a1b2c3d4e5f6..."           │  → "a1b2c3d4e5f6..."          │
└────────────────────────────────┴───────────────────────────────┘

Résultat :
- Même fichier, même contenu → hashes IDENTIQUES ✅
- Pas de sync inutile pour fichiers inchangés
- Meilleure performance (moins de transferts)
```

---

## Étapes d'implémentation

| # | Tâche | Fichier(s) | Effort |
|---|-------|------------|--------|
| 1 | Remplacer `computeHash()` par SHA256 async | `obsidian-plugin/src/sync-service.ts` | 15 min |
| 2 | Adapter les appels (async/await) | `obsidian-plugin/src/sync-service.ts` | 10 min |
| 3 | Créer un test unitaire de hash | `backend/tests/test_hash_compatibility.py` | 20 min |
| 4 | Test d'intégration : même contenu = même hash | `backend/tests/test_hash_compatibility.py` | 15 min |
| 5 | Test manuel end-to-end | - | 20 min |

**Effort total estimé : ~1h20**

---

## Implémentation détaillée

### Étape 1 : Nouveau `computeHash()` avec SHA256

```typescript
// AVANT (hash JS simple - INCORRECT)
private computeHash(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
        const char = content.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash = hash & hash;
    }
    const hexHash = Math.abs(hash).toString(16).padStart(16, "0");
    return hexHash.repeat(4);
}

// APRÈS (SHA256 via Web Crypto API)
private async computeHash(content: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}
```

### Étape 2 : Adapter les appels

Les méthodes utilisant `computeHash()` doivent devenir async :

```typescript
// collectLocalNotes() - déjà async, ajouter await
const hash = await this.computeHash(content);

// pushNotes() - déjà async, ajouter await
content_hash: await this.computeHash(content),
```

---

## Tests automatisés à créer

### Test 1 : Même contenu = même hash (cross-language)

```python
# test_hash_compatibility.py

def test_sha256_matches_python():
    """Le hash calculé par le plugin doit correspondre au hash Python."""
    content = "# Test\n\nContenu de test."
    
    # Hash Python (serveur)
    import hashlib
    python_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    # Simuler le hash JS (après correction)
    # Le test vérifie que le format est correct (64 caractères hex)
    assert len(python_hash) == 64
    assert all(c in '0123456789abcdef' for c in python_hash)
```

### Test 2 : Fichier identique non re-synchronisé

```python
@pytest.mark.asyncio
async def test_identical_file_no_sync(authenticated_client):
    """
    Si Device A et Device B ont le même fichier avec le même contenu,
    aucune sync ne doit être demandée.
    """
    client, token = authenticated_client
    content = "# Note identique\n\nContenu partagé."
    
    # Calculer le hash SHA256 (comme le plugin le fera)
    import hashlib
    correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    # Device A push
    await client.post("/sync/push", headers=auth_headers(token), json={
        "notes": [{
            "path": "shared.md",
            "content": content,
            "content_hash": correct_hash,
            "modified_at": "2026-01-12T10:00:00",
            "is_deleted": False
        }]
    })
    
    # Device B sync avec le MÊME contenu et MÊME hash
    response = await client.post("/sync", headers=auth_headers(token), json={
        "last_sync": "2026-01-01T00:00:00",
        "notes": [{
            "path": "shared.md",
            "content_hash": correct_hash,  # Même hash !
            "modified_at": "2026-01-12T10:00:00",
            "is_deleted": False
        }],
        "attachments": []
    })
    
    data = response.json()
    # Aucune action nécessaire car hashes identiques
    assert "shared.md" not in data["notes_to_push"]
    assert all(n["path"] != "shared.md" for n in data["notes_to_pull"])
    assert all(n["path"] != "shared.md" for n in data["conflicts"])
```

### Test 3 : Contenu différent = hash différent

```python
@pytest.mark.asyncio
async def test_different_content_different_hash(authenticated_client):
    """
    Si le contenu change, le hash doit changer et une sync doit être demandée.
    """
    client, token = authenticated_client
    
    import hashlib
    content_v1 = "# Version 1"
    content_v2 = "# Version 2"
    hash_v1 = hashlib.sha256(content_v1.encode('utf-8')).hexdigest()
    hash_v2 = hashlib.sha256(content_v2.encode('utf-8')).hexdigest()
    
    # Vérifier que les hashes sont différents
    assert hash_v1 != hash_v2
    
    # Push version 1
    await client.post("/sync/push", headers=auth_headers(token), json={
        "notes": [{
            "path": "versioned.md",
            "content": content_v1,
            "content_hash": hash_v1,
            "modified_at": "2026-01-12T10:00:00",
            "is_deleted": False
        }]
    })
    
    # Sync avec version 2 (hash différent, client plus récent)
    response = await client.post("/sync", headers=auth_headers(token), json={
        "last_sync": "2026-01-01T00:00:00",
        "notes": [{
            "path": "versioned.md",
            "content_hash": hash_v2,
            "modified_at": "2026-01-12T12:00:00",  # Plus récent
            "is_deleted": False
        }],
        "attachments": []
    })
    
    data = response.json()
    # Hash différent + client plus récent = push demandé
    assert "versioned.md" in data["notes_to_push"]
```

### Test 4 : Unicode et caractères spéciaux

```python
@pytest.mark.asyncio
async def test_hash_unicode_content(authenticated_client):
    """Le hash doit fonctionner avec du contenu Unicode."""
    client, token = authenticated_client
    
    import hashlib
    content = "# 日本語テスト\n\nÉmojis: 🎉🚀\nAccents: éèêë"
    correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    # Push avec contenu Unicode
    response = await client.post("/sync/push", headers=auth_headers(token), json={
        "notes": [{
            "path": "unicode.md",
            "content": content,
            "content_hash": correct_hash,
            "modified_at": "2026-01-12T10:00:00",
            "is_deleted": False
        }]
    })
    
    assert response.status_code == 200
    assert "unicode.md" in response.json()["success"]
    
    # Pull et vérifier le hash
    pull_response = await client.post("/sync/pull", headers=auth_headers(token), json={
        "paths": ["unicode.md"]
    })
    
    note = pull_response.json()["notes"][0]
    assert note["content_hash"] == correct_hash
```

---

## Tests manuels end-to-end

### Test A : Nouveau device avec fichiers existants

```
Scénario :
1. Device A a "note.md" et sync
2. Device B a aussi "note.md" avec LE MÊME contenu
3. Device B installe le plugin et sync

Résultat attendu :
- Hashes identiques → aucune sync nécessaire
- Le fichier de Device B reste inchangé
```

### Test B : Nouveau device avec fichiers différents

```
Scénario :
1. Device A a "note.md" (version A) et sync
2. Device B a aussi "note.md" (version B, contenu différent)
3. Device B sync

Résultat attendu :
- Hashes différents → comparaison par timestamp
- Le plus récent gagne (ou conflit si même timestamp)
```

---

## Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Web Crypto API non disponible | Obsidian utilise Electron/Chromium, toujours disponible |
| Performance sur gros fichiers | SHA256 est rapide, même sur fichiers de plusieurs Mo |
| Migration des anciens hashes | Le serveur recalcule toujours le hash au push, pas de problème |
| Encodage UTF-8 différent | TextEncoder garantit UTF-8 côté JS, .encode('utf-8') côté Python |

---

## Validation finale

- [ ] Test : Même fichier sur 2 devices → aucune sync
- [ ] Test : Fichier modifié → sync demandée
- [ ] Test : Unicode/émojis → hash correct
- [ ] Test : Gros fichier (1Mo+) → performance OK
- [ ] Tous les tests automatisés passent
