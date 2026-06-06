"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function WeaknessChart({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data).map(([topic, accuracy]) => ({ topic, accuracy }));
  if (!rows.length) return <div className="panel p-5 text-sm text-ink/65 dark:text-white/60">No quiz data yet.</div>;
  return (
    <section className="panel p-5">
      <p className="section-kicker">Accuracy</p>
      <h2 className="mt-1 text-xl font-black text-ink dark:text-white">Topic performance</h2>
      <div className="mt-5 h-72">
        <ResponsiveContainer>
          <BarChart data={rows}>
            <XAxis dataKey="topic" tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Bar dataKey="accuracy" fill="#1f7a5f" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
