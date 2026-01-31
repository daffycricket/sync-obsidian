"""
Tests unitaires pour services/compare_sync.py
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.compare_sync import compare_notes
from app.schemas import ClientNoteInfo


@pytest.fixture
def mock_db():
    """Mock de la session async SQLAlchemy."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock d'un utilisateur."""
    user = MagicMock()
    user.id = 1
    return user


class TestCompareNotes:
    """Tests pour compare_notes()"""

    @pytest.mark.asyncio
    async def test_compare_empty_both(self, mock_db, mock_user):
        """Client et serveur vides"""
        with patch('app.services.compare_sync.get_server_notes', return_value=[]):

            result = await compare_notes(mock_db, mock_user, [])

            assert result.summary.total_client == 0
            assert result.summary.total_server == 0
            assert result.summary.identical == 0

    @pytest.mark.asyncio
    async def test_compare_client_has_new_note(self, mock_db, mock_user):
        """Client a une note que le serveur n'a pas → to_push"""
        with patch('app.services.compare_sync.get_server_notes', return_value=[]):

            client_notes = [ClientNoteInfo(
                path="new.md",
                content_hash="hash1",
                modified_at=datetime.utcnow()
            )]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.to_push == 1
            assert len(result.to_push) == 1
            assert result.to_push[0].path == "new.md"
            assert result.to_push[0].reason == "not_on_server"

    @pytest.mark.asyncio
    async def test_compare_server_has_new_note(self, mock_db, mock_user):
        """Serveur a une note que le client n'a pas → to_pull"""
        server_note = MagicMock()
        server_note.path = "server.md"
        server_note.content_hash = "hash1"
        server_note.modified_at = datetime.utcnow()
        server_note.is_deleted = False

        with patch('app.services.compare_sync.get_server_notes', return_value=[server_note]):

            result = await compare_notes(mock_db, mock_user, [])

            assert result.summary.to_pull == 1
            assert len(result.to_pull) == 1
            assert result.to_pull[0].path == "server.md"
            assert result.to_pull[0].reason == "not_on_client"

    @pytest.mark.asyncio
    async def test_compare_identical_notes(self, mock_db, mock_user):
        """Notes identiques (même hash)"""
        now = datetime.utcnow()

        server_note = MagicMock()
        server_note.path = "same.md"
        server_note.content_hash = "identical_hash"
        server_note.modified_at = now
        server_note.is_deleted = False

        with patch('app.services.compare_sync.get_server_notes', return_value=[server_note]):

            client_notes = [ClientNoteInfo(
                path="same.md",
                content_hash="identical_hash",
                modified_at=now
            )]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.identical == 1
            assert result.summary.to_push == 0
            assert result.summary.to_pull == 0

    @pytest.mark.asyncio
    async def test_compare_client_newer(self, mock_db, mock_user):
        """Client plus récent → to_push"""
        server_note = MagicMock()
        server_note.path = "note.md"
        server_note.content_hash = "old_hash"
        server_note.modified_at = datetime(2024, 1, 1, 10, 0, 0)
        server_note.is_deleted = False

        with patch('app.services.compare_sync.get_server_notes', return_value=[server_note]):

            client_notes = [ClientNoteInfo(
                path="note.md",
                content_hash="new_hash",
                modified_at=datetime(2024, 1, 1, 12, 0, 0)
            )]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.to_push == 1
            assert result.to_push[0].reason == "client_newer"

    @pytest.mark.asyncio
    async def test_compare_server_newer(self, mock_db, mock_user):
        """Serveur plus récent → to_pull"""
        server_note = MagicMock()
        server_note.path = "note.md"
        server_note.content_hash = "new_hash"
        server_note.modified_at = datetime(2024, 1, 1, 12, 0, 0)
        server_note.is_deleted = False

        with patch('app.services.compare_sync.get_server_notes', return_value=[server_note]):

            client_notes = [ClientNoteInfo(
                path="note.md",
                content_hash="old_hash",
                modified_at=datetime(2024, 1, 1, 10, 0, 0)
            )]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.to_pull == 1
            assert result.to_pull[0].reason == "server_newer"

    @pytest.mark.asyncio
    async def test_compare_conflict(self, mock_db, mock_user):
        """Même timestamp, hash différent → conflit"""
        same_time = datetime(2024, 1, 1, 10, 0, 0)

        server_note = MagicMock()
        server_note.path = "conflict.md"
        server_note.content_hash = "server_hash"
        server_note.modified_at = same_time
        server_note.is_deleted = False

        with patch('app.services.compare_sync.get_server_notes', return_value=[server_note]):

            client_notes = [ClientNoteInfo(
                path="conflict.md",
                content_hash="client_hash",
                modified_at=same_time
            )]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.conflicts == 1
            assert result.conflicts[0].reason == "both_modified"

    @pytest.mark.asyncio
    async def test_compare_deleted_on_server(self, mock_db, mock_user):
        """Note supprimée sur serveur"""
        server_note = MagicMock()
        server_note.path = "deleted.md"
        server_note.content_hash = ""
        server_note.modified_at = datetime.utcnow()
        server_note.is_deleted = True

        with patch('app.services.compare_sync.get_server_notes', return_value=[server_note]):

            client_notes = [ClientNoteInfo(
                path="deleted.md",
                content_hash="hash",
                modified_at=datetime.utcnow()
            )]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.deleted_on_server == 1
            assert result.deleted_on_server[0].path == "deleted.md"

    @pytest.mark.asyncio
    async def test_compare_mixed_scenario(self, mock_db, mock_user):
        """Scénario mixte avec plusieurs cas"""
        now = datetime.utcnow()
        old = datetime(2024, 1, 1, 10, 0, 0)
        new = datetime(2024, 1, 1, 12, 0, 0)

        server_notes = [
            # Identique
            MagicMock(path="identical.md", content_hash="h1", modified_at=now, is_deleted=False),
            # Serveur plus récent
            MagicMock(path="server_newer.md", content_hash="h2_new", modified_at=new, is_deleted=False),
            # Seulement sur serveur
            MagicMock(path="server_only.md", content_hash="h3", modified_at=now, is_deleted=False),
        ]

        with patch('app.services.compare_sync.get_server_notes', return_value=server_notes):

            client_notes = [
                ClientNoteInfo(path="identical.md", content_hash="h1", modified_at=now),
                ClientNoteInfo(path="server_newer.md", content_hash="h2_old", modified_at=old),
                ClientNoteInfo(path="client_only.md", content_hash="h4", modified_at=now),
            ]

            result = await compare_notes(mock_db, mock_user, client_notes)

            assert result.summary.identical == 1
            assert result.summary.to_push == 1  # client_only
            assert result.summary.to_pull == 2  # server_newer + server_only
