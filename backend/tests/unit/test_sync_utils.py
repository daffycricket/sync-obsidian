"""
Tests unitaires pour services/sync_utils.py
"""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.sync_utils import (
    normalize_datetime,
    parse_attachment_references,
    OBSIDIAN_LINK_PATTERN
)


class TestNormalizeDatetime:
    """Tests pour normalize_datetime()"""

    def test_none_returns_none(self):
        assert normalize_datetime(None) is None

    def test_naive_datetime_unchanged(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = normalize_datetime(dt)
        assert result == dt
        assert result.tzinfo is None

    def test_aware_utc_removes_tzinfo(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = normalize_datetime(dt)
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_aware_other_timezone_converts_to_utc(self):
        # UTC+2
        tz_plus2 = timezone(timedelta(hours=2))
        dt = datetime(2024, 1, 15, 12, 30, 0, tzinfo=tz_plus2)
        result = normalize_datetime(dt)
        # 12:30 UTC+2 = 10:30 UTC
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_aware_negative_timezone(self):
        # UTC-5
        tz_minus5 = timezone(timedelta(hours=-5))
        dt = datetime(2024, 1, 15, 5, 30, 0, tzinfo=tz_minus5)
        result = normalize_datetime(dt)
        # 05:30 UTC-5 = 10:30 UTC
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None


class TestParseAttachmentReferences:
    """Tests pour parse_attachment_references()"""

    def test_empty_content(self):
        assert parse_attachment_references("") == []
        assert parse_attachment_references(None) == []

    def test_no_references(self):
        content = "Just some plain text without any links."
        assert parse_attachment_references(content) == []

    def test_image_embed(self):
        content = "Some text ![[image.png]] more text"
        result = parse_attachment_references(content)
        assert "image.png" in result

    def test_simple_link(self):
        content = "Link to [[document.pdf]]"
        result = parse_attachment_references(content)
        assert "document.pdf" in result

    def test_markdown_note_link_ignored(self):
        """Les liens vers des notes .md doivent être ignorés"""
        content = "Link to [[other-note.md]]"
        result = parse_attachment_references(content)
        assert result == []

    def test_markdown_note_link_case_insensitive(self):
        """Les liens .MD doivent aussi être ignorés"""
        content = "Link to [[NOTE.MD]]"
        result = parse_attachment_references(content)
        assert result == []

    def test_link_with_alias(self):
        """Liens avec alias: [[file|display text]]"""
        content = "See ![[image.png|my image]]"
        result = parse_attachment_references(content)
        assert "image.png" in result
        assert "my image" not in result

    def test_multiple_references(self):
        content = "![[img1.png]] and [[doc.pdf]] and ![[img2.jpg]]"
        result = parse_attachment_references(content)
        assert len(result) == 3
        assert "img1.png" in result
        assert "doc.pdf" in result
        assert "img2.jpg" in result

    def test_duplicate_references_deduplicated(self):
        content = "![[img.png]] and ![[img.png]] again"
        result = parse_attachment_references(content)
        assert result.count("img.png") == 1

    def test_nested_path(self):
        content = "![[attachments/images/photo.png]]"
        result = parse_attachment_references(content)
        assert "attachments/images/photo.png" in result

    def test_various_extensions(self):
        content = """
        ![[photo.jpg]]
        ![[document.pdf]]
        ![[audio.mp3]]
        ![[video.mp4]]
        ![[archive.zip]]
        """
        result = parse_attachment_references(content)
        assert len(result) == 5

    def test_mixed_notes_and_attachments(self):
        content = "See [[note.md]] and ![[image.png]] and [[another.md]]"
        result = parse_attachment_references(content)
        assert result == ["image.png"]


class TestObsidianLinkPattern:
    """Tests pour le pattern regex OBSIDIAN_LINK_PATTERN"""

    def test_basic_link(self):
        matches = OBSIDIAN_LINK_PATTERN.findall("[[file.txt]]")
        assert matches == ["file.txt"]

    def test_embed_link(self):
        matches = OBSIDIAN_LINK_PATTERN.findall("![[image.png]]")
        assert matches == ["image.png"]

    def test_link_with_alias(self):
        matches = OBSIDIAN_LINK_PATTERN.findall("[[file.txt|display]]")
        assert matches == ["file.txt"]

    def test_multiple_links(self):
        text = "[[a.txt]] and ![[b.png]] and [[c.pdf|doc]]"
        matches = OBSIDIAN_LINK_PATTERN.findall(text)
        assert matches == ["a.txt", "b.png", "c.pdf"]
