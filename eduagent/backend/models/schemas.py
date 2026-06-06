from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Difficulty = Literal["Easy", "Medium", "Hard"]
Priority = Literal["High", "Medium", "Low"]
PlanStatus = Literal["running", "upcoming", "completed"]


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    coins: int = 0
    badges: list[str] = Field(default_factory=list)


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=6)


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)


class GoogleAuthRequest(BaseModel):
    credential: str


class AuthResponse(BaseModel):
    token: str
    user: UserProfile


class UploadResponse(BaseModel):
    success: bool
    pages: int = 1
    preview: str


class Topic(BaseModel):
    name: str
    subtopics: list[str] = Field(default_factory=list)
    weightage: float = Field(default=10, ge=0, le=100)
    difficulty: Difficulty = "Medium"
    estimated_hours: float = Field(default=1, gt=0)


class StudyResource(BaseModel):
    title: str
    url: str
    type: str = "Search"


class StudySession(BaseModel):
    topic: str
    subtopic: str = ""
    hours: float = Field(gt=0)
    activity: str
    priority: Priority = "Medium"
    focus_points: list[str] = Field(default_factory=list)
    resources: list[StudyResource] = Field(default_factory=list)


class StudyDay(BaseModel):
    day: int
    date: date
    sessions: list[StudySession]


class StudyPlanResponse(BaseModel):
    id: int | None = None
    study_plan: list[StudyDay]
    topics: list[Topic]
    total_days: int
    hours_per_topic: dict[str, float]


class StudyPlanSummary(BaseModel):
    id: int
    title: str
    status: PlanStatus
    created_at: datetime
    start_date: date | None = None
    end_date: date | None = None
    total_days: int = 0
    total_sessions: int = 0
    total_hours: float = 0
    daily_hours: float = 0
    topic_count: int = 0
    primary_topics: list[str] = Field(default_factory=list)


class GeneratePlanRequest(BaseModel):
    student_id: str
    exam_date: date
    daily_hours: int = Field(ge=1, le=12)
    force_new: bool = False


class GenerateQuizRequest(BaseModel):
    student_id: str
    plan_id: int | None = None
    topic: str
    subtopic: str = ""
    count: int = Field(default=5, ge=1, le=10)
    difficulty: Difficulty = "Medium"


class QuizQuestion(BaseModel):
    id: str
    question: str
    options: dict[Literal["A", "B", "C", "D"], str]
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: str
    difficulty: Difficulty = "Medium"
    topic: str
    subtopic: str = ""


class SubmittedAnswer(BaseModel):
    question_id: str
    selected_option: Literal["A", "B", "C", "D"]


class QuizSubmitRequest(BaseModel):
    student_id: str
    plan_id: int | None = None
    answers: list[SubmittedAnswer]

    @field_validator("answers")
    @classmethod
    def require_answers(cls, value: list[SubmittedAnswer]) -> list[SubmittedAnswer]:
        if not value:
            raise ValueError("At least one answer is required.")
        return value


class RewardSummary(BaseModel):
    coins: int = 0
    coins_earned: int = 0
    badges: list[str] = Field(default_factory=list)
    new_badges: list[str] = Field(default_factory=list)
    streak_days: int = 0
    streak_recoveries_available: int = 0
    recover_streak_cost: int = 75


class QuizSubmitResponse(BaseModel):
    score: float
    correct: int
    wrong: int
    explanations: list[dict[str, Any]]
    updated_weak_areas: list[str]
    rewards: RewardSummary | None = None


class HeatmapDay(BaseModel):
    date: str
    count: int
    accuracy: float
    recovered: bool = False


class MistakeInsight(BaseModel):
    topic: str
    subtopic: str = ""
    mistakes: int
    last_question: str
    selected_answer: str
    correct_answer: str
    feedback: str
    resources: list[StudyResource] = Field(default_factory=list)


class FeedbackItem(BaseModel):
    topic: str
    accuracy: float
    priority: Priority
    diagnosis: str
    next_steps: list[str]
    resources: list[StudyResource] = Field(default_factory=list)


class ProgressResponse(BaseModel):
    overall_accuracy: float
    topics_covered: list[str]
    topics_remaining: list[str]
    weak_areas: list[str]
    strong_areas: list[str]
    streak_days: int
    total_questions_attempted: int
    accuracy_by_topic: dict[str, float]
    insight: str
    history: list[dict[str, str | int | float]]
    heatmap: list[HeatmapDay] = Field(default_factory=list)
    mistakes: list[MistakeInsight] = Field(default_factory=list)
    feedback: list[FeedbackItem] = Field(default_factory=list)
    rewards: RewardSummary | None = None


class WeaknessResponse(BaseModel):
    weak_topics: list[str]
    strong_topics: list[str]
    accuracy_by_topic: dict[str, float]
    insight: str


class RevisionResponse(BaseModel):
    priority_topics: list[str]
    exam_focus: list[str]
    revision_plan: list[StudyDay]
    feedback: list[FeedbackItem] = Field(default_factory=list)


class DailyTaskStatus(BaseModel):
    date: str
    topic: str
    subtopic: str = ""
    concepts_completed: bool
    practice_completed: bool
    quiz_count: int
    quiz_completed: bool
    day_completed: bool
    resources: list[StudyResource] = Field(default_factory=list)


class TaskCompleteRequest(BaseModel):
    student_id: str
    plan_id: int | None = None
    task_date: date
    task_type: Literal["concepts", "practice"]
    topic: str


class StreakRecoveryRequest(BaseModel):
    student_id: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    student_id: str
    message: str
    history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    plan_updates: list[str] = Field(default_factory=list)


class CareerPath(BaseModel):
    role: str
    match_score: int = Field(ge=0, le=100)
    matching_skills: list[str]
    certifications: list[str]
    companies: list[str]
    avg_salary_lpa: str


class CareerResponse(BaseModel):
    careers: list[CareerPath]
