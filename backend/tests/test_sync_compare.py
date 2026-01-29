"""
Tests d'intégration pour l'endpoint POST /sync/compare (comparaison client/serveur).
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestSyncCompareEndpoint:
    """Tests du endpoint POST /sync/compare."""

    @pytest.mark.asyncio
    async def test_compare_empty_client_empty_server(self, authenticated_client):
        """Comparaison avec client et serveur vides."""
        client, token = authenticated_client

        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={"notes": []}
        )

        assert response.status_code == 200
        data = response.json()

        assert "server_time" in data
        assert data["summary"]["total_client"] == 0
        assert data["summary"]["total_server"] == 0
        assert data["summary"]["to_push"] == 0
        assert data["summary"]["to_pull"] == 0
        assert data["summary"]["conflicts"] == 0
        assert data["summary"]["identical"] == 0
        assert data["to_push"] == []
        assert data["to_pull"] == []
        assert data["conflicts"] == []

    @pytest.mark.asyncio
    async def test_compare_client_has_new_notes(self, authenticated_client):
        """Notes sur le client qui n'existent pas sur le serveur -> to_push."""
        client, token = authenticated_client

        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "new-note.md",
                        "content_hash": "abc123",
                        "modified_at": "2026-01-29T10:00:00"
                    },
                    {
                        "path": "another-new.md",
                        "content_hash": "def456",
                        "modified_at": "2026-01-29T11:00:00"
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["total_client"] == 2
        assert data["summary"]["total_server"] == 0
        assert data["summary"]["to_push"] == 2
        assert data["summary"]["to_pull"] == 0

        paths = [n["path"] for n in data["to_push"]]
        assert "new-note.md" in paths
        assert "another-new.md" in paths

        for note in data["to_push"]:
            assert note["reason"] == "not_on_server"

    @pytest.mark.asyncio
    async def test_compare_server_has_new_notes(self, authenticated_client):
        """Notes sur le serveur qui n'existent pas sur le client -> to_pull."""
        client, token = authenticated_client

        # Créer des notes sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "server-note1.md", "content": "content1", "content_hash": "h1", "modified_at": "2026-01-29T10:00:00", "is_deleted": False},
                    {"path": "server-note2.md", "content": "content2", "content_hash": "h2", "modified_at": "2026-01-29T11:00:00", "is_deleted": False}
                ]
            }
        )

        # Comparer avec un client vide
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={"notes": []}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["total_client"] == 0
        assert data["summary"]["total_server"] == 2
        assert data["summary"]["to_push"] == 0
        assert data["summary"]["to_pull"] == 2

        paths = [n["path"] for n in data["to_pull"]]
        assert "server-note1.md" in paths
        assert "server-note2.md" in paths

        for note in data["to_pull"]:
            assert note["reason"] == "not_on_client"

    @pytest.mark.asyncio
    async def test_compare_identical_notes(self, authenticated_client):
        """Notes identiques sur client et serveur -> identical."""
        client, token = authenticated_client

        # Créer une note sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "identical.md", "content": "same content", "content_hash": "samehash", "modified_at": "2026-01-29T10:00:00", "is_deleted": False}
                ]
            }
        )

        # Récupérer le hash réel calculé par le serveur
        notes_response = await client.get("/sync/notes", headers=auth_headers(token))
        server_hash = notes_response.json()["notes"][0]["content_hash"]

        # Comparer avec le même hash
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "identical.md",
                        "content_hash": server_hash,
                        "modified_at": "2026-01-29T10:00:00"
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["identical"] == 1
        assert data["summary"]["to_push"] == 0
        assert data["summary"]["to_pull"] == 0
        assert data["summary"]["conflicts"] == 0

    @pytest.mark.asyncio
    async def test_compare_client_newer(self, authenticated_client):
        """Client a une version plus récente -> to_push."""
        client, token = authenticated_client

        # Créer une note sur le serveur (ancienne)
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "note.md", "content": "old content", "content_hash": "oldhash", "modified_at": "2026-01-28T10:00:00", "is_deleted": False}
                ]
            }
        )

        # Comparer avec une version plus récente côté client
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note.md",
                        "content_hash": "newhash",
                        "modified_at": "2026-01-29T10:00:00"  # Plus récent
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["to_push"] == 1
        assert data["to_push"][0]["path"] == "note.md"
        assert data["to_push"][0]["reason"] == "client_newer"

    @pytest.mark.asyncio
    async def test_compare_server_newer(self, authenticated_client):
        """Serveur a une version plus récente -> to_pull."""
        client, token = authenticated_client

        # Créer une note sur le serveur (récente)
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "note.md", "content": "new content", "content_hash": "newhash", "modified_at": "2026-01-29T15:00:00", "is_deleted": False}
                ]
            }
        )

        # Comparer avec une version plus ancienne côté client
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note.md",
                        "content_hash": "oldhash",
                        "modified_at": "2026-01-28T10:00:00"  # Plus ancien
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["to_pull"] == 1
        assert data["to_pull"][0]["path"] == "note.md"
        assert data["to_pull"][0]["reason"] == "server_newer"

    @pytest.mark.asyncio
    async def test_compare_conflict(self, authenticated_client):
        """Même timestamp mais hash différent -> conflict."""
        client, token = authenticated_client

        # Créer une note sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "conflict.md", "content": "server version", "content_hash": "serverhash", "modified_at": "2026-01-29T10:00:00", "is_deleted": False}
                ]
            }
        )

        # Comparer avec même timestamp mais hash différent
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "conflict.md",
                        "content_hash": "clienthash",  # Hash différent
                        "modified_at": "2026-01-29T10:00:00"  # Même timestamp
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["conflicts"] == 1
        assert data["conflicts"][0]["path"] == "conflict.md"
        assert data["conflicts"][0]["reason"] == "both_modified"
        assert data["conflicts"][0]["client_hash"] == "clienthash"

    @pytest.mark.asyncio
    async def test_compare_deleted_on_server(self, authenticated_client):
        """Note supprimée sur le serveur -> deleted_on_server."""
        client, token = authenticated_client

        # Créer puis supprimer une note sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "deleted.md", "content": "content", "content_hash": "h1", "modified_at": "2026-01-28T10:00:00", "is_deleted": False}
                ]
            }
        )

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "deleted.md", "content": "", "content_hash": "", "modified_at": "2026-01-29T10:00:00", "is_deleted": True}
                ]
            }
        )

        # Comparer - le client a encore la note
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "deleted.md",
                        "content_hash": "h1",
                        "modified_at": "2026-01-28T10:00:00"
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["deleted_on_server"] == 1
        assert data["deleted_on_server"][0]["path"] == "deleted.md"

    @pytest.mark.asyncio
    async def test_compare_mixed_scenario(self, authenticated_client):
        """Scénario mixte avec plusieurs types de différences."""
        client, token = authenticated_client

        # Créer des notes sur le serveur
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "server-only.md", "content": "server", "content_hash": "h1", "modified_at": "2026-01-29T10:00:00", "is_deleted": False},
                    {"path": "identical.md", "content": "same", "content_hash": "h2", "modified_at": "2026-01-29T10:00:00", "is_deleted": False},
                    {"path": "server-newer.md", "content": "updated", "content_hash": "h3", "modified_at": "2026-01-29T15:00:00", "is_deleted": False},
                ]
            }
        )

        # Récupérer les hash réels
        notes_response = await client.get("/sync/notes", headers=auth_headers(token))
        notes = {n["path"]: n for n in notes_response.json()["notes"]}

        # Comparer avec un mix de situations
        response = await client.post(
            "/sync/compare",
            headers=auth_headers(token),
            json={
                "notes": [
                    {"path": "client-only.md", "content_hash": "client", "modified_at": "2026-01-29T10:00:00"},
                    {"path": "identical.md", "content_hash": notes["identical.md"]["content_hash"], "modified_at": "2026-01-29T10:00:00"},
                    {"path": "server-newer.md", "content_hash": "old", "modified_at": "2026-01-28T10:00:00"},
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["summary"]["total_client"] == 3
        assert data["summary"]["total_server"] == 3
        assert data["summary"]["to_push"] == 1  # client-only
        assert data["summary"]["to_pull"] == 2  # server-only + server-newer
        assert data["summary"]["identical"] == 1

    @pytest.mark.asyncio
    async def test_compare_unauthenticated(self, client: AsyncClient):
        """POST /sync/compare sans authentification doit échouer."""
        response = await client.post(
            "/sync/compare",
            json={"notes": []}
        )
        assert response.status_code in [401, 403]
