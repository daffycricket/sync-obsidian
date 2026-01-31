"""
Logique de synchronisation des pièces jointes (attachments).
"""
import base64
import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Attachment, User
from ..schemas import AttachmentContent
from ..core import storage
from .sync_utils import (
    get_attachment_by_path,
    MAX_ATTACHMENT_SIZE
)


logger = logging.getLogger(__name__)


async def push_attachments(
    db: AsyncSession,
    user: User,
    attachments: List[AttachmentContent]
) -> Tuple[List[str], List[str]]:
    """
    Reçoit les attachments du client et les sauvegarde.
    Vérifie la taille max (25 Mo).
    Gère également les suppressions (is_deleted=True).
    Retourne les listes des succès et échecs.
    """
    success = []
    failed = []
    user_id = user.id

    for att in attachments:
        try:
            # Vérifier la taille
            if att.size > MAX_ATTACHMENT_SIZE:
                logger.warning(
                    f"Attachment trop volumineux - user_id={user_id}, path={att.path}, size={att.size}"
                )
                failed.append(att.path)
                continue

            existing = await get_attachment_by_path(db, user_id, att.path)

            if att.is_deleted:
                # Suppression : supprimer le fichier physique et marquer en base
                await storage.delete_attachment(user_id, att.path)

                if existing:
                    existing.is_deleted = True
                    existing.modified_at = att.modified_at
                    existing.synced_at = datetime.utcnow()
                    existing.content_hash = ""
                    existing.size = 0
                else:
                    # Créer une entrée pour tracer la suppression
                    new_att = Attachment(
                        user_id=user_id,
                        path=att.path,
                        content_hash="",
                        size=0,
                        mime_type=None,
                        modified_at=att.modified_at,
                        synced_at=datetime.utcnow(),
                        is_deleted=True
                    )
                    db.add(new_att)
            else:
                # Création/modification normale
                content_bytes = base64.b64decode(att.content_base64)
                computed_hash = await storage.save_attachment(user_id, att.path, content_bytes)

                if existing:
                    existing.content_hash = computed_hash
                    existing.size = len(content_bytes)
                    existing.mime_type = att.mime_type
                    existing.modified_at = att.modified_at
                    existing.synced_at = datetime.utcnow()
                    existing.is_deleted = False
                else:
                    new_att = Attachment(
                        user_id=user_id,
                        path=att.path,
                        content_hash=computed_hash,
                        size=len(content_bytes),
                        mime_type=att.mime_type,
                        modified_at=att.modified_at,
                        synced_at=datetime.utcnow(),
                        is_deleted=False
                    )
                    db.add(new_att)

            await db.commit()
            success.append(att.path)

        except ValueError as e:
            # Erreur de validation de chemin (path traversal, etc.)
            logger.warning(
                f"Chemin invalide rejeté - user_id={user_id}, path={att.path}, error={str(e)}"
            )
            failed.append(att.path)
            await db.rollback()
        except Exception as e:
            logger.error(
                f"Erreur lors de la sauvegarde de l'attachment - user_id={user_id}, path={att.path}, error={str(e)}",
                exc_info=True
            )
            failed.append(att.path)
            await db.rollback()

    return success, failed


async def pull_attachments(
    db: AsyncSession,
    user: User,
    paths: List[str]
) -> List[AttachmentContent]:
    """
    Retourne le contenu des attachments demandés (encodé en base64).
    Pour les attachments supprimés, retourne is_deleted=True avec contenu vide.
    """
    attachments = []
    user_id = user.id

    for path in paths:
        try:
            att_record = await get_attachment_by_path(db, user_id, path)
            if att_record:
                if att_record.is_deleted:
                    # Attachment supprimé : renvoyer les métadonnées avec contenu vide
                    attachments.append(AttachmentContent(
                        path=path,
                        content_base64="",
                        content_hash="",
                        size=0,
                        mime_type=None,
                        modified_at=att_record.modified_at,
                        is_deleted=True
                    ))
                else:
                    content = await storage.read_attachment(user_id, path)
                    if content is not None:
                        attachments.append(AttachmentContent(
                            path=path,
                            content_base64=base64.b64encode(content).decode("utf-8"),
                            content_hash=att_record.content_hash,
                            size=att_record.size,
                            mime_type=att_record.mime_type,
                            modified_at=att_record.modified_at,
                            is_deleted=False
                        ))
        except ValueError as e:
            # Erreur de validation de chemin (path traversal, etc.)
            logger.warning(
                f"Chemin invalide rejeté lors du pull - user_id={user_id}, path={path}, error={str(e)}"
            )
            # Ne pas ajouter l'attachment à la liste

    return attachments
