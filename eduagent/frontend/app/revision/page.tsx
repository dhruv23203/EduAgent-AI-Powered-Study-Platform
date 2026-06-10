"use client";

import { useEffect, useState } from "react";
import { AlertCircle, ArrowRight, Brain, CheckCircle2, ClipboardList, Loader2, PartyPopper, RefreshCw, Repeat2, Target, XCircle, type LucideIcon } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { StudyPlanView } from "@/components/StudyPlanView";
import { generateRevisionQuiz, getRevision, getRevisionQuizHistory, QuizQuestion, RevisionQuizHistoryItem, RevisionQuizSubmitResponse, submitRevisionQuiz, RevisionResponse, studentIdFromStorage } from "@/lib/api";

export default function RevisionPage() {
  const [data, setData] = useState<RevisionResponse | null>(null);
  const [quiz, setQuiz] = useState<QuizQuestion[]>([]);
  const [selected, setSelected] = useState<Record<string, "A" | "B" | "C" | "D">>({});
  const [summary, setSummary] = useState<RevisionQuizSubmitResponse | null>(null);
  const [history, setHistory] = useState<RevisionQuizHistoryItem[]>([]);
  const [quizLoading, setQuizLoading] = useState(false);
  const [error, setError] = useState("");
  const latest = summary || history[0] || null;

  useEffect(() => {
    const studentId = studentIdFromStorage();
    const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    getRevision(studentId, planId).then(setData).catch((e) => setError(e instanceof Error ? e.message : "Revision unavailable."));
    getRevisionQuizHistory(studentId, planId).then(setHistory).catch(() => setHistory([]));
  }, []);

  async function startQuiz() {
    const studentId = studentIdFromStorage();
    const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    setQuizLoading(true);
    setSummary(null);
    setSelected({});
    setError("");
    try {
      const rows = await generateRevisionQuiz(studentId, planId);
      setQuiz(rows);
      if (!rows.length) setError("No revision quiz is available yet. Finish today, then come back tomorrow so the quiz can use previous mistakes.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not start revision quiz.");
    } finally {
      setQuizLoading(false);
    }
  }

  async function submitQuiz() {
    const studentId = studentIdFromStorage();
    const planId = Number(localStorage.getItem("eduagent_selected_plan_id") || "") || null;
    setQuizLoading(true);
    setError("");
    try {
      const result = await submitRevisionQuiz(studentId, quiz.map((item) => ({ question_id: item.id, selected_option: selected[item.id] || "A" })), planId);
      setSummary(result);
      setHistory((rows) => [{ ...result, attempted_at: new Date().toISOString() }, ...rows]);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not submit revision quiz.");
    } finally {
      setQuizLoading(false);
    }
  }

  return (
    <AppShell>
      <section className="overflow-hidden rounded-lg bg-ink text-white shadow-panel">
        <div className="grid gap-5 p-6 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="section-kicker">Revision</p>
            <h1 className="mt-2 text-3xl font-black">Today's focused revision</h1>
            <p className="mt-2 max-w-2xl text-white/68">Only previous quizzes and completed concepts are used. Future plan topics stay out of this section.</p>
          </div>
          {data && !data.is_first_day ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <MiniStat icon={Repeat2} label="Revision need" value={`${data.revision_percentage}%`} />
              <MiniStat icon={Target} label="Latest quiz" value={latest ? `${latest.score}%` : "Not taken"} />
              <MiniStat icon={ClipboardList} label="History" value={history.length} />
            </div>
          ) : null}
        </div>
      </section>
      {error ? <div className="panel mt-6 border-coral/20 p-5 text-coral">{error}</div> : null}
      {!data && !error ? <div className="panel mt-6 flex items-center gap-3 p-5 font-semibold"><Loader2 className="h-5 w-5 animate-spin text-fern" /> Loading revision...</div> : null}
      {data?.is_first_day ? (
        <section className="panel mt-6 p-6 text-center">
          <span className="mx-auto grid h-14 w-14 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200"><PartyPopper className="h-7 w-7" /></span>
          <h2 className="mt-4 text-2xl font-black">Nothing to revise today</h2>
          <p className="mx-auto mt-2 max-w-xl leading-7 text-ink/65 dark:text-white/65">{data.message}</p>
        </section>
      ) : null}
      {data && !data.is_first_day ? (
        <>
          <section className="panel mt-6 p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="section-kicker">Priority</p>
                <h2 className="text-xl font-black">What to fix first</h2>
                <p className="mt-1 text-sm text-ink/55 dark:text-white/55">{data.message}</p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">{data.priority_topics.map((topic) => <span key={topic} className="rounded-md bg-fern/10 px-3 py-2 font-black text-fern dark:bg-emerald-300/10 dark:text-emerald-200">{topic}</span>)}</div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {data.exam_focus.map((item) => <div key={item} className="rounded-lg border border-ink/10 bg-[#f8faf9] p-3 text-sm font-bold text-ink/70 dark:border-white/10 dark:bg-white/5 dark:text-white/70">{item}</div>)}
            </div>
          </section>
          <div className="mt-6"><StudyPlanView plan={data.revision_plan} /></div>
          <section className="panel mt-6 p-5">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200"><Brain className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <p className="section-kicker">Revision quiz</p>
                <h2 className="text-xl font-black">Mistake-based revision MCQ</h2>
                <p className="mt-1 text-sm text-ink/55 dark:text-white/55">This is separate from the normal quiz. It saves revision quiz history and feedback here.</p>
              </div>
              <button type="button" onClick={startQuiz} disabled={quizLoading} className="focus-ring inline-flex items-center gap-2 rounded-lg bg-fern px-4 py-3 text-sm font-black text-white hover:bg-emerald-700 disabled:opacity-60">
                {quizLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : quiz.length ? <RefreshCw className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                {quiz.length ? "New revision quiz" : "Start revision quiz"}
              </button>
            </div>
            {quiz.length ? (
              <div className="mt-5 grid gap-4">
                {quiz.map((question, index) => (
                  <RevisionQuestionCard
                    key={question.id}
                    index={index}
                    question={question}
                    selected={selected[question.id]}
                    locked={!!summary}
                    onSelect={(option) => setSelected((current) => ({ ...current, [question.id]: option }))}
                  />
                ))}
                {!summary ? (
                  <button type="button" onClick={submitQuiz} disabled={quizLoading || quiz.some((item) => !selected[item.id])} className="focus-ring inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-ink px-5 font-black text-white hover:bg-fern disabled:opacity-60 dark:bg-fern dark:hover:bg-skydeep">
                    {quizLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />} Submit revision quiz
                  </button>
                ) : null}
              </div>
            ) : null}
            {summary ? <RevisionSummary summary={summary} /> : null}
          </section>

          <section className="panel mt-6 p-5">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-coral/10 text-coral"><AlertCircle className="h-5 w-5" /></span>
              <div>
                <p className="section-kicker">Revision quiz history</p>
                <h2 className="text-xl font-black">Specific mistakes and feedback</h2>
              </div>
            </div>
            {history.length ? <div className="mt-5 grid gap-4">{history.map((item) => <HistoryCard key={item.quiz_run_id} item={item} />)}</div> : <p className="mt-4 rounded-lg border border-dashed border-ink/15 bg-[#f8faf9] p-4 text-sm font-semibold text-ink/60 dark:border-white/10 dark:bg-white/5 dark:text-white/60">No revision quiz history yet. Start and submit the revision quiz above to save mistake feedback here.</p>}
          </section>

          <section className="panel mt-6 p-5">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-fern/10 text-fern dark:bg-emerald-200/10 dark:text-emerald-200"><ClipboardList className="h-5 w-5" /></span>
              <div>
                <p className="section-kicker">Self-check</p>
                <h2 className="text-xl font-black">10 supporting revision prompts</h2>
              </div>
            </div>
            <ol className="mt-5 grid gap-3 lg:grid-cols-2">
              {data.quiz_questions.map((question, index) => (
                <li key={`${question}-${index}`} className="flex gap-3 rounded-lg border border-ink/10 bg-[#f8faf9] p-4 text-sm leading-6 text-ink/72 dark:border-white/10 dark:bg-[#101923] dark:text-white/72">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-fern text-xs font-black text-white">{index + 1}</span>
                  {question}
                </li>
              ))}
            </ol>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}

function RevisionQuestionCard({ index, question, selected, locked, onSelect }: { index: number; question: QuizQuestion; selected?: string; locked: boolean; onSelect: (option: "A" | "B" | "C" | "D") => void }) {
  return (
    <article className="rounded-lg border border-ink/10 bg-[#f8faf9] p-4 dark:border-white/10 dark:bg-[#101923]">
      <p className="text-xs font-black uppercase tracking-[0.14em] text-fern">Question {index + 1} | {question.topic}</p>
      <h3 className="mt-2 font-black leading-7">{question.question}</h3>
      <div className="mt-4 grid gap-2">
        {(["A", "B", "C", "D"] as const).map((key) => {
          const isSelected = selected === key;
          const isCorrect = locked && question.correct_answer === key;
          const state = isCorrect ? "border-fern bg-fern/10 text-fern" : locked && isSelected ? "border-coral bg-coral/10 text-coral" : isSelected ? "border-fern bg-fern/10 text-fern" : "border-ink/10 bg-white text-ink dark:border-white/10 dark:bg-white/5 dark:text-white";
          return <button key={key} type="button" disabled={locked} onClick={() => onSelect(key)} className={`focus-ring flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-left text-sm font-bold ${state}`}><span><b className="mr-2">{key}</b>{question.options[key]}</span>{isCorrect ? <CheckCircle2 className="h-4 w-4" /> : locked && isSelected ? <XCircle className="h-4 w-4" /> : null}</button>;
        })}
      </div>
      {locked ? <p className="mt-3 rounded-md bg-white p-3 text-sm leading-6 text-ink/65 dark:bg-white/5 dark:text-white/65"><b>Feedback: </b>{question.explanation}</p> : null}
    </article>
  );
}

function RevisionSummary({ summary }: { summary: RevisionQuizSubmitResponse }) {
  return (
    <div className="mt-5 rounded-lg border border-fern/20 bg-fern/5 p-4 dark:bg-emerald-300/10">
      <p className="section-kicker">Saved revision result</p>
      <h3 className="mt-1 text-2xl font-black">{summary.score}%</h3>
      <p className="mt-1 text-sm font-semibold text-ink/60 dark:text-white/60">{summary.correct} correct, {summary.wrong} to revise.</p>
      {summary.mistakes.length ? <div className="mt-4 grid gap-3">{summary.mistakes.map((item) => <MistakeCard key={`${item.question}-${item.selected_answer}`} item={item} />)}</div> : <p className="mt-3 text-sm font-bold text-fern">No revision mistakes in this run.</p>}
    </div>
  );
}

function HistoryCard({ item }: { item: RevisionQuizHistoryItem }) {
  return (
    <article className="rounded-lg border border-ink/10 bg-[#f8faf9] p-4 dark:border-white/10 dark:bg-[#101923]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h3 className="font-black">Revision quiz - {new Date(item.attempted_at).toLocaleDateString()}</h3><p className="mt-1 text-sm font-semibold text-ink/55 dark:text-white/55">{item.correct}/{item.total} correct</p></div>
        <span className="rounded-md bg-fern/10 px-3 py-2 font-black text-fern">{item.score}%</span>
      </div>
      {item.mistakes.length ? <div className="mt-4 grid gap-3">{item.mistakes.map((mistake) => <MistakeCard key={`${item.quiz_run_id}-${mistake.question}`} item={mistake} />)}</div> : <p className="mt-4 text-sm font-bold text-fern">Perfect revision run.</p>}
    </article>
  );
}

function MistakeCard({ item }: { item: RevisionQuizSubmitResponse["mistakes"][number] }) {
  return (
    <div className="rounded-md border border-coral/20 bg-coral/5 p-3 text-sm dark:bg-coral/10">
      <p className="font-black text-coral">{item.topic}{item.subtopic ? ` - ${item.subtopic}` : ""}</p>
      <p className="mt-2 leading-6 text-ink/72 dark:text-white/72">{item.question}</p>
      <p className="mt-2 text-xs font-black uppercase tracking-[0.12em] text-ink/45 dark:text-white/45">Selected {item.selected_answer} | Correct {item.correct_answer}</p>
      <p className="mt-2 leading-6 text-ink/68 dark:text-white/68">{item.feedback}</p>
      <p className="mt-2 rounded bg-white p-2 text-xs font-semibold text-ink/55 dark:bg-white/5 dark:text-white/55">{item.source_mistake}</p>
    </div>
  );
}

function MiniStat({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/10 px-4 py-3 text-right">
      <p className="flex items-center justify-end gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-white/50"><Icon className="h-4 w-4 text-amber" /> {label}</p>
      <p className="mt-1 text-2xl font-black text-white">{value}</p>
    </div>
  );
}
