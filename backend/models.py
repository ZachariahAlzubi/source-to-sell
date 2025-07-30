"""
SQLModel database models for Source-to-Sell CRM
All tables as specified in tech spec section 4.2
"""

from datetime import datetime
from typing import Optional, Any
from sqlmodel import SQLModel, Field, create_engine, Session
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DATABASE_URL, echo=False)

class Account(SQLModel, table=True):
    """Company/prospect accounts"""
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    domain: str = Field(unique=True, index=True)
    website: Optional[str] = None
    industry: Optional[str] = None
    size_hint: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Source(SQLModel, table=True):
    """URL sources and extracted content"""
    __tablename__ = "sources"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    url: str
    title: str = ""
    raw_text: str = ""
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # success, error, pending

class Claim(SQLModel, table=True):
    """Profile claims with provenance"""
    __tablename__ = "claims"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    text: str
    source_url: Optional[str] = None
    evidence_quote: Optional[str] = None
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Activity(SQLModel, table=True):
    """Meeting summaries and notes"""
    __tablename__ = "activities"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    type: str  # call_summary, note
    content: str  # JSON string for structured data
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Asset(SQLModel, table=True):
    """Generated assets (email, pitch, landing page)"""
    __tablename__ = "assets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    kind: str  # email, pitch_md, landing_zip
    path: str  # file path
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Contact(SQLModel, table=True):
    """Contact persons (optional for MVP)"""
    __tablename__ = "contacts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id")
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

def create_db_and_tables():
    """Initialize database and create all tables"""
    SQLModel.metadata.create_all(engine)

# Utility functions for database operations
def get_session():
    """Get database session"""
    return Session(engine)