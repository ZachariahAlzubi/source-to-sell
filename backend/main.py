"""
Source-to-Sell MVP - FastAPI Backend
Main application entry point with all endpoints
"""

import os
import logging
import time
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import json
import zipfile
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from sqlmodel import Session, select

from models import (
    Account, Source, Claim, Activity, Asset,
    engine, create_db_and_tables
)
from schemas import (
    ProspectCreateRequest, CompanyProfile, EmailDraft, 
    PitchOutline, MeetingSummary, GenerateAssetsRequest
)
from services import LLMService, ExtractionService, AssetService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Source-to-Sell API",
    description="Prospect research and asset generation API",
    version="1.0.0"
)

# CORS middleware for extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
extraction_service = ExtractionService()
asset_service = AssetService()

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Database dependency
def get_session():
    with Session(engine) as session:
        yield session

# Request/Response timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {process_time:.3f}s")
    return response

# API Routes

@app.post("/prospects/create")
async def create_prospect(
    request: ProspectCreateRequest,
    session: Session = Depends(get_session)
):
    """Create or update prospect account and fetch sources"""
    try:
        start_time = time.time()
        
        # Extract domain from company URL for deduplication
        domain = extraction_service.extract_domain(request.company_url)
        
        # Check for existing account by domain
        existing_account = session.exec(
            select(Account).where(Account.domain == domain)
        ).first()
        
        if existing_account:
            account = existing_account
            logger.info(f"Found existing account: {account.name} ({domain})")
        else:
            # Create new account
            account = Account(
                name=request.company_name or domain,
                domain=domain,
                website=request.company_url,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            logger.info(f"Created new account: {account.name} ({domain})")
        
        # Collect all URLs to fetch
        urls_to_fetch = [request.company_url]
        if request.extra_urls:
            urls_to_fetch.extend([url for url in request.extra_urls if url])
        
        # Fetch and extract content from URLs
        for url in urls_to_fetch:
            # Check if source already exists
            existing_source = session.exec(
                select(Source).where(
                    Source.account_id == account.id,
                    Source.url == url
                )
            ).first()
            
            if not existing_source:
                try:
                    content = extraction_service.extract_content(url)
                    source = Source(
                        account_id=account.id,
                        url=url,
                        title=content.get("title", ""),
                        raw_text=content.get("text", "")[:10000],  # Limit text size
                        fetched_at=datetime.utcnow(),
                        status="success"
                    )
                    session.add(source)
                except Exception as e:
                    logger.error(f"Failed to fetch {url}: {str(e)}")
                    source = Source(
                        account_id=account.id,
                        url=url,
                        title="",
                        raw_text="",
                        fetched_at=datetime.utcnow(),
                        status=f"error: {str(e)}"
                    )
                    session.add(source)
        
        session.commit()
        
        elapsed = time.time() - start_time
        logger.info(f"Prospect creation completed in {elapsed:.2f}s")
        
        return {
            "account_id": account.id,
            "message": "Account created/updated successfully",
            "sources_fetched": len(urls_to_fetch),
            "processing_time": elapsed
        }
        
    except Exception as e:
        logger.error(f"Error creating prospect: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts")
async def list_accounts(session: Session = Depends(get_session)):
    """List all accounts"""
    accounts = session.exec(select(Account)).all()
    return [
        {
            "id": account.id,
            "name": account.name,
            "domain": account.domain,
            "website": account.website,
            "industry": account.industry,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
        for account in accounts
    ]

@app.get("/accounts/{account_id}")
async def get_account(account_id: int, session: Session = Depends(get_session)):
    """Get account details with all related data"""
    account = session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get related data
    sources = session.exec(
        select(Source).where(Source.account_id == account_id)
    ).all()
    
    claims = session.exec(
        select(Claim).where(Claim.account_id == account_id)
    ).all()
    
    activities = session.exec(
        select(Activity).where(Activity.account_id == account_id)
    ).all()
    
    assets = session.exec(
        select(Asset).where(Asset.account_id == account_id)
    ).all()
    
    return {
        "account": account,
        "sources": sources,
        "claims": claims,
        "activities": activities,
        "assets": assets
    }

@app.post("/accounts/{account_id}/generate_profile")
async def generate_profile(
    account_id: int,
    session: Session = Depends(get_session)
):
    """Generate company profile using LLM with provenance"""
    try:
        start_time = time.time()
        
        account = session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Get sources for context
        sources = session.exec(
            select(Source).where(
                Source.account_id == account_id,
                Source.status == "success"
            )
        ).all()
        
        if not sources:
            raise HTTPException(
                status_code=400, 
                detail="No successful sources found for this account"
            )
        
        # Generate profile using LLM
        profile = await llm_service.generate_profile(account, sources)
        
        # Update account with profile data
        account.industry = profile.industry
        account.size_hint = profile.size_hint
        account.summary = f"{profile.company_name} - {', '.join(profile.products) if profile.products else 'N/A'}"
        account.updated_at = datetime.utcnow()
        
        # Clear existing claims and add new ones
        existing_claims = session.exec(
            select(Claim).where(Claim.account_id == account_id)
        ).all()
        for claim in existing_claims:
            session.delete(claim)
        
        # Add new claims
        for claim_data in profile.claims:
            claim = Claim(
                account_id=account_id,
                text=claim_data.text,
                source_url=claim_data.source_url,
                evidence_quote=claim_data.evidence_quote,
                confidence=claim_data.confidence,
                created_at=datetime.utcnow()
            )
            session.add(claim)
        
        session.commit()
        
        elapsed = time.time() - start_time
        
        # Calculate provenance metrics
        sourced_claims = len([c for c in profile.claims if c.source_url])
        total_claims = len(profile.claims)
        provenance_coverage = sourced_claims / total_claims if total_claims > 0 else 0
        
        logger.info(f"Profile generated in {elapsed:.2f}s, provenance: {provenance_coverage:.2%}")
        
        return {
            "profile": profile,
            "processing_time": elapsed,
            "provenance_coverage": provenance_coverage,
            "claims_count": total_claims
        }
        
    except Exception as e:
        logger.error(f"Error generating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accounts/{account_id}/generate_assets")
async def generate_assets(
    account_id: int,
    request: GenerateAssetsRequest,
    session: Session = Depends(get_session)
):
    """Generate email, pitch, and landing page assets"""
    try:
        start_time = time.time()
        
        account = session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Get latest claims for context
        claims = session.exec(
            select(Claim).where(Claim.account_id == account_id)
        ).all()
        
        if not claims:
            raise HTTPException(
                status_code=400,
                detail="No profile data found. Generate profile first."
            )
        
        # Generate assets
        email_draft = await llm_service.generate_email(
            account, claims, request.persona
        )
        pitch_outline = await llm_service.generate_pitch(account, claims)
        
        # Create asset files
        email_path = asset_service.create_email_file(account_id, email_draft)
        pitch_path = asset_service.create_pitch_file(account_id, pitch_outline)
        landing_zip_path = asset_service.create_landing_page(
            account, claims, email_draft
        )
        
        # Save asset records
        assets_data = [
            ("email", email_path),
            ("pitch_md", pitch_path),
            ("landing_zip", landing_zip_path)
        ]
        
        for asset_kind, file_path in assets_data:
            # Remove existing asset of same type
            existing = session.exec(
                select(Asset).where(
                    Asset.account_id == account_id,
                    Asset.kind == asset_kind
                )
            ).first()
            if existing:
                session.delete(existing)
            
            # Add new asset
            asset = Asset(
                account_id=account_id,
                kind=asset_kind,
                path=file_path,
                created_at=datetime.utcnow()
            )
            session.add(asset)
        
        session.commit()
        
        elapsed = time.time() - start_time
        logger.info(f"Assets generated in {elapsed:.2f}s")
        
        return {
            "email_draft": email_draft,
            "pitch_outline": pitch_outline,
            "assets": {
                "email_path": email_path,
                "pitch_path": pitch_path,
                "landing_zip_path": landing_zip_path
            },
            "processing_time": elapsed
        }
        
    except Exception as e:
        logger.error(f"Error generating assets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accounts/{account_id}/upload_transcript")
async def upload_transcript(
    account_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Upload and summarize meeting transcript"""
    try:
        start_time = time.time()
        
        account = session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Read transcript content
        content = await file.read()
        transcript_text = content.decode('utf-8')
        
        # Generate meeting summary
        meeting_summary = await llm_service.generate_meeting_summary(transcript_text)
        
        # Create activity record
        activity = Activity(
            account_id=account_id,
            type="call_summary",
            content=meeting_summary.dict(),
            created_at=datetime.utcnow()
        )
        session.add(activity)
        session.commit()
        
        elapsed = time.time() - start_time
        logger.info(f"Transcript processed in {elapsed:.2f}s")
        
        return {
            "meeting_summary": meeting_summary,
            "activity_id": activity.id,
            "processing_time": elapsed
        }
        
    except Exception as e:
        logger.error(f"Error processing transcript: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/accounts/{account_id}")
async def delete_account(account_id: int, session: Session = Depends(get_session)):
    """Hard delete account and all related data"""
    try:
        account = session.get(Account, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Delete related records (cascading)
        related_tables = [Source, Claim, Activity, Asset]
        for table in related_tables:
            records = session.exec(
                select(table).where(table.account_id == account_id)
            ).all()
            for record in records:
                session.delete(record)
        
        # Delete asset files
        assets_dir = Path(f"assets/account_{account_id}")
        if assets_dir.exists():
            shutil.rmtree(assets_dir)
        
        # Delete account
        session.delete(account)
        session.commit()
        
        logger.info(f"Account {account_id} deleted successfully")
        
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Web UI Routes

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: Session = Depends(get_session)):
    """Main dashboard page"""
    accounts = session.exec(select(Account)).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "accounts": accounts}
    )

@app.get("/accounts/{account_id}/view", response_class=HTMLResponse)
async def account_detail(
    request: Request,
    account_id: int,
    session: Session = Depends(get_session)
):
    """Account detail page"""
    account_data = await get_account(account_id, session)
    return templates.TemplateResponse(
        "account_detail.html",
        {"request": request, **account_data}
    )

@app.get("/download/{asset_type}/{account_id}")
async def download_asset(
    asset_type: str,
    account_id: int,
    session: Session = Depends(get_session)
):
    """Download generated asset files"""
    asset = session.exec(
        select(Asset).where(
            Asset.account_id == account_id,
            Asset.kind == asset_type
        )
    ).first()
    
    if not asset or not Path(asset.path).exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return FileResponse(
        path=asset.path,
        filename=Path(asset.path).name,
        media_type='application/octet-stream'
    )

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and create directories"""
    create_db_and_tables()
    
    # Create necessary directories
    directories = ["assets", "static", "templates"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    logger.info("Source-to-Sell API started successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)