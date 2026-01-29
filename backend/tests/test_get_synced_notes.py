"""
Tests d'intégration pour l'endpoint GET /sync/notes (visualisation des notes synchronisées).
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestGetSyncedNotesEndpoint:
    """Tests du endpoint GET /sync/notes."""

    @pytest.mark.asyncio
    async def test_get_notes_empty(self, authenticated_client):
        """GET /sync/notes sans notes doit retourner une liste vide."""
        client, token = authenticated_client

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 50
        assert data["total_pages"] == 1
        assert data["notes"] == []
        assert data["attachments"] == []

    @pytest.mark.asyncio
    async def test_get_notes_with_data(self, authenticated_client):
        """GET /sync/notes avec des notes doit les retourner."""
        client, token = authenticated_client

        # Créer quelques notes
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note1.md",
                        "content": "# Note 1\nContenu de la note 1",
                        "content_hash": "hash1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "folder/note2.md",
                        "content": "# Note 2\nContenu de la note 2",
                        "content_hash": "hash2",
                        "modified_at": "2026-01-11T11:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Récupérer les notes
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["notes"]) == 2

        # Vérifier les champs de chaque note
        paths = [n["path"] for n in data["notes"]]
        assert "note1.md" in paths
        assert "folder/note2.md" in paths

        # Vérifier la structure d'une note
        note = next(n for n in data["notes"] if n["path"] == "note1.md")
        assert "content_hash" in note
        assert "modified_at" in note
        assert "synced_at" in note
        assert note["is_deleted"] is False
        assert "size_bytes" in note
        assert note["size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_get_notes_unauthenticated(self, client: AsyncClient):
        """GET /sync/notes sans authentification doit échouer."""
        response = await client.get("/sync/notes")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_notes_pagination(self, authenticated_client):
        """GET /sync/notes avec pagination."""
        client, token = authenticated_client

        # Créer 5 notes
        notes = [
            {
                "path": f"note{i}.md",
                "content": f"# Note {i}",
                "content_hash": f"hash{i}",
                "modified_at": "2026-01-11T10:00:00",
                "is_deleted": False
            }
            for i in range(5)
        ]

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={"notes": notes}
        )

        # Récupérer page 1 avec page_size=2
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"page": 1, "page_size": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3
        assert len(data["notes"]) == 2

        # Récupérer page 2
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"page": 2, "page_size": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["notes"]) == 2

        # Récupérer page 3 (dernière, partielle)
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"page": 3, "page_size": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3
        assert len(data["notes"]) == 1

    @pytest.mark.asyncio
    async def test_get_notes_path_filter(self, authenticated_client):
        """GET /sync/notes avec filtre par chemin."""
        client, token = authenticated_client

        # Créer des notes dans différents dossiers
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "root.md", "content": "root", "content_hash": "h1", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                    {"path": "folder/note1.md", "content": "f1", "content_hash": "h2", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                    {"path": "folder/note2.md", "content": "f2", "content_hash": "h3", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                    {"path": "other/note3.md", "content": "o1", "content_hash": "h4", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                ]
            }
        )

        # Filtrer par "folder/"
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"path_filter": "folder/"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["notes"]) == 2
        paths = [n["path"] for n in data["notes"]]
        assert "folder/note1.md" in paths
        assert "folder/note2.md" in paths
        assert "root.md" not in paths
        assert "other/note3.md" not in paths

    @pytest.mark.asyncio
    async def test_get_notes_include_deleted(self, authenticated_client):
        """GET /sync/notes avec include_deleted."""
        client, token = authenticated_client

        # Créer une note puis la supprimer
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "active.md", "content": "active", "content_hash": "h1", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                    {"path": "deleted.md", "content": "to delete", "content_hash": "h2", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                ]
            }
        )

        # Supprimer une note
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "deleted.md", "content": "", "content_hash": "", "modified_at": "2026-01-11T12:00:00", "is_deleted": True},
                ]
            }
        )

        # Sans include_deleted (par défaut)
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["notes"][0]["path"] == "active.md"

        # Avec include_deleted=true
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"include_deleted": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        paths = [n["path"] for n in data["notes"]]
        assert "active.md" in paths
        assert "deleted.md" in paths

        # Vérifier le flag is_deleted
        deleted_note = next(n for n in data["notes"] if n["path"] == "deleted.md")
        assert deleted_note["is_deleted"] is True

    @pytest.mark.asyncio
    async def test_get_notes_page_size_limits(self, authenticated_client):
        """GET /sync/notes respecte les limites de page_size."""
        client, token = authenticated_client

        # page_size trop grand
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"page_size": 300}
        )
        assert response.status_code == 422  # Validation error

        # page_size trop petit
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"page_size": 0}
        )
        assert response.status_code == 422

        # page invalide
        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token),
            params={"page": 0}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_notes_sorted_by_path(self, authenticated_client):
        """GET /sync/notes retourne les notes triées par path."""
        client, token = authenticated_client

        # Créer des notes dans un ordre non alphabétique
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "zebra.md", "content": "z", "content_hash": "hz", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                    {"path": "alpha.md", "content": "a", "content_hash": "ha", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                    {"path": "middle.md", "content": "m", "content_hash": "hm", "modified_at": "2026-01-11T10:00:00", "is_deleted": False},
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        paths = [n["path"] for n in data["notes"]]
        assert paths == ["alpha.md", "middle.md", "zebra.md"]


class TestSyncViewerPage:
    """Tests de la page sync-viewer."""

    @pytest.mark.asyncio
    async def test_sync_viewer_page_exists(self, client: AsyncClient):
        """La page sync-viewer doit être accessible."""
        response = await client.get("/sync-viewer")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "SyncObsidian" in response.text
