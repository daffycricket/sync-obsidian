"""
Tests de compatibilité des hashes entre le plugin et le serveur.
Vérifie que SHA256 est utilisé de manière cohérente.
"""
import pytest
import hashlib
from httpx import AsyncClient
from .conftest import auth_headers


class TestHashFormat:
    """Tests du format des hashes."""
    
    def test_sha256_format(self):
        """Le hash SHA256 doit être une chaîne de 64 caractères hexadécimaux."""
        content = "# Test\n\nContenu de test."
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        assert len(content_hash) == 64
        assert all(c in '0123456789abcdef' for c in content_hash)
    
    def test_sha256_deterministic(self):
        """Le même contenu doit toujours produire le même hash."""
        content = "# Note identique"
        hash1 = hashlib.sha256(content.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        assert hash1 == hash2
    
    def test_sha256_different_content(self):
        """Des contenus différents doivent produire des hashes différents."""
        content1 = "# Version 1"
        content2 = "# Version 2"
        hash1 = hashlib.sha256(content1.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(content2.encode('utf-8')).hexdigest()
        
        assert hash1 != hash2


class TestHashCompatibility:
    """Tests de compatibilité hash entre client et serveur."""
    
    @pytest.mark.asyncio
    async def test_identical_file_no_sync_needed(self, authenticated_client):
        """
        Si le client et le serveur ont le même fichier avec le même contenu,
        aucune sync ne doit être demandée.
        """
        client, token = authenticated_client
        content = "# Note identique\n\nContenu partagé entre devices."
        
        # Calculer le hash SHA256 (comme le plugin le fera après correction)
        correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Simuler Device A qui push
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "shared-identical.md",
                    "content": content,
                    "content_hash": correct_hash,
                    "modified_at": "2026-01-12T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        # Simuler Device B qui sync avec le MÊME contenu et MÊME hash
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-01T00:00:00",
                "notes": [{
                    "path": "shared-identical.md",
                    "content_hash": correct_hash,  # Même hash car même contenu
                    "modified_at": "2026-01-12T10:00:00",
                    "is_deleted": False
                }],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Aucune action nécessaire car hashes identiques
        assert "shared-identical.md" not in data["notes_to_push"]
        assert all(n["path"] != "shared-identical.md" for n in data["notes_to_pull"])
        assert all(n["path"] != "shared-identical.md" for n in data["conflicts"])
    
    @pytest.mark.asyncio
    async def test_different_content_triggers_sync(self, authenticated_client):
        """
        Si le contenu change, le hash change et une sync doit être demandée.
        """
        client, token = authenticated_client
        
        content_v1 = "# Version 1\n\nContenu original."
        content_v2 = "# Version 2\n\nContenu modifié."
        hash_v1 = hashlib.sha256(content_v1.encode('utf-8')).hexdigest()
        hash_v2 = hashlib.sha256(content_v2.encode('utf-8')).hexdigest()
        
        # Vérifier que les hashes sont différents
        assert hash_v1 != hash_v2
        
        # Push version 1
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "versioned-note.md",
                    "content": content_v1,
                    "content_hash": hash_v1,
                    "modified_at": "2026-01-12T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        # Sync avec version 2 (hash différent, client plus récent)
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": "2026-01-01T00:00:00",
                "notes": [{
                    "path": "versioned-note.md",
                    "content_hash": hash_v2,
                    "modified_at": "2026-01-12T12:00:00",  # Plus récent
                    "is_deleted": False
                }],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Hash différent + client plus récent = push demandé
        assert "versioned-note.md" in data["notes_to_push"]
    
    @pytest.mark.asyncio
    async def test_server_recalculates_hash_on_push(self, authenticated_client):
        """
        Le serveur doit recalculer le hash au push et stocker le bon.
        """
        client, token = authenticated_client
        content = "# Note avec hash recalculé"
        
        # Hash correct
        correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Push avec un hash "incorrect" (le serveur devrait le recalculer)
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "recalculated-hash.md",
                    "content": content,
                    "content_hash": "wrong-hash-from-client",
                    "modified_at": "2026-01-12T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        # Pull pour vérifier le hash stocké
        response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["recalculated-hash.md"]}
        )
        
        assert response.status_code == 200
        note = response.json()["notes"][0]
        
        # Le serveur a recalculé le hash correctement
        assert note["content_hash"] == correct_hash


