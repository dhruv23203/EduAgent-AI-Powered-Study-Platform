from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Student
from models.schemas import UploadResponse
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
    parsed = extract_pdf_text(data)
    text = parsed.text or file.filename or ""
    if kind == "syllabus":
        student.syllabus_text = text
    else:
        student.notes_text = text
    db.add(student)
    db.commit()
    return UploadResponse(success=True, pages=parsed.pages, preview=text[:700])
