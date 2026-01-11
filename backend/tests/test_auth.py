"""
Tests d'intégration pour l'authentification.
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestHealthCheck:
    """Tests du health check."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Le health check doit retourner un statut healthy."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "syncobsidian"


class TestRegister:
    """Tests de l'inscription."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """L'inscription avec des données valides doit réussir."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data
        assert "hashed_password" not in data
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient):
        """L'inscription avec un username déjà utilisé doit échouer."""
        # Premier utilisateur
        await client.post(
            "/auth/register",
            json={
                "username": "duplicateuser",
                "email": "first@example.com",
                "password": "password123"
            }
        )
        
        # Deuxième utilisateur avec le même username
        response = await client.post(
            "/auth/register",
            json={
                "username": "duplicateuser",
                "email": "second@example.com",
                "password": "password456"
            }
        )
        
        assert response.status_code == 400
        assert "déjà utilisé" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        """L'inscription avec un email déjà utilisé doit échouer."""
        # Premier utilisateur
        await client.post(
            "/auth/register",
            json={
                "username": "user1",
                "email": "duplicate@example.com",
                "password": "password123"
            }
        )
        
        # Deuxième utilisateur avec le même email
        response = await client.post(
            "/auth/register",
            json={
                "username": "user2",
                "email": "duplicate@example.com",
                "password": "password456"
            }
        )
        
        assert response.status_code == 400
        assert "déjà utilisé" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """L'inscription avec un email invalide doit échouer."""
        response = await client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "not-an-email",
                "password": "password123"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestLogin:
    """Tests de la connexion."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """La connexion avec des identifiants valides doit réussir."""
        # Créer un utilisateur
        await client.post(
            "/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "password": "mypassword123"
            }
        )
        
        # Se connecter
        response = await client.post(
            "/auth/login",
            json={
                "username": "loginuser",
                "password": "mypassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 50  # JWT is long
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """La connexion avec un mauvais mot de passe doit échouer."""
        # Créer un utilisateur
        await client.post(
            "/auth/register",
            json={
                "username": "wrongpassuser",
                "email": "wrongpass@example.com",
                "password": "correctpassword"
            }
        )
        
        # Essayer de se connecter avec le mauvais mot de passe
        response = await client.post(
            "/auth/login",
            json={
                "username": "wrongpassuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """La connexion avec un utilisateur inexistant doit échouer."""
        response = await client.post(
            "/auth/login",
            json={
                "username": "nonexistent",
                "password": "somepassword"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"]


class TestAuthMe:
    """Tests du endpoint /auth/me."""
    
    @pytest.mark.asyncio
    async def test_get_me_authenticated(self, authenticated_client):
        """Un utilisateur authentifié peut récupérer ses informations."""
        client, token = authenticated_client
        
        response = await client.get("/auth/me", headers=auth_headers(token))
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_me_no_token(self, client: AsyncClient):
        """Sans token, l'accès doit être refusé."""
        response = await client.get("/auth/me")
        
        assert response.status_code in [401, 403]  # Unauthorized ou Forbidden
    
    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Avec un token invalide, l'accès doit être refusé."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_me_malformed_header(self, client: AsyncClient):
        """Avec un header mal formé, l'accès doit être refusé."""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "NotBearer token"}
        )
        
        assert response.status_code in [401, 403]  # Unauthorized ou Forbidden
