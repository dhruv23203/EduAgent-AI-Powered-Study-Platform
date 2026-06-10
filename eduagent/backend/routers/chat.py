import base64
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from agents.fallbacks import allow_local_fallback, sanitize_document_text, should_use_local_ai
from agents.llm import AgentError, LLMJSONClient
from db.database import get_db
from db.models import Student
from models.schemas import ChatRequest, ChatResponse, ChatTurn
from utils.pdf_parser import extract_pdf_text

router = APIRouter(prefix="/api/chat", tags=["chat"])

ACADEMIC_KEYWORDS = {
    "algorithm", "code", "program", "python", "java", "tree", "graph", "array", "stack", "queue", "sql", "dbms",
    "math", "solve", "formula", "diameter", "recursion", "physics", "chemistry", "biology", "derivative",
    "integral", "equation", "compiler", "complexity", "syllabus", "question", "answer", "proof",
}
COACH_KEYWORDS = {
    "stress", "anxiety", "anxious", "sad", "motivate", "motivation", "burnout", "tired", "sleep",
    "procrastinate", "distraction", "focus", "pressure", "confidence", "panic", "overwhelmed", "routine",
    "depression", "depressed", "emotional", "emotion", "lonely", "cry", "crying", "hopeless", "fear",
    "scared", "mental", "mood", "self harm", "suicide", "suicidal",
}


def _is_academic(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in ACADEMIC_KEYWORDS)


def _is_coach(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in COACH_KEYWORDS)


def _history(raw: str) -> list[ChatTurn]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
        return [ChatTurn.model_validate(item) for item in payload[-8:]]
    except (json.JSONDecodeError, TypeError, ValidationError):
        return []


def _format_history(history: list[ChatTurn]) -> str:
    return "\n\n".join(f"{'Learner' if item.role == 'user' else 'EduAgent'}: {item.content[:1400]}" for item in history[-8:]) or "No earlier turns."


async def _read_upload(file: UploadFile) -> tuple[str, dict[str, str] | None]:
    data = await file.read()
    name = file.filename or "attachment"
    content_type = file.content_type or "unknown"
    if content_type.startswith("image/"):
        encoded = base64.b64encode(data).decode("ascii")
        if len(encoded) > 4 * 1024 * 1024:
            return (
                f"File: {name} ({content_type}, {len(data)} bytes)\nThis image is too large for Groq vision. Ask the learner to upload a smaller screenshot or crop the important area.",
                None,
            )
        return (
            f"File: {name} ({content_type}, {len(data)} bytes)\nScreenshot/image attached for visual analysis.",
            {"filename": name, "mime_type": content_type, "base64": encoded},
        )
    if "pdf" in content_type or data.lstrip().startswith(b"%PDF"):
        parsed = extract_pdf_text(data)
        text = parsed.text
        label = f"{name} ({parsed.pages} page PDF)"
    else:
        text = sanitize_document_text(data.decode("utf-8", errors="ignore"))
        label = f"{name} ({content_type}, {len(data)} bytes)"
    if not text.strip():
        text = "No readable text could be extracted from this file. Use the filename/type as context and ask the learner for details if needed."
    return f"File: {label}\n{text[:6000]}", None


async def _uploaded_context(files: list[UploadFile]) -> tuple[str, list[dict[str, str]]]:
    chunks = []
    images = []
    for file in files[:6]:
        text, image = await _read_upload(file)
        chunks.append(text)
        if image:
            images.append(image)
    return "\n\n---\n\n".join(chunks), images


def _complete(system: str, user: str, academic: bool) -> str:
    client = LLMJSONClient(max_tokens=2200)
    if not should_use_local_ai() and client.available:
        try:
            return client.complete(system, user, temperature=0.25 if academic else 0.45)
        except AgentError:
            if not allow_local_fallback():
                raise
    if academic:
        return "Let's solve it step by step. Identify the core concept, write the rule, apply it to the example, then verify edge cases. If you asked for code, specify the language and I will write it cleanly."
    return "That sounds heavy. Shrink the next step to one 25-minute block, remove one distraction, and finish with a tiny quiz or checklist so your brain gets a clear win."


@router.post("/academic", response_model=ChatResponse)
async def academic_chat(
    student_id: str = Form(...),
    message: str = Form(""),
    history: str = Form("[]"),
    file: UploadFile | None = File(None),
    files: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
) -> ChatResponse:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    uploads = [item for item in (files or []) if item.filename]
    if file and file.filename:
        uploads.append(file)
    file_text, images = await _uploaded_context(uploads) if uploads else ("", [])
    if _is_coach(message) and not _is_academic(message) and not file_text.strip():
        return ChatResponse(answer="This sounds emotional or motivational. Please switch to Motivation coach so EduAgent can support you in the right mode.")
    system = "You are EduAgent's academic solver. Answer the exact academic/coding question. For code, provide working code, explanation, complexity, and edge cases. If screenshots are attached, read the screenshot and solve what is visible."
    prompt = f"System instruction:\n{system}\n\nRecent conversation:\n{_format_history(_history(history))}\n\nCurrent question:\n{message or 'Analyze the uploaded file(s).'}\n\nUploaded context:\n{file_text[:12000]}"
    if images:
        client = LLMJSONClient(max_tokens=2400)
        try:
            return ChatResponse(answer=client.complete_with_images(prompt, images, temperature=0.2))
        except AgentError:
            if not allow_local_fallback():
                raise
    return ChatResponse(answer=_complete(system, prompt, academic=True))


@router.post("/coach", response_model=ChatResponse)
def coach_chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    if _is_academic(payload.message):
        return ChatResponse(answer="This is an academic or coding question. Please switch to Academic solver so EduAgent can solve it properly.")
    system = "You are EduAgent's motivation coach. Respond with empathy, a practical plan adjustment, and one tiny next action."
    prompt = f"Exam date: {student.exam_date}. Daily hours: {student.daily_hours}.\n\nRecent conversation:\n{_format_history(payload.history)}\n\nCurrent issue:\n{payload.message}"
    return ChatResponse(answer=_complete(system, prompt, academic=False), plan_updates=["Shrink the next study block to 25 minutes.", "Move revision before new learning if confidence is low.", "End with one small quiz to rebuild momentum."])
