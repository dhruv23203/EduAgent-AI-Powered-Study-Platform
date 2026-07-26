# EduAgent

EduAgent is a FastAPI + Next.js study platform with login, study plans, quizzes, progress tracking, revision, rewards, file upload, and AI-backed chat features.

## Tech Stack

- Backend: Python, FastAPI, Uvicorn, SQLAlchemy, SQLite
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
- AI provider: Groq-compatible chat completion API through `backend/agents/llm.py`
- Vector memory: student-isolated local embeddings stored in SQLite (no extra service required)

Uploaded syllabus/notes are chunked and indexed for similarity retrieval. Academic
chat also recalls relevant earlier academic exchanges. Set `VECTOR_MEMORY_ENABLED=false`
in `backend/.env` to disable retrieval and retain the original behavior.

## Project Structure

```text
eduagent/
  backend/
    main.py
    requirements.txt
    .env.example
    db/
    routers/
    agents/
  frontend/
    package.json
    .env.example
    app/
    components/
    lib/
  README.md
```

## Prerequisites

Install these before running the project:

- Python 3.10 or newer
- Node.js 18.17 or newer
- npm

This workspace was verified with:

```powershell
python --version
node --version
npm --version
```

Verified versions: Python 3.13.5, Node.js 22.14.0, npm 10.9.2.

## 1. Open The Project

In PowerShell, go to the repository folder:

```powershell
cd "C:\Users\Dhruv malhan\Desktop\New folder (4)\New folder\eduagent"
```

If you cloned the project somewhere else, use that `eduagent` folder path instead.

## 2. Start The Backend

Open the first PowerShell terminal:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the backend environment file:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

For local development, the defaults in `backend\.env.example` are enough to start the server. To enable real AI responses, edit `backend\.env` and set:

```text
GROQ_API_KEY=your_groq_api_key
GROQ_API_KEY_2=optional_backup_groq_api_key
```

If one Groq key reaches its rate limit, EduAgent automatically tries the next configured key. You can also use a single comma-separated value:

```text
GROQ_API_KEYS=groq_key_one,groq_key_two
```

The default Groq text model is `openai/gpt-oss-120b`. Image-capable requests use `qwen/qwen3.6-27b`.

Run the backend:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- API root: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/api/health`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

The SQLite database is created automatically at `backend\eduagent.db` when the backend starts. You do not need to run Alembic migrations or a separate database init script.

## 3. Start The Frontend

Open a second PowerShell terminal:

```powershell
cd "C:\Users\Dhruv malhan\Desktop\New folder (4)\New folder\eduagent"
cd frontend
npm install
```

Create the frontend environment file:

```powershell
if (!(Test-Path .env.local)) { Copy-Item .env.example .env.local }
```

Make sure `frontend\.env.local` contains:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Google login is optional. If you want it, also set:

```text
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_oauth_web_client_id
```

Run the frontend:

```powershell
npm run dev
```

Frontend URL:

- App: `http://localhost:3000`

## 4. Check That Everything Is Running

With both terminals still running, open:

```text
http://localhost:3000
```

You can also verify the backend from PowerShell:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health
```

Expected backend response:

```json
{"status":"ok"}
```

## Daily Run Commands

After dependencies and `.env` files are already set up, use these two terminals.

Backend terminal:

```powershell
cd "C:\Users\Dhruv malhan\Desktop\New folder (4)\New folder\eduagent\backend"
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd "C:\Users\Dhruv malhan\Desktop\New folder (4)\New folder\eduagent\frontend"
npm run dev
```

## PowerShell Activation Fix

If PowerShell blocks virtual environment activation, run this in the same terminal and try activating again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

If you use Command Prompt instead of PowerShell, activate the backend venv with:

```bat
venv\Scripts\activate.bat
```

## Common Issues

Port `8000` is already in use:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

If you change the backend port, also update `frontend\.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8001
```

Port `3000` is already in use:

```powershell
npm run dev -- -p 3001
```

If package installs look broken, reinstall from the project folders:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```powershell
cd frontend
npm install
```

## Useful Commands

Backend import check:

```powershell
cd backend
.\venv\Scripts\python.exe -c "import main; print('backend import ok')"
```

Frontend production build:

```powershell
cd frontend
npm run build
```

Note: `npm run lint` may ask to configure ESLint if no ESLint config exists yet.
