"""
Logique de synchronisation des notes.
"""
import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Note, User
from ..schemas import (
    NoteMetadata, NoteContent, AttachmentMetadata,
    SyncRequest, SyncResponse
)
from .. import storage
from .sync_utils import (
    normalize_datetime,
    get_server_notes,
    get_note_by_path,
    get_server_attachments
)


logger = logging.getLogger(__name__)


async def process_sync(
    db: AsyncSession,
    user: User,
    request: SyncRequest
) -> SyncResponse:
    """
    Traite une requête de synchronisation.
    Compare les métadonnées client/serveur et détermine les actions à effectuer.
    Gère les suppressions : propage is_deleted aux autres devices.
    """
    server_time = datetime.utcnow()

    # Récupérer TOUTES les notes du serveur pour la comparaison
    # (pas seulement celles modifiées depuis last_sync)
    all_server_notes = await get_server_notes(db, user.id, since=None)
    server_notes_map = {n.path: n for n in all_server_notes}

    # Récupérer les notes serveur modifiées depuis le dernier sync (pour notes_to_pull)
    server_notes_changed = await get_server_notes(db, user.id, request.last_sync)
    server_notes_changed_paths = {n.path for n in server_notes_changed}

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
        else:
            # Normaliser les timestamps pour comparaison
            client_time = normalize_datetime(client_note.modified_at)
            server_time_note = normalize_datetime(server_note.modified_at)

            if client_note.is_deleted:
                # Client signale une suppression
                if not server_note.is_deleted:
                    if client_time >= server_time_note:
                        # Suppression client est plus récente -> accepter
                        notes_to_push.append(client_note.path)
                    else:
                        # Serveur a été modifié après la suppression -> conflit
                        conflicts.append(NoteMetadata(
                            path=server_note.path,
                            content_hash=server_note.content_hash,
                            modified_at=server_note.modified_at,
                            is_deleted=server_note.is_deleted
                        ))
                # Si déjà supprimé sur le serveur, rien à faire
            elif server_note.is_deleted:
                # Serveur a supprimé mais client a encore la note
                if client_time > server_time_note:
                    # Client a modifié après la suppression -> recréer la note
                    notes_to_push.append(client_note.path)
                else:
                    # Suppression serveur est plus récente -> propager au client
                    # Les suppressions sont toujours propagées (même si pas modifiées depuis last_sync)
                    notes_to_pull.append(NoteMetadata(
                        path=server_note.path,
                        content_hash=server_note.content_hash,
                        modified_at=server_note.modified_at,
                        is_deleted=True
                    ))
            elif server_note.content_hash == client_note.content_hash:
                # Même hash -> pas de changement
                pass
            elif client_time > server_time_note:
                # Client plus récent -> le serveur veut recevoir la mise à jour
                notes_to_push.append(client_note.path)
            elif server_time_note > client_time:
                # Serveur plus récent -> client doit récupérer
                # Mais seulement si la note a été modifiée depuis last_sync
                if server_note.path in server_notes_changed_paths:
                    notes_to_pull.append(NoteMetadata(
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
            # Ne pas envoyer les notes supprimées si le client ne les connaît pas
            # (évite de propager des suppressions de notes jamais vues)
            if not server_note.is_deleted:
                # Le client n'a JAMAIS eu cette note -> TOUJOURS la proposer
                # Correction: on ne filtre plus par last_sync ici car le client
                # ne connaît pas cette note, il doit la recevoir indépendamment
                # de quand elle a été créée/modifiée sur le serveur
                notes_to_pull.append(NoteMetadata(
                    path=server_note.path,
                    content_hash=server_note.content_hash,
                    modified_at=server_note.modified_at,
                    is_deleted=server_note.is_deleted
                ))

    # Logique pour les pièces jointes
    attachments_to_pull: List[AttachmentMetadata] = []
    attachments_to_push: List[str] = []

    # Récupérer tous les attachments du serveur
    all_server_attachments = await get_server_attachments(db, user.id)
    server_attachments_map = {a.path: a for a in all_server_attachments}

    # Map des attachments client
    client_attachments_map = {a.path: a for a in request.attachments}

    # Analyser chaque attachment du client
    for client_att in request.attachments:
        server_att = server_attachments_map.get(client_att.path)

        if server_att is None:
            # Attachment n'existe pas sur le serveur -> le serveur veut le recevoir
            attachments_to_push.append(client_att.path)
        elif server_att.content_hash != client_att.content_hash:
            # Hash différent - comme les attachments sont immutables,
            # c'est un conflit. On garde la version serveur (client doit pull)
            attachments_to_pull.append(AttachmentMetadata(
                path=server_att.path,
                content_hash=server_att.content_hash,
                size=server_att.size,
                mime_type=server_att.mime_type,
                modified_at=server_att.modified_at,
                is_deleted=server_att.is_deleted
            ))
        # Si même hash, rien à faire

    # Attachments sur le serveur que le client n'a pas
    for path, server_att in server_attachments_map.items():
        if path not in client_attachments_map:
            # Le client n'a pas cet attachment -> toujours le proposer
            attachments_to_pull.append(AttachmentMetadata(
                path=server_att.path,
                content_hash=server_att.content_hash,
                size=server_att.size,
                mime_type=server_att.mime_type,
                modified_at=server_att.modified_at,
                is_deleted=server_att.is_deleted
            ))

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
    Gère également les suppressions (is_deleted=True).
    Retourne les listes des succès et échecs.
    """
    success = []
    failed = []
    user_id = user.id  # Capturer l'ID avant le try/except pour éviter les problèmes SQLAlchemy

    for note in notes:
        try:
            existing = await get_note_by_path(db, user_id, note.path)

            if note.is_deleted:
                # Suppression : supprimer le fichier physique et marquer en base
                await storage.delete_note(user.id, note.path)

                if existing:
                    existing.is_deleted = True
                    existing.modified_at = note.modified_at
                    existing.synced_at = datetime.utcnow()
                    existing.content_hash = ""  # Hash vide pour note supprimée
                else:
                    # Créer une entrée pour tracer la suppression
                    new_note = Note(
                        user_id=user_id,
                        path=note.path,
                        content_hash="",
                        modified_at=note.modified_at,
                        synced_at=datetime.utcnow(),
                        is_deleted=True
                    )
                    db.add(new_note)
            else:
                # Création/modification normale
                computed_hash = await storage.save_note(user_id, note.path, note.content)

                if existing:
                    existing.content_hash = computed_hash
                    existing.modified_at = note.modified_at
                    existing.synced_at = datetime.utcnow()
                    existing.is_deleted = False
                else:
                    new_note = Note(
                        user_id=user_id,
                        path=note.path,
                        content_hash=computed_hash,
                        modified_at=note.modified_at,
                        synced_at=datetime.utcnow(),
                        is_deleted=False
                    )
                    db.add(new_note)

            await db.commit()
            success.append(note.path)

        except ValueError as e:
            # Erreur de validation de chemin (path traversal, etc.)
            logger.warning(
                f"Chemin invalide rejeté - user_id={user_id}, path={note.path}, error={str(e)}"
            )
            failed.append(note.path)
            await db.rollback()
        except Exception as e:
            logger.error(
                f"Erreur lors de la sauvegarde de la note - user_id={user_id}, path={note.path}, error={str(e)}",
                exc_info=True
            )
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
    Pour les notes supprimées, retourne is_deleted=True avec contenu vide.
    """
    notes = []
    user_id = user.id  # Capturer l'ID avant la boucle pour éviter les problèmes SQLAlchemy

    for path in paths:
        try:
            note_record = await get_note_by_path(db, user_id, path)
            if note_record:
                if note_record.is_deleted:
                    # Note supprimée : renvoyer les métadonnées avec contenu vide
                    notes.append(NoteContent(
                        path=path,
                        content="",
                        content_hash="",
                        modified_at=note_record.modified_at,
                        is_deleted=True
                    ))
                else:
                    content = await storage.read_note(user_id, path)
                    if content is not None:
                        notes.append(NoteContent(
                            path=path,
                            content=content,
                            content_hash=note_record.content_hash,
                            modified_at=note_record.modified_at,
                            is_deleted=False
                        ))
        except ValueError as e:
            # Erreur de validation de chemin (path traversal, etc.)
            logger.warning(
                f"Chemin invalide rejeté lors du pull - user_id={user_id}, path={path}, error={str(e)}"
            )
            # Ne pas ajouter la note à la liste (comme si elle n'existait pas)

    return notes
