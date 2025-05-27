# DocumentIQ

## How it Works

### Get Started
**Your documents and assets, fully under control.**

Never miss an expiring contract, overlooked liability, or outdated insurance. Our AI audits, summarizes, and keeps every document category—from Identity to Everything—in check.

All your finances, investments, and important documents in one place.

Secure, organized, and always within reach.

## Features

- **Advanced Encryption**
  FIPS 140-2 Validated
- **Extra level of protection**
  Passcode-based access
- **Multi-Layered Security**
  Face ID and SSO integration
- **AI Document Intelligence**
  Automatic classification, extraction, and smart search

## Setup

1. Copy the development environment file:
   ```bash
   cp .env.devel .env
   ```
2. Build and start the Docker containers:
   ```bash
   docker compose build
   docker compose up
   ```

# documentIQ Backend

A FastAPI service that ingests customer documents (via upload or GCS), stores them per customer, logs metadata in a database, and triggers AI analysis with webhook callbacks.

## Features

* Upload or fetch documents from Google Cloud Storage
* Store files under `BASE_UPLOAD_DIR` organized by customer ID
* Track metadata (UUID, size, timestamps, status) in the `files` table
* Trigger AI processing workflows and notify via webhooks

## Requirements

* Python 3.12 or higher
* SQLite (default) or another SQL database (configure `DATABASE_URL`)
* Google Cloud credentials (set `GOOGLE_APPLICATION_CREDENTIALS`)

## Installation

```bash
git clone https://github.com/your-org/documentIQ.git
cd documentIQ/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Edit `backend/config.py` or use environment variables:

* `BASE_UPLOAD_DIR`: directory to store uploaded files
* `DATABASE_URL`: connection string for your database
* `GOOGLE_APPLICATION_CREDENTIALS`: GCS service account key

## Running the Server

```bash
uvicorn backend.main:app --reload
```

The API listens on `/api/v1/document/{customer_id}` for POST requests.

## Usage Example

```bash
curl -X POST "http://localhost:8000/api/v1/1" \
  -F "customer_data={\"customer_name\": \"Acme Corp\"}" \
  -F "file=@/path/to/doc.pdf" \
  -F "ai_analysis_mode=standard" \
  -F "output_language=English" \
  -F "webhook_url=https://example.com/webhook"
```

## License

MIT License. No documents were harmed in the making of this API—though we can’t promise the same for your typos.
