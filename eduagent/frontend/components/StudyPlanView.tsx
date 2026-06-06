import { CalendarDays, ExternalLink, Target } from "lucide-react";
import { StudyDay } from "@/lib/api";

export function StudyPlanView({ plan, compact = false }: { plan: StudyDay[]; compact?: boolean }) {
  if (!plan.length) return <div className="panel p-6 text-sm text-ink/65 dark:text-white/65">No study plan selected.</div>;
  const rows = compact ? plan.slice(0, 5) : plan;
  return (
    <div className="grid gap-4">
      {rows.map((day) => (
        <section key={`${day.day}-${day.date}`} className="panel overflow-hidden">
          <div className="border-b border-ink/10 bg-[#f8faf9] px-5 py-4 dark:border-white/10 dark:bg-white/5">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-fern">Day {day.day}</p>
            <h2 className="mt-1 flex items-center gap-2 text-xl font-black text-ink dark:text-white"><CalendarDays className="h-5 w-5 text-skydeep" /> {day.date}</h2>
          </div>
          <div className="grid gap-3 p-5">
            {day.sessions.map((session, index) => (
              <article key={`${session.topic}-${index}`} className="rounded-lg border border-ink/10 bg-white p-4 dark:border-white/10 dark:bg-[#101923]">
                <h3 className="font-black text-ink dark:text-white">{session.topic}</h3>
                <p className="mt-1 text-sm text-ink/60 dark:text-white/60">{session.subtopic} - {session.hours}h - {session.activity}</p>
                <div className="mt-3 grid gap-2 text-sm text-ink/70 dark:text-white/70">
                  {session.focus_points.slice(0, compact ? 2 : 3).map((point) => <p key={point} className="flex gap-2"><Target className="mt-0.5 h-4 w-4 shrink-0 text-fern" />{point}</p>)}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {session.resources.slice(0, 3).map((resource) => (
                    <a key={resource.url} href={resource.url} target="_blank" rel="noreferrer" className="focus-ring inline-flex items-center gap-1 rounded-md bg-mist px-2.5 py-1.5 text-xs font-bold text-fern dark:bg-white/10">{resource.title}<ExternalLink className="h-3 w-3" /></a>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
