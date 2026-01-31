"""
Tests unitaires pour services/notes_sync.py
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notes_sync import push_notes, pull_notes, process_sync
from app.schemas import NoteContent, NoteMetadata, SyncRequest


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


class TestPushNotes:
    """Tests pour push_notes()"""

    @pytest.mark.asyncio
    async def test_push_new_note(self, mock_db, mock_user):
        """Nouvelle note créée avec succès"""
        with patch('app.services.notes_sync.get_note_by_path', return_value=None), \
             patch('app.services.notes_sync.storage.save_note', return_value='hash123'):

            notes = [NoteContent(
                path="test.md",
                content="# Test",
                content_hash="hash123",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert success == ["test.md"]
            assert failed == []
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_update_existing_note(self, mock_db, mock_user):
        """Note existante mise à jour"""
        existing_note = MagicMock()
        existing_note.content_hash = "old_hash"

        with patch('app.services.notes_sync.get_note_by_path', return_value=existing_note), \
             patch('app.services.notes_sync.storage.save_note', return_value='new_hash'):

            notes = [NoteContent(
                path="test.md",
                content="# Updated",
                content_hash="new_hash",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert success == ["test.md"]
            assert failed == []
            assert existing_note.content_hash == "new_hash"
            mock_db.add.assert_not_called()  # Pas d'ajout, juste update

    @pytest.mark.asyncio
    async def test_push_deleted_note_existing(self, mock_db, mock_user):
        """Suppression d'une note existante"""
        existing_note = MagicMock()
        existing_note.is_deleted = False

        with patch('app.services.notes_sync.get_note_by_path', return_value=existing_note), \
             patch('app.services.notes_sync.storage.delete_note', return_value=None):

            notes = [NoteContent(
                path="test.md",
                content="",
                content_hash="",
                modified_at=datetime.utcnow(),
                is_deleted=True
            )]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert success == ["test.md"]
            assert existing_note.is_deleted == True
            assert existing_note.content_hash == ""

    @pytest.mark.asyncio
    async def test_push_deleted_note_not_existing(self, mock_db, mock_user):
        """Suppression d'une note qui n'existe pas encore"""
        with patch('app.services.notes_sync.get_note_by_path', return_value=None), \
             patch('app.services.notes_sync.storage.delete_note', return_value=None):

            notes = [NoteContent(
                path="test.md",
                content="",
                content_hash="",
                modified_at=datetime.utcnow(),
                is_deleted=True
            )]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert success == ["test.md"]
            mock_db.add.assert_called_once()  # Crée une entrée pour tracer

    @pytest.mark.asyncio
    async def test_push_invalid_path_value_error(self, mock_db, mock_user):
        """Path invalide lève ValueError → failed"""
        with patch('app.services.notes_sync.get_note_by_path', side_effect=ValueError("Invalid path")):

            notes = [NoteContent(
                path="../../../etc/passwd",
                content="hack",
                content_hash="xxx",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert success == []
            assert failed == ["../../../etc/passwd"]
            mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_exception_rollback(self, mock_db, mock_user):
        """Exception → rollback et note dans failed"""
        with patch('app.services.notes_sync.get_note_by_path', side_effect=Exception("DB error")):

            notes = [NoteContent(
                path="test.md",
                content="# Test",
                content_hash="hash",
                modified_at=datetime.utcnow(),
                is_deleted=False
            )]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert success == []
            assert failed == ["test.md"]
            mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_multiple_notes_partial_failure(self, mock_db, mock_user):
        """Plusieurs notes, échec partiel"""
        call_count = [0]

        async def mock_get_note(*args):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Bad path")
            return None

        with patch('app.services.notes_sync.get_note_by_path', side_effect=mock_get_note), \
             patch('app.services.notes_sync.storage.save_note', return_value='hash'):

            notes = [
                NoteContent(path="good1.md", content="ok", content_hash="h1", modified_at=datetime.utcnow(), is_deleted=False),
                NoteContent(path="bad.md", content="fail", content_hash="h2", modified_at=datetime.utcnow(), is_deleted=False),
                NoteContent(path="good2.md", content="ok", content_hash="h3", modified_at=datetime.utcnow(), is_deleted=False),
            ]

            success, failed = await push_notes(mock_db, mock_user, notes)

            assert "good1.md" in success
            assert "good2.md" in success
            assert "bad.md" in failed


class TestPullNotes:
    """Tests pour pull_notes()"""

    @pytest.mark.asyncio
    async def test_pull_existing_note(self, mock_db, mock_user):
        """Pull d'une note existante"""
        note_record = MagicMock()
        note_record.is_deleted = False
        note_record.content_hash = "hash123"
        note_record.modified_at = datetime.utcnow()

        with patch('app.services.notes_sync.get_note_by_path', return_value=note_record), \
             patch('app.services.notes_sync.storage.read_note', return_value="# Content"):

            result = await pull_notes(mock_db, mock_user, ["test.md"])

            assert len(result) == 1
            assert result[0].path == "test.md"
            assert result[0].content == "# Content"
            assert result[0].is_deleted == False

    @pytest.mark.asyncio
    async def test_pull_deleted_note(self, mock_db, mock_user):
        """Pull d'une note supprimée → contenu vide, is_deleted=True"""
        note_record = MagicMock()
        note_record.is_deleted = True
        note_record.modified_at = datetime.utcnow()

        with patch('app.services.notes_sync.get_note_by_path', return_value=note_record):

            result = await pull_notes(mock_db, mock_user, ["deleted.md"])

            assert len(result) == 1
            assert result[0].path == "deleted.md"
            assert result[0].content == ""
            assert result[0].is_deleted == True

    @pytest.mark.asyncio
    async def test_pull_nonexistent_note(self, mock_db, mock_user):
        """Pull d'une note inexistante → pas dans le résultat"""
        with patch('app.services.notes_sync.get_note_by_path', return_value=None):

            result = await pull_notes(mock_db, mock_user, ["nonexistent.md"])

            assert result == []

    @pytest.mark.asyncio
    async def test_pull_invalid_path(self, mock_db, mock_user):
        """Pull avec path invalide → ignoré"""
        with patch('app.services.notes_sync.get_note_by_path', side_effect=ValueError("Invalid")):

            result = await pull_notes(mock_db, mock_user, ["../bad.md"])

            assert result == []

    @pytest.mark.asyncio
    async def test_pull_multiple_notes(self, mock_db, mock_user):
        """Pull de plusieurs notes"""
        def mock_get_note(db, user_id, path):
            if path == "exists.md":
                note = MagicMock()
                note.is_deleted = False
                note.content_hash = "hash"
                note.modified_at = datetime.utcnow()
                return note
            return None

        with patch('app.services.notes_sync.get_note_by_path', side_effect=mock_get_note), \
             patch('app.services.notes_sync.storage.read_note', return_value="content"):

            result = await pull_notes(mock_db, mock_user, ["exists.md", "notexists.md"])

            assert len(result) == 1
            assert result[0].path == "exists.md"


class TestProcessSync:
    """Tests pour process_sync()"""

    @pytest.mark.asyncio
    async def test_sync_client_has_new_note(self, mock_db, mock_user):
        """Client a une note que le serveur n'a pas → to_push"""
        with patch('app.services.notes_sync.get_server_notes', return_value=[]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(
                last_sync=None,
                notes=[NoteMetadata(path="new.md", content_hash="h1", modified_at=datetime.utcnow(), is_deleted=False)],
                attachments=[]
            )

            result = await process_sync(mock_db, mock_user, request)

            assert "new.md" in result.notes_to_push
            assert result.notes_to_pull == []

    @pytest.mark.asyncio
    async def test_sync_server_has_new_note(self, mock_db, mock_user):
        """Serveur a une note que le client n'a pas → to_pull"""
        server_note = MagicMock()
        server_note.path = "server.md"
        server_note.content_hash = "h1"
        server_note.modified_at = datetime.utcnow()
        server_note.is_deleted = False

        with patch('app.services.notes_sync.get_server_notes', return_value=[server_note]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(last_sync=None, notes=[], attachments=[])

            result = await process_sync(mock_db, mock_user, request)

            assert len(result.notes_to_pull) == 1
            assert result.notes_to_pull[0].path == "server.md"

    @pytest.mark.asyncio
    async def test_sync_same_hash_no_action(self, mock_db, mock_user):
        """Même hash → pas d'action"""
        now = datetime.utcnow()
        server_note = MagicMock()
        server_note.path = "same.md"
        server_note.content_hash = "identical_hash"
        server_note.modified_at = now
        server_note.is_deleted = False

        with patch('app.services.notes_sync.get_server_notes', return_value=[server_note]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(
                last_sync=None,
                notes=[NoteMetadata(path="same.md", content_hash="identical_hash", modified_at=now, is_deleted=False)],
                attachments=[]
            )

            result = await process_sync(mock_db, mock_user, request)

            assert result.notes_to_push == []
            assert result.notes_to_pull == []
            assert result.conflicts == []

    @pytest.mark.asyncio
    async def test_sync_client_newer_to_push(self, mock_db, mock_user):
        """Client plus récent → to_push"""
        server_note = MagicMock()
        server_note.path = "note.md"
        server_note.content_hash = "old_hash"
        server_note.modified_at = datetime(2024, 1, 1, 10, 0, 0)
        server_note.is_deleted = False

        with patch('app.services.notes_sync.get_server_notes', return_value=[server_note]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(
                last_sync=None,
                notes=[NoteMetadata(
                    path="note.md",
                    content_hash="new_hash",
                    modified_at=datetime(2024, 1, 1, 12, 0, 0),  # Plus récent
                    is_deleted=False
                )],
                attachments=[]
            )

            result = await process_sync(mock_db, mock_user, request)

            assert "note.md" in result.notes_to_push

    @pytest.mark.asyncio
    async def test_sync_conflict_same_timestamp_different_hash(self, mock_db, mock_user):
        """Même timestamp mais hash différent → conflit"""
        same_time = datetime(2024, 1, 1, 10, 0, 0)

        server_note = MagicMock()
        server_note.path = "conflict.md"
        server_note.content_hash = "server_hash"
        server_note.modified_at = same_time
        server_note.is_deleted = False

        with patch('app.services.notes_sync.get_server_notes', return_value=[server_note]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(
                last_sync=None,
                notes=[NoteMetadata(
                    path="conflict.md",
                    content_hash="client_hash",  # Hash différent
                    modified_at=same_time,  # Même timestamp
                    is_deleted=False
                )],
                attachments=[]
            )

            result = await process_sync(mock_db, mock_user, request)

            assert len(result.conflicts) == 1
            assert result.conflicts[0].path == "conflict.md"

    @pytest.mark.asyncio
    async def test_sync_client_deletion(self, mock_db, mock_user):
        """Client supprime une note → to_push si plus récent"""
        server_note = MagicMock()
        server_note.path = "deleted.md"
        server_note.content_hash = "hash"
        server_note.modified_at = datetime(2024, 1, 1, 10, 0, 0)
        server_note.is_deleted = False

        with patch('app.services.notes_sync.get_server_notes', return_value=[server_note]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(
                last_sync=None,
                notes=[NoteMetadata(
                    path="deleted.md",
                    content_hash="",
                    modified_at=datetime(2024, 1, 1, 12, 0, 0),  # Suppression plus récente
                    is_deleted=True
                )],
                attachments=[]
            )

            result = await process_sync(mock_db, mock_user, request)

            assert "deleted.md" in result.notes_to_push

    @pytest.mark.asyncio
    async def test_sync_server_deletion_propagates(self, mock_db, mock_user):
        """Serveur a supprimé → to_pull avec is_deleted"""
        server_note = MagicMock()
        server_note.path = "server_deleted.md"
        server_note.content_hash = ""
        server_note.modified_at = datetime(2024, 1, 1, 12, 0, 0)
        server_note.is_deleted = True

        with patch('app.services.notes_sync.get_server_notes', return_value=[server_note]), \
             patch('app.services.notes_sync.get_server_attachments', return_value=[]):

            request = SyncRequest(
                last_sync=None,
                notes=[NoteMetadata(
                    path="server_deleted.md",
                    content_hash="hash",
                    modified_at=datetime(2024, 1, 1, 10, 0, 0),  # Client plus ancien
                    is_deleted=False
                )],
                attachments=[]
            )

            result = await process_sync(mock_db, mock_user, request)

            assert len(result.notes_to_pull) == 1
            assert result.notes_to_pull[0].is_deleted == True
