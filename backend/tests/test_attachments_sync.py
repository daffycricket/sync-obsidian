"""
Tests d'intégration pour la synchronisation des pièces jointes (attachments).
"""
import pytest
import base64
from httpx import AsyncClient
from .conftest import auth_headers


class TestAttachmentsSync:
    """Tests de synchronisation des attachments."""

    @pytest.mark.asyncio
    async def test_push_attachment_success(self, authenticated_client):
        """
        Un client peut envoyer un attachment au serveur.
        """
        client, token = authenticated_client

        # Créer un contenu binaire de test (image PNG factice)
        content = b"\x89PNG\r\n\x1a\n" + b"fake image content for testing"
        content_base64 = base64.b64encode(content).decode("utf-8")

        response = await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "attachments/test-image.png",
                        "content_base64": content_base64,
                        "content_hash": "abc123",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "attachments/test-image.png" in data["success"]
        assert len(data["failed"]) == 0

    @pytest.mark.asyncio
    async def test_push_attachment_too_large(self, authenticated_client):
        """
        Un attachment > 25 Mo est rejeté.
        On simule en envoyant un petit fichier mais avec size > 25 Mo.
        """
        client, token = authenticated_client

        # Petit contenu mais on déclare une taille de 26 Mo
        content = b"small content"
        content_base64 = base64.b64encode(content).decode("utf-8")
        fake_size = 26 * 1024 * 1024  # 26 Mo déclaré

        response = await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "attachments/huge-file.bin",
                        "content_base64": content_base64,
                        "content_hash": "toobig",
                        "size": fake_size,  # Taille déclarée > 25 Mo
                        "mime_type": "application/octet-stream",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "attachments/huge-file.bin" in data["failed"]
        assert len(data["success"]) == 0

    @pytest.mark.asyncio
    async def test_pull_attachment_success(self, authenticated_client):
        """
        Un client peut récupérer un attachment depuis le serveur.
        """
        client, token = authenticated_client

        # D'abord, pusher un attachment
        content = b"PDF content here"
        content_base64 = base64.b64encode(content).decode("utf-8")

        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "docs/document.pdf",
                        "content_base64": content_base64,
                        "content_hash": "pdfhash123",
                        "size": len(content),
                        "mime_type": "application/pdf",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Puis le récupérer
        response = await client.post(
            "/sync/attachments/pull",
            headers=auth_headers(token),
            json={
                "paths": ["docs/document.pdf"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["attachments"]) == 1

        att = data["attachments"][0]
        assert att["path"] == "docs/document.pdf"
        assert att["content_base64"] == content_base64
        assert att["size"] == len(content)

    @pytest.mark.asyncio
    async def test_pull_attachment_not_found(self, authenticated_client):
        """
        Un attachment inexistant n'est pas retourné (pas d'erreur, juste absent).
        """
        client, token = authenticated_client

        response = await client.post(
            "/sync/attachments/pull",
            headers=auth_headers(token),
            json={
                "paths": ["nonexistent/file.png"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["attachments"]) == 0

    @pytest.mark.asyncio
    async def test_sync_detects_missing_attachments(self, authenticated_client):
        """
        L'endpoint /sync détecte les attachments que le client n'a pas.

        Scénario:
        1. Serveur a un attachment
        2. Client sync sans mentionner cet attachment
        3. Serveur doit le proposer dans attachments_to_pull
        """
        client, token = authenticated_client

        # Pusher un attachment sur le serveur
        content = b"image data"
        content_base64 = base64.b64encode(content).decode("utf-8")

        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "images/photo.jpg",
                        "content_base64": content_base64,
                        "content_hash": "imagehash",
                        "size": len(content),
                        "mime_type": "image/jpeg",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Sync sans mentionner l'attachment
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []  # Client n'a pas l'attachment
            }
        )

        assert response.status_code == 200
        data = response.json()

        # L'attachment doit être proposé au pull
        att_paths = [a["path"] for a in data["attachments_to_pull"]]
        assert "images/photo.jpg" in att_paths

    @pytest.mark.asyncio
    async def test_sync_detects_attachments_to_push(self, authenticated_client):
        """
        L'endpoint /sync détecte les attachments que le serveur n'a pas.

        Scénario:
        1. Client mentionne un attachment
        2. Serveur ne l'a pas
        3. Serveur doit le demander dans attachments_to_push
        """
        client, token = authenticated_client

        # Sync avec un attachment que le serveur n'a pas
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": [
                    {
                        "path": "new-image.png",
                        "content_hash": "newhash",
                        "size": 1000,
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Le serveur doit demander l'attachment
        assert "new-image.png" in data["attachments_to_push"]

    @pytest.mark.asyncio
    async def test_sync_same_hash_no_transfer(self, authenticated_client):
        """
        Si client et serveur ont le même hash, pas de transfert.
        """
        client, token = authenticated_client

        # Pusher un attachment
        content = b"same content"
        content_base64 = base64.b64encode(content).decode("utf-8")
        import hashlib
        content_hash = hashlib.sha256(content).hexdigest()

        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "same-file.txt",
                        "content_base64": content_base64,
                        "content_hash": content_hash,
                        "size": len(content),
                        "mime_type": "text/plain",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Sync avec le même attachment (même hash)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": [
                    {
                        "path": "same-file.txt",
                        "content_hash": content_hash,
                        "size": len(content),
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Ni push ni pull car même hash
        assert "same-file.txt" not in data["attachments_to_push"]
        att_paths = [a["path"] for a in data["attachments_to_pull"]]
        assert "same-file.txt" not in att_paths

    @pytest.mark.asyncio
    async def test_delete_attachment_propagation(self, authenticated_client):
        """
        La suppression d'un attachment est propagée.
        """
        client, token = authenticated_client

        # Pusher un attachment
        content = b"to be deleted"
        content_base64 = base64.b64encode(content).decode("utf-8")

        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "temp/delete-me.png",
                        "content_base64": content_base64,
                        "content_hash": "deletehash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Supprimer l'attachment (is_deleted=True)
        response = await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "temp/delete-me.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-29T11:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )

        assert response.status_code == 200

        # Vérifier que l'attachment est supprimé (pull ne retourne rien)
        pull_response = await client.post(
            "/sync/attachments/pull",
            headers=auth_headers(token),
            json={
                "paths": ["temp/delete-me.png"]
            }
        )

        data = pull_response.json()
        # Soit l'attachment n'est plus retourné, soit il est marqué is_deleted
        if len(data["attachments"]) > 0:
            assert data["attachments"][0]["is_deleted"] == True

    @pytest.mark.asyncio
    async def test_multidevice_attachment_sync(self, authenticated_client):
        """
        Scénario multi-device complet:
        1. Device A push un attachment
        2. Device B sync et reçoit l'attachment dans attachments_to_pull
        3. Device B pull l'attachment
        4. Device B sync à nouveau - plus de transfert nécessaire
        """
        client, token = authenticated_client

        # Device A push un attachment
        content = b"shared attachment content"
        content_base64 = base64.b64encode(content).decode("utf-8")
        import hashlib
        content_hash = hashlib.sha256(content).hexdigest()

        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "shared/file.zip",
                        "content_base64": content_base64,
                        "content_hash": content_hash,
                        "size": len(content),
                        "mime_type": "application/zip",
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Device B sync sans connaître l'attachment
        sync_response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )

        data = sync_response.json()
        att_to_pull = [a["path"] for a in data["attachments_to_pull"]]
        assert "shared/file.zip" in att_to_pull

        # Device B pull l'attachment
        pull_response = await client.post(
            "/sync/attachments/pull",
            headers=auth_headers(token),
            json={
                "paths": ["shared/file.zip"]
            }
        )

        pull_data = pull_response.json()
        assert len(pull_data["attachments"]) == 1
        assert pull_data["attachments"][0]["content_base64"] == content_base64

        # Device B sync à nouveau avec l'attachment maintenant connu
        sync_response2 = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": data["server_time"],
                "notes": [],
                "attachments": [
                    {
                        "path": "shared/file.zip",
                        "content_hash": content_hash,
                        "size": len(content),
                        "modified_at": "2026-01-29T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        data2 = sync_response2.json()
        # Plus de transfert nécessaire
        assert "shared/file.zip" not in data2["attachments_to_push"]
        att_to_pull2 = [a["path"] for a in data2["attachments_to_pull"]]
        assert "shared/file.zip" not in att_to_pull2
