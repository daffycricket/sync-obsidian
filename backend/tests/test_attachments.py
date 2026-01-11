"""
Tests d'intégration pour les pièces jointes.
"""
import pytest
import base64
from httpx import AsyncClient
from .conftest import auth_headers


class TestAttachmentSync:
    """Tests de synchronisation des pièces jointes."""
    
    @pytest.mark.asyncio
    async def test_sync_with_attachment_metadata(self, authenticated_client):
        """Sync avec métadonnées de pièces jointes."""
        client, token = authenticated_client
        
        response = await client.post(
            "/sync",
            headers=auth_headers(token),
            json={
                "last_sync": None,
                "notes": [],
                "attachments": [
                    {
                        "path": "images/photo.png",
                        "content_hash": "imghash123",
                        "size": 1024,
                        "mime_type": "image/png",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Les pièces jointes sont gérées séparément
        assert "attachments_to_pull" in data
        assert "attachments_to_push" in data
    
    @pytest.mark.asyncio
    async def test_sync_note_with_embedded_image_link(self, authenticated_client):
        """Note avec lien vers image embarquée."""
        client, token = authenticated_client
        
        content = """# Note avec image

Voici une image :

![[images/screenshot.png]]

Et une autre avec chemin relatif :
![Alt text](./attachments/diagram.png)
"""
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "note-with-image.md",
                        "content": content,
                        "content_hash": "notehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert "note-with-image.md" in response.json()["success"]
        
        # Vérifier que le contenu est préservé
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["note-with-image.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert "![[images/screenshot.png]]" in note["content"]
        assert "![Alt text](./attachments/diagram.png)" in note["content"]


class TestVariousFileTypes:
    """Tests avec différents types de fichiers Markdown."""
    
    @pytest.mark.asyncio
    async def test_note_with_frontmatter(self, authenticated_client):
        """Note avec frontmatter YAML."""
        client, token = authenticated_client
        
        content = """---
title: Ma note
tags:
  - test
  - integration
date: 2026-01-11
aliases:
  - "note test"
---

# Contenu après frontmatter

Ceci est le contenu principal.
"""
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "frontmatter-note.md",
                        "content": content,
                        "content_hash": "fmhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        
        # Vérifier que le frontmatter est préservé
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["frontmatter-note.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert "---" in note["content"]
        assert "title: Ma note" in note["content"]
        assert "tags:" in note["content"]
    
    @pytest.mark.asyncio
    async def test_note_with_code_blocks(self, authenticated_client):
        """Note avec blocs de code."""
        client, token = authenticated_client
        
        content = '''# Code Examples

## Python
```python
def hello():
    print("Hello, World!")
```

## JavaScript
```javascript
const greet = () => {
    console.log("Hello!");
};
```

## Inline code

Use `pip install` to install packages.
'''
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "code-note.md",
                        "content": content,
                        "content_hash": "codehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        
        # Vérifier la préservation du code
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["code-note.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert "```python" in note["content"]
        assert "def hello():" in note["content"]
    
    @pytest.mark.asyncio
    async def test_note_with_wikilinks(self, authenticated_client):
        """Note avec wikilinks Obsidian."""
        client, token = authenticated_client
        
        content = """# Note avec liens

Lien simple : [[Autre note]]

Lien avec alias : [[Autre note|Mon alias]]

Lien vers section : [[Autre note#Section]]

Lien vers fichier embarqué : ![[document.pdf]]
"""
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "wikilinks-note.md",
                        "content": content,
                        "content_hash": "wikihash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["wikilinks-note.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert "[[Autre note]]" in note["content"]
        assert "[[Autre note|Mon alias]]" in note["content"]
    
    @pytest.mark.asyncio
    async def test_note_with_tables(self, authenticated_client):
        """Note avec tableaux Markdown."""
        client, token = authenticated_client
        
        content = """# Tableau de données

| Nom | Âge | Ville |
|-----|-----|-------|
| Alice | 30 | Paris |
| Bob | 25 | Lyon |
| Charlie | 35 | Marseille |

Fin du document.
"""
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "table-note.md",
                        "content": content,
                        "content_hash": "tablehash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["table-note.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert "| Nom | Âge | Ville |" in note["content"]
        assert "| Alice | 30 | Paris |" in note["content"]
    
    @pytest.mark.asyncio
    async def test_very_long_note(self, authenticated_client):
        """Note très longue (plusieurs Ko)."""
        client, token = authenticated_client
        
        # Générer une note de ~50KB
        paragraphs = []
        for i in range(500):
            paragraphs.append(f"## Section {i}\n\nCeci est le paragraphe numéro {i}. " * 3)
        
        content = "# Document très long\n\n" + "\n\n".join(paragraphs)
        
        response = await client.post(
            "/sync/push",
            headers=auth_headers(token),
            json={
                "notes": [
                    {
                        "path": "very-long-note.md",
                        "content": content,
                        "content_hash": "longhash",
                        "modified_at": "2026-01-11T10:00:00",
                        "is_deleted": False
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        assert "very-long-note.md" in response.json()["success"]
        
        # Vérifier qu'on peut la récupérer entièrement
        pull_response = await client.post(
            "/sync/pull",
            headers=auth_headers(token),
            json={"paths": ["very-long-note.md"]}
        )
        
        note = pull_response.json()["notes"][0]
        assert len(note["content"]) > 40000  # Au moins 40KB
        assert "## Section 499" in note["content"]
