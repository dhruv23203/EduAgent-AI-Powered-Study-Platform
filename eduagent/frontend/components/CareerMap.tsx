import { Award, Building2, ExternalLink } from "lucide-react";
import { CareerResponse } from "@/lib/api";

export function CareerMap({ careers }: { careers: CareerResponse["careers"] }) {
  if (!careers.length) return <div className="panel p-5 text-sm text-ink/65 dark:text-white/65">Career matches will appear here.</div>;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {careers.map((career) => (
        <article key={career.role} className="panel overflow-hidden">
          <div className="border-b border-ink/10 bg-[#f8faf9] p-5 dark:border-white/10 dark:bg-white/5">
            <div className="flex items-start justify-between gap-3">
              <div><h2 className="text-xl font-black text-ink dark:text-white">{career.role}</h2><p className="mt-1 text-sm font-semibold text-ink/60 dark:text-white/60">{career.avg_salary_lpa} LPA</p></div>
              <span className="rounded-md bg-mist px-3 py-2 text-sm font-black text-fern dark:bg-white/10">{career.match_score}%</span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-mist dark:bg-white/10"><div className="h-full rounded-full bg-fern" style={{ width: `${career.match_score}%` }} /></div>
          </div>
          <div className="p-5">
            <div className="flex flex-wrap gap-2">{career.matching_skills.map((skill) => <span key={skill} className="rounded-md bg-skydeep/10 px-3 py-1 text-sm font-bold text-skydeep dark:bg-white/10 dark:text-sky-200">{skill}</span>)}</div>
            <div className="mt-4 grid gap-2 text-sm text-fern dark:text-emerald-200">{career.certifications.map((cert) => <p key={cert} className="flex items-center gap-2"><Award className="h-4 w-4" />{cert}<ExternalLink className="h-3 w-3" /></p>)}</div>
            <div className="mt-4 flex flex-wrap gap-2">{career.companies.map((company) => <span key={company} className="inline-flex items-center gap-2 rounded-md bg-[#f8fbfa] px-3 py-1 text-sm font-semibold text-ink/70 dark:bg-white/10 dark:text-white/75"><Building2 className="h-3.5 w-3.5" />{company}</span>)}</div>
          </div>
        </article>
      ))}
    </div>
  );
}
