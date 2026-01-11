from datetime import datetime
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .models import Note, Attachment, User
from .schemas import (
    NoteMetadata, NoteContent, AttachmentMetadata,
    SyncRequest, SyncResponse
)
from . import storage


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


async def process_sync(
    db: AsyncSession,
    user: User,
    request: SyncRequest
) -> SyncResponse:
    """
    Traite une requête de synchronisation.
    Compare les métadonnées client/serveur et détermine les actions à effectuer.
    """
    server_time = datetime.utcnow()
    
    # Récupérer les notes serveur modifiées depuis le dernier sync
    server_notes = await get_server_notes(db, user.id, request.last_sync)
    server_notes_map = {n.path: n for n in server_notes}
    
    # Notes envoyées par le client
    client_notes_map = {n.path: n for n in request.notes}
    
    notes_to_pull: List[NoteMetadata] = []
    notes_to_push: List[str] = []
    conflicts: List[NoteMetadata] = []
    
    # Analyser chaque note du client
    for client_note in request.notes:
        server_note = server_notes_map.get(client_note.path)
        
        if server_note is None:
            # Note n'existe pas sur le serveur -> le serveur veut la recevoir
            notes_to_push.append(client_note.path)
        elif server_note.content_hash == client_note.content_hash:
            # Même hash -> pas de changement
            pass
        elif client_note.modified_at > server_note.modified_at:
            # Client plus récent -> le serveur veut recevoir la mise à jour
            notes_to_push.append(client_note.path)
        elif server_note.modified_at > client_note.modified_at:
            # Serveur plus récent -> conflit potentiel
            conflicts.append(NoteMetadata(
                path=server_note.path,
                content_hash=server_note.content_hash,
                modified_at=server_note.modified_at,
                is_deleted=server_note.is_deleted
            ))
        else:
            # Même timestamp mais hash différent -> conflit
            conflicts.append(NoteMetadata(
                path=server_note.path,
                content_hash=server_note.content_hash,
                modified_at=server_note.modified_at,
                is_deleted=server_note.is_deleted
            ))
    
    # Notes sur le serveur que le client n'a pas mentionnées
    for path, server_note in server_notes_map.items():
        if path not in client_notes_map:
            notes_to_pull.append(NoteMetadata(
                path=server_note.path,
                content_hash=server_note.content_hash,
                modified_at=server_note.modified_at,
                is_deleted=server_note.is_deleted
            ))
    
    # Même logique pour les pièces jointes
    attachments_to_pull: List[AttachmentMetadata] = []
    attachments_to_push: List[str] = []
    
    # TODO: Implémenter la logique pour les pièces jointes (similaire aux notes)
    
    return SyncResponse(
        server_time=server_time,
        notes_to_pull=notes_to_pull,
        notes_to_push=notes_to_push,
        conflicts=conflicts,
        attachments_to_pull=attachments_to_pull,
        attachments_to_push=attachments_to_push
    )


async def push_notes(
    db: AsyncSession,
    user: User,
    notes: List[NoteContent]
) -> Tuple[List[str], List[str]]:
    """
    Reçoit les notes du client et les sauvegarde.
    Retourne les listes des succès et échecs.
    """
    success = []
    failed = []
    
    for note in notes:
        try:
            # Sauvegarder le fichier
            computed_hash = await storage.save_note(user.id, note.path, note.content)
            
            # Mettre à jour ou créer l'entrée en base
            existing = await get_note_by_path(db, user.id, note.path)
            
            if existing:
                existing.content_hash = computed_hash
                existing.modified_at = note.modified_at
                existing.synced_at = datetime.utcnow()
                existing.is_deleted = note.is_deleted
            else:
                new_note = Note(
                    user_id=user.id,
                    path=note.path,
                    content_hash=computed_hash,
                    modified_at=note.modified_at,
                    synced_at=datetime.utcnow(),
                    is_deleted=note.is_deleted
                )
                db.add(new_note)
            
            await db.commit()
            success.append(note.path)
            
        except Exception as e:
            failed.append(note.path)
            await db.rollback()
    
    return success, failed


async def pull_notes(
    db: AsyncSession,
    user: User,
    paths: List[str]
) -> List[NoteContent]:
    """
    Retourne le contenu des notes demandées.
    """
    notes = []
    
    for path in paths:
        note_record = await get_note_by_path(db, user.id, path)
        if note_record:
            content = await storage.read_note(user.id, path)
            if content is not None:
                notes.append(NoteContent(
                    path=path,
                    content=content,
                    content_hash=note_record.content_hash,
                    modified_at=note_record.modified_at,
                    is_deleted=note_record.is_deleted
                ))
    
    return notes
