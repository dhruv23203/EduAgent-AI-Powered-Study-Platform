from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from agents.fallbacks import sanitize_document_text
from db.database import get_db
from db.models import Student
from models.schemas import UploadResponse
from memory.store import index_text
from utils.pdf_parser import extract_pdf_text

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/{kind}", response_model=UploadResponse)
async def upload_pdf(kind: str, student_id: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadResponse:
    if kind not in {"syllabus", "notes"}:
        raise HTTPException(status_code=400, detail="Upload kind must be syllabus or notes.")
    student = db.get(Student, student_id)
    if student is None:
        student = Student(id=student_id)
        db.add(student)
        db.commit()
        db.refresh(student)
    data = await file.read()
    try:
        parsed = extract_pdf_text(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    text = sanitize_document_text(parsed.text)
    if len(text) < 40:
        raise HTTPException(
            status_code=422,
            detail="Could not extract readable syllabus/notes text from this file. Upload a text-based PDF or a .txt file, then generate the plan again.",
        )
    if kind == "syllabus":
        student.syllabus_text = text
        student.syllabus_filename = file.filename or ""
    else:
        student.notes_text = text
        student.notes_filename = file.filename or ""
    db.add(student)
    db.commit()
    # Replaces the previous vectors for this source while preserving the raw text.
    index_text(db, student_id, text, kind, source_id=kind)
    return UploadResponse(success=True, pages=parsed.pages, preview=text[:700])
