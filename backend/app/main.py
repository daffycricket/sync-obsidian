from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager

from .config import settings
from .database import get_db, init_db
from .models import User
from .schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    SyncRequest, SyncResponse,
    PushNotesRequest, PushNotesResponse,
    PullNotesRequest, PullNotesResponse,
    SyncedNotesResponse,
    CompareRequest, CompareResponse
)
from .auth import (
    get_password_hash, authenticate_user,
    create_access_token, get_current_user
)
from .sync import process_sync, push_notes, pull_notes, get_synced_notes, compare_notes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="SyncObsidian API",
    description="API de synchronisation Obsidian auto-hébergée",
    version="1.0.0",
    lifespan=lifespan
)

# Compression GZip pour réduire la bande passante (~80% sur du Markdown)
app.add_middleware(GZipMiddleware, minimum_size=500)  # Compresse si > 500 octets

# CORS pour permettre les requêtes depuis Obsidian
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fichiers statiques
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


# ============ Health Check ============

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "syncobsidian"}


@app.get("/sync-viewer")
async def sync_viewer():
    """Page HTML de visualisation des notes synchronisées."""
    return FileResponse(static_path / "sync-viewer.html")


# ============ Auth Endpoints ============

@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Vérifier si l'utilisateur existe déjà
    result = await db.execute(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom d'utilisateur ou email déjà utilisé"
        )
    
    # Créer l'utilisateur
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@app.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return Token(access_token=access_token)


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# ============ Sync Endpoints ============

@app.post("/sync", response_model=SyncResponse)
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


@app.post("/sync/push", response_model=PushNotesResponse)
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


@app.post("/sync/pull", response_model=PullNotesResponse)
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


@app.get("/sync/notes", response_model=SyncedNotesResponse)
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


@app.post("/sync/compare", response_model=CompareResponse)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
