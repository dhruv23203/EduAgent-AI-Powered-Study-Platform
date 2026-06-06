from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Student
from models.schemas import CareerPath, CareerResponse

router = APIRouter(prefix="/api/career", tags=["career"])


@router.get("/{student_id}", response_model=CareerResponse)
def get_career(student_id: str, db: Session = Depends(get_db)) -> CareerResponse:
    if db.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    careers = [
        CareerPath(role="Software Development Engineer (Backend)", match_score=90, avg_salary_lpa="8-25", matching_skills=["Algorithms", "DBMS", "APIs"], certifications=["AWS Developer Associate", "System Design foundations"], companies=["Google", "Microsoft", "Amazon"]),
        CareerPath(role="Data Engineer", match_score=84, avg_salary_lpa="10-22", matching_skills=["SQL", "Graphs", "Pipelines"], certifications=["Google Cloud Data Engineer", "Databricks Data Engineer"], companies=["Flipkart", "Swiggy", "Zomato"]),
        CareerPath(role="Algorithm Engineer", match_score=88, avg_salary_lpa="15-35", matching_skills=["Trees", "Graphs", "Dynamic Programming"], certifications=["Stanford Algorithms", "Competitive Programming"], companies=["Adobe", "Uber", "Atlassian"]),
        CareerPath(role="Backend Infrastructure Engineer", match_score=82, avg_salary_lpa="12-28", matching_skills=["Operating Systems", "Databases", "Distributed Systems"], certifications=["Kubernetes Administrator", "Linux Foundation"], companies=["Razorpay", "PhonePe", "Hotstar"]),
    ]
    return CareerResponse(careers=careers)
