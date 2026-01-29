# Meta AI Analyst

A **read-only** AI-powered analytics platform for Meta (Facebook) ad accounts. Get conversational insights about your ad performance without any risk of modifying your campaigns.

## Features

- **Daily Data Snapshots**: Automatically collects ad account metrics daily
- **AI-Powered Q&A**: Ask questions in natural language, get evidence-based answers
- **Diagnostic Engine**: Detects fatigue, saturation, delivery concentration, auction shifts, and tracking issues
- **Attribution Tracking**: Standard and incremental attribution views
- **Events Manager Monitoring**: Pixel health and tracking quality

## What It Does NOT Do

- ❌ Create, edit, or pause ads
- ❌ Change budgets
- ❌ Guess or assume - only uses actual data
- ❌ Hardcode rules

## Project Structure

```
Meta AI/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database setup
│   ├── scheduler.py         # Background job scheduler
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py        # SQLAlchemy models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── meta_client.py   # Meta Marketing API client
│   │   ├── snapshot_service.py
│   │   ├── analytics.py     # Diagnostic engine
│   │   └── ai_analyst.py    # AI-powered analyst
│   └── api/
│       ├── __init__.py
│       └── routes.py        # API endpoints
├── static/
│   └── index.html           # Web UI
├── tests/
│   └── __init__.py
├── .env                     # Environment variables (create from .env.example)
├── .gitignore
├── requirements.txt
├── run.py                   # Application entry point
├── setup.py                 # Database setup
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with:

```env
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_ACCESS_TOKEN=your_access_token
META_AD_ACCOUNT_ID=act_your_account_id
DATABASE_URL=sqlite:///./meta_ai_analyst.db
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview
ENVIRONMENT=development
API_PORT=8000
```

### 3. Initialize Database

```bash
python setup.py
```

### 4. Run the Server

```bash
python run.py
```

Open http://localhost:8000 in your browser.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/health` | GET | Health check |
| `/ask` | POST | Ask a question |
| `/overview` | GET | Daily overview |
| `/snapshot` | POST | Trigger data snapshot |
| `/snapshots` | GET | List historical data |
| `/diagnostics` | GET | View diagnostics |
| `/docs` | GET | API documentation |

## Usage

### Ask Questions

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How is my ad account performing?"}'
```

### Get Daily Overview

```bash
curl http://localhost:8000/overview
```

### Fetch Historical Data

```bash
curl http://localhost:8000/snapshots
```

## Diagnostics

The system automatically computes:

| Diagnostic | What It Detects |
|------------|-----------------|
| **Fatigue** | Frequency increasing - audience seeing ads too often |
| **Saturation** | Reach efficiency declining - market exhausted |
| **Delivery Concentration** | Spend concentrated in few campaigns |
| **Auction Shifts** | CPM volatility - competitive changes |
| **Tracking Degradation** | Pixel quality issues |

## License

MIT
