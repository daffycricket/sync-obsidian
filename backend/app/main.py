from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
    PullNotesRequest, PullNotesResponse
)
from .auth import (
    get_password_hash, authenticate_user, 
    create_access_token, get_current_user
)
from .sync import process_sync, push_notes, pull_notes


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

# CORS pour permettre les requêtes depuis Obsidian
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Health Check ============

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "syncobsidian"}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
