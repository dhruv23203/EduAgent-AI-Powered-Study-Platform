export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export type StudyResource = { title: string; url: string; type: string };
export type Topic = { name: string; subtopics: string[]; weightage: number; difficulty: "Easy" | "Medium" | "Hard"; estimated_hours: number };
export type StudySession = { topic: string; subtopic: string; hours: number; activity: string; priority: "High" | "Medium" | "Low"; focus_points: string[]; resources: StudyResource[] };
export type StudyDay = { day: number; date: string; sessions: StudySession[] };
export type StudyPlanResponse = { id?: number | null; study_plan: StudyDay[]; topics: Topic[]; total_days: number; hours_per_topic: Record<string, number> };
export type StudyPlanStatus = "running" | "upcoming" | "completed";
export type StudyPlanSummary = { id: number; title: string; status: StudyPlanStatus; created_at: string; start_date: string | null; end_date: string | null; total_days: number; total_sessions: number; total_hours: number; daily_hours: number; topic_count: number; primary_topics: string[] };
export type QuizQuestion = { id: string; question: string; options: Record<"A" | "B" | "C" | "D", string>; correct_answer: "A" | "B" | "C" | "D"; explanation: string; difficulty: "Easy" | "Medium" | "Hard"; topic: string; subtopic: string };
export type RewardSummary = { coins: number; coins_earned: number; badges: string[]; new_badges: string[]; streak_days: number; streak_recoveries_available: number; recover_streak_cost: number };
export type ProgressResponse = {
  overall_accuracy: number;
  topics_covered: string[];
  topics_remaining: string[];
  weak_areas: string[];
  strong_areas: string[];
  streak_days: number;
  total_questions_attempted: number;
  accuracy_by_topic: Record<string, number>;
  insight: string;
  history: Array<Record<string, string | number>>;
  heatmap: Array<{ date: string; count: number; accuracy: number; recovered: boolean }>;
  mistakes: Array<{ topic: string; subtopic: string; mistakes: number; last_question: string; selected_answer: string; correct_answer: string; feedback: string; resources: StudyResource[] }>;
  feedback: Array<{ topic: string; accuracy: number; priority: "High" | "Medium" | "Low"; diagnosis: string; next_steps: string[]; resources: StudyResource[] }>;
  rewards: RewardSummary | null;
};
export type RevisionResponse = {
  priority_topics: string[];
  exam_focus: string[];
  revision_plan: StudyDay[];
  feedback: ProgressResponse["feedback"];
  is_first_day: boolean;
  message: string;
  quiz_questions: string[];
  revision_percentage: number;
  quiz_accuracy: number;
  total_revision_questions: number;
};
export type RevisionMistakeFeedback = { question: string; topic: string; subtopic: string; selected_answer: string; correct_answer: string; feedback: string; source_mistake: string };
export type RevisionQuizSubmitResponse = { quiz_run_id: string; score: number; correct: number; wrong: number; total: number; mistakes: RevisionMistakeFeedback[] };
export type RevisionQuizHistoryItem = RevisionQuizSubmitResponse & { attempted_at: string };
export type DailyTaskStatus = { date: string; topic: string; subtopic: string; concepts_completed: boolean; practice_completed: boolean; quiz_count: number; quiz_completed: boolean; day_completed: boolean; resources: StudyResource[] };
export type UsageResponse = { date: string; provider?: string; model: string; vision_model?: string; daily_limit: number; requests_used: number; requests_remaining: number; budget_scope?: "all_plans"; counter_scope?: string; api_keys_configured?: number; active_key_slot?: number; limited_key_slots?: number[] };
export type UserProfile = { id: string; name: string; email: string; coins: number; badges: string[] };
export type AuthResponse = { token: string; user: UserProfile };
export type ChatTurn = { role: "user" | "assistant"; content: string };
export type ChatResponse = { answer: string; plan_updates: string[] };
export type SavedChatMessage = ChatTurn & { id: string; plan_updates?: string[]; attachments?: string[] };
export type ChatThreadSummary = { id: string; mode: "academic" | "coach"; title: string; updated_at: string; message_count: number };
export type ChatThreadDetail = ChatThreadSummary & { messages: SavedChatMessage[] };

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (element: HTMLElement, options: Record<string, string | number | boolean>) => void;
          prompt: () => void;
        };
      };
    };
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error(`Backend is not reachable at ${API_URL}. Make sure the FastAPI server is running.`);
  }
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

function tokenFromStorage() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("eduagent_auth_token") || "";
}

function authHeaders(): HeadersInit {
  const token = tokenFromStorage();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function saveAuth(auth: AuthResponse) {
  localStorage.setItem("eduagent_auth_token", auth.token);
  localStorage.setItem("eduagent_user", JSON.stringify(auth.user));
  localStorage.setItem("eduagent_student_id", auth.user.id);
}

export function logout() {
  localStorage.removeItem("eduagent_auth_token");
  localStorage.removeItem("eduagent_user");
  localStorage.removeItem("eduagent_selected_plan_id");
}

export function currentUserFromStorage(): UserProfile | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("eduagent_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    return null;
  }
}

