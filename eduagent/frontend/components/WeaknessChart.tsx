"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function WeaknessChart({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data).map(([topic, accuracy]) => ({ topic, accuracy })).sort((a, b) => a.accuracy - b.accuracy);
  const average = rows.length ? Math.round(rows.reduce((sum, row) => sum + row.accuracy, 0) / rows.length) : 0;
  const weakest = rows[0];
  if (!rows.length) return <div className="panel p-5 text-sm text-ink/65 dark:text-white/60">No quiz data yet.</div>;
  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-ink/10 bg-[#f8faf9] p-5 dark:border-white/10 dark:bg-white/5">
        <div>
          <p className="section-kicker">Accuracy</p>
          <h2 className="mt-1 text-xl font-black text-ink dark:text-white">Topic performance</h2>
          <p className="mt-1 text-sm text-ink/55 dark:text-white/55">Sorted from weakest to strongest so revision priorities are obvious.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-right">
          <div className="rounded-md border border-ink/10 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#101923]">
            <p className="text-xs font-black uppercase tracking-[0.12em] text-ink/45 dark:text-white/45">Average</p>
            <p className="text-2xl font-black text-fern">{average}%</p>
          </div>
          <div className="rounded-md border border-ink/10 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#101923]">
            <p className="text-xs font-black uppercase tracking-[0.12em] text-ink/45 dark:text-white/45">Revise</p>
            <p className="max-w-32 truncate text-sm font-black text-coral">{weakest?.topic || "None"}</p>
          </div>
        </div>
      </div>
      <div className="h-80 p-5">
        <ResponsiveContainer>
          <BarChart data={rows} margin={{ top: 8, right: 12, left: -18, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(23,33,43,0.12)" />
            <XAxis dataKey="topic" tick={{ fontSize: 12, fill: "currentColor" }} tickLine={false} axisLine={false} interval={0} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "currentColor" }} tickLine={false} axisLine={false} />
            <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid rgba(23,33,43,0.12)", fontWeight: 700 }} formatter={(value) => [`${value}%`, "Accuracy"]} />
            <Bar dataKey="accuracy" fill="#238269" radius={[7, 7, 0, 0]} maxBarSize={56} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
