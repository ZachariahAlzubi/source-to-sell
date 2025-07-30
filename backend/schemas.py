"""
Pydantic schemas for API requests/responses
JSON schemas as specified in tech spec section 4.4
"""

from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# Request schemas

class ProspectCreateRequest(BaseModel):
    """Request to create new prospect"""
    company_name: Optional[str] = None
    company_url: str = Field(..., description="Main company website URL")
    extra_urls: Optional[List[str]] = Field(
        default=None,
        description="Additional URLs to fetch (max 2)"
    )
    
    @validator('extra_urls')
    def validate_extra_urls(cls, v):
        if v and len(v) > 2:
            raise ValueError("Maximum 2 extra URLs allowed")
        return v

class GenerateAssetsRequest(BaseModel):
    """Request to generate assets with persona"""
    persona: str = Field(
        default="Exec",
        description="Target persona: Exec, Buyer, or Champion"
    )
    
    @validator('persona')
    def validate_persona(cls, v):
        allowed = ["Exec", "Buyer", "Champion"]
        if v not in allowed:
            raise ValueError(f"Persona must be one of: {allowed}")
        return v

# Response schemas (JSON schemas from tech spec)

class ClaimData(BaseModel):
    """Individual claim with provenance"""
    text: str = Field(..., description="The claim text")
    source_url: Optional[str] = Field(
        None, 
        description="Source URL if available, null for unsourced claims"
    )
    evidence_quote: Optional[str] = Field(
        None,
        description="Supporting quote from source"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0"
    )

class CompanyProfile(BaseModel):
    """Company profile with claims and provenance"""
    company_name: str
    industry: Optional[str] = None
    size_hint: Optional[str] = None
    products: List[str] = Field(default_factory=list)
    pain_points: List[str] = Field(default_factory=list)
    recent_events: List[str] = Field(default_factory=list)
    claims: List[ClaimData] = Field(default_factory=list)

class EmailDraft(BaseModel):
    """Generated email draft"""
    persona: str = Field(..., description="Target persona")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(
        ...,
        description="Email body (120-180 words)",
        max_length=1000  # Allow some buffer over 180 words
    )
    cta: str = Field(..., description="Call to action")
    
    @validator('body')
    def validate_word_count(cls, v):
        word_count = len(v.split())
        if word_count > 200:  # Generous upper limit
            raise ValueError("Email body should be 120-180 words")
        return v

class PitchObjection(BaseModel):
    """Pitch objection with response"""
    objection: str
    response: str

class PitchOutline(BaseModel):
    """Generated pitch outline"""
    agenda: List[str] = Field(
        ...,
        description="6-8 main agenda points",
        min_items=6,
        max_items=8
    )
    objections: List[PitchObjection] = Field(
        ...,
        description="2 objections with rebuttals",
        min_items=2,
        max_items=2
    )

class NextStep(BaseModel):
    """Meeting next step item"""
    owner: str = Field(..., description="Person responsible")
    task: str = Field(..., description="Task description")
    due_date: Optional[date] = Field(None, description="Due date if specified")

class MeetingSummary(BaseModel):
    """Meeting transcript summary"""
    summary: str = Field(..., description="High-level meeting summary")
    next_steps: List[NextStep] = Field(
        default_factory=list,
        description="Action items from meeting"
    )
    blockers: List[str] = Field(
        default_factory=list,
        description="Identified blockers or concerns"
    )
    objections: List[str] = Field(
        default_factory=list,
        description="Objections raised during meeting"
    )

# Error response schema
class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)