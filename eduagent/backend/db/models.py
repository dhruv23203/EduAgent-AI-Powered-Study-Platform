from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    badges_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    syllabus_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_text: Mapped[str | None] = mapped_column(Text, nullable=True)


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(Text, ForeignKey("students.id"), index=True, nullable=False)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(Text, ForeignKey("students.id"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("study_plans.id"), index=True, nullable=True)
    question_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    topic: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    subtopic: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(Text, ForeignKey("students.id"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("study_plans.id"), index=True, nullable=True)
    quiz_run_id: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    question_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    topic: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    subtopic: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class StudyTaskCompletion(Base):
    __tablename__ = "study_task_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(Text, ForeignKey("students.id"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("study_plans.id"), index=True, nullable=True)
    task_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    task_type: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class StreakRecovery(Base):
    __tablename__ = "streak_recoveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id"), index=True, nullable=False)
    recovered_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    spent_coins: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RewardLedger(Base):
    __tablename__ = "reward_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("study_plans.id"), index=True, nullable=True)
    quiz_run_id: Mapped[str | None] = mapped_column(Text, index=True, nullable=True)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_badges_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RevisionQuizQuestion(Base):
    __tablename__ = "revision_quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(Text, ForeignKey("students.id"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("study_plans.id"), index=True, nullable=True)
    question_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    topic: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    subtopic: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_feedback: Mapped[str] = mapped_column(Text, nullable=False)
    source_mistake: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(Text, default="Medium", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RevisionQuizAttempt(Base):
    __tablename__ = "revision_quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(Text, ForeignKey("students.id"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("study_plans.id"), index=True, nullable=True)
    quiz_run_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    question_id: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    topic: Mapped[str] = mapped_column(Text, index=True, nullable=False)
    subtopic: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    source_mistake: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
