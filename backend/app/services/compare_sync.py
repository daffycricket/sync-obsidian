"""
Fonctions de comparaison et visualisation pour le debug.
"""
import logging
from datetime import datetime
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..models import Note, Attachment, User
from ..schemas import (
    ClientNoteInfo,
    SyncedNoteInfo, SyncedAttachmentInfo, SyncedNotesResponse,
    ReferencedAttachment,
    CompareResponse, CompareSummary,
    NoteToPush, NoteToPull, NoteConflict, NoteDeletedOnServer
)
from .. import storage
from .sync_utils import (
    normalize_datetime,
    get_server_notes,
    parse_attachment_references
)


logger = logging.getLogger(__name__)


async def get_synced_notes(
    db: AsyncSession,
    user: User,
    page: int = 1,
    page_size: int = 50,
    include_deleted: bool = False,
    path_filter: str = None,
    modified_after: datetime = None,
    modified_before: datetime = None
) -> SyncedNotesResponse:
    """
    Récupère la liste des notes synchronisées pour un utilisateur avec pagination.
    Utilisé pour le debug et la visualisation.
    """
    user_id = user.id

    # Construction de la requête de base pour les notes
    notes_query = select(Note).where(Note.user_id == user_id)
    count_query = select(func.count(Note.id)).where(Note.user_id == user_id)

    # Filtres
    if not include_deleted:
        notes_query = notes_query.where(Note.is_deleted == False)
        count_query = count_query.where(Note.is_deleted == False)

    if path_filter:
        notes_query = notes_query.where(Note.path.like(f"{path_filter}%"))
        count_query = count_query.where(Note.path.like(f"{path_filter}%"))

    if modified_after:
        notes_query = notes_query.where(Note.modified_at > modified_after)
        count_query = count_query.where(Note.modified_at > modified_after)

    if modified_before:
        notes_query = notes_query.where(Note.modified_at < modified_before)
        count_query = count_query.where(Note.modified_at < modified_before)

    # Compter le total
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()

    # Pagination
    offset = (page - 1) * page_size
    notes_query = notes_query.order_by(Note.path).offset(offset).limit(page_size)

    # Exécuter la requête
    result = await db.execute(notes_query)
    notes_records = result.scalars().all()

    # Récupérer tous les attachments de l'utilisateur pour vérifier l'existence
    all_attachments_query = select(Attachment).where(Attachment.user_id == user_id)
    if not include_deleted:
        all_attachments_query = all_attachments_query.where(Attachment.is_deleted == False)
    all_att_result = await db.execute(all_attachments_query)
    all_attachments = {att.path: att for att in all_att_result.scalars().all()}

    # Construire la réponse avec les tailles de fichiers et les attachments référencés
    notes_list = []
    for note in notes_records:
        size = storage.get_note_size(user_id, note.path) if not note.is_deleted else 0

        # Parser le contenu pour trouver les références aux attachments
        referenced_attachments = []
        if not note.is_deleted:
            try:
                content = await storage.read_note(user_id, note.path)
                if content:
                    refs = parse_attachment_references(content)
                    for ref_path in refs:
                        # Vérifier si l'attachment existe
                        att = all_attachments.get(ref_path)
                        referenced_attachments.append(ReferencedAttachment(
                            path=ref_path,
                            exists=att is not None,
                            size_bytes=att.size if att else None
                        ))
            except Exception as e:
                logger.warning(f"Erreur parsing attachments pour {note.path}: {e}")

        notes_list.append(SyncedNoteInfo(
            path=note.path,
            content_hash=note.content_hash,
            modified_at=note.modified_at,
            synced_at=note.synced_at,
            is_deleted=note.is_deleted,
            size_bytes=size,
            referenced_attachments=referenced_attachments
        ))

    # Même logique pour les attachments (simplifié - pas de pagination séparée)
    attachments_query = select(Attachment).where(Attachment.user_id == user_id)
    if not include_deleted:
        attachments_query = attachments_query.where(Attachment.is_deleted == False)
    attachments_query = attachments_query.limit(100)  # Limite pour éviter surcharge

    att_result = await db.execute(attachments_query)
    attachments_records = att_result.scalars().all()

    attachments_list = []
    for att in attachments_records:
        attachments_list.append(SyncedAttachmentInfo(
            path=att.path,
            content_hash=att.content_hash,
            modified_at=att.modified_at,
            synced_at=att.synced_at,
            is_deleted=att.is_deleted,
            size_bytes=att.size,
            mime_type=att.mime_type
        ))

    # Calculer le nombre total de pages
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return SyncedNotesResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        notes=notes_list,
        attachments=attachments_list
    )


