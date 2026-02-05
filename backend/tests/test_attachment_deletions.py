"""
Tests d'intégration pour la synchronisation des suppressions de pièces jointes (attachments).
Miroir des tests de test_sync_deletions.py mais pour les attachments.
"""
import base64
import pytest
from datetime import datetime
from httpx import AsyncClient
from .conftest import auth_headers


def create_attachment_base64(content: bytes = b"test content") -> str:
    """Helper pour créer le contenu base64 d'un attachment."""
    return base64.b64encode(content).decode("utf-8")


class TestAttachmentDeletionPropagation:
    """Tests de propagation des suppressions d'attachments entre devices."""

    @pytest.mark.asyncio
    async def test_delete_local_attachment_syncs_to_server(self, authenticated_client):
        """
        Test 1: Suppression locale propagée au serveur.
        1. Créer et sync un attachment
        2. Envoyer l'attachment avec is_deleted=true
        3. Vérifier que le serveur le marque comme supprimé
        """
        client, token = authenticated_client
        content = b"image data here"
        content_base64 = create_attachment_base64(content)

        # 1. Créer un attachment sur le serveur
        push_resp = await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "images/photo.png",
                        "content_base64": content_base64,
                        "content_hash": "originalhash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        assert push_resp.status_code == 200
        assert "images/photo.png" in push_resp.json()["success"]

        # 2. Supprimer l'attachment (envoyer avec is_deleted=true)
        delete_resp = await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "images/photo.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        assert delete_resp.status_code == 200
        assert "images/photo.png" in delete_resp.json()["success"]

        # 3. Vérifier que le pull retourne is_deleted=true
        pull_resp = await client.post(
            "/sync/attachments/pull",
            headers=auth_headers(token),
            json={"paths": ["images/photo.png"]}
        )
        assert pull_resp.status_code == 200
        attachments = pull_resp.json()["attachments"]
        assert len(attachments) == 1
        assert attachments[0]["path"] == "images/photo.png"
        assert attachments[0]["is_deleted"] == True
        assert attachments[0]["content_base64"] == ""

    @pytest.mark.asyncio
    async def test_deleted_attachment_not_resurrected(self, authenticated_client):
        """
        Test 2: Attachment supprimé n'est pas ressuscité.
        1. Créer et supprimer un attachment
        2. Sync sans mentionner l'attachment
        3. L'attachment ne doit pas réapparaître dans attachments_to_pull
        """
        client, token = authenticated_client
        content = b"ghost image"
        content_base64 = create_attachment_base64(content)

        # 1. Créer un attachment
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "ghost.png",
                        "content_base64": content_base64,
                        "content_hash": "ghosthash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # 2. Supprimer l'attachment
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "ghost.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )

        # 3. Sync sans mentionner l'attachment - il ne doit PAS réapparaître
        sync_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-01T00:00:00",
                "notes": [],
                "attachments": []  # Client ne mentionne pas ghost.png
            }
        )

        assert sync_resp.status_code == 200
        data = sync_resp.json()

        # Vérifier que ghost.png n'est PAS dans attachments_to_pull
        pulled_paths = [a["path"] for a in data["attachments_to_pull"]]
        assert "ghost.png" not in pulled_paths

    @pytest.mark.asyncio
    async def test_deletion_propagates_to_other_device(self, authenticated_client):
        """
        Test 3: Suppression propagée aux autres devices.
        Simule Device A qui supprime, Device B qui sync.
        """
        client, token = authenticated_client
        content = b"shared image"
        content_base64 = create_attachment_base64(content)

        # Device A crée l'attachment
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "shared.png",
                        "content_base64": content_base64,
                        "content_hash": "sharedhash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Device B sync pour avoir l'attachment (simule un premier sync)
        sync_b1 = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )
        assert "shared.png" in [a["path"] for a in sync_b1.json()["attachments_to_pull"]]

        # Device A supprime l'attachment
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "shared.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )

        # Device B sync avec l'attachment (comme s'il l'avait encore)
        sync_b2 = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-11T10:30:00",  # Après premier sync
                "notes": [],
                "attachments": [
                    {
                        "path": "shared.png",
                        "content_hash": "sharedhash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        assert sync_b2.status_code == 200
        data = sync_b2.json()

        # Device B doit recevoir l'info de suppression
        pulled = [a for a in data["attachments_to_pull"] if a["path"] == "shared.png"]
        assert len(pulled) == 1
        assert pulled[0]["is_deleted"] == True


class TestAttachmentDeletionConflicts:
    """Tests de conflits liés aux suppressions d'attachments."""

    @pytest.mark.asyncio
    async def test_client_deletes_server_modified_attachment(self, authenticated_client):
        """
        Si client supprime mais serveur a modifié après, le serveur gagne.
        (Les attachments n'ont pas de conflit, on re-propose la version serveur)
        """
        client, token = authenticated_client
        content_v1 = b"version 1"
        content_v2 = b"version 2 modified"

        # Créer l'attachment initial
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "conflict.png",
                        "content_base64": create_attachment_base64(content_v1),
                        "content_hash": "v1hash",
                        "size": len(content_v1),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Simuler: serveur reçoit une mise à jour (via un autre device)
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "conflict.png",
                        "content_base64": create_attachment_base64(content_v2),
                        "content_hash": "v2hash",
                        "size": len(content_v2),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T12:00:00",  # Plus récent
                        "is_deleted": False
                    }
                ]
            }
        )

        # Client essaie de supprimer avec un timestamp plus ancien
        sync_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-11T09:00:00",
                "notes": [],
                "attachments": [
                    {
                        "path": "conflict.png",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T11:00:00",  # Avant la modif serveur
                        "is_deleted": True
                    }
                ]
            }
        )

        assert sync_resp.status_code == 200
        data = sync_resp.json()

        # Le serveur doit re-proposer l'attachment (pas de suppression)
        pulled = [a for a in data["attachments_to_pull"] if a["path"] == "conflict.png"]
        assert len(pulled) == 1
        assert pulled[0]["is_deleted"] == False

    @pytest.mark.asyncio
    async def test_client_modify_after_server_delete(self, authenticated_client):
        """
        Si client modifie après que serveur ait supprimé, client peut recréer.
        """
        client, token = authenticated_client
        content = b"original content"

        # Créer l'attachment
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "phoenix.png",
                        "content_base64": create_attachment_base64(content),
                        "content_hash": "originalhash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Serveur supprime
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "phoenix.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T11:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )

        # Client sync avec une version modifiée APRÈS la suppression
        new_content = b"new content after delete"
        sync_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-11T10:30:00",
                "notes": [],
                "attachments": [
                    {
                        "path": "phoenix.png",
                        "content_hash": "newhash",
                        "size": len(new_content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T12:00:00",  # Après la suppression
                        "is_deleted": False
                    }
                ]
            }
        )

        assert sync_resp.status_code == 200
        data = sync_resp.json()

        # Client peut recréer l'attachment (car plus récent)
        assert "phoenix.png" in data["attachments_to_push"]

    @pytest.mark.asyncio
    async def test_server_delete_wins_over_older_client(self, authenticated_client):
        """
        Si serveur supprime et client a une version plus ancienne, suppression propagée.
        """
        client, token = authenticated_client
        content = b"some content"

        # Créer l'attachment
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "deleted.png",
                        "content_base64": create_attachment_base64(content),
                        "content_hash": "originalhash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Serveur supprime
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "deleted.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )

        # Client sync avec l'ancienne version
        sync_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-11T10:30:00",
                "notes": [],
                "attachments": [
                    {
                        "path": "deleted.png",
                        "content_hash": "originalhash",
                        "size": len(content),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",  # Plus ancien
                        "is_deleted": False
                    }
                ]
            }
        )

        assert sync_resp.status_code == 200
        data = sync_resp.json()

        # Client doit recevoir la suppression
        pulled = [a for a in data["attachments_to_pull"] if a["path"] == "deleted.png"]
        assert len(pulled) == 1
        assert pulled[0]["is_deleted"] == True


