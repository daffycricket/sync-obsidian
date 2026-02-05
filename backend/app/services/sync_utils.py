"""
Utilitaires partagés pour la synchronisation.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models import Note, Attachment


logger = logging.getLogger(__name__)

# Regex pour trouver les références Obsidian: ![[file]] ou [[file]]
OBSIDIAN_LINK_PATTERN = re.compile(r'!?\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')

# Limite de taille pour les attachments (25 Mo)
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024


def parse_attachment_references(content: str) -> List[str]:
    """
    Parse le contenu d'une note pour trouver les références aux attachments.
    Cherche les patterns ![[filename]] et [[filename]] (liens Obsidian).
    Retourne uniquement les fichiers non-markdown (images, PDFs, etc.)
    """
    if not content:
        return []

    matches = OBSIDIAN_LINK_PATTERN.findall(content)
    attachments = []

    for match in matches:
        # Ignorer les liens vers d'autres notes markdown
        if not match.lower().endswith('.md'):
            attachments.append(match)

    return list(set(attachments))  # Dédupliquer


def normalize_datetime(dt: datetime) -> datetime:
    """
    Normalise un datetime pour la comparaison.
    Supprime les infos de timezone pour comparer en UTC naive.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        # Convertir en UTC puis supprimer la timezone
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


async def get_server_notes(
    db: AsyncSession,
    user_id: int,
    since: datetime = None
) -> List[Note]:
    """Récupère les notes modifiées depuis une date."""
    query = select(Note).where(Note.user_id == user_id)
    if since:
        query = query.where(Note.modified_at > since)
    result = await db.execute(query)
    return result.scalars().all()


async def get_note_by_path(db: AsyncSession, user_id: int, path: str) -> Note:
    """Récupère une note par son chemin."""
    result = await db.execute(
        select(Note).where(
            and_(Note.user_id == user_id, Note.path == path)
        )
    )
    return result.scalar_one_or_none()


async def get_server_attachments(db: AsyncSession, user_id: int) -> List[Attachment]:
    """Récupère tous les attachments d'un utilisateur (y compris supprimés)."""
    query = select(Attachment).where(Attachment.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_attachment_by_path(db: AsyncSession, user_id: int, path: str) -> Attachment:
    """Récupère un attachment par son chemin."""
    result = await db.execute(
        select(Attachment).where(
            and_(Attachment.user_id == user_id, Attachment.path == path)
        )
    )
    return result.scalar_one_or_none()
