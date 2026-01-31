"""
Endpoints de synchronisation.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import get_current_user
from ..models import User
from ..schemas import (
    SyncRequest, SyncResponse,
    PushNotesRequest, PushNotesResponse,
    PullNotesRequest, PullNotesResponse,
    PushAttachmentsRequest, PushAttachmentsResponse,
    PullAttachmentsRequest, PullAttachmentsResponse,
    SyncedNotesResponse,
    CompareRequest, CompareResponse
)
from ..services import (
    process_sync,
    push_notes, pull_notes,
    push_attachments, pull_attachments,
    get_synced_notes, compare_notes
)


router = APIRouter(prefix="/sync", tags=["Synchronization"])


@router.post("", response_model=SyncResponse)
async def sync(
    request: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint principal de synchronisation.
    Reçoit les métadonnées des notes locales et retourne les actions à effectuer.
    """
    return await process_sync(db, current_user, request)


@router.post("/push", response_model=PushNotesResponse)
async def sync_push(
    request: PushNotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reçoit les contenus des notes à pousser vers le serveur.
    """
    success, failed = await push_notes(db, current_user, request.notes)
    return PushNotesResponse(success=success, failed=failed)


@router.post("/pull", response_model=PullNotesResponse)
async def sync_pull(
    request: PullNotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne le contenu des notes demandées.
    """
    notes = await pull_notes(db, current_user, request.paths)
    return PullNotesResponse(notes=notes)


@router.get("/notes", response_model=SyncedNotesResponse)
async def get_notes(
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(50, ge=1, le=200, description="Éléments par page"),
    include_deleted: bool = Query(False, description="Inclure les notes supprimées"),
    path_filter: Optional[str] = Query(None, description="Filtrer par préfixe de chemin"),
    modified_after: Optional[datetime] = Query(None, description="Notes modifiées après cette date"),
    modified_before: Optional[datetime] = Query(None, description="Notes modifiées avant cette date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Liste toutes les notes synchronisées pour l'utilisateur connecté.
    Utile pour le debug et la visualisation de l'état du serveur.
    """
    return await get_synced_notes(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        include_deleted=include_deleted,
        path_filter=path_filter,
        modified_after=modified_after,
        modified_before=modified_before
    )


@router.post("/compare", response_model=CompareResponse)
async def sync_compare(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare les notes du client avec celles du serveur.
    Retourne les différences catégorisées : à pusher, à puller, conflits, supprimées.
    """
    return await compare_notes(db, current_user, request.notes)


@router.post("/attachments/push", response_model=PushAttachmentsResponse)
async def sync_attachments_push(
    request: PushAttachmentsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reçoit les pièces jointes à pousser vers le serveur.
    Les fichiers sont encodés en base64. Limite : 25 Mo par fichier.
    """
    success, failed = await push_attachments(db, current_user, request.attachments)
    return PushAttachmentsResponse(success=success, failed=failed)


@router.post("/attachments/pull", response_model=PullAttachmentsResponse)
async def sync_attachments_pull(
    request: PullAttachmentsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne les pièces jointes demandées (encodées en base64).
    """
    attachments = await pull_attachments(db, current_user, request.paths)
    return PullAttachmentsResponse(attachments=attachments)
