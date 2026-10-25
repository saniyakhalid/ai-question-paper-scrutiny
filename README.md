# AI-Based Intelligent Question Paper Scrutiny DSS

A college examination decision-support portal for faculty and moderators. Faculty upload a paper into a selected subject workspace; the backend validates the document before generating a report. Moderators retain the final decision.

## What is implemented

- React web app with a responsive light theme, public landing page, campus carousel, authentication modal, teacher dashboard, upload, history, curriculum management, scrutiny reports, and moderator review.
- FastAPI API with JWT bearer authentication, password hashing, role checks, MongoDB persistence, audit events, file size limits, PDF/DOCX extraction, and report exports.
- Dynamic subject, course outcome, unit, topic, syllabus, and examination-pattern management.
- Faculty can create, edit, and delete subject workspaces and their curriculum. An uploaded searchable PDF, DOCX, or TXT syllabus is previewed first; recognized subject metadata, unit topics, and course outcomes are then imported. The subject library accepts multiple `.ppt`/`.pptx` files per subject, and moderators/administrators can review them while faculty can remove their own PPTs.
- Backend subject validation before analysis. Mismatch, inconclusive, and extraction-failure outcomes are stored separately from a scrutiny score and written to the audit trail. Direct analysis and moderator review calls are blocked for papers that did not pass validation.
- Deterministic checks for marks, question numbering, configured CO/unit coverage, configured Bloom targets, configured internal-choice requirements, and solving-time feasibility when all required inputs exist.
- Similarity comparison against previous papers for the same subject using TF-IDF text matching.

The system is a decision aid. A score does not certify examination quality, and moderators make the final decision.

## Architecture

| Layer | Implementation |
|---|---|
| Frontend | React 18 (JavaScript/JSX), Vite, Tailwind CSS, React Router, Axios, Recharts |
| Backend | Python, FastAPI, Pydantic, PyMongo |
| Primary database | MongoDB; indexes are initialized by the backend |
| Document parsing | PyMuPDF for PDF, python-docx for DOCX, text extraction for TXT |
| Optional AI | Gemini via `google-generativeai`; `AI_PROVIDER=mock` uses offline keyword heuristics and deterministic checks |
| Similarity | scikit-learn TF-IDF and cosine similarity over subject-specific previous papers |

The live API uses MongoDB. Some SQLAlchemy models and SQLite/PostgreSQL dependencies remain as legacy compatibility code; the current API does not use PostgreSQL or Alembic migrations. Mongo document fields added by the validation/report work are backward-compatible and need no destructive migration. Do not point these instructions at a production database.

## Scoring and evidence

The report rubric has a 100-point weighting: marks (15), numbering (5), Bloom distribution (15), CO coverage (15), unit coverage/compliance (20), grammar/quality (10), historical similarity (10), solving time (5), and choice pattern (5). A configured PASS earns the category weight, WARNING earns half, and FAIL earns zero. `NOT_EVALUATED` categories earn no points and are excluded from the evaluated-weight denominator.

The displayed score is normalized over evaluated categories and is accompanied by evidence coverage. An overall score is withheld unless marks, numbering, CO coverage, and unit coverage have evaluable evidence. Optional checks without required data remain unavailable. Review the report's category table and analysis notice before using a score.

With `AI_PROVIDER=mock`, the system does not claim that Gemini ran. Bloom levels and CO/unit mappings are heuristic suggestions without a fabricated confidence value; grammar and question-quality analysis are marked unavailable. Gemini analysis is optional and requires a configured API key. Previous-paper similarity uses TF-IDF lexical matching and is not a plagiarism finding. If no same-subject historical questions exist, the report says that comparison was not performed.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- MongoDB 7 locally or a MongoDB-compatible service
- Optional: Gemini API key for provider-backed analysis
- Optional for scanned PDFs: Tesseract OCR and the Python OCR packages described below

## Run locally on Windows PowerShell

### 1. Start MongoDB

From the repository root, use Docker Compose for a local development database:

```powershell
docker compose up -d mongodb
```

This compose file starts only MongoDB. It stores local data in the `mongo_data` Docker volume. The backend and frontend run from source below.

### 2. Configure and start the backend

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
$env:JWT_SECRET = (python -c "import secrets; print(secrets.token_urlsafe(48))")
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The example environment file contains a placeholder for `JWT_SECRET`; the generated shell variable overrides it for this PowerShell session. Set a persistent random secret through a secret manager for deployments. The development default database URI is `mongodb://localhost:27017`, database `question_paper_scrutiny`.

FastAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). The root endpoint reports whether MongoDB is connected or the backend is degraded.

### 3. Start the frontend

In a second PowerShell window:

```powershell
Set-Location frontend
npm ci
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm run dev -- --host 127.0.0.1
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Vite proxies `/api` requests to `VITE_API_TARGET` (default `http://127.0.0.1:8000`).

The login form offers Faculty, Moderator, and Administrator sign-in choices and checks the selected role against the role returned by the backend. Public registration creates faculty accounts only. An administrator can create moderator or administrator accounts from the User Access page. To create the first administrator, the optional `scripts/seed_data.py` bootstrap reads `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` from the environment (password minimum 12 characters); it never prints the password or changes an existing account. Do not use seeded demo accounts for deployment.

### Optional Gemini configuration

Set these in the backend process environment or `backend/.env`:

```text
AI_PROVIDER=gemini
GEMINI_API_KEY=<secret from your provider>
GEMINI_MODEL=gemini-1.5-flash
```

Without a provider key, offline heuristic mode is used and clearly identified in reports. OCR for image-only PDFs requires a local Tesseract installation; unreadable files remain unscored.

## Tests and build checks

Run backend tests from `backend`:

```powershell
python -m pytest -v
```

Mongo integration tests force `mongodb://127.0.0.1:27017`, use a randomly named temporary database and temporary upload folder, and drop only that database at session end. They are skipped if local MongoDB is unavailable. Other unit and fake-database API tests run without touching application records.

Run the frontend production build from `frontend`:

```powershell
npm run build
```

## Configuration reference

Backend variables are listed in `backend/.env.example`:

- `JWT_SECRET` — generated random value, at least 32 characters
- `MONGODB_URI`, `MONGODB_DB_NAME` — primary data store
- `AI_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` — optional AI provider
- `CORS_ORIGINS` — comma-separated allowed web origins
- `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` — document storage and upload limit
- `ENVIRONMENT`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_ALGORITHM` — runtime/security settings
- `SEED_ADMIN_EMAIL`, `SEED_ADMIN_PASSWORD` — optional one-time initial administrator bootstrap; keep these out of committed files and clear them after use

Frontend proxy configuration is in `frontend/.env.example`.

## Known limitations

- In-paper duplicate detection and a separately managed question-bank comparison are not implemented; the report states this clearly.
- Historical comparison is available only when previous papers for the same subject have been uploaded. It is TF-IDF matching, not embedding-based semantic retrieval.
- Offline mode does not evaluate grammar or question quality and does not assign confidence values to heuristic mappings.
- Bloom distribution is a compliance result only when an institutional Bloom target has been configured.
- Image-only PDFs require optional OCR software; otherwise the upload is retained as an extraction/validation failure without a score.
- Legacy SQLAlchemy/SQLite compatibility files are not the source of truth for the running API.

See [docs/architecture-and-limitations.md](docs/architecture-and-limitations.md) for the validation flow, score data model, safety boundaries, and acceptance audit notes.
