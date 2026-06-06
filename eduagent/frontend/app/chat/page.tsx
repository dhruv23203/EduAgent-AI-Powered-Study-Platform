"use client";

import { FormEvent, Fragment, ReactNode, useEffect, useRef, useState } from "react";
import { Bot, Check, Clipboard, Loader2, MessageSquarePlus, Send, UploadCloud, UserRound } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { academicChat, ChatTurn, coachChat, studentIdFromStorage } from "@/lib/api";

type ChatMessage = ChatTurn & { id: string; planUpdates?: string[] };
const id = () => (crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
const history = (rows: ChatMessage[]): ChatTurn[] => rows.slice(-8).map((row) => ({ role: row.role, content: row.content.slice(0, 1400) }));

export default function ChatPage() {
  const [mode, setMode] = useState<"academic" | "coach">("academic");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  function switchMode(next: "academic" | "coach") { setMode(next); setMessage(""); setMessages([]); setFile(null); setError(""); }
  async function submit(event: FormEvent) {
    event.preventDefault();
    const prompt = message.trim();
    if (!prompt) return;
    const prior = history(messages);
    setMessages((rows) => [...rows, { id: id(), role: "user", content: prompt }]);
    setMessage("");
    setLoading(true);
    setError("");
    try {
      const studentId = studentIdFromStorage();
      const result = mode === "academic" ? await academicChat(studentId, prompt, file, prior) : await coachChat(studentId, prompt, prior);
      setMessages((rows) => [...rows, { id: id(), role: "assistant", content: result.answer, planUpdates: result.plan_updates }]);
      setFile(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Chat failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <section className="rounded-lg bg-ink p-6 text-white shadow-panel"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-white/60">Chatbots</p><h1 className="mt-2 text-3xl font-black">Ask EduAgent</h1><p className="mt-2 max-w-2xl text-white/65">Use academic mode for problem solving, or coach mode for motivation, time issues, distractions, and plan adjustments.</p></section>
      <section className="panel mx-auto mt-6 min-h-[360px] max-w-5xl p-5">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 pb-4 dark:border-white/10"><div><p className="section-kicker">Conversation</p><h2 className="text-xl font-black">{mode === "academic" ? "Academic solver thread" : "Motivation coach thread"}</h2></div><button onClick={() => { setMessages([]); setMessage(""); }} className="focus-ring inline-flex items-center gap-2 rounded-lg border border-ink/10 bg-white px-4 py-2 text-sm font-black hover:text-fern dark:border-white/10 dark:bg-white/10"><MessageSquarePlus className="h-4 w-4" /> New chat</button></div>
        <div className="space-y-5">{messages.length ? messages.map((item) => item.role === "user" ? <UserBubble key={item.id}>{item.content}</UserBubble> : <AssistantBubble key={item.id}><MarkdownMessage content={item.content} />{item.planUpdates?.length ? <div className="mt-5 rounded-xl border border-fern/15 bg-fern/5 p-4 dark:bg-emerald-300/10"><p className="font-black">Plan adjustment ideas</p>{item.planUpdates.map((u) => <p key={u} className="mt-2 text-sm">{u}</p>)}</div> : null}</AssistantBubble>) : <div className="grid min-h-[220px] place-items-center rounded-2xl border border-dashed border-ink/15 bg-[#f8faf9] px-6 text-center dark:border-white/10 dark:bg-white/5"><div><Bot className="mx-auto h-10 w-10 text-fern" /><h3 className="mt-4 text-xl font-black">Start a continuous chat</h3><p className="mt-2 max-w-md text-sm leading-6 text-ink/60 dark:text-white/60">Ask your first question below. Follow-ups stay in this thread.</p></div></div>}{loading ? <AssistantBubble><div className="flex items-center gap-3 text-sm font-semibold"><Loader2 className="h-4 w-4 animate-spin text-fern" /> EduAgent is thinking...</div></AssistantBubble> : null}<div ref={endRef} /></div>
      </section>
      <form onSubmit={submit} className="panel mx-auto mt-5 max-w-5xl p-5">
        <div className="grid grid-cols-2 rounded-lg bg-mist p-1 dark:bg-white/10"><button type="button" onClick={() => switchMode("academic")} className={`rounded-md px-3 py-2 font-black ${mode === "academic" ? "bg-white text-ink shadow-soft" : "text-ink/60 dark:text-white/60"}`}>Academic solver</button><button type="button" onClick={() => switchMode("coach")} className={`rounded-md px-3 py-2 font-black ${mode === "coach" ? "bg-white text-ink shadow-soft" : "text-ink/60 dark:text-white/60"}`}>Motivation coach</button></div>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={4} placeholder={mode === "academic" ? "Ask a coding, math, science, or exam topic question..." : "Share what is blocking your study momentum..."} className="focus-ring mt-5 w-full rounded-lg border border-ink/10 bg-white p-3 text-ink dark:border-white/10 dark:bg-[#0f1720] dark:text-white" required />
        {mode === "academic" ? <label className="mt-4 flex cursor-pointer items-center justify-between rounded-lg border border-dashed border-ink/20 bg-[#f8faf9] px-4 py-3 text-sm font-semibold text-ink/65 dark:border-white/10 dark:bg-white/10 dark:text-white/65"><span className="flex items-center gap-2"><UploadCloud className="h-4 w-4 text-fern" />{file ? file.name : "Upload text or PDF problem"}</span><input type="file" accept=".txt,application/pdf" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label> : null}
        <button disabled={loading || !message.trim()} className="focus-ring mt-5 inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-ink px-6 font-bold text-white hover:bg-skydeep disabled:opacity-60">{loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />} Send</button>
      </form>
      {error ? <div className="panel mx-auto mt-6 max-w-5xl border-coral/20 p-5 text-coral">{error}</div> : null}
    </AppShell>
  );
}

function UserBubble({ children }: { children: ReactNode }) { return <div className="flex items-start justify-end gap-3"><div className="max-w-[82%] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-fern px-4 py-3 font-semibold leading-6 text-white shadow-soft">{children}</div><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-ink text-white dark:bg-white dark:text-ink"><UserRound className="h-5 w-5" /></span></div>; }
function AssistantBubble({ children }: { children: ReactNode }) { return <div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-fern text-white"><Bot className="h-5 w-5" /></span><article className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-ink/10 bg-white p-5 shadow-soft dark:border-white/10 dark:bg-[#151f2a]"><div className="mb-3 flex items-center justify-between border-b border-ink/10 pb-3 dark:border-white/10"><h2 className="font-black">EduAgent response</h2><span className="rounded-full bg-fern/10 px-3 py-1 text-xs font-black text-fern">AI</span></div>{children}</article></div>; }

function MarkdownMessage({ content }: { content: string }) { const parts = content.split(/```([\w-]*)\n([\s\S]*?)```/g); return <div className="text-[15px] leading-7 text-ink/75 dark:text-white/75">{parts.map((part, i) => i % 3 === 2 ? <CodeBlock key={i} code={part} language={parts[i - 1] || "code"} /> : i % 3 === 1 ? null : <Fragment key={i}>{renderText(part)}</Fragment>)}</div>; }
function renderText(text: string) { return text.split("\n").filter((line) => line.trim() && !/^[-=]{3,}$/.test(line.trim())).map((line, i) => { const trimmed = line.trim(); if (/^#{1,3}\s/.test(trimmed) || /^\*\*.*\*\*$/.test(trimmed)) return <h3 key={i} className="mb-2 mt-4 text-xl font-black">{trimmed.replace(/^#{1,3}\s/, "").replace(/^\*\*|\*\*$/g, "")}</h3>; if (/^[-*]\s/.test(trimmed)) return <p key={i} className="ml-4 list-item">{inline(trimmed.replace(/^[-*]\s/, ""))}</p>; return <p key={i} className="mb-3">{inline(trimmed)}</p>; }); }
function inline(text: string) { return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((token, i) => token.startsWith("**") ? <strong key={i}>{token.slice(2, -2)}</strong> : token.startsWith("`") ? <code key={i} className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-skydeep dark:bg-white/10 dark:text-emerald-200">{token.slice(1, -1)}</code> : token); }
function CodeBlock({ code, language }: { code: string; language: string }) { const [copied, setCopied] = useState(false); async function copy() { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1200); } return <div className="mb-5 overflow-hidden rounded-xl border border-ink/10 bg-[#0b1220] dark:border-white/10"><div className="flex items-center justify-between border-b border-white/10 bg-white/5 px-4 py-2"><span className="text-xs font-black uppercase tracking-[0.14em] text-white/60">{language}</span><button type="button" onClick={copy} className="inline-flex items-center gap-2 rounded-md px-2 py-1 text-xs font-bold text-white/70 hover:bg-white/10">{copied ? <Check className="h-3.5 w-3.5" /> : <Clipboard className="h-3.5 w-3.5" />}{copied ? "Copied" : "Copy"}</button></div><pre className="max-h-[520px] overflow-x-auto p-4 text-sm leading-6 text-slate-100"><code>{code.trim()}</code></pre></div>; }
