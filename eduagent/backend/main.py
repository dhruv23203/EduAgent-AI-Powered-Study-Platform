import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.llm import get_usage_status
from db.database import init_db
from routers import auth, chat, export, progress, quiz, revision, rewards, study, tasks, upload

load_dotenv()

app = FastAPI(
    title="EduAgent API",
    description="AI-powered personalized student study assistant.",
    version="1.0.0",
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url, "http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "EduAgent API", "docs": "/docs"}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/usage")
def usage() -> dict:
    return get_usage_status()


app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(study.router)
app.include_router(quiz.router)
app.include_router(progress.router)
app.include_router(revision.router)
app.include_router(rewards.router)
app.include_router(tasks.router)
app.include_router(chat.router)
app.include_router(export.router)
