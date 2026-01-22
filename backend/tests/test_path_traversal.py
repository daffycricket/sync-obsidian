"""
Tests de protection contre les attaques path traversal.
"""
import pytest
from httpx import AsyncClient
from .conftest import auth_headers


class TestPathTraversalProtection:
    """Tests de protection contre les attaques path traversal."""
    
    @pytest.mark.asyncio
    async def test_valid_paths_accepted(self, authenticated_client):
        """Les chemins valides doivent être acceptés."""
        client, token = authenticated_client
        
        valid_paths = [
            "note.md",
            "dossier/note.md",
            "dossier/sous-dossier/note.md",
            "note avec espaces.md",
            "note-avec-tirets.md",
            "note_avec_underscores.md",
            "Noté Accentuée.md",
        ]
        
        for path in valid_paths:
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": path,
                            "content": f"# {path}",
                            "content_hash": f"hash-{path}",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200, f"Failed for valid path: {path}"
            assert path in response.json()["success"], f"Path {path} should be in success list"
    
    @pytest.mark.asyncio
    async def test_path_traversal_attacks_rejected(self, authenticated_client):
        """Les attaques path traversal doivent être rejetées."""
        client, token = authenticated_client
        
        malicious_paths = [
            "../../../etc/passwd",
            "../../../../etc/passwd",
            "../config.py",
            "./../secret.md",
            "notes/../../etc/passwd",
            "notes/../..",
            "notes/../../../../../../etc/passwd",
            "../",
            "..",
            "./..",
        ]
        
        for path in malicious_paths:
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": path,
                            "content": "malicious content",
                            "content_hash": "malicious-hash",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200, f"Request should succeed but note should fail for: {path}"
            result = response.json()
            assert path in result["failed"], f"Path {path} should be in failed list"
            assert path not in result["success"], f"Path {path} should NOT be in success list"
    
    @pytest.mark.asyncio
    async def test_absolute_paths_rejected(self, authenticated_client):
        """Les chemins absolus doivent être rejetés."""
        client, token = authenticated_client
        
        absolute_paths = [
            "/etc/passwd",
            "/absolute/path.md",
            "/root/.ssh/id_rsa",
            "C:\\Windows\\System32",  # Windows path (devrait être rejeté aussi)
        ]
        
        for path in absolute_paths:
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": path,
                            "content": "malicious content",
                            "content_hash": "malicious-hash",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            assert path in result["failed"], f"Absolute path {path} should be rejected"
            assert path not in result["success"]
    
    @pytest.mark.asyncio
    async def test_deep_paths_within_limit_accepted(self, authenticated_client):
        """Les chemins profonds mais dans la limite (30 niveaux) doivent être acceptés."""
        client, token = authenticated_client
        
        # Créer un chemin avec exactement 30 niveaux (29 dossiers + 1 fichier = 30 parties)
        deep_path = "/".join([f"folder{i}" for i in range(29)]) + "/note.md"
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": deep_path,
                        "content": "# Deep note",
                        "content_hash": "deep-hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert deep_path in response.json()["success"]
    
    @pytest.mark.asyncio
    async def test_too_deep_paths_rejected(self, authenticated_client):
        """Les chemins trop profonds (> 30 niveaux) doivent être rejetés."""
        client, token = authenticated_client
        
        # Créer un chemin avec 31 niveaux (dépasse la limite)
        too_deep_path = "/".join([f"folder{i}" for i in range(31)]) + "/note.md"
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": too_deep_path,
                        "content": "# Too deep note",
                        "content_hash": "too-deep-hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert too_deep_path in result["failed"], "Path with > 30 levels should be rejected"
        assert too_deep_path not in result["success"]
    
    @pytest.mark.asyncio
    async def test_empty_path_rejected(self, authenticated_client):
        """Les chemins vides doivent être rejetés."""
        client, token = authenticated_client
        
        empty_paths = ["", "   ", "\t", "\n"]
        
        for path in empty_paths:
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": path,
                            "content": "content",
                            "content_hash": "hash",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            result = response.json()
            assert path in result["failed"] or len(result["success"]) == 0
    
    @pytest.mark.asyncio
    async def test_pull_endpoint_rejects_malicious_paths(self, authenticated_client):
        """L'endpoint /sync/pull doit rejeter les chemins malveillants."""
        client, token = authenticated_client
        
        malicious_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "../config.py",
        ]
        
        for path in malicious_paths:
            response = await client.post(
                "/sync/pull",
                headers=auth_headers(token),
                json={"paths": [path]}
            )
            
            assert response.status_code == 200
            # Le chemin malveillant ne doit pas apparaître dans les résultats
            notes = response.json()["notes"]
            note_paths = [note["path"] for note in notes]
            assert path not in note_paths, f"Malicious path {path} should not be returned"
    
    @pytest.mark.asyncio
    async def test_no_system_files_created(self, authenticated_client, setup_database):
        """Aucun fichier système ne doit être créé lors d'une attaque."""
        import os
        from pathlib import Path
        
        client, token = authenticated_client
        
        # Tenter de créer un fichier système
        malicious_path = "../../../etc/test_syncobsidian_hack"
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": malicious_path,
                        "content": "hacked",
                        "content_hash": "hack-hash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert malicious_path in response.json()["failed"]
        
        # Vérifier que le fichier système n'existe pas
        system_file = Path("/etc/test_syncobsidian_hack")
        assert not system_file.exists(), "System file should not be created"
    
    @pytest.mark.asyncio
    async def test_path_traversal_in_deletion(self, authenticated_client):
        """Les suppressions avec chemins malveillants doivent être rejetées."""
        client, token = authenticated_client
        
        malicious_path = "../../../etc/passwd"
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": malicious_path,
                        "content": "",
                        "content_hash": "",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": True
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert malicious_path in result["failed"], "Deletion with malicious path should fail"
    
    @pytest.mark.asyncio
    async def test_multiple_malicious_paths_in_batch(self, authenticated_client):
        """Un batch avec plusieurs chemins malveillants doit tous les rejeter."""
        client, token = authenticated_client
        
        malicious_paths = [
            "../../../etc/passwd",
            "/etc/shadow",
            "../config.py",
            "normal-note.md",  # Un chemin valide dans le batch
        ]
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": path,
                        "content": f"# {path}",
                        "content_hash": f"hash-{path}",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                    for path in malicious_paths
                ]
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Les chemins malveillants doivent être rejetés
        assert "../../../etc/passwd" in result["failed"]
        assert "/etc/shadow" in result["failed"]
        assert "../config.py" in result["failed"]
        
        # Le chemin valide doit être accepté
        assert "normal-note.md" in result["success"]
    
    @pytest.mark.asyncio
    async def test_retrocompatibility_valid_paths(self, authenticated_client):
        """Vérifier que les chemins valides des tests existants fonctionnent toujours."""
        client, token = authenticated_client
        
        # Chemins utilisés dans test_edge_cases.py
        retro_paths = [
            "empty.md",
            "note avec espaces.md",
            "note-avec-tirets.md",
            "note_avec_underscores.md",
            "Noté Accentuée.md",
        ]
        
        for path in retro_paths:
            response = await client.post(
                "/sync/push",
                headers=auth_headers(token),
                json={
                    "notes": [
                        {
                            "path": path,
                            "content": f"# {path}",
                            "content_hash": f"hash-{path}",
                            "modified_at": "2026-01-11T10:00:00",
                            "is_deleted": False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            assert path in response.json()["success"], f"Retrocompatible path {path} should work"
