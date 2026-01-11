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
