from app import db
from sqlalchemy import String, Integer, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List, Optional

class User(db.Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    skill_level: Mapped[str] = mapped_column(String(20), nullable=False, default='Beginner')  # Beginner, Intermediate, Advanced
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    gear_items: Mapped[List["GearItem"]] = relationship("GearItem", back_populates="user", cascade="all, delete-orphan")
    chat_sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class GearItem(db.Model):
    __tablename__ = 'gear_items'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('users.id'), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # camera_body, lens, lighting, backdrop, accessory
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    specifications: Mapped[Optional[str]] = mapped_column(JSON)  # Store additional specs as JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="gear_items")

class ChatSession(db.Model):
    __tablename__ = 'chat_sessions'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('users.id'), nullable=False)
    session_token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    current_step: Mapped[Optional[int]] = mapped_column(Integer, default=0)  # For beginner step tracking
    conversation_context: Mapped[Optional[str]] = mapped_column(JSON)  # Store context as JSON
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, bot, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    step_number: Mapped[Optional[int]] = mapped_column(Integer)  # For beginner step tracking
    message_metadata: Mapped[Optional[str]] = mapped_column(JSON)  # Additional message data
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
