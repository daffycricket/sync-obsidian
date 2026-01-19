"""
Tests d'intégration pour la synchronisation des notes.
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from .conftest import auth_headers


class TestSyncEndpoint:
    """Tests du endpoint /sync principal."""
    
    @pytest.mark.asyncio
    async def test_sync_empty_vault(self, authenticated_client):
        """Sync avec un vault vide doit retourner des listes vides."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["notes_to_pull"] == []
        assert data["notes_to_push"] == []
        assert data["conflicts"] == []
        assert "server_time" in data
    
    @pytest.mark.asyncio
    async def test_sync_new_local_note(self, authenticated_client):
        """Une nouvelle note locale doit être demandée en push."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "nouvelle-note.md",
                        "content_hash": "abc123def456",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "nouvelle-note.md" in data["notes_to_push"]
        assert data["notes_to_pull"] == []
        assert data["conflicts"] == []
    
    @pytest.mark.asyncio
    async def test_sync_multiple_new_notes(self, authenticated_client):
        """Plusieurs nouvelles notes locales doivent être demandées en push."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "note1.md",
                        "content_hash": "hash1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "dossier/note2.md",
                        "content_hash": "hash2",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "dossier/sous-dossier/note3.md",
                        "content_hash": "hash3",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["notes_to_push"]) == 3
        assert "note1.md" in data["notes_to_push"]
        assert "dossier/note2.md" in data["notes_to_push"]
        assert "dossier/sous-dossier/note3.md" in data["notes_to_push"]
    
    @pytest.mark.asyncio
    async def test_sync_unauthenticated(self, client: AsyncClient):
        """Sync sans authentification doit échouer."""
        response = await client.post(
            "/sync",
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )
        
        assert response.status_code in [401, 403]  # Unauthorized ou Forbidden


class TestPushNotes:
    """Tests du endpoint /sync/push."""
    
    @pytest.mark.asyncio
    async def test_push_single_note(self, authenticated_client):
        """Push d'une seule note doit réussir."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "test.md",
                        "content": "# Test\n\nContenu de test.",
                        "content_hash": "somehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "test.md" in data["success"]
        assert data["failed"] == []
    
    @pytest.mark.asyncio
    async def test_push_multiple_notes(self, authenticated_client):
        """Push de plusieurs notes doit réussir."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note1.md",
                        "content": "# Note 1",
                        "content_hash": "hash1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "note2.md",
                        "content": "# Note 2",
                        "content_hash": "hash2",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["success"]) == 2
        assert "note1.md" in data["success"]
        assert "note2.md" in data["success"]
    
    @pytest.mark.asyncio
    async def test_push_note_with_nested_path(self, authenticated_client):
        """Push d'une note dans un sous-dossier doit créer les dossiers."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "dossier/sous-dossier/note.md",
                        "content": "# Note imbriquée",
                        "content_hash": "hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "dossier/sous-dossier/note.md" in data["success"]
    
    @pytest.mark.asyncio
    async def test_push_note_with_unicode(self, authenticated_client):
        """Push d'une note avec contenu Unicode doit fonctionner."""
        client, token = authenticated_client
        
        content = """# 日本語テスト

Ceci est un test avec des émojis 🎉 et des accents éèêë.

## Section avec caractères spéciaux

- Élément avec é
- 中文字符
- Symboles: © ® ™ € £ ¥
"""
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "unicode-test.md",
                        "content": content,
                        "content_hash": "unicodehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert "unicode-test.md" in response.json()["success"]


