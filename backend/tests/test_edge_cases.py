"""
Tests des cas limites et erreurs.
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestEdgeCases:
    """Tests des cas limites."""
    
    @pytest.mark.asyncio
    async def test_empty_note_content(self, authenticated_client):
        """Push d'une note avec contenu vide."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "empty.md",
                        "content": "",
                        "content_hash": "emptyhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert "empty.md" in response.json()["success"]
    
    @pytest.mark.asyncio
    async def test_special_characters_in_path(self, authenticated_client):
        """Chemins avec caractères spéciaux."""
        client, token = authenticated_client
        
        paths = [
            "note avec espaces.md",
            "note-avec-tirets.md",
            "note_avec_underscores.md",
            "Noté Accentuée.md",
        ]
        
        for path in paths:
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": path,
                            "content": f"# {path}",
                            "content_hash": f"hash-{path}",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200, f"Failed for path: {path}"
            assert path in response.json()["success"]
    
    @pytest.mark.asyncio
    async def test_deeply_nested_path(self, authenticated_client):
        """Chemin très profond."""
        client, token = authenticated_client
        
        deep_path = "/".join([f"folder{i}" for i in range(10)]) + "/deep-note.md"
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": deep_path,
                        "content": "# Note très profonde",
                        "content_hash": "deephash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert deep_path in response.json()["success"]
    
    @pytest.mark.asyncio
    async def test_update_existing_note(self, authenticated_client):
        """Mise à jour d'une note existante."""
        client, token = authenticated_client
        
        # Version 1
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "updatable.md",
                        "content": "# Version 1",
                        "content_hash": "v1hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Version 2
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "updatable.md",
                        "content": "# Version 2 - Mise à jour",
                        "content_hash": "v2hash",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        
        # Vérifier que c'est bien la V2
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["updatable.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert "Version 2" in note["content"]
        assert "Version 1" not in note["content"]
    
    @pytest.mark.asyncio
    async def test_sync_with_invalid_json(self, authenticated_client):
        """Requête avec JSON invalide."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync",
            headers={
                **auth_headers(token),
                "Content-Type": "application/json"
            },
            content="not valid json"
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    @pytest.mark.asyncio
    async def test_push_with_missing_fields(self, authenticated_client):
        """Push avec champs manquants."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "incomplete.md"
                        # Manque content, content_hash, modified_at
                    }
                ]
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_pull_empty_paths_list(self, authenticated_client):
        """Pull avec liste de chemins vide."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": []}
        )
        
        assert response.status_code == 200
        assert response.json()["notes"] == []
    
    @pytest.mark.asyncio
    async def test_note_with_only_whitespace(self, authenticated_client):
        """Note contenant uniquement des espaces."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "whitespace.md",
                        "content": "   \n\n\t\t\n   ",
                        "content_hash": "whitespacehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200


class TestConcurrentSync:
    """Tests de synchronisation concurrente."""
    
    @pytest.mark.asyncio
    async def test_rapid_consecutive_pushes(self, authenticated_client):
        """Plusieurs pushes consécutifs rapides."""
        client, token = authenticated_client
        
        # 10 pushes rapides
        for i in range(10):
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": f"rapid-{i}.md",
                            "content": f"# Note {i}",
                            "content_hash": f"hash{i}",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            assert response.status_code == 200
        
        # Vérifier qu'on peut toutes les récupérer
        paths = [f"rapid-{i}.md" for i in range(10)]
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": paths}
        )
        
        assert len(pull_response.json()["notes"]) == 10
    
    @pytest.mark.asyncio
    async def test_large_batch_push(self, authenticated_client):
        """Push d'un grand nombre de notes en une fois."""
        client, token = authenticated_client
        
        notes = [
            {
                "path": f"batch/note-{i}.md",
                "content": f"# Batch Note {i}\n\nContenu de la note {i}.",
                "content_hash": f"batchhash{i}",
                "modified_at": "2026-01-11T10:00:00",
                "is_deleted": False
            }
            for i in range(50)
        ]
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={"notes": notes}
        )
        
        assert response.status_code == 200
        assert len(response.json()["success"]) == 50
        assert response.json()["failed"] == []
