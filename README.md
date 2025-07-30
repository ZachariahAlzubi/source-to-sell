# Source-to-Sell MVP

A browser extension + FastAPI backend for B2B prospect research and asset generation. Capture company information from any website, generate AI-powered profiles with provenance, and create tailored sales assets (emails, pitch outlines, landing pages).

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Chrome browser
- OpenAI API key

### 1. Backend Setup

```bash
# Clone and navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (and optionally OPENAI_MODEL)

# Start the API server
python main.py
```

The API will be available at `http://localhost:8000`

### 2. Browser Extension Setup

```bash
# In Chrome, go to: chrome://extensions/
# Enable "Developer mode"
# Click "Load unpacked"
# Select the 'extension' folder
```

### 3. One-Click Demo

```bash
# Seed with demo companies (requires API running)
cd backend
python seed_data.py
```

This creates 5 demo accounts (Stripe, Shopify, Notion, Figma, Airtable) with generated profiles and assets.

## 📋 Features

### Core Functionality
- **Prospect Capture**: Browser extension detects company info from any website
- **Content Extraction**: Fetches and analyzes up to 3 URLs per prospect
- **AI Profile Generation**: LLM-powered company profiles with source citations
- **Asset Generation**: Tailored emails, pitch outlines, and landing pages
- **Transcript Analysis**: Upload meeting recordings for automated summaries

### AI & Provenance
- Every factual claim includes source URLs and confidence scores
- Unsourced claims explicitly flagged
- Evidence quotes from original content
- Provenance coverage metrics

### Generated Assets
1. **Email Drafts**: Persona-based (Exec/Buyer/Champion), 120-180 words
2. **Pitch Outlines**: 6-8 agenda points + 2 objections with rebuttals
3. **Landing Pages**: Static HTML/CSS with proof points, downloadable zip

## 🛠 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chrome MV3    │    │   FastAPI       │    │   SQLite        │
│   Extension     │───▶│   Backend       │───▶│   Database      │
│                 │    │                 │    │                 │
│ • Popup UI      │    │ • REST API      │    │ • Accounts      │
│ • Content Script│    │ • LLM Service   │    │ • Sources       │
│ • Company       │    │ • Extraction    │    │ • Claims        │
│   Detection     │    │ • Asset Gen     │    │ • Assets        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tech Stack
- **Frontend**: Chrome Extension (Manifest V3), HTML/CSS/JS
- **Backend**: FastAPI, SQLModel, SQLite
- **AI**: OpenAI GPT-4o (configurable)
- **Extraction**: BeautifulSoup, requests
- **Templates**: Jinja2 for asset generation

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prospects/create` | POST | Create prospect from URLs |
| `/accounts` | GET | List all accounts |
| `/accounts/{id}` | GET | Account details |
| `/accounts/{id}/generate_profile` | POST | Generate AI profile |
| `/accounts/{id}/generate_assets` | POST | Generate sales assets |
| `/accounts/{id}/upload_transcript` | POST | Process meeting transcript |
| `/accounts/{id}` | DELETE | Delete account |

## 📊 Database Schema

```sql
-- Core tables
accounts: id, name, domain, website, industry, summary, timestamps
sources: id, account_id, url, title, text, status, fetched_at
claims: id, account_id, text, source_url, evidence_quote, confidence
assets: id, account_id, kind, path, created_at
activities: id, account_id, type, content, created_at
```

## 🎯 Usage Flow

1. **Capture**: Visit company website → Extension popup → Fill form → Create prospect
2. **Profile**: API fetches URLs → Extracts content → LLM generates profile with claims
3. **Assets**: Generate persona-based email → Pitch outline → Landing page
4. **Download**: Access assets via web UI or direct download links

## ⚙️ Configuration

### Environment Variables (.env)
```bash
OPENAI_API_KEY=sk-...           # Required for LLM features
OPENAI_MODEL=gpt-4-0613         # LLM model (optional)
APP_BASE_URL=http://localhost:8000
DB_PATH=./app.db
LOG_LEVEL=INFO
```

### Alternative LLM Providers
The system is designed for easy LLM swapping:
- Default: OpenAI GPT-4o
- Alternative: Claude 3.5 (future)
- Local: Ollama + Mixtral/Llama3 (future)

## 🧪 Testing

### Manual Test Flow
1. Install extension and start backend
2. Visit `https://stripe.com` 
3. Click extension icon → Capture prospect
4. Go to dashboard → Generate profile
5. Generate assets → Download landing page
6. Verify: Claims have sources, email is 120-180 words

### Seed Data Testing
```bash
python seed_data.py
```
Creates 5 complete prospects for testing all features.

## 📈 Performance Targets

- Profile generation: ≤10s (2 URLs)
- Asset generation: ≤6s per asset (p50)
- Provenance coverage: ≥70% of claims sourced
- Email length: 120-180 words

## 🔒 Privacy & Security

- **Local-first**: SQLite database, local file storage
- **No telemetry**: All data stays local
- **Content filtering**: Redacts emails/phones in LLM prompts
- **Consent notices**: For transcript uploads
- **Delete function**: Complete data removal

## 🚧 Limitations (MVP)

- Single-user only (no multi-tenant)
- No live Salesforce integration
- No real-time meeting hooks
- Local development only
- Manual prospect capture (no automation)

## 🔮 Future Enhancements

- [ ] Salesforce OAuth integration
- [ ] Multi-tenant hosting
- [ ] Zoom/Teams webhook integration
- [ ] RAG-based company knowledge base
- [ ] Advanced prospect scoring
- [ ] Team collaboration features

## 🐛 Troubleshooting

### Common Issues

**Extension not detecting company**
- Ensure you're on a company website (not Google, etc.)
- Try refreshing the page
- Check browser console for errors

**API connection errors**
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS settings if using different ports
- Ensure OpenAI API key is valid

**Profile generation fails**
- Check OpenAI API key and quota
- Verify sources were fetched successfully
- Look for API errors in backend logs

**Assets not generating**
- Ensure profile exists first
- Check file permissions in assets/ directory
- Verify Jinja2 templates are present

### Debug Mode
```bash
# Start with debug logging
LOG_LEVEL=DEBUG python main.py

# Check database directly
sqlite3 app.db ".tables"
sqlite3 app.db "SELECT * FROM accounts;"
```

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

---

**Built with ❤️ for B2B sales teams**

For support or questions, open an issue on GitHub.