class TestHashUnicode:
    """Tests de hash avec contenu Unicode."""
    
    @pytest.mark.asyncio
    async def test_hash_unicode_content(self, authenticated_client):
        """Le hash doit fonctionner avec du contenu Unicode."""
        client, token = authenticated_client
        
        content = "# 日本語テスト\n\nÉmojis: 🎉🚀\nAccents: éèêë café naïve"
        correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Push avec contenu Unicode
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "unicode-hash-test.md",
                    "content": content,
                    "content_hash": correct_hash,
                    "modified_at": "2026-01-12T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        assert response.status_code == 200
        assert "unicode-hash-test.md" in response.json()["success"]
        
        # Pull et vérifier le hash
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["unicode-hash-test.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert note["content_hash"] == correct_hash
        assert note["content"] == content
    
    @pytest.mark.asyncio
    async def test_hash_empty_content(self, authenticated_client):
        """Le hash d'un contenu vide doit être cohérent."""
        client, token = authenticated_client
        
        content = ""
        correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Hash connu de la chaîne vide en SHA256
        expected_empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert correct_hash == expected_empty_hash
        
        # Push note vide
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "empty-content.md",
                    "content": content,
                    "content_hash": correct_hash,
                    "modified_at": "2026-01-12T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        assert response.status_code == 200


class TestNewDeviceScenario:
    """Tests du scénario nouveau device."""
    
    @pytest.mark.asyncio
    async def test_new_device_same_file_same_content(self, authenticated_client):
        """
        Nouveau device avec un fichier identique existant.
        Aucune sync ne devrait être nécessaire.
        """
        client, token = authenticated_client
        
        content = "# Mon fichier\n\nContenu que j'ai sur les deux devices."
        correct_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Device A push le fichier
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "existing-on-both.md",
                    "content": content,
                    "content_hash": correct_hash,
                    "modified_at": "2026-01-10T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        # Device B (nouveau) sync pour la première fois avec le même fichier
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,  # Premier sync
                "notes": [{
                    "path": "existing-on-both.md",
                    "content_hash": correct_hash,  # Même hash
                    "modified_at": "2026-01-10T10:00:00",  # Même timestamp
                    "is_deleted": False
                }],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Fichiers identiques = aucune action
        assert "existing-on-both.md" not in data["notes_to_push"]
        assert all(n["path"] != "existing-on-both.md" for n in data["notes_to_pull"])
    
    @pytest.mark.asyncio
    async def test_new_device_same_file_different_content(self, authenticated_client):
        """
        Nouveau device avec un fichier de même nom mais contenu différent.
        Le plus récent doit gagner.
        """
        client, token = authenticated_client
        
        content_server = "# Version serveur"
        content_local = "# Version locale (plus récente)"
        hash_server = hashlib.sha256(content_server.encode('utf-8')).hexdigest()
        hash_local = hashlib.sha256(content_local.encode('utf-8')).hexdigest()
        
        # Device A push une version ancienne
        await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "different-content.md",
                    "content": content_server,
                    "content_hash": hash_server,
                    "modified_at": "2026-01-10T10:00:00",
                    "is_deleted": False
                }]
            }
        )
        
        # Device B a une version locale plus récente
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [{
                    "path": "different-content.md",
                    "content_hash": hash_local,  # Hash différent
                    "modified_at": "2026-01-12T15:00:00",  # Plus récent
                    "is_deleted": False
                }],
                "attachments": []
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Client plus récent = push demandé
        assert "different-content.md" in data["notes_to_push"]
