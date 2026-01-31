"""
Tests unitaires pour services/attachments_sync.py
"""
import pytest
import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.attachments_sync import push_attachments, pull_attachments
from app.services.sync_utils import MAX_ATTACHMENT_SIZE
from app.schemas import AttachmentContent


@pytest.fixture
def mock_db():
    """Mock de la session async SQLAlchemy."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_user():
    """Mock d'un utilisateur."""
    user = MagicMock()
    user.id = 1
    return user


class TestPushAttachments:
    """Tests pour push_attachments()"""

    @pytest.mark.asyncio
    async def test_push_new_attachment(self, mock_db, mock_user):
        """Nouvel attachment créé avec succès"""
        content = b"binary content"
        content_b64 = base64.b64encode(content).decode("utf-8")

        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=None), \
             patch('app.services.attachments_sync.storage.save_attachment', return_value='hash123'):

            attachments = [AttachmentContent(
                path="image.png",
                content_base64=content_b64,
                content_hash="hash123",
                size=len(content),
                mime_type="image/png",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_attachments(mock_db, mock_user, attachments)

            assert success == ["image.png"]
            assert failed == []
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_update_existing_attachment(self, mock_db, mock_user):
        """Attachment existant mis à jour"""
        existing = MagicMock()
        existing.content_hash = "old_hash"
        content = b"new content"
        content_b64 = base64.b64encode(content).decode("utf-8")

        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=existing), \
             patch('app.services.attachments_sync.storage.save_attachment', return_value='new_hash'):

            attachments = [AttachmentContent(
                path="image.png",
                content_base64=content_b64,
                content_hash="new_hash",
                size=len(content),
                mime_type="image/png",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_attachments(mock_db, mock_user, attachments)

            assert success == ["image.png"]
            assert existing.content_hash == "new_hash"
            mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_push_too_large_attachment(self, mock_db, mock_user):
        """Attachment trop volumineux → rejeté"""
        attachments = [AttachmentContent(
            path="huge.zip",
            content_base64="",
            content_hash="hash",
            size=MAX_ATTACHMENT_SIZE + 1,  # Trop gros
            mime_type="application/zip",
            modified_at=datetime.utcnow(),
            is_deleted=False
        )]

        success, failed = await push_attachments(mock_db, mock_user, attachments)

        assert success == []
        assert failed == ["huge.zip"]

    @pytest.mark.asyncio
    async def test_push_deleted_attachment_existing(self, mock_db, mock_user):
        """Suppression d'un attachment existant"""
        existing = MagicMock()
        existing.is_deleted = False

        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=existing), \
             patch('app.services.attachments_sync.storage.delete_attachment', return_value=None):

            attachments = [AttachmentContent(
                path="image.png",
                content_base64="",
                content_hash="",
                size=0,
                mime_type=None,
                modified_at=datetime.utcnow(),
                is_deleted=True
            )]

            success, failed = await push_attachments(mock_db, mock_user, attachments)

            assert success == ["image.png"]
            assert existing.is_deleted == True

    @pytest.mark.asyncio
    async def test_push_deleted_attachment_not_existing(self, mock_db, mock_user):
        """Suppression d'un attachment qui n'existe pas → crée trace"""
        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=None), \
             patch('app.services.attachments_sync.storage.delete_attachment', return_value=None):

            attachments = [AttachmentContent(
                path="ghost.png",
                content_base64="",
                content_hash="",
                size=0,
                mime_type=None,
                modified_at=datetime.utcnow(),
                is_deleted=True
            )]

            success, failed = await push_attachments(mock_db, mock_user, attachments)

            assert success == ["ghost.png"]
            mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_invalid_path(self, mock_db, mock_user):
        """Path invalide → failed + rollback"""
        with patch('app.services.attachments_sync.get_attachment_by_path', side_effect=ValueError("Invalid")):

            attachments = [AttachmentContent(
                path="../../../etc/passwd",
                content_base64="",
                content_hash="h",
                size=10,
                mime_type=None,
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_attachments(mock_db, mock_user, attachments)

            assert success == []
            assert failed == ["../../../etc/passwd"]
            mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_exception_rollback(self, mock_db, mock_user):
        """Exception DB → rollback"""
        with patch('app.services.attachments_sync.get_attachment_by_path', side_effect=Exception("DB error")):

            attachments = [AttachmentContent(
                path="image.png",
                content_base64="",
                content_hash="h",
                size=10,
                mime_type="image/png",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_attachments(mock_db, mock_user, attachments)

            assert success == []
            assert failed == ["image.png"]
            mock_db.rollback.assert_called_once()


class TestPullAttachments:
    """Tests pour pull_attachments()"""

    @pytest.mark.asyncio
    async def test_pull_existing_attachment(self, mock_db, mock_user):
        """Pull d'un attachment existant"""
        att_record = MagicMock()
        att_record.is_deleted = False
        att_record.content_hash = "hash123"
        att_record.size = 100
        att_record.mime_type = "image/png"
        att_record.modified_at = datetime.utcnow()

        content = b"binary data"

        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=att_record), \
             patch('app.services.attachments_sync.storage.read_attachment', return_value=content):

            result = await pull_attachments(mock_db, mock_user, ["image.png"])

            assert len(result) == 1
            assert result[0].path == "image.png"
            assert result[0].content_base64 == base64.b64encode(content).decode("utf-8")
            assert result[0].is_deleted == False

    @pytest.mark.asyncio
    async def test_pull_deleted_attachment(self, mock_db, mock_user):
        """Pull d'un attachment supprimé"""
        att_record = MagicMock()
        att_record.is_deleted = True
        att_record.modified_at = datetime.utcnow()

        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=att_record):

            result = await pull_attachments(mock_db, mock_user, ["deleted.png"])

            assert len(result) == 1
            assert result[0].path == "deleted.png"
            assert result[0].content_base64 == ""
            assert result[0].is_deleted == True

    @pytest.mark.asyncio
    async def test_pull_nonexistent_attachment(self, mock_db, mock_user):
        """Pull d'un attachment inexistant"""
        with patch('app.services.attachments_sync.get_attachment_by_path', return_value=None):

            result = await pull_attachments(mock_db, mock_user, ["nonexistent.png"])

            assert result == []

    @pytest.mark.asyncio
    async def test_pull_invalid_path(self, mock_db, mock_user):
        """Pull avec path invalide → ignoré"""
        with patch('app.services.attachments_sync.get_attachment_by_path', side_effect=ValueError("Invalid")):

            result = await pull_attachments(mock_db, mock_user, ["../bad.png"])

            assert result == []
