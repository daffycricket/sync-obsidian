from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="owner", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    path = Column(String(500), nullable=False)  # Chemin relatif dans le vault
    content_hash = Column(String(64), nullable=False)  # SHA256 du contenu
    modified_at = Column(DateTime, nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    owner = relationship("User", back_populates="notes")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'path', name='uq_notes_user_path'),
        {"sqlite_autoincrement": True},
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    path = Column(String(500), nullable=False)
    content_hash = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    modified_at = Column(DateTime, nullable=False)
    synced_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    owner = relationship("User", back_populates="attachments")

    __table_args__ = (
        UniqueConstraint('user_id', 'path', name='uq_attachments_user_path'),
    )
