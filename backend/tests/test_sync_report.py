"""
Tests pour la génération de conflits qui seront utilisés dans le rapport de sync.
Note : Le backend ne gère pas directement le rapport (c'est côté plugin),
mais on peut tester les cas qui génèrent des conflits.
"""
import pytest
import hashlib
from datetime import datetime, timedelta
from httpx import AsyncClient
from .conftest import auth_headers


def compute_hash(content: str) -> str:
    """Calcule le hash SHA256 d'un contenu."""
    return hashlib.sha256(content.encode()).hexdigest()


class TestSyncConflictReporting:
    """Tests pour les conflits qui apparaîtront dans le rapport."""
    
    @pytest.mark.asyncio
    async def test_sync_conflict_returns_conflict_metadata(self, authenticated_client):
        """
        Quand client et serveur ont modifié le même fichier,
        le conflit doit être retourné dans conflicts[] avec le path.
        """
        client, token = authenticated_client
        
        # 1. Créer une note sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note-conflit.md",
                        "content": "Version serveur",
                        "content_hash": "hash_serveur",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # 2. Simuler une modification côté client (hash différent, même timestamp)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "note-conflit.md",
                        "content_hash": "hash_client_different",
                        "modified_at": "2026-01-19T10:00:00",  # Même timestamp
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Le conflit doit être détecté
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["path"] == "note-conflit.md"
        assert "content_hash" in data["conflicts"][0]
        assert "modified_at" in data["conflicts"][0]
    
    @pytest.mark.asyncio
    async def test_sync_conflict_server_content_preserved(self, authenticated_client):
        """
        Après un conflit détecté, le contenu serveur doit être accessible via pull.
        """
        client, token = authenticated_client
        
        # 1. Créer une note sur le serveur avec un contenu spécifique
        server_content = "Contenu serveur original"
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note-preserve.md",
                        "content": server_content,
                        "content_hash": "hash_serveur_123",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # 2. Simuler un conflit (client modifie aussi)
        sync_response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "note-preserve.md",
                        "content_hash": "hash_client_different",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert sync_response.status_code == 200
        sync_data = sync_response.json()
        assert len(sync_data["conflicts"]) == 1
        
        # 3. Puller la version serveur pour vérifier qu'elle est préservée
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={
                "paths": ["note-preserve.md"]
            }
        )
        
        assert pull_response.status_code == 200
        pull_data = pull_response.json()
        
        # Le contenu serveur doit être accessible
        assert len(pull_data["notes"]) == 1
        assert pull_data["notes"][0]["path"] == "note-preserve.md"
        assert pull_data["notes"][0]["content"] == server_content
        # Le serveur recalcule le hash SHA256, donc on vérifie le vrai hash
        expected_hash = compute_hash(server_content)
        assert pull_data["notes"][0]["content_hash"] == expected_hash
    
    @pytest.mark.asyncio
    async def test_multiple_conflicts_all_returned(self, authenticated_client):
        """
        Si plusieurs fichiers sont en conflit, tous doivent être retournés.
        """
        client, token = authenticated_client
        
        # 1. Créer plusieurs notes sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflit1.md",
                        "content": "Serveur 1",
                        "content_hash": "hash_s1",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "conflit2.md",
                        "content": "Serveur 2",
                        "content_hash": "hash_s2",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "conflit3.md",
                        "content": "Serveur 3",
                        "content_hash": "hash_s3",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # 2. Simuler des modifications côté client (conflits)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "conflit1.md",
                        "content_hash": "hash_c1",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "conflit2.md",
                        "content_hash": "hash_c2",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "conflit3.md",
                        "content_hash": "hash_c3",
                        "modified_at": "2026-01-19T10:00:00",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Tous les conflits doivent être détectés
        assert len(data["conflicts"]) == 3
        paths = [c["path"] for c in data["conflicts"]]
        assert "conflit1.md" in paths
        assert "conflit2.md" in paths
        assert "conflit3.md" in paths
