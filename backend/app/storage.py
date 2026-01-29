import os
import hashlib
import aiofiles
from pathlib import Path
from typing import Optional
from .config import settings


def sanitize_path(path: str) -> str:
    """
    Valide et nettoie un chemin de fichier pour empêcher les attaques path traversal.
    
    Args:
        path: Chemin relatif à valider
        
    Returns:
        Chemin normalisé et validé
        
    Raises:
        ValueError: Si le chemin est invalide ou représente une tentative d'attaque
    """
    if not path or not path.strip():
        raise ValueError("Le chemin ne peut pas être vide")
    
    # Normaliser le chemin pour résoudre les .. et .
    normalized = os.path.normpath(path)
    
    # Vérifier qu'il ne commence pas par / ou \
    if normalized.startswith(('/', '\\')):
        raise ValueError("Le chemin ne peut pas commencer par / ou \\")
    
    # Vérifier qu'il n'y a pas de chemin absolu (après vérification du début)
    # Cela capture aussi les chemins Windows comme C:\
    if os.path.isabs(normalized) or (len(normalized) >= 2 and normalized[1] == ':'):
        raise ValueError("Les chemins absolus ne sont pas autorisés")
    
    # Vérifier qu'il n'y a pas de .. après normalisation
    # (normpath résout les .. mais on vérifie quand même)
    if '..' in normalized:
        raise ValueError("Les chemins avec .. ne sont pas autorisés")
    
    # Vérifier la profondeur maximale (30 niveaux)
    parts = Path(normalized).parts
    if len(parts) > 30:
        raise ValueError(f"Le chemin est trop profond (max 30 niveaux, trouvé {len(parts)})")
    
    return normalized


def get_user_storage_path(user_id: int) -> Path:
    """Retourne le chemin de stockage pour un utilisateur."""
    path = Path(settings.storage_path) / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_note_path(user_id: int, note_path: str) -> Path:
    """Retourne le chemin complet d'une note."""
    sanitized = sanitize_path(note_path)
    user_storage = get_user_storage_path(user_id)
    return user_storage / "notes" / sanitized


def get_attachment_path(user_id: int, attachment_path: str) -> Path:
    """Retourne le chemin complet d'une pièce jointe."""
    sanitized = sanitize_path(attachment_path)
    user_storage = get_user_storage_path(user_id)
    return user_storage / "attachments" / sanitized


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


def get_note_size(user_id: int, path: str) -> Optional[int]:
    """Retourne la taille d'une note en octets, ou None si elle n'existe pas."""
    try:
        note_path = get_note_path(user_id, path)
        if note_path.exists():
            return note_path.stat().st_size
    except (ValueError, OSError):
        pass
    return None


def get_attachment_size(user_id: int, path: str) -> Optional[int]:
    """Retourne la taille d'une pièce jointe en octets, ou None si elle n'existe pas."""
    try:
        attachment_path = get_attachment_path(user_id, path)
        if attachment_path.exists():
            return attachment_path.stat().st_size
    except (ValueError, OSError):
        pass
    return None