class TestAttachmentDeleteAndRecreate:
    """Tests de suppression puis re-création d'attachments."""

    @pytest.mark.asyncio
    async def test_delete_then_recreate(self, authenticated_client):
        """Supprimer puis re-créer un attachment fonctionne."""
        client, token = authenticated_client
        content_v1 = b"version 1"
        content_v2 = b"version 2 resurrected"

        # Créer
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "phoenix.png",
                        "content_base64": create_attachment_base64(content_v1),
                        "content_hash": "v1hash",
                        "size": len(content_v1),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Supprimer
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "phoenix.png",
                        "content_base64": "",
                        "content_hash": "",
                        "size": 0,
                        "mime_type": None,
                        "modified_at": "2026-01-11T11:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )

        # Re-créer avec nouveau contenu
        recreate_resp = await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "phoenix.png",
                        "content_base64": create_attachment_base64(content_v2),
                        "content_hash": "v2hash",
                        "size": len(content_v2),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T12:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        assert recreate_resp.status_code == 200
        assert "phoenix.png" in recreate_resp.json()["success"]

        # Vérifier le contenu
        pull_resp = await client.post(
            "/sync/attachments/pull",
            headers=auth_headers(token),
            json={"paths": ["phoenix.png"]}
        )
        assert pull_resp.status_code == 200
        attachments = pull_resp.json()["attachments"]
        assert len(attachments) == 1
        assert attachments[0]["is_deleted"] == False
        assert attachments[0]["content_base64"] == create_attachment_base64(content_v2)


class TestFirstSyncNoFalseAttachmentDeletions:
    """Tests pour éviter les fausses suppressions lors du premier sync."""

    @pytest.mark.asyncio
    async def test_first_sync_existing_server_attachments(self, authenticated_client):
        """
        Premier sync d'un nouveau device ne doit pas créer de fausses suppressions.
        Le serveur a des attachments, le client fait son premier sync sans rien.
        """
        client, token = authenticated_client
        content1 = b"image 1"
        content2 = b"image 2"

        # Créer des attachments sur le serveur (via un autre "device")
        await client.post(
            "/sync/attachments/push",
            headers=auth_headers(token),
            json={
                "attachments": [
                    {
                        "path": "existing1.png",
                        "content_base64": create_attachment_base64(content1),
                        "content_hash": "e1hash",
                        "size": len(content1),
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    },
                    {
                        "path": "existing2.jpg",
                        "content_base64": create_attachment_base64(content2),
                        "content_hash": "e2hash",
                        "size": len(content2),
                        "mime_type": "image/jpeg",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        # Nouveau device fait son premier sync (last_sync=null, attachments=[])
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

        # Les attachments serveur doivent être proposés au pull, pas supprimés
        pulled_paths = [a["path"] for a in data["attachments_to_pull"]]
        assert "existing1.png" in pulled_paths
        assert "existing2.jpg" in pulled_paths

        # Pas d'attachments à push (le client n'a rien)
        assert data["attachments_to_push"] == []