async def compare_notes(
    db: AsyncSession,
    user: User,
    client_notes: List[ClientNoteInfo]
) -> CompareResponse:
    """
    Compare les notes du client avec celles du serveur.
    Retourne les différences catégorisées par action nécessaire.
    """
    server_time = datetime.utcnow()
    user_id = user.id

    # Récupérer toutes les notes du serveur
    all_server_notes = await get_server_notes(db, user_id, since=None)
    server_notes_map = {n.path: n for n in all_server_notes}

    # Map des notes client
    client_notes_map = {n.path: n for n in client_notes}

    to_push: List[NoteToPush] = []
    to_pull: List[NoteToPull] = []
    conflicts: List[NoteConflict] = []
    deleted_on_server: List[NoteDeletedOnServer] = []
    identical_count = 0

    # Analyser chaque note du client
    for client_note in client_notes:
        server_note = server_notes_map.get(client_note.path)

        if server_note is None:
            # Note existe côté client mais pas serveur -> à pusher
            to_push.append(NoteToPush(
                path=client_note.path,
                reason="not_on_server",
                client_modified=client_note.modified_at
            ))
        elif server_note.is_deleted:
            # Note supprimée sur le serveur
            deleted_on_server.append(NoteDeletedOnServer(
                path=server_note.path,
                deleted_at=server_note.modified_at
            ))
        else:
            # Normaliser les timestamps pour comparaison
            client_time = normalize_datetime(client_note.modified_at)
            server_time_note = normalize_datetime(server_note.modified_at)

            if server_note.content_hash == client_note.content_hash:
                # Même hash -> identique
                identical_count += 1
            elif client_time > server_time_note:
                # Client plus récent -> à pusher
                to_push.append(NoteToPush(
                    path=client_note.path,
                    reason="client_newer",
                    client_modified=client_note.modified_at
                ))
            elif server_time_note > client_time:
                # Serveur plus récent -> à puller
                to_pull.append(NoteToPull(
                    path=server_note.path,
                    reason="server_newer",
                    server_modified=server_note.modified_at,
                    client_modified=client_note.modified_at
                ))
            else:
                # Même timestamp mais hash différent -> conflit
                conflicts.append(NoteConflict(
                    path=client_note.path,
                    reason="both_modified",
                    client_hash=client_note.content_hash,
                    server_hash=server_note.content_hash,
                    client_modified=client_note.modified_at,
                    server_modified=server_note.modified_at
                ))

    # Notes sur le serveur que le client n'a pas
    for path, server_note in server_notes_map.items():
        if path not in client_notes_map:
            if server_note.is_deleted:
                # Ignorer les notes supprimées que le client ne connaît pas
                pass
            else:
                # Note existe sur serveur mais pas client -> à puller
                to_pull.append(NoteToPull(
                    path=server_note.path,
                    reason="not_on_client",
                    server_modified=server_note.modified_at
                ))

    # Compter les notes serveur non supprimées
    server_active_count = sum(1 for n in all_server_notes if not n.is_deleted)

    summary = CompareSummary(
        total_client=len(client_notes),
        total_server=server_active_count,
        to_push=len(to_push),
        to_pull=len(to_pull),
        conflicts=len(conflicts),
        identical=identical_count,
        deleted_on_server=len(deleted_on_server)
    )

    return CompareResponse(
        server_time=server_time,
        summary=summary,
        to_push=to_push,
        to_pull=to_pull,
        conflicts=conflicts,
        deleted_on_server=deleted_on_server
    )