class TestPullNotes:
    """Tests du endpoint /sync/pull."""
    
    @pytest.mark.asyncio
    async def test_pull_existing_note(self, authenticated_client):
        """Pull d'une note existante doit retourner le contenu."""
        client, token = authenticated_client
        
        # D'abord, push une note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "to-pull.md",
                        "content": "# Contenu à récupérer\n\nCeci est le contenu.",
                        "content_hash": "pullhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Ensuite, pull la note
        response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={
                "paths": ["to-pull.md"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 1
        note = data["notes"][0]
        assert note["path"] == "to-pull.md"
        assert "# Contenu à récupérer" in note["content"]
        assert "content_hash" in note
    
    @pytest.mark.asyncio
    async def test_pull_nonexistent_note(self, authenticated_client):
        """Pull d'une note inexistante doit retourner une liste vide."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={
                "paths": ["nonexistent.md"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == []
    
    @pytest.mark.asyncio
    async def test_pull_multiple_notes(self, authenticated_client):
        """Pull de plusieurs notes doit toutes les retourner."""
        client, token = authenticated_client
        
        # Push plusieurs notes
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "multi1.md",
                        "content": "# Note 1",
                        "content_hash": "h1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "multi2.md",
                        "content": "# Note 2",
                        "content_hash": "h2",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "multi3.md",
                        "content": "# Note 3",
                        "content_hash": "h3",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Pull les trois notes
        response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={
                "paths": ["multi1.md", "multi2.md", "multi3.md"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 3
        paths = [n["path"] for n in data["notes"]]
        assert "multi1.md" in paths
        assert "multi2.md" in paths
        assert "multi3.md" in paths


class TestSyncWithTimestamps:
    """Tests de synchronisation avec différents timestamps."""
    
    @pytest.mark.asyncio
    async def test_sync_client_newer(self, authenticated_client):
        """Si le client a une version plus récente, push demandé."""
        client, token = authenticated_client
        
        old_time = "2026-01-10T10:00:00"
        new_time = "2026-01-11T15:00:00"
        
        # Push une note ancienne
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "timestamp-test.md",
                        "content": "# Version ancienne",
                        "content_hash": "oldhash",
                        "modified_at": old_time,
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Sync avec une version plus récente (hash différent)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": old_time,
                "notes": [
                    {
                        "path": "timestamp-test.md",
                        "content_hash": "newhash",  # Hash différent
                        "modified_at": new_time,    # Plus récent
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Client plus récent = le serveur demande le push
        assert "timestamp-test.md" in data["notes_to_push"]
    
    @pytest.mark.asyncio
    async def test_sync_server_newer_asks_client_to_pull(self, authenticated_client):
        """Si le serveur a une version plus récente, le client doit la récupérer."""
        client, token = authenticated_client
        
        server_time = "2026-01-11T15:00:00"
        client_time = "2026-01-10T10:00:00"
        
        # Push une note récente sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflict-test.md",
                        "content": "# Version serveur récente",
                        "content_hash": "serverhash",
                        "modified_at": server_time,
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Sync avec une version plus ancienne du client (hash différent)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "conflict-test.md",
                        "content_hash": "clienthash",  # Hash différent
                        "modified_at": client_time,     # Plus ancien
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Serveur plus récent = client doit récupérer la version serveur
        pulled_paths = [n["path"] for n in data["notes_to_pull"]]
        assert "conflict-test.md" in pulled_paths
    
    @pytest.mark.asyncio
    async def test_sync_same_timestamp_different_hash_creates_conflict(self, authenticated_client):
        """Si même timestamp mais hash différent, c'est un vrai conflit."""
        client, token = authenticated_client
        
        same_time = "2026-01-11T15:00:00"
        
        # Push une note sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "real-conflict.md",
                        "content": "# Version serveur",
                        "content_hash": "serverhash",
                        "modified_at": same_time,
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Sync avec même timestamp mais hash différent (vrai conflit)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "real-conflict.md",
                        "content_hash": "clienthash",  # Hash différent
                        "modified_at": same_time,       # Même timestamp
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Même timestamp mais hash différent = conflit
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["path"] == "real-conflict.md"
    
    @pytest.mark.asyncio
    async def test_sync_same_hash_no_action(self, authenticated_client):
        """Si le hash est identique (calculé par le serveur), aucune action nécessaire."""
        client, token = authenticated_client
        
        content = "# Contenu identique"
        
        # Push une note
        push_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "same-hash.md",
                        "content": content,
                        "content_hash": "will-be-recalculated",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        assert push_resp.status_code == 200
        
        # Récupérer le hash calculé par le serveur
        pull_resp = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["same-hash.md"]}
        )
        server_hash = pull_resp.json()["notes"][0]["content_hash"]
        
        # Sync avec le même hash (celui calculé par le serveur)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-10T00:00:00",
                "notes": [
                    {
                        "path": "same-hash.md",
                        "content_hash": server_hash,  # Même hash que le serveur
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Même hash = pas d'action
        assert "same-hash.md" not in data["notes_to_push"]
        assert all(n["path"] != "same-hash.md" for n in data["conflicts"])
    
    @pytest.mark.asyncio
    async def test_sync_server_has_new_notes(self, authenticated_client):
        """Les notes du serveur non mentionnées par le client sont à pull."""
        client, token = authenticated_client
        
        # Push une note sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "server-only.md",
                        "content": "# Note serveur uniquement",
                        "content_hash": "serverhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Sync sans mentionner cette note
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-01T00:00:00",  # Ancien sync
                "notes": [],  # Client ne mentionne pas server-only.md
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Le serveur a une note que le client n'a pas = pull
        assert len(data["notes_to_pull"]) == 1
        assert data["notes_to_pull"][0]["path"] == "server-only.md"


class TestDeletedNotes:
    """Tests pour les notes supprimées."""
    
    @pytest.mark.asyncio
    async def test_push_deleted_note(self, authenticated_client):
        """Push d'une note marquée comme supprimée."""
        client, token = authenticated_client
        
        # D'abord créer la note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "to-delete.md",
                        "content": "# À supprimer",
                        "content_hash": "hash1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Marquer comme supprimée
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "to-delete.md",
                        "content": "",
                        "content_hash": "deletedhash",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert "to-delete.md" in response.json()["success"]
