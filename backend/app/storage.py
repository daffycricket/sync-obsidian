import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional
from .config import settings


def get_user_storage_path(user_id: int) -> Path:
    """Retourne le chemin de stockage pour un utilisateur."""
    path = Path(settings.storage_path) / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_note_path(user_id: int, note_path: str) -> Path:
    """Retourne le chemin complet d'une note."""
    user_storage = get_user_storage_path(user_id)
    return user_storage / "notes" / note_path


def get_attachment_path(user_id: int, attachment_path: str) -> Path:
    """Retourne le chemin complet d'une pièce jointe."""
    user_storage = get_user_storage_path(user_id)
    return user_storage / "attachments" / attachment_path


def compute_hash(content: bytes) -> str:
    """Calcule le hash SHA256 d'un contenu."""
    return hashlib.sha256(content).hexdigest()


async def save_note(user_id: int, path: str, content: str) -> str:
    """Sauvegarde une note et retourne son hash."""
    note_path = get_note_path(user_id, path)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    
    content_bytes = content.encode("utf-8")
    content_hash = compute_hash(content_bytes)
    
    async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
        await f.write(content)
    
    return content_hash


async def read_note(user_id: int, path: str) -> Optional[str]:
    """Lit le contenu d'une note."""
    note_path = get_note_path(user_id, path)
    
    if not note_path.exists():
        return None
    
    async with aiofiles.open(note_path, "r", encoding="utf-8") as f:
        return await f.read()


async def delete_note(user_id: int, path: str) -> bool:
    """Supprime une note."""
    note_path = get_note_path(user_id, path)
    
    if note_path.exists():
        os.remove(note_path)
        return True
    return False


async def save_attachment(user_id: int, path: str, content: bytes) -> str:
    """Sauvegarde une pièce jointe et retourne son hash."""
    attachment_path = get_attachment_path(user_id, path)
    attachment_path.parent.mkdir(parents=True, exist_ok=True)
    
    content_hash = compute_hash(content)
    
    async with aiofiles.open(attachment_path, "wb") as f:
        await f.write(content)
    
    return content_hash


async def read_attachment(user_id: int, path: str) -> Optional[bytes]:
    """Lit le contenu d'une pièce jointe."""
    attachment_path = get_attachment_path(user_id, path)
    
    if not attachment_path.exists():
        return None
    
    async with aiofiles.open(attachment_path, "rb") as f:
        return await f.read()


async def delete_attachment(user_id: int, path: str) -> bool:
    """Supprime une pièce jointe."""
    attachment_path = get_attachment_path(user_id, path)
    
    if attachment_path.exists():
        os.remove(attachment_path)
        return True
    return False
