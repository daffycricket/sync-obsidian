"""
Tests pour vérifier que les fichiers non modifiés ne sont pas renvoyés inutilement.
"""
import pytest
import hashlib
from datetime import datetime, timedelta
from httpx import AsyncClient
from .conftest import auth_headers


class TestUnchangedFilesNotPushed:
    """Tests pour vérifier que les fichiers non modifiés ne sont pas envoyés à nouveau."""
    
    @pytest.mark.asyncio
    async def test_unchanged_file_not_pushed_on_second_sync(self, authenticated_client):
        """
        Bug corrigé : Un fichier non modifié ne doit pas être envoyé à nouveau.
        
        Scénario :
        1. Client push un fichier
        2. Sync OK, last_sync est mis à jour
        3. Sync à nouveau sans modifier le fichier
        4. Le fichier ne doit PAS être dans notes_to_push
        """
        client, token = authenticated_client
        
        content = "# Note non modifiée\n\nContenu original."
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        modified_time = "2026-01-19T10:00:00Z"
        
        # 1. Push le fichier initialement
        push_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": "unchanged-note.md",
                    "content": content,
                    "content_hash": content_hash,
                    "modified_at": modified_time,
                    "is_deleted": False
                }]
            }
        )
        assert push_resp.status_code == 200
        
        # 2. Premier sync - établir last_sync
        sync1_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [{
                    "path": "unchanged-note.md",
                    "content_hash": content_hash,
                    "modified_at": modified_time,
                    "is_deleted": False
                }],
                "attachments": []
            }
        )
        assert sync1_resp.status_code == 200
        sync1_data = sync1_resp.json()
        last_sync = sync1_data["server_time"]
        
        # 3. Deuxième sync immédiatement après - le fichier n'a PAS changé
        sync2_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": last_sync,
                "notes": [{
                    "path": "unchanged-note.md",
                    "content_hash": content_hash,  # Même hash
                    "modified_at": modified_time,  # Même timestamp
                    "is_deleted": False
                }],
                "attachments": []
            }
        )
        assert sync2_resp.status_code == 200
        sync2_data = sync2_resp.json()
        
        # Le fichier ne doit PAS être dans notes_to_push car il n'a pas changé
        assert "unchanged-note.md" not in sync2_data["notes_to_push"]
        assert len(sync2_data["conflicts"]) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_unchanged_files_not_pushed(self, authenticated_client):
        """
        Plusieurs fichiers non modifiés ne doivent pas être renvoyés.
        """
        client, token = authenticated_client
        
        files = [
            {
                "path": "file1.md",
                "content": "# File 1\n\nContent 1.",
                "modified_at": "2026-01-19T10:00:00Z"
            },
            {
                "path": "file2.md",
                "content": "# File 2\n\nContent 2.",
                "modified_at": "2026-01-19T10:00:00Z"
            },
            {
                "path": "file3.md",
                "content": "# File 3\n\nContent 3.",
                "modified_at": "2026-01-19T10:00:00Z"
            }
        ]
        
        # Calculer les hashes
        for f in files:
            f["content_hash"] = hashlib.sha256(f["content"].encode('utf-8')).hexdigest()
        
        # 1. Push tous les fichiers
        push_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [{
                    "path": f["path"],
                    "content": f["content"],
                    "content_hash": f["content_hash"],
                    "modified_at": f["modified_at"],
                    "is_deleted": False
                } for f in files]
            }
        )
        assert push_resp.status_code == 200
        
        # 2. Premier sync
        sync1_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [{
                    "path": f["path"],
                    "content_hash": f["content_hash"],
                    "modified_at": f["modified_at"],
                    "is_deleted": False
                } for f in files],
                "attachments": []
            }
        )
        assert sync1_resp.status_code == 200
        last_sync = sync1_resp.json()["server_time"]
        
        # 3. Deuxième sync - aucun fichier modifié
        sync2_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": last_sync,
                "notes": [{
                    "path": f["path"],
                    "content_hash": f["content_hash"],
                    "modified_at": f["modified_at"],
                    "is_deleted": False
                } for f in files],
                "attachments": []
            }
        )
        assert sync2_resp.status_code == 200
        sync2_data = sync2_resp.json()
        
        # Aucun fichier ne doit être dans notes_to_push
        assert len(sync2_data["notes_to_push"]) == 0
        assert len(sync2_data["conflicts"]) == 0
    
    @pytest.mark.asyncio
    async def test_changed_file_pushed_unchanged_not_pushed(self, authenticated_client):
        """
        Seuls les fichiers modifiés doivent être envoyés, pas les non modifiés.
        """
        client, token = authenticated_client
        
        file1_content_v1 = "# File 1\n\nVersion 1"
        file1_hash_v1 = hashlib.sha256(file1_content_v1.encode('utf-8')).hexdigest()
        file2_content = "# File 2\n\nUnchanged"
        file2_hash = hashlib.sha256(file2_content.encode('utf-8')).hexdigest()
        
        # 1. Push les deux fichiers
        push_resp = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "file1.md",
                        "content": file1_content_v1,
                        "content_hash": file1_hash_v1,
                        "modified_at": "2026-01-19T10:00:00Z",
                        "is_deleted": False
                    },
                    {
                        "path": "file2.md",
                        "content": file2_content,
                        "content_hash": file2_hash,
                        "modified_at": "2026-01-19T10:00:00Z",
                        "is_deleted": False
                    }
                ]
            }
        )
        assert push_resp.status_code == 200
        
        # 2. Premier sync
        sync1_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [
                    {
                        "path": "file1.md",
                        "content_hash": file1_hash_v1,
                        "modified_at": "2026-01-19T10:00:00Z",
                        "is_deleted": False
                    },
                    {
                        "path": "file2.md",
                        "content_hash": file2_hash,
                        "modified_at": "2026-01-19T10:00:00Z",
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        assert sync1_resp.status_code == 200
        last_sync = sync1_resp.json()["server_time"]
        
        # 3. Modifier seulement file1
        file1_content_v2 = "# File 1\n\nVersion 2"
        file1_hash_v2 = hashlib.sha256(file1_content_v2.encode('utf-8')).hexdigest()
        
        sync2_resp = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": last_sync,
                "notes": [
                    {
                        "path": "file1.md",
                        "content_hash": file1_hash_v2,  # Hash différent
                        "modified_at": "2026-01-19T11:00:00Z",  # Plus récent
                        "is_deleted": False
                    },
                    {
                        "path": "file2.md",
                        "content_hash": file2_hash,  # Même hash
                        "modified_at": "2026-01-19T10:00:00Z",  # Même timestamp
                        "is_deleted": False
                    }
                ],
                "attachments": []
            }
        )
        assert sync2_resp.status_code == 200
        sync2_data = sync2_resp.json()
        
        # Seul file1 doit être dans notes_to_push
        assert "file1.md" in sync2_data["notes_to_push"]
        assert "file2.md" not in sync2_data["notes_to_push"]
