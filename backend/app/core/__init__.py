"""
Module core - Infrastructure technique (config, DB, sécurité, storage, logging).
"""
from .config import settings, get_settings
from .database import Base, engine, async_session_maker, get_db, init_db
from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    get_current_user,
    authenticate_user,
)
from .storage import (
    sanitize_path,
    get_user_storage_path,
    get_note_path,
    get_attachment_path,
    compute_hash,
    save_note,
    read_note,
    delete_note,
    save_attachment,
    read_attachment,
    delete_attachment,
    get_note_size,
    get_attachment_size,
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Database
    "Base",
    "engine",
    "async_session_maker",
    "get_db",
    "init_db",
    # Security
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "authenticate_user",
    # Storage
    "sanitize_path",
    "get_user_storage_path",
    "get_note_path",
    "get_attachment_path",
    "compute_hash",
    "save_note",
    "read_note",
    "delete_note",
    "save_attachment",
    "read_attachment",
    "delete_attachment",
    "get_note_size",
    "get_attachment_size",
]
