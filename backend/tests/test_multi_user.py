"""
Tests d'intégration pour la séparation des données entre utilisateurs.
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestMultiUserIsolation:
    """Tests d'isolation des données entre utilisateurs."""
    
    @pytest.mark.asyncio
    async def test_users_cannot_see_each_others_notes(self, client: AsyncClient, setup_database):
        """Les notes d'un utilisateur ne sont pas visibles par un autre."""
        # Créer deux utilisateurs
        await client.post(
            "/auth/register",
            json={
                "username": "user1",
                "email": "user1@example.com",
                "password": "password1"
            }
        )
        await client.post(
            "/auth/register",
            json={
                "username": "user2",
                "email": "user2@example.com",
                "password": "password2"
            }
        )
        
        # Connexion user1
        resp1 = await client.post(
            "/auth/login",
            json={"username": "user1", "password": "password1"}
        )
        token1 = resp1.json()["access_token"]
        
        # Connexion user2
        resp2 = await client.post(
            "/auth/login",
            json={"username": "user2", "password": "password2"}
        )
        token2 = resp2.json()["access_token"]
        
        # User1 push une note privée
        await client.post(
            "/sync/push",
            headers=auth_headers(token1),
            json={
                "notes": [
                    {
                        "path": "private-user1.md",
                        "content": "# Secret de User1",
                        "content_hash": "secrethash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # User2 essaie de récupérer la note de User1
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token2),
            json={"paths": ["private-user1.md"]}
        )
        
        # User2 ne doit pas voir la note de User1
        assert pull_response.status_code == 200
        assert pull_response.json()["notes"] == []
        
        # User2 sync ne doit pas voir la note de User1
        sync_response = await client.post(
            "/sync",
            headers=auth_headers(token2),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": []
            }
        )
        
        assert sync_response.status_code == 200
        # Pas de notes à pull pour User2
        assert sync_response.json()["notes_to_pull"] == []
    
    @pytest.mark.asyncio
    async def test_same_filename_different_users(self, client: AsyncClient, setup_database):
        """Deux utilisateurs peuvent avoir des notes avec le même nom."""
        # Créer deux utilisateurs
        await client.post(
            "/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "alicepass"
            }
        )
        await client.post(
            "/auth/register",
            json={
                "username": "bob",
                "email": "bob@example.com",
                "password": "bobpass"
            }
        )
        
        # Connexions
        resp_alice = await client.post(
            "/auth/login",
            json={"username": "alice", "password": "alicepass"}
        )
        token_alice = resp_alice.json()["access_token"]
        
        resp_bob = await client.post(
            "/auth/login",
            json={"username": "bob", "password": "bobpass"}
        )
        token_bob = resp_bob.json()["access_token"]
        
        # Même nom de fichier, contenu différent
        await client.post(
            "/sync/push",
            headers=auth_headers(token_alice),
            json={
                "notes": [
                    {
                        "path": "todo.md",
                        "content": "# TODO Alice\n\n- Faire les courses",
                        "content_hash": "alicehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        await client.post(
            "/sync/push",
            headers=auth_headers(token_bob),
            json={
                "notes": [
                    {
                        "path": "todo.md",
                        "content": "# TODO Bob\n\n- Réviser l'examen",
                        "content_hash": "bobhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        # Chaque utilisateur récupère SA version
        pull_alice = await client.post(
            "/sync/pull",
            headers=auth_headers(token_alice),
            json={"paths": ["todo.md"]}
        )
        
        pull_bob = await client.post(
            "/sync/pull",
            headers=auth_headers(token_bob),
            json={"paths": ["todo.md"]}
        )
        
        assert "TODO Alice" in pull_alice.json()["notes"][0]["content"]
        assert "TODO Bob" in pull_bob.json()["notes"][0]["content"]
        
        # Vérifier que les contenus sont bien différents
        assert pull_alice.json()["notes"][0]["content"] != pull_bob.json()["notes"][0]["content"]
