import Link from "next/link";
import {
  ArrowRight,
  BookOpenCheck,
  Bot,
  CalendarCheck2,
  CheckCircle2,
  Flame,
  GraduationCap,
  LineChart,
  ShieldCheck,
  Trophy,
  UploadCloud
} from "lucide-react";

const featureCards = [
  { title: "Plans", metric: "Saved", copy: "Current, existing, and completed study plans stay attached to each account.", icon: BookOpenCheck },
  { title: "Streaks", metric: "Daily", copy: "A LeetCode-style heatmap makes consistency visible from start date to exam day.", icon: Flame },
  { title: "Rewards", metric: "+Coins", copy: "Badges, targets, and recovery coins keep the student loop active.", icon: Trophy }
];

const workflow = [
  { title: "Upload", copy: "Syllabus and notes", icon: UploadCloud },
  { title: "Plan", copy: "Daily exam lane", icon: CalendarCheck2 },
  { title: "Quiz", copy: "Groq-generated checks", icon: Bot },
  { title: "Improve", copy: "Weak-area feedback", icon: LineChart }
];

export default function WelcomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-ink text-white">
      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1800&q=80')] bg-cover bg-center" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(9,16,24,.94)_0%,rgba(9,16,24,.82)_48%,rgba(9,16,24,.60)_100%)]" />
      <div className="absolute inset-x-0 bottom-0 h-56 bg-[linear-gradient(0deg,rgba(9,16,24,.88)_0%,rgba(9,16,24,0)_100%)]" />
      <div className="hero-grid absolute inset-0" />
      <section className="relative mx-auto flex min-h-screen max-w-7xl flex-col justify-between px-5 py-7 sm:px-6 lg:py-9">
        <nav className="flex flex-wrap items-center justify-between gap-4">
          <span className="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/10 px-4 py-2 font-black text-white shadow-panel backdrop-blur-md">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-fern">
              <GraduationCap className="h-5 w-5 text-white" />
            </span>
            EduAgent
          </span>
          <div className="hidden flex-wrap gap-3 md:flex">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-bold text-white/85 backdrop-blur">
              <ShieldCheck className="h-4 w-4 text-emerald-200" /> Private progress
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-bold text-white/85 backdrop-blur">
              <Bot className="h-4 w-4 text-amber" /> Groq quizzes
            </span>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[minmax(0,1fr)_430px] lg:py-8">
          <div className="max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100 backdrop-blur">
              <Flame className="h-4 w-4 text-amber" /> Streaks, quizzes, badges
            </div>
            <h1 className="mt-7 max-w-4xl text-5xl font-black leading-[1.02] text-white sm:text-6xl lg:text-7xl">
              Turn PDFs into your study command center.
            </h1>
            <p className="mt-6 max-w-3xl text-xl leading-9 text-white/88">
              Upload syllabus and notes, get a daily plan, generate Groq quizzes, track streaks, earn badges, and chat with academic or motivation agents.
            </p>
            <div className="mt-9 flex flex-wrap gap-4">
              <Link href="/login?mode=signup" className="focus-ring group inline-flex items-center gap-3 rounded-lg bg-fern px-6 py-4 text-lg font-black text-white shadow-panel transition hover:-translate-y-0.5 hover:bg-emerald-700">
                Start as new user <ArrowRight className="h-5 w-5 transition group-hover:translate-x-1" />
              </Link>
              <Link href="/login?mode=login" className="focus-ring inline-flex items-center gap-3 rounded-lg border border-white/25 bg-white/10 px-6 py-4 text-lg font-black text-white shadow-soft backdrop-blur-md transition hover:-translate-y-0.5 hover:bg-white/20">
                Existing user login
              </Link>
            </div>
            <div className="mt-8 grid max-w-3xl gap-3 sm:grid-cols-4">
              {workflow.map(({ title, copy, icon: Icon }) => (
                <div key={title} className="rounded-lg border border-white/15 bg-white/10 p-3 backdrop-blur transition hover:-translate-y-1 hover:border-amber/50 hover:bg-white/15">
                  <Icon className="h-5 w-5 text-amber" />
                  <p className="mt-3 font-black text-white">{title}</p>
                  <p className="mt-1 text-sm font-semibold text-white/68">{copy}</p>
                </div>
              ))}
            </div>
          </div>

          <aside className="glass-card slow-float hidden p-5 lg:block">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-100">Live cockpit</p>
                <h2 className="mt-2 text-2xl font-black text-white">Today&apos;s lane</h2>
              </div>
              <span className="rounded-full bg-amber px-3 py-1 text-sm font-black text-ink">+45 coins</span>
            </div>
            <div className="mt-5 space-y-3">
              {["Finish Binary Trees", "Practice 12 problems", "Complete 3 quizzes"].map((item, index) => (
                <div key={item} className="flex items-center justify-between rounded-lg border border-white/12 bg-white/10 p-3">
                  <span className="font-bold text-white/88">{item}</span>
                  <CheckCircle2 className={`h-5 w-5 ${index < 2 ? "text-emerald-200" : "text-white/45"}`} />
                </div>
              ))}
            </div>
            <div className="mt-5 rounded-lg border border-white/12 bg-white/10 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-black uppercase tracking-[0.18em] text-white/55">Study heatmap</span>
                <LineChart className="h-5 w-5 text-amber" />
              </div>
              <div className="mt-4 grid grid-cols-7 gap-2">
                {[3, 1, 4, 2, 5, 3, 4, 2, 5, 3, 4, 5, 1, 3, 4, 2, 5, 4, 3, 5, 2].map((level, index) => (
                  <span
                    key={`${level}-${index}`}
                    className={`h-7 rounded-md ${level === 1 ? "bg-white/20" : level === 2 ? "bg-emerald-200/55" : level === 3 ? "bg-emerald-400/70" : level === 4 ? "bg-fern" : "bg-amber"}`}
                  />
                ))}
              </div>
            </div>
          </aside>
        </div>

        <div className="grid gap-4 pb-4 md:grid-cols-3">
          {featureCards.map(({ title, metric, copy, icon: Icon }) => (
            <article key={title} className="group rounded-lg border border-white/20 bg-white/10 p-5 shadow-soft backdrop-blur-md transition hover:-translate-y-1 hover:border-amber/45 hover:bg-white/15">
              <div className="flex items-start justify-between gap-4">
                <Icon className="h-7 w-7 text-amber" />
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-black uppercase tracking-[0.12em] text-white/70">{metric}</span>
              </div>
              <h2 className="mt-4 text-2xl font-black text-white">{title}</h2>
              <p className="mt-2 leading-7 text-white/72">{copy}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
