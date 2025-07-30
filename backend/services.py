"""
Service classes for LLM, extraction, and asset generation
Core business logic separated from API endpoints
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import zipfile
import shutil

import requests
from bs4 import BeautifulSoup
import openai
from jinja2 import Environment, FileSystemLoader

from schemas import (
    CompanyProfile, EmailDraft, PitchOutline, MeetingSummary,
    ClaimData, PitchObjection, NextStep
)
from models import Account, Source, Claim

logger = logging.getLogger(__name__)

class ExtractionService:
    """Service for extracting content from web pages"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return url.split('/')[0] if '/' in url else url
    
    def extract_content(self, url: str) -> Dict[str, str]:
        """Extract title and main content from URL"""
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = self.session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.get_text().strip()
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            # Extract main content (simple approach)
            main_content = soup.find('main') or soup.find('article') or soup.find('div', {'class': 'content'})
            if not main_content:
                main_content = soup.find('body')
            
            if main_content:
                text = main_content.get_text()
            else:
                text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return {
                "title": title,
                "text": text,
                "url": url
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            raise Exception(f"Failed to extract content: {str(e)}")

class LLMService:
    """Service for all LLM interactions"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set - LLM features will not work")
    
    async def generate_profile(self, account: Account, sources: List[Source]) -> CompanyProfile:
        """Generate company profile with provenance from sources"""
        
        # Prepare source context
        source_context = ""
        for i, source in enumerate(sources, 1):
            source_context += f"\n--- Source {i}: {source.url} ---\n"
            source_context += f"Title: {source.title}\n"
            source_context += f"Content: {source.raw_text[:2000]}\n"  # Limit per source
        
        prompt = f"""
You are a B2B sales researcher. Analyze the provided source content and generate a detailed company profile.

CRITICAL REQUIREMENTS:
1. Every factual claim MUST be backed by evidence from the provided sources
2. If you cannot find evidence in sources, mark source_url as null and set confidence ≤ 0.3
3. Include direct quotes as evidence_quote for each sourced claim
4. Confidence scores: 0.8-1.0 (clear evidence), 0.5-0.7 (implied), 0.1-0.3 (unsourced/inferred)

Company: {account.name}
Domain: {account.domain}

Source Content:
{source_context}

Generate a JSON response with this exact structure:
{{
  "company_name": "{account.name}",
  "industry": "specific industry category",
  "size_hint": "employee count range or revenue",
  "products": ["specific product 1", "product 2"],
  "pain_points": ["specific challenge 1", "challenge 2"],
  "recent_events": ["recent development 1", "event 2"],
  "claims": [
    {{
      "text": "Factual claim about the company",
      "source_url": "https://source-url-if-available" or null,
      "evidence_quote": "Direct quote supporting this claim" or null,
      "confidence": 0.85
    }}
  ]
}}

Ensure all claims are specific and actionable for sales purposes.
"""
        
        try:
            response = await self._call_llm(prompt, max_retries=2)
            profile_data = json.loads(response)
            
            # Validate and create claims
            claims = []
            for claim_data in profile_data.get("claims", []):
                claims.append(ClaimData(**claim_data))
            
            profile = CompanyProfile(
                company_name=profile_data["company_name"],
                industry=profile_data.get("industry"),
                size_hint=profile_data.get("size_hint"),
                products=profile_data.get("products", []),
                pain_points=profile_data.get("pain_points", []),
                recent_events=profile_data.get("recent_events", []),
                claims=claims
            )
            
            return profile
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise Exception("LLM returned invalid JSON")
        except Exception as e:
            logger.error(f"Error generating profile: {e}")
            raise Exception(f"Profile generation failed: {str(e)}")
    
    async def generate_email(self, account: Account, claims: List[Claim], persona: str) -> EmailDraft:
        """Generate personalized email draft"""
        
        # Prepare context from claims
        context = f"Company: {account.name}\n"
        context += f"Industry: {account.industry or 'Unknown'}\n"
        context += f"Size: {account.size_hint or 'Unknown'}\n\n"
        
        context += "Key insights:\n"
        for claim in claims[:5]:  # Use top 5 claims
            if claim.confidence > 0.5:
                context += f"- {claim.text}\n"
        
        persona_instructions = {
            "Exec": "Write for C-level executives. Focus on business impact, ROI, and strategic value.",
            "Buyer": "Write for decision makers. Focus on solution benefits, competitive advantages.",
            "Champion": "Write for internal advocates. Focus on technical benefits and team impact."
        }
        
        prompt = f"""
Write a personalized sales email for {persona} persona.

{persona_instructions.get(persona, "")}

Context:
{context}

Requirements:
- Subject line that captures attention
- Body: 120-180 words maximum
- Professional but conversational tone
- One clear call-to-action
- Reference specific company insights
- No placeholder text or brackets

Return JSON format:
{{
  "persona": "{persona}",
  "subject": "Compelling subject line",
  "body": "Email body content (120-180 words)",
  "cta": "Specific call to action"
}}
"""
        
        try:
            response = await self._call_llm(prompt)
            email_data = json.loads(response)
            return EmailDraft(**email_data)
        except Exception as e:
            logger.error(f"Error generating email: {e}")
            raise Exception(f"Email generation failed: {str(e)}")
    
    async def generate_pitch(self, account: Account, claims: List[Claim]) -> PitchOutline:
        """Generate pitch outline with objections"""
        
        context = f"Company: {account.name}\n"
        context += f"Industry: {account.industry or 'Unknown'}\n"
        
        context += "Key insights:\n"
        for claim in claims[:8]:  # Use top claims
            if claim.confidence > 0.5:
                context += f"- {claim.text}\n"
        
        prompt = f"""
Create a sales pitch outline for this prospect:

{context}

Generate exactly 6-8 agenda points and exactly 2 objections with responses.

Return JSON format:
{{
  "agenda": [
    "Opening & rapport building",
    "Discovery of current challenges",
    "Solution overview tailored to {account.name}",
    "ROI and business case",
    "Implementation approach",
    "Next steps and timeline",
    "Q&A and objection handling",
    "Commitment and follow-up"
  ],
  "objections": [
    {{
      "objection": "Common objection like budget/timing/priority",
      "response": "Specific response addressing their situation"
    }},
    {{
      "objection": "Technical or integration concern",
      "response": "Detailed response with proof points"
    }}
  ]
}}
"""
        
        try:
            response = await self._call_llm(prompt)
            pitch_data = json.loads(response)
            
            objections = [PitchObjection(**obj) for obj in pitch_data["objections"]]
            
            return PitchOutline(
                agenda=pitch_data["agenda"],
                objections=objections
            )
        except Exception as e:
            logger.error(f"Error generating pitch: {e}")
            raise Exception(f"Pitch generation failed: {str(e)}")
    
    async def generate_meeting_summary(self, transcript: str) -> MeetingSummary:
        """Generate meeting summary from transcript"""
        
        prompt = f"""
Analyze this meeting transcript and extract key information:

{transcript[:8000]}  # Limit transcript size

Return JSON format:
{{
  "summary": "High-level summary of the meeting",
  "next_steps": [
    {{
      "owner": "Person responsible",
      "task": "Specific task description",
      "due_date": "YYYY-MM-DD or null"
    }}
  ],
  "blockers": ["Identified blocker or concern"],
  "objections": ["Objection raised during meeting"]
}}

Focus on actionable items and explicit concerns mentioned.
"""
        
        try:
            response = await self._call_llm(prompt)
            summary_data = json.loads(response)
            
            next_steps = [NextStep(**step) for step in summary_data.get("next_steps", [])]
            
            return MeetingSummary(
                summary=summary_data["summary"],
                next_steps=next_steps,
                blockers=summary_data.get("blockers", []),
                objections=summary_data.get("objections", [])
            )
        except Exception as e:
            logger.error(f"Error generating meeting summary: {e}")
            raise Exception(f"Meeting summary failed: {str(e)}")
    
    async def _call_llm(self, prompt: str, max_retries: int = 1) -> str:
        """Make LLM API call with retries"""
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a B2B sales research assistant. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"LLM call failed, retrying: {e}")
                    time.sleep(1)
                    continue
                raise e

class AssetService:
    """Service for generating and managing asset files"""
    
    def __init__(self):
        self.assets_dir = Path("assets")
        self.templates_dir = Path("templates")
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True
        )
    
    def create_email_file(self, account_id: int, email: EmailDraft) -> str:
        """Create email draft file"""
        account_dir = self.assets_dir / f"account_{account_id}"
        account_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = account_dir / f"email_draft_{int(time.time())}.txt"
        
        content = f"""Subject: {email.subject}

{email.body}

---
Call to Action: {email.cta}
Persona: {email.persona}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        file_path.write_text(content)
        return str(file_path)
    
    def create_pitch_file(self, account_id: int, pitch: PitchOutline) -> str:
        """Create pitch outline markdown file"""
        account_dir = self.assets_dir / f"account_{account_id}"
        account_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = account_dir / f"pitch_outline_{int(time.time())}.md"
        
        content = f"""# Sales Pitch Outline

## Agenda

"""
        for i, item in enumerate(pitch.agenda, 1):
            content += f"{i}. {item}\n"
        
        content += f"""

## Objection Handling

"""
        for obj in pitch.objections:
            content += f"""
**Objection:** {obj.objection}
**Response:** {obj.response}

"""
        
        content += f"""
---
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        file_path.write_text(content)
        return str(file_path)
    
    def create_landing_page(self, account: Account, claims: List[Claim], email: EmailDraft) -> str:
        """Create landing page HTML/CSS zip file"""
        account_dir = self.assets_dir / f"account_{account_id}"
        account_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory for landing page files
        temp_dir = account_dir / f"landing_temp_{int(time.time())}"
        temp_dir.mkdir()
        
        # Get high-confidence claims for proof points
        proof_claims = [c for c in claims if c.confidence > 0.7][:3]
        
        # Generate HTML
        html_content = self._generate_landing_html(account, proof_claims, email)
        (temp_dir / "index.html").write_text(html_content)
        
        # Generate CSS
        css_content = self._generate_landing_css()
        (temp_dir / "styles.css").write_text(css_content)
        
        # Create zip file
        zip_path = account_dir / f"landing_page_{int(time.time())}.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in temp_dir.iterdir():
                zipf.write(file_path, file_path.name)
        
        # Clean up temp directory
        shutil.rmtree(temp_dir)
        
        return str(zip_path)
    
    def _generate_landing_html(self, account: Account, claims: List[Claim], email: EmailDraft) -> str:
        """Generate landing page HTML"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solutions for {account.name}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Tailored Solutions for {account.name}</h1>
            <p class="subheader">Accelerate your growth with our proven platform</p>
        </header>
        
        <main>
            <section class="value-props">
                <h2>Why leading {account.industry or 'companies'} choose us</h2>
                <div class="benefits">
                    <div class="benefit">
                        <h3>🚀 Rapid Implementation</h3>
                        <p>Deploy in weeks, not months, with our battle-tested platform</p>
                    </div>
                    <div class="benefit">
                        <h3>📈 Measurable ROI</h3>
                        <p>See immediate impact with comprehensive analytics and reporting</p>
                    </div>
                    <div class="benefit">
                        <h3>🔧 Seamless Integration</h3>
                        <p>Works with your existing tools and workflows</p>
                    </div>
                </div>
            </section>
            
            {self._generate_proof_section(claims)}
            
            <section class="cta-section">
                <h2>Ready to transform your operations?</h2>
                <p>Join {account.name} and hundreds of other industry leaders</p>
                <button class="cta-button">{email.cta}</button>
                <p class="cta-note">Book a personalized demo to see how we can help {account.name}</p>
            </section>
        </main>
        
        <footer>
            <p>Generated for {account.name} • {datetime.now().strftime('%B %Y')}</p>
        </footer>
    </div>
</body>
</html>"""
    
    def _generate_proof_section(self, claims: List[Claim]) -> str:
        """Generate proof points section"""
        if not claims:
            return ""
        
        section = '<section class="proof-section">\n<h2>Built for companies like yours</h2>\n<div class="proof-points">\n'
        
        for claim in claims[:3]:
            section += f'''
                <div class="proof-point">
                    <p>"{claim.text}"</p>
                    {f'<cite>Source: {claim.source_url}</cite>' if claim.source_url else ''}
                </div>
            '''
        
        section += '</div>\n</section>'
        return section
    
    def _generate_landing_css(self) -> str:
        """Generate landing page CSS"""
        return """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

header {
    text-align: center;
    color: white;
    margin-bottom: 3rem;
}

header h1 {
    font-size: 3rem;
    margin-bottom: 1rem;
    font-weight: 700;
}

.subheader {
    font-size: 1.25rem;
    opacity: 0.9;
}

main {
    background: white;
    border-radius: 12px;
    padding: 3rem;
    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}

.value-props h2, .proof-section h2 {
    text-align: center;
    margin-bottom: 2rem;
    color: #2d3748;
    font-size: 2rem;
}

.benefits {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
}

.benefit {
    padding: 1.5rem;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    text-align: center;
}

.benefit h3 {
    margin-bottom: 1rem;
    color: #4a5568;
    font-size: 1.25rem;
}

.proof-section {
    margin: 3rem 0;
    padding: 2rem;
    background: #f7fafc;
    border-radius: 8px;
}

.proof-points {
    display: grid;
    gap: 1.5rem;
}

.proof-point {
    padding: 1rem;
    background: white;
    border-left: 4px solid #667eea;
    border-radius: 4px;
}

.proof-point cite {
    font-size: 0.875rem;
    color: #718096;
    font-style: normal;
}

.cta-section {
    text-align: center;
    padding: 3rem 0;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-radius: 8px;
    margin-top: 3rem;
}

.cta-section h2 {
    color: white;
    margin-bottom: 1rem;
}

.cta-button {
    background: white;
    color: #667eea;
    padding: 1rem 2rem;
    border: none;
    border-radius: 6px;
    font-size: 1.125rem;
    font-weight: 600;
    cursor: pointer;
    margin: 1rem 0;
    transition: transform 0.2s;
}

.cta-button:hover {
    transform: translateY(-2px);
}

.cta-note {
    opacity: 0.9;
    font-size: 0.875rem;
}

footer {
    text-align: center;
    margin-top: 2rem;
    color: white;
    opacity: 0.8;
}

@media (max-width: 768px) {
    .container {
        padding: 1rem;
    }
    
    header h1 {
        font-size: 2rem;
    }
    
    main {
        padding: 2rem;
    }
    
    .benefits {
        grid-template-columns: 1fr;
    }
}
"""