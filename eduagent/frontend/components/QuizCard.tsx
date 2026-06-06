import { CheckCircle2, XCircle } from "lucide-react";
import { QuizQuestion } from "@/lib/api";

export function QuizCard({ question, selected, locked, onSelect }: { question: QuizQuestion; selected?: string; locked: boolean; onSelect: (option: "A" | "B" | "C" | "D") => void }) {
  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-ink/10 bg-[#f8faf9] px-5 py-4 dark:border-white/10 dark:bg-white/5">
        <span className="rounded-md bg-mist px-3 py-2 text-sm font-semibold text-fern dark:bg-white/10">{question.topic}</span>
        <span className="text-sm font-medium text-ink/60 dark:text-white/60">{question.difficulty}</span>
      </div>
      <div className="p-5">
        <h1 className="text-2xl font-black leading-snug text-ink dark:text-white">{question.question}</h1>
        <div className="mt-5 grid gap-3">
          {(["A", "B", "C", "D"] as const).map((key) => {
            const isSelected = selected === key;
            const isCorrect = question.correct_answer === key;
            const state = locked && isCorrect ? "border-fern bg-fern/10 text-fern dark:text-emerald-200" : locked && isSelected ? "border-coral bg-coral/10 text-coral" : isSelected ? "border-fern bg-fern/10 text-fern" : "border-ink/10 bg-white text-ink hover:border-skydeep dark:border-white/10 dark:bg-[#101923] dark:text-white";
            return (
              <button key={key} type="button" disabled={locked} onClick={() => onSelect(key)} className={`focus-ring flex items-center justify-between rounded-lg border px-4 py-3 text-left font-semibold ${state}`}>
                <span><span className="mr-4 font-black">{key}</span>{question.options[key]}</span>
                {locked && isCorrect ? <CheckCircle2 className="h-5 w-5" /> : locked && isSelected ? <XCircle className="h-5 w-5" /> : null}
              </button>
            );
          })}
        </div>
        {locked ? <div className="mt-5 rounded-lg border border-fern/20 bg-mist p-4 text-sm leading-6 text-ink/75 dark:bg-white/10 dark:text-white/75"><b>Explanation: </b>{question.explanation}</div> : null}
      </div>
    </section>
  );
}
