from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# Auth schemas
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Sync schemas
class NoteMetadata(BaseModel):
    path: str
    content_hash: str
    modified_at: datetime
    is_deleted: bool = False


class NoteContent(BaseModel):
    path: str
    content: str
    content_hash: str
    modified_at: datetime
    is_deleted: bool = False


class AttachmentMetadata(BaseModel):
    path: str
    content_hash: str
    size: int
    mime_type: Optional[str] = None
    modified_at: datetime
    is_deleted: bool = False


class AttachmentContent(BaseModel):
    """Contenu complet d'un attachment pour push/pull."""
    path: str
    content_base64: str  # Contenu encodé en base64
    content_hash: str
    size: int
    mime_type: Optional[str] = None
    modified_at: datetime
    is_deleted: bool = False


class SyncRequest(BaseModel):
    last_sync: Optional[datetime] = None
    notes: List[NoteMetadata] = []
    attachments: List[AttachmentMetadata] = []


class SyncResponse(BaseModel):
    server_time: datetime
    notes_to_pull: List[NoteMetadata] = []
    notes_to_push: List[str] = []  # Paths des notes que le serveur veut recevoir
    conflicts: List[NoteMetadata] = []
    attachments_to_pull: List[AttachmentMetadata] = []
    attachments_to_push: List[str] = []


class PushNotesRequest(BaseModel):
    notes: List[NoteContent]


class PushNotesResponse(BaseModel):
    success: List[str] = []
    failed: List[str] = []


class PullNotesRequest(BaseModel):
    paths: List[str]


class PullNotesResponse(BaseModel):
    notes: List[NoteContent]


class PushAttachmentsRequest(BaseModel):
    attachments: List[AttachmentContent]


class PushAttachmentsResponse(BaseModel):
    success: List[str] = []
    failed: List[str] = []


class PullAttachmentsRequest(BaseModel):
    paths: List[str]


class PullAttachmentsResponse(BaseModel):
    attachments: List[AttachmentContent]


# Schemas pour GET /sync/notes (visualisation des notes synchronisées)
class ReferencedAttachment(BaseModel):
    """Attachment référencé dans une note via ![[...]] ou [[...]]"""
    path: str
    exists: bool  # True si l'attachment existe sur le serveur
    size_bytes: Optional[int] = None


class SyncedNoteInfo(BaseModel):
    path: str
    content_hash: str
    modified_at: datetime
    synced_at: datetime
    is_deleted: bool
    size_bytes: Optional[int] = None
    referenced_attachments: List[ReferencedAttachment] = []

    class Config:
        from_attributes = True


class SyncedAttachmentInfo(BaseModel):
    path: str
    content_hash: str
    modified_at: datetime
    synced_at: datetime
    is_deleted: bool
    size_bytes: int
    mime_type: Optional[str] = None

    class Config:
        from_attributes = True


class SyncedNotesResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    total_pages: int
    notes: List[SyncedNoteInfo]
    attachments: List[SyncedAttachmentInfo]


# Schemas pour POST /sync/compare (comparaison client/serveur)
class ClientNoteInfo(BaseModel):
    """Note côté client pour comparaison."""
    path: str
    content_hash: str
    modified_at: datetime


class CompareRequest(BaseModel):
    """Requête de comparaison client/serveur."""
    notes: List[ClientNoteInfo]


class CompareSummary(BaseModel):
    """Résumé de la comparaison."""
    total_client: int
    total_server: int
    to_push: int
    to_pull: int
    conflicts: int
    identical: int
    deleted_on_server: int


class NoteToPush(BaseModel):
    """Note à envoyer au serveur."""
    path: str
    reason: str  # "not_on_server" ou "client_newer"
    client_modified: datetime


class NoteToPull(BaseModel):
    """Note à récupérer du serveur."""
    path: str
    reason: str  # "not_on_client" ou "server_newer"
    server_modified: datetime
    client_modified: Optional[datetime] = None


class NoteConflict(BaseModel):
    """Note en conflit."""
    path: str
    reason: str  # "both_modified"
    client_hash: str
    server_hash: str
    client_modified: datetime
    server_modified: datetime


class NoteDeletedOnServer(BaseModel):
    """Note supprimée sur le serveur."""
    path: str
    deleted_at: datetime


class CompareResponse(BaseModel):
    """Réponse de comparaison client/serveur."""
    server_time: datetime
    summary: CompareSummary
    to_push: List[NoteToPush] = []
    to_pull: List[NoteToPull] = []
    conflicts: List[NoteConflict] = []
    deleted_on_server: List[NoteDeletedOnServer] = []
