"""
Configuration pytest pour les tests d'intégration.
"""
import os
import asyncio
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Chemins absolus dans le workspace
TEST_DIR = Path("/Users/nico/syncobsidian/backend/test_data")
TEST_DB_PATH = TEST_DIR / "test.db"
TEST_STORAGE_PATH = TEST_DIR / "storage"

# Configuration de test - doit être avant les imports de l'app
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["STORAGE_PATH"] = str(TEST_STORAGE_PATH)
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"

from app.main import app
from app.database import Base, get_db
from app.config import settings


def ensure_test_dirs():
    """Créer les dossiers de test."""
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    TEST_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def cleanup_test_dirs():
    """Nettoyer les dossiers de test."""
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


# Engine de test
ensure_test_dirs()
test_engine = create_async_engine(
    f"sqlite+aiosqlite:///{TEST_DB_PATH}",
    echo=False,
    future=True
)

test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def override_get_db():
    async with test_async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Créer un event loop pour la session de test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def setup_database():
    """Créer/nettoyer la base de données avant chaque test."""
    # Créer les dossiers
    ensure_test_dirs()
    
    # Créer les tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Nettoyer après le test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(setup_database) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP pour les tests."""
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    """Client HTTP avec un utilisateur authentifié."""
    # Créer un utilisateur
    await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Se connecter
    response = await client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    token = response.json()["access_token"]
    
    yield client, token


def auth_headers(token: str) -> dict:
    """Génère les headers d'authentification."""
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Session de base de données pour les tests nécessitant un accès direct."""
    async with test_async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def authenticated_client_with_db(client: AsyncClient, db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, str, AsyncSession, int], None]:
    """Client HTTP avec un utilisateur authentifié et accès à la base de données.
    Retourne (client, token, db_session, user_id).
    """
    # Créer un utilisateur
    await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    # Se connecter
    response = await client.post(
        "/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    token = response.json()["access_token"]

    # Récupérer l'ID utilisateur depuis la DB
    from app.models import User
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.username == "testuser"))
    user = result.scalar_one()

    yield client, token, db_session, user.id