export function signup(name: string, email: string, password: string) {
  return request<AuthResponse>("/api/auth/signup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, email, password }) });
}
export function login(email: string, password: string) {
  return request<AuthResponse>("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
}
export function googleLogin(credential: string) {
  return request<AuthResponse>("/api/auth/google", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ credential }) });
}
export function getMe() {
  return request<UserProfile>("/api/auth/me", { headers: authHeaders(), cache: "no-store" });
}
export function uploadPdf(kind: "syllabus" | "notes", studentId: string, file: File) {
  const form = new FormData();
  form.append("student_id", studentId);
  form.append("file", file);
  return request<{ success: boolean; pages: number; preview: string }>(`/api/upload/${kind}`, { method: "POST", body: form });
}
export function generatePlan(studentId: string, examDate: string, dailyHours: number, forceNew = true) {
  return request<StudyPlanResponse>("/api/study/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, exam_date: examDate, daily_hours: dailyHours, force_new: forceNew }) });
}
export function getStudyPlans(studentId: string) {
  return request<StudyPlanSummary[]>(`/api/study/plans/${studentId}`, { cache: "no-store" });
}
export function getStudyPlan(studentId: string, planId: number) {
  return request<StudyPlanResponse>(`/api/study/plans/${studentId}/${planId}`, { cache: "no-store" });
}
export function deleteStudyPlan(studentId: string, planId: number) {
  return request<{ success: boolean; deleted_plan_id: number }>(`/api/study/plans/${studentId}/${planId}`, { method: "DELETE" });
}
export function generateQuiz(studentId: string, topic: string, subtopic: string, difficulty = "Medium", planId?: number | null) {
  return request<QuizQuestion[]>("/api/quiz/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, plan_id: planId || null, topic, subtopic, difficulty, count: 5 }) });
}
export function submitQuiz(studentId: string, answers: Array<{ question_id: string; selected_option: string }>, planId?: number | null) {
  return request<{ score: number; correct: number; wrong: number; explanations: Array<Record<string, string | boolean | Record<string, string>>>; updated_weak_areas: string[]; rewards: RewardSummary | null }>("/api/quiz/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, plan_id: planId || null, answers }) });
}
export function getProgress(studentId: string, planId?: number | null) {
  return request<ProgressResponse>(`/api/progress/${studentId}${planId ? `?plan_id=${planId}` : ""}`, { cache: "no-store" });
}
export function getRevision(studentId: string, planId?: number | null) {
  return request<RevisionResponse>(`/api/revision/${studentId}${planId ? `?plan_id=${planId}` : ""}`, { cache: "no-store" });
}
export function generateRevisionQuiz(studentId: string, planId?: number | null) {
  return request<QuizQuestion[]>("/api/revision/quiz/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, plan_id: planId || null, count: 10 }) });
}
export function submitRevisionQuiz(studentId: string, answers: Array<{ question_id: string; selected_option: string }>, planId?: number | null) {
  return request<RevisionQuizSubmitResponse>("/api/revision/quiz/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, plan_id: planId || null, answers }) });
}
export function getRevisionQuizHistory(studentId: string, planId?: number | null) {
  return request<RevisionQuizHistoryItem[]>(`/api/revision/quiz/history/${studentId}${planId ? `?plan_id=${planId}` : ""}`, { cache: "no-store" });
}
export function getUsage() {
  return request<UsageResponse>("/api/usage", { cache: "no-store" });
}
export function getDailyTask(studentId: string, date: string, planId?: number | null) {
  return request<DailyTaskStatus>(`/api/tasks/${studentId}/${date}${planId ? `?plan_id=${planId}` : ""}`, { cache: "no-store" });
}
export function completeTask(studentId: string, date: string, taskType: "concepts" | "practice", topic: string, planId?: number | null) {
  return request<DailyTaskStatus>("/api/tasks/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, plan_id: planId || null, task_date: date, task_type: taskType, topic }) });
}
export function recoverStreak(studentId: string) {
  return request<RewardSummary>("/api/rewards/recover-streak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId }) });
}
export function academicChat(studentId: string, message: string, files: File[] = [], history: ChatTurn[] = []) {
  const form = new FormData();
  form.append("student_id", studentId);
  form.append("message", message);
  form.append("history", JSON.stringify(history));
  files.forEach((file) => form.append("files", file));
  return request<ChatResponse>("/api/chat/academic", { method: "POST", body: form });
}
export function coachChat(studentId: string, message: string, history: ChatTurn[] = []) {
  return request<ChatResponse>("/api/chat/coach", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ student_id: studentId, message, history }) });
}
export function getChatThreads(studentId: string) {
  return request<ChatThreadSummary[]>(`/api/chat/threads/${studentId}`, { cache: "no-store" });
}
export function getChatThread(studentId: string, threadId: string) {
  return request<ChatThreadDetail>(`/api/chat/threads/${studentId}/${threadId}`, { cache: "no-store" });
}
export function saveChatThread(thread: { id: string; student_id: string; mode: "academic" | "coach"; title: string; messages: SavedChatMessage[] }) {
  return request<ChatThreadDetail>("/api/chat/threads", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(thread) });
}
export function studentIdFromStorage() {
  if (typeof window === "undefined") return "";
  const user = currentUserFromStorage();
  if (user) return user.id;
  let id = localStorage.getItem("eduagent_student_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("eduagent_student_id", id);
  }
  return id;
}
