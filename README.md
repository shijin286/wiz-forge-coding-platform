# WizForge AI: Intelligent Code Review Platform

[![CI](https://github.com/shijin286/wiz-forge-coding-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/shijin286/wiz-forge-coding-platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)

![Review results](docs/screenshots/review.png)

WizForge AI reviews source code in two layers:

1. **Deterministic static analysis.** AST checks for Python and pattern rules for JavaScript/TypeScript, Java, C/C++ and Go, plus language-independent secret detection. These are reproducible and explainable.
2. **AI-assisted review (Claude).** A second pass for issues pattern matching can't see, such as logic errors, edge cases and insecure data flow. AI results are labelled as *potential* findings with a confidence level and are shown separately from the static results.

Submitted code is **never executed**. Python is parsed with `ast.parse`, and other languages are scanned as text.

## Features

- JWT authentication (register / login), bcrypt password hashing
- Monaco code editor with syntax highlighting, file upload with language detection, sample snippets
- Quality score (0–100) and letter grade, code metrics (LOC, functions, cyclomatic complexity, comment ratio)
- Findings list with severity, category, rule ID, explanation and suggested fix; filter by severity and source; click a finding to jump to its line (lines are highlighted in the editor)
- AI review runs as a background task and the UI polls until it finishes. If the API key is missing or the call fails, the static results still show and the failure is explained
- Dashboard with a quality-score trend chart (hover tooltips, table view), severity breakdown, language mix and recent reviews; searchable, paginated review history
- **Import from GitHub:** paste a public GitHub file link to review it. Only `github.com` / `raw.githubusercontent.com` file URLs are accepted, and redirects are not followed, so the server can't be tricked into fetching internal addresses (SSRF)
- **PDF report export:** score, metrics, every finding with its fix, the applied auto-fixes, and the source listing with flagged lines in red ([sample report](docs/sample-report.pdf))
- **Rate limiting:** 10 sign-in attempts per minute per IP address, 30 reviews and 20 imports per minute per user
- Per-user data isolation (users can only see or delete their own reviews)

## Screenshots

| Dashboard | New review |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![New review](docs/screenshots/new-review.png) |
| **Review history** | **Sign in** |
| ![History](docs/screenshots/history.png) | ![Sign in](docs/screenshots/login.png) |

**Corrected code:** an automatic fix, shown as a diff, with the score before and after.

![Corrected code](docs/screenshots/corrected-code.png)

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS v4, Monaco Editor, React Router |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2 |
| Database | PostgreSQL (SQLite works for local dev and tests) |
| AI | Claude API (`anthropic` SDK), model `claude-opus-5-5`, structured JSON output |
| Tests | pytest + FastAPI TestClient |

## Architecture

```
React SPA ──/api──▶ FastAPI
                     ├─ routers/auth.py      register, login, me (JWT)
                     ├─ routers/reviews.py   create / list / get / delete
                     ├─ routers/stats.py     dashboard aggregates
                     ├─ services.py          orchestrates a review
                     │    ├─ analysis/        static engine (sync, deterministic)
                     │    └─ ai/              Claude reviewer (background task)
                     └─ models.py ──▶ PostgreSQL (users, reviews, findings)
```

A `POST /api/reviews` runs static analysis right away and returns the review with status `processing`. A background task then calls Claude, adds the AI findings, recalculates the score and marks the review `completed`.

## Quick start with Docker

Runs the whole stack (PostgreSQL, FastAPI, and the React app behind nginx) with one command:

```bash
docker compose up --build
```

Then open http://localhost:8080. For the AI review, create a `.env` file next to `docker-compose.yml` containing `ANTHROPIC_API_KEY=...`.

## Getting started (Windows, without Docker)

Prerequisites: Python 3.12+, Node.js 20+, and PostgreSQL 16 (optional for local dev).

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then edit .env
python seed_demo.py         # optional: demo account + sample reviews
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

**Database.** `.env.example` points at PostgreSQL:
`postgresql+psycopg://postgres:wizforge_dev@localhost:5432/wizforge`. Create the database first (`createdb -U postgres wizforge`, or in pgAdmin). Without PostgreSQL, set `DATABASE_URL=sqlite:///./wizforge.db`.

**AI review.** Put your Claude API key in `ANTHROPIC_API_KEY` (from https://platform.claude.com). Without a key the app still works and reports that the AI review is unavailable.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend on port 8000.

Demo login (after `seed_demo.py`): the credentials are at the top of [backend/seed_demo.py](backend/seed_demo.py).

### 3. Tests

```powershell
cd backend
.venv\Scripts\python -m pytest -q
```

Tests run against a throwaway SQLite database and mock the Claude call, so they need no API key or PostgreSQL.

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account, returns JWT |
| POST | `/api/auth/login` | Returns JWT |
| GET | `/api/auth/me` | Current user |
| POST | `/api/reviews` | Submit code `{title, language, code, use_ai}` |
| GET | `/api/reviews?search=&language=&limit=&offset=` | Paginated history |
| GET | `/api/reviews/{id}` | Review with findings and metrics |
| GET | `/api/reviews/{id}/report.pdf` | Download the review as a PDF report |
| DELETE | `/api/reviews/{id}` | Delete a review |
| POST | `/api/import/github` | Fetch a public GitHub file `{url}` → `{filename, language, code}` |
| POST | `/api/detect-language` | Guess the language of `{code}` |
| GET | `/api/stats` | Dashboard aggregates |
| GET | `/api/languages` | Supported languages |
| GET | `/api/health` | Health and AI configuration |

## Static analysis rules

| Area | Rules |
|---|---|
| Python (AST) | syntax errors, `eval`/`exec`, SQL built with f-strings/`%`/`+`, `shell=True` / `os.system`, `pickle.loads`, `yaml.load` without a safe loader, `verify=False`, MD5/SHA1, bare `except`, swallowed exceptions, mutable default arguments, `== None`, shadowed built-ins, unused imports, high cyclomatic complexity, long functions |
| JavaScript / TypeScript | `eval`, `new Function`, string `setTimeout`, `innerHTML` (XSS), `document.write`, SQL/shell commands built from template literals, empty `catch`, `==`/`!=`, `var`, `console.log` |
| Java | SQL concatenation, string `==`, empty `catch`, `Runtime.exec`, `System.out` |
| C / C++ | `gets`/`strcpy`/`sprintf`, `system()`, `using namespace std` |
| Go | ignored errors, `fmt.Sprintf` SQL |
| All languages | hard-coded passwords/keys/tokens, AWS keys, private keys, provider API tokens, TODO/FIXME, long lines |

**Scoring.** The score is 100 minus weighted penalties (critical 20, high 10, medium 4, low 1.5, info 0.25), softened for larger files. Low-confidence AI findings are shown but don't affect the score.

## Corrected code

Every review ends with a **Corrected code** section: a side-by-side diff of the original and the fixed file, with Copy and Download buttons, the score before and after, a list of what was fixed, and what still needs a manual fix.

- **Auto-fix (no API key needed).** Mechanical fixes that can't change behaviour by accident. Examples: missing semicolons, case typos, `== None` → `is None`, bare `except`, `==` → `===`, `var` → `let`, Java string `==` → `.equals()`, `printf(var)` → `printf("%s", var)`, `gets`/`strcpy`/`sprintf` → bounds-checked calls (only when the buffer size is known), `%`-formatted SQL → parameterised queries, `shell=True` strings → argument lists, `innerHTML` → `textContent` (when no markup is built), mutable default arguments, and hard-coded secrets → environment variables.
- **AI fix (with `ANTHROPIC_API_KEY`).** Claude returns the complete corrected file, including fixes that need judgement (null dereferences, SQL in other languages, `eval`, ignored errors).
- **Re-analysis.** The "still needs a fix" list comes from running the static analyzer again on the corrected code, so it is always accurate, whoever made the fix.

## AI design and safety

- **Structured output.** Claude must return JSON that matches a schema (summary, strengths, findings with severity/category/line/confidence), so the response is always parseable.
- **Prompt-injection resistance.** The code is wrapped in `<code>` tags and the system prompt tells the model to treat it as data. Comments such as "ignore all bugs" are ignored or reported as findings.
- **No duplicates.** Static findings are passed to the model so it focuses on what the rules missed.
- **Graceful failure.** Auth, rate-limit, connection, refusal and truncation errors each produce a clear message, and the review completes with static results only.
- **Refusal fallback.** Requests opt into the API's server-side fallback (`fallbacks: "default"`), so a safety-classifier decline is retried on a fallback model.
- **Model and effort** are configurable via `AI_MODEL` and `AI_EFFORT`. Higher effort is more thorough but slower and costlier.

## Roadmap

- **Phase 4:** ~~metric trends over time~~, ~~PDF report export~~, ~~import from GitHub~~ (done); next: unit-test generation, GitHub PR integration (webhook + review comments)
- **Phase 5:** ~~Docker Compose~~ (done), ~~CI with pytest and the TypeScript build~~ (done), ~~rate limiting~~ (done), Alembic migrations, deployment (e.g. Render/Railway + managed PostgreSQL)

README screenshots are generated by `backend/scripts/take_screenshots.py` (Playwright with the local Edge browser; `pip install playwright` first) while the app is running.

## Project structure

```
backend/
  app/
    analysis/   engine.py, python_rules.py, pattern_rules.py, metrics.py
    ai/         claude_reviewer.py
    routers/    auth.py, reviews.py, stats.py
    config.py  database.py  models.py  schemas.py  security.py  services.py  main.py
  tests/        test_analysis.py, test_api.py
  seed_demo.py
frontend/
  src/
    components/ Layout, CodeEditor, FindingCard, ui
    pages/      Login, Dashboard, NewReview, ReviewDetail, History
    lib/        api, auth, types, format, samples
```
