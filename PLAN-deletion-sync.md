# Plan : Synchronisation des suppressions de fichiers

## Problème actuel

Quand un fichier est supprimé localement, le plugin ne le détecte pas et le serveur le renvoie au prochain sync.

```
Situation actuelle :
1. User supprime "note.md" sur Device A
2. Device A sync → ne mentionne pas "note.md" (fichier absent = invisible)
3. Serveur : "note.md existe chez moi, pas chez client → notes_to_pull"
4. Device A reçoit "note.md" → fichier ressuscité ! ❌
```

## Solution

Mémoriser les fichiers connus et détecter ceux qui disparaissent.

```
Solution :
1. Plugin stocke la liste des fichiers après chaque sync réussi
2. Au prochain sync, compare : fichiers actuels vs fichiers mémorisés
3. Fichiers disparus → envoyés avec is_deleted: true
4. Serveur marque le fichier comme supprimé
5. Autres devices reçoivent la suppression
```

---

## Étapes d'implémentation

| # | Tâche | Fichier(s) | Effort |
|---|-------|------------|--------|
| 1 | Ajouter `delete_note()` au storage | `backend/app/storage.py` | 5 min |
| 2 | Modifier `push_notes()` pour gérer `is_deleted` | `backend/app/sync.py` | 15 min |
| 3 | Modifier `process_sync()` pour propager les suppressions | `backend/app/sync.py` | 20 min |
| 4 | Ajouter tests backend | `backend/tests/test_sync_deletions.py` | 30 min |
| 5 | Ajouter `knownFiles` aux settings du plugin | `obsidian-plugin/src/types.ts` | 10 min |
| 6 | Modifier `collectLocalNotes()` pour détecter suppressions | `obsidian-plugin/src/sync-service.ts` | 20 min |
| 7 | Sauvegarder `knownFiles` après sync réussi | `obsidian-plugin/src/sync-service.ts` | 15 min |
| 8 | Tests manuels end-to-end | - | 30 min |

**Effort total estimé : ~2h30**

---

## Tests automatisés à créer

### Test 1 : Suppression locale propagée au serveur

```
Scénario :
1. Créer et sync une note
2. Envoyer la note avec is_deleted=true
3. Vérifier que le serveur la marque comme supprimée
```

### Test 2 : Suppression propagée aux autres devices

```
Scénario :
1. Device A crée "note.md"
2. Device A supprime "note.md" (is_deleted=true)
3. Device B sync → doit recevoir "note.md" avec is_deleted=true
```

### Test 3 : Fichier supprimé n'est pas ressuscité

```
Scénario :
1. Créer et supprimer une note
2. Sync sans mentionner la note
3. La note ne doit pas réapparaître dans notes_to_pull
```

### Test 4 : Conflit suppression vs modification

```
Scénario :
1. Device A et B ont "note.md"
2. Device A supprime "note.md"
3. Device B modifie "note.md" (sans savoir qu'elle est supprimée)
4. Device B sync → conflit détecté
```

---

## Risques et mitigations

| Risque | Mitigation |
|--------|------------|
| Première sync = tout marqué comme "supprimé" | Ne détecter les suppressions que si `knownFiles` n'est pas vide |
| Fichier renommé = suppression + création | OK, comportement attendu |
| Gros vault = `knownFiles` très long | Stocker seulement les paths (strings), pas les contenus |
| Sync interrompu = état incohérent | Mettre à jour `knownFiles` seulement après sync réussi |

---

## Validation finale

- [ ] Test : Supprimer un fichier sur Device A → disparaît sur Device B
- [ ] Test : Supprimer puis re-créer un fichier → fonctionne
- [ ] Test : Première sync d'un nouveau device → pas de fausses suppressions
- [ ] Test : Conflit suppression/modification → géré proprement
- [ ] Tous les tests automatisés passent
