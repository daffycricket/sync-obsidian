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


class TestReferencedAttachments:
    """Tests des attachments référencés dans les notes."""

    @pytest.mark.asyncio
    async def test_note_with_no_attachments(self, authenticated_client):
        """Note sans références d'attachments."""
        client, token = authenticated_client

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "simple.md",
                        "content": "# Simple note\n\nNo attachments here.",
                        "content_hash": "h1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]
        assert note["referenced_attachments"] == []

    @pytest.mark.asyncio
    async def test_note_with_missing_attachments(self, authenticated_client):
        """Note avec références d'attachments non existants sur le serveur."""
        client, token = authenticated_client

        content = """# Note avec images

![[screenshot.png]]
![[diagram.pdf]]
![[video.mp4]]
"""

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "with-attachments.md",
                        "content": content,
                        "content_hash": "h1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]

        # Vérifier les références
        assert len(note["referenced_attachments"]) == 3

        paths = [att["path"] for att in note["referenced_attachments"]]
        assert "screenshot.png" in paths
        assert "diagram.pdf" in paths
        assert "video.mp4" in paths

        # Tous devraient être marqués comme non existants
        for att in note["referenced_attachments"]:
            assert att["exists"] is False
            assert att["size_bytes"] is None

    @pytest.mark.asyncio
    async def test_note_with_existing_attachments(self, authenticated_client_with_db):
        """Note avec références d'attachments existants sur le serveur."""
        client, token, db_session, user_id = authenticated_client_with_db
        from app.models import Attachment
        from datetime import datetime

        # Créer des attachments dans la base de données
        attachments_data = [
            {"path": "images/photo.png", "content_hash": "hash1", "size": 1024, "mime_type": "image/png"},
            {"path": "docs/manual.pdf", "content_hash": "hash2", "size": 2048, "mime_type": "application/pdf"},
            {"path": "assets/logo.svg", "content_hash": "hash3", "size": 512, "mime_type": "image/svg+xml"},
        ]

        for att_data in attachments_data:
            attachment = Attachment(
                user_id=user_id,
                path=att_data["path"],
                content_hash=att_data["content_hash"],
                size=att_data["size"],
                mime_type=att_data["mime_type"],
                modified_at=datetime.utcnow(),
                is_deleted=False
            )
            db_session.add(attachment)
        await db_session.commit()

        # Créer une note qui référence ces attachments
        content = """# Documentation

![[images/photo.png]]
![[docs/manual.pdf]]
![[assets/logo.svg]]
![[missing-file.jpg]]
"""

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "doc.md",
                        "content": content,
                        "content_hash": "dochash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]

        assert len(note["referenced_attachments"]) == 4

        # Vérifier les attachments existants
        att_map = {att["path"]: att for att in note["referenced_attachments"]}

        assert att_map["images/photo.png"]["exists"] is True
        assert att_map["images/photo.png"]["size_bytes"] == 1024

        assert att_map["docs/manual.pdf"]["exists"] is True
        assert att_map["docs/manual.pdf"]["size_bytes"] == 2048

        assert att_map["assets/logo.svg"]["exists"] is True
        assert att_map["assets/logo.svg"]["size_bytes"] == 512

        # L'attachment manquant
        assert att_map["missing-file.jpg"]["exists"] is False
        assert att_map["missing-file.jpg"]["size_bytes"] is None

    @pytest.mark.asyncio
    async def test_note_with_aliased_attachments(self, authenticated_client):
        """Note avec références d'attachments avec alias (ex: ![[file|alias]])."""
        client, token = authenticated_client

        content = """# Note avec alias

![[architecture-diagram.png|Diagramme d'architecture]]
![[roadmap.pdf|Planning 2026]]
"""

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "aliased.md",
                        "content": content,
                        "content_hash": "h1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]

        paths = [att["path"] for att in note["referenced_attachments"]]
        assert "architecture-diagram.png" in paths
        assert "roadmap.pdf" in paths
        # L'alias ne doit pas être inclus dans le path
        assert all("|" not in p for p in paths)

    @pytest.mark.asyncio
    async def test_note_ignores_markdown_links(self, authenticated_client):
        """Les liens vers d'autres notes .md ne sont pas comptés comme attachments."""
        client, token = authenticated_client

        content = """# Note avec liens

![[other-note.md]]
[[reference.md|Voir aussi]]
![[image.png]]
"""

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "links.md",
                        "content": content,
                        "content_hash": "h1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]

        # Seul image.png doit être référencé, pas les .md
        assert len(note["referenced_attachments"]) == 1
        assert note["referenced_attachments"][0]["path"] == "image.png"

    @pytest.mark.asyncio
    async def test_note_deduplicates_attachments(self, authenticated_client):
        """Les références en double sont dédupliquées."""
        client, token = authenticated_client

        content = """# Note avec doublons

![[image.png]]
Texte entre les deux.
![[image.png]]
Et encore: ![[image.png]]
"""

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "duplicates.md",
                        "content": content,
                        "content_hash": "h1",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]

        # Une seule référence malgré les doublons
        assert len(note["referenced_attachments"]) == 1
        assert note["referenced_attachments"][0]["path"] == "image.png"

    @pytest.mark.asyncio
    async def test_various_attachment_types(self, authenticated_client_with_db):
        """Test avec différents types d'attachments (images, PDF, audio, vidéo)."""
        client, token, db_session, user_id = authenticated_client_with_db
        from app.models import Attachment
        from datetime import datetime

        # Créer des attachments de différents types
        attachments_data = [
            {"path": "image.png", "content_hash": "h1", "size": 1024, "mime_type": "image/png"},
            {"path": "image.jpg", "content_hash": "h2", "size": 2048, "mime_type": "image/jpeg"},
            {"path": "image.gif", "content_hash": "h3", "size": 512, "mime_type": "image/gif"},
            {"path": "image.webp", "content_hash": "h4", "size": 768, "mime_type": "image/webp"},
            {"path": "vector.svg", "content_hash": "h5", "size": 256, "mime_type": "image/svg+xml"},
            {"path": "document.pdf", "content_hash": "h6", "size": 4096, "mime_type": "application/pdf"},
            {"path": "audio.mp3", "content_hash": "h7", "size": 8192, "mime_type": "audio/mpeg"},
            {"path": "video.mp4", "content_hash": "h8", "size": 16384, "mime_type": "video/mp4"},
            {"path": "archive.zip", "content_hash": "h9", "size": 32768, "mime_type": "application/zip"},
        ]

        for att_data in attachments_data:
            attachment = Attachment(
                user_id=user_id,
                path=att_data["path"],
                content_hash=att_data["content_hash"],
                size=att_data["size"],
                mime_type=att_data["mime_type"],
                modified_at=datetime.utcnow(),
                is_deleted=False
            )
            db_session.add(attachment)
        await db_session.commit()

        # Créer une note qui référence tous ces attachments
        content = """# Multi-media note

## Images
![[image.png]]
![[image.jpg]]
![[image.gif]]
![[image.webp]]
![[vector.svg]]

## Documents
![[document.pdf]]

## Media
![[audio.mp3]]
![[video.mp4]]

## Archives
![[archive.zip]]
"""

        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "multimedia.md",
                        "content": content,
                        "content_hash": "mmhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )

        response = await client.get(
            "/sync/notes",
            headers=auth_headers(token)
        )

        assert response.status_code == 200
        data = response.json()
        note = data["notes"][0]

        # Tous les attachments doivent être référencés
        assert len(note["referenced_attachments"]) == 9

        # Tous doivent exister avec leur taille
        for att in note["referenced_attachments"]:
            assert att["exists"] is True
            assert att["size_bytes"] is not None
            assert att["size_bytes"] > 0


class TestSyncViewerPage:
    """Tests de la page sync-viewer."""

    @pytest.mark.asyncio
    async def test_sync_viewer_page_exists(self, client: AsyncClient):
        """La page sync-viewer doit être accessible."""
        response = await client.get("/sync-viewer")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "SyncObsidian" in response.text
