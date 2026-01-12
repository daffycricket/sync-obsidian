"""
Tests d'intégration pour la synchronisation des suppressions de notes.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from .conftest import auth_headers


class TestDeletionPropagation:
    """Tests de propagation des suppressions entre devices."""
    
    @pytest.mark.asyncio
    async def test_delete_local_note_syncs_to_server(self, authenticated_client):
        """
        Test 1: Suppression locale propagée au serveur.
        1. Créer et sync une note
        2. Envoyer la note avec is_deleted=true
        3. Vérifier que le serveur la marque comme supprimée
        """
        client, token = authenticated_client
        
        # 1. Créer une note sur le serveur
        push_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note-to-delete.md",
                        "content": "# Note à supprimer",
                        "content_hash": "originalhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        assert push_resp.status_code == 200
        assert "note-to-delete.md" in push_resp.json()["success"]
        
        # 2. Supprimer la note (envoyer avec is_deleted=true)
        delete_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note-to-delete.md",
                        "content": "",
                        "content_hash": "",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        assert delete_resp.status_code == 200
        assert "note-to-delete.md" in delete_resp.json()["success"]
        
        # 3. Vérifier que le pull retourne is_deleted=true
        pull_resp = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["note-to-delete.md"]}
        )
        assert pull_resp.status_code == 200
        notes = pull_resp.json()["notes"]
        assert len(notes) == 1
        assert notes[0]["path"] == "note-to-delete.md"
        assert notes[0]["is_deleted"] == True
        assert notes[0]["content"] == ""
    
    @pytest.mark.asyncio
    async def test_deleted_note_not_resurrected(self, authenticated_client):
        """
        Test 3: Fichier supprimé n'est pas ressuscité.
        1. Créer et supprimer une note
        2. Sync sans mentionner la note
        3. La note ne doit pas réapparaître dans notes_to_pull
        """
        client, token = authenticated_client
        
        # 1. Créer une note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "ghost-note.md",
                        "content": "# Note fantôme",
                        "content_hash": "ghosthash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # 2. Supprimer la note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "ghost-note.md",
                        "content": "",
                        "content_hash": "",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        
        # 3. Sync sans mentionner la note - elle ne doit PAS réapparaître
        sync_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-01T00:00:00",
                "notes": [],  # Client ne mentionne pas ghost-note.md
                "attachments": []
            }
        )
        
        assert sync_resp.status_code == 200
        data = sync_resp.json()
        
        # Vérifier que ghost-note.md n'est PAS dans notes_to_pull
        pulled_paths = [n["path"] for n in data["notes_to_pull"]]
        assert "ghost-note.md" not in pulled_paths
    
    @pytest.mark.asyncio
    async def test_deletion_propagates_to_other_device(self, authenticated_client):
        """
        Test 2: Suppression propagée aux autres devices.
        Simule Device A qui supprime, Device B qui sync.
        """
        client, token = authenticated_client
        
        # Device A crée la note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "shared-note.md",
                        "content": "# Note partagée",
                        "content_hash": "sharedhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Device B sync pour avoir la note (simule un premier sync)
        sync_b1 = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )
        assert "shared-note.md" in [n["path"] for n in sync_b1.json()["notes_to_pull"]]
        
        # Device A supprime la note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "shared-note.md",
                        "content": "",
                        "content_hash": "",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        
        # Device B sync avec la note (comme si elle l'avait encore)
        sync_b2 = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-11T10:30:00",  # Après premier sync
                "notes": [
                    {
                        "path": "shared-note.md",
                        "content_hash": "sharedhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert sync_b2.status_code == 200
        data = sync_b2.json()
        
        # Device B doit recevoir l'info de suppression
        pulled = [n for n in data["notes_to_pull"] if n["path"] == "shared-note.md"]
        assert len(pulled) == 1
        assert pulled[0]["is_deleted"] == True


class TestDeletionConflicts:
    """Tests de conflits liés aux suppressions."""
    
    @pytest.mark.asyncio
    async def test_conflict_delete_vs_modify(self, authenticated_client):
        """
        Test 4: Conflit suppression vs modification.
        1. Device A et B ont "note.md"
        2. Device A supprime "note.md"
        3. Device B modifie "note.md" (sans savoir qu'elle est supprimée)
        4. Device B sync → conflit détecté
        """
        client, token = authenticated_client
        
        initial_time = "2026-01-11T10:00:00"
        delete_time = "2026-01-11T11:00:00"
        modify_time = "2026-01-11T11:30:00"  # Après la suppression
        
        # Device A crée la note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflict-note.md",
                        "content": "# Contenu initial",
                        "content_hash": "initialhash",
                        "modified_at": initial_time,
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Device A supprime la note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflict-note.md",
                        "content": "",
                        "content_hash": "",
                        "modified_at": delete_time,
                        "is_deleted": True
                    }
                ]
            }
        )
        
        # Device B modifie la note (ne sait pas qu'elle a été supprimée)
        sync_b = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": initial_time,
                "notes": [
                    {
                        "path": "conflict-note.md",
                        "content_hash": "modifiedhash",  # Contenu modifié
                        "modified_at": modify_time,  # Plus récent que la suppression
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert sync_b.status_code == 200
        data = sync_b.json()
        
        # Le client a modifié après la suppression -> il peut re-pusher
        # (on accepte la résurrection si le client est plus récent)
        assert "conflict-note.md" in data["notes_to_push"]
    
    @pytest.mark.asyncio
    async def test_modify_before_delete_creates_conflict(self, authenticated_client):
        """
        Si Device B a modifié AVANT la suppression de Device A,
        mais sync APRÈS, c'est un conflit.
        """
        client, token = authenticated_client
        
        initial_time = "2026-01-11T10:00:00"
        modify_time = "2026-01-11T10:30:00"  # Avant la suppression
        delete_time = "2026-01-11T11:00:00"  # Après la modification
        
        # Créer et sync initial
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflict2.md",
                        "content": "# Initial",
                        "content_hash": "initialhash",
                        "modified_at": initial_time,
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Device A supprime (après avoir reçu la version initiale)
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflict2.md",
                        "content": "",
                        "content_hash": "",
                        "modified_at": delete_time,
                        "is_deleted": True
                    }
                ]
            }
        )
        
        # Device B sync avec modification AVANT la suppression
        sync_b = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": initial_time,
                "notes": [
                    {
                        "path": "conflict2.md",
                        "content_hash": "modifiedhash",
                        "modified_at": modify_time,  # Avant delete_time
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert sync_b.status_code == 200
        data = sync_b.json()
        
        # Suppression est plus récente -> le client reçoit la suppression
        pulled = [n for n in data["notes_to_pull"] if n["path"] == "conflict2.md"]
        assert len(pulled) == 1
        assert pulled[0]["is_deleted"] == True


class TestDeleteAndRecreate:
    """Tests de suppression puis re-création."""
    
    @pytest.mark.asyncio
    async def test_delete_then_recreate(self, authenticated_client):
        """Supprimer puis re-créer un fichier fonctionne."""
        client, token = authenticated_client
        
        # Créer
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "phoenix.md",
                        "content": "# Version 1",
                        "content_hash": "v1hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Supprimer
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "phoenix.md",
                        "content": "",
                        "content_hash": "",
                        "modified_at": "2026-01-11T11:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        
        # Re-créer avec nouveau contenu
        recreate_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "phoenix.md",
                        "content": "# Version 2 - Resurgi!",
                        "content_hash": "v2hash",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        assert recreate_resp.status_code == 200
        assert "phoenix.md" in recreate_resp.json()["success"]
        
        # Vérifier le contenu
        pull_resp = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["phoenix.md"]}
        )
        assert pull_resp.status_code == 200
        notes = pull_resp.json()["notes"]
        assert len(notes) == 1
        assert notes[0]["is_deleted"] == False
        assert "Version 2" in notes[0]["content"]


class TestFirstSyncNoFalseDeletions:
    """Tests pour éviter les fausses suppressions lors du premier sync."""
    
    @pytest.mark.asyncio
    async def test_first_sync_existing_server_notes(self, authenticated_client):
        """
        Premier sync d'un nouveau device ne doit pas créer de fausses suppressions.
        Le serveur a des notes, le client fait son premier sync sans rien.
        """
        client, token = authenticated_client
        
        # Créer des notes sur le serveur (via un autre "device")
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "existing1.md",
                        "content": "# Existing 1",
                        "content_hash": "e1hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "existing2.md",
                        "content": "# Existing 2",
                        "content_hash": "e2hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Nouveau device fait son premier sync (last_sync=null, notes=[])
        sync_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )
        
        assert sync_resp.status_code == 200
        data = sync_resp.json()
        
        # Les notes serveur doivent être proposées au pull, pas supprimées
        pulled_paths = [n["path"] for n in data["notes_to_pull"]]
        assert "existing1.md" in pulled_paths
        assert "existing2.md" in pulled_paths
        
        # Pas de notes à push (le client n'a rien)
        assert data["notes_to_push"] == []
