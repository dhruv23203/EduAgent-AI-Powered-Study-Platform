"use client";

import { FormEvent, Fragment, ReactNode, useEffect, useRef, useState } from "react";
import { Bot, Check, Clipboard, FileText, Loader2, MessageSquarePlus, Paperclip, Send, UploadCloud, UserRound, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { academicChat, ChatTurn, coachChat, studentIdFromStorage } from "@/lib/api";

type ChatMessage = ChatTurn & { id: string; planUpdates?: string[]; attachments?: string[] };
const id = () => (crypto?.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
const history = (rows: ChatMessage[]): ChatTurn[] => rows.slice(-8).map((row) => ({ role: row.role, content: row.content.slice(0, 1400) }));

export default function ChatPage() {
  const [mode, setMode] = useState<"academic" | "coach">("academic");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  function switchMode(next: "academic" | "coach") { setMode(next); setMessage(""); setMessages([]); setFiles([]); setError(""); }
  function addFiles(list: FileList | null) {
    if (!list) return;
    setFiles((current) => [...current, ...Array.from(list)].slice(0, 6));
  }
  function removeFile(index: number) {
    setFiles((current) => current.filter((_, i) => i !== index));
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    const prompt = message.trim();
    if (!prompt && !files.length) return;
    const prior = history(messages);
    const outgoingFiles = files;
    const outgoingText = prompt || "Please analyze the uploaded file(s).";
    setMessages((rows) => [...rows, { id: id(), role: "user", content: outgoingText, attachments: outgoingFiles.map((item) => item.name) }]);
    setMessage("");
    setFiles([]);
    setLoading(true);
    setError("");
    try {
      const studentId = studentIdFromStorage();
      const result = mode === "academic" ? await academicChat(studentId, outgoingText, outgoingFiles, prior) : await coachChat(studentId, outgoingText, prior);
      setMessages((rows) => [...rows, { id: id(), role: "assistant", content: result.answer, planUpdates: result.plan_updates }]);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Chat failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <section className="mx-auto flex min-h-[calc(100vh-7rem)] max-w-5xl flex-col overflow-hidden rounded-lg border border-ink/10 bg-white shadow-panel dark:border-white/10 dark:bg-[#151f2a]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink/10 bg-[#f8faf9] px-5 py-4 dark:border-white/10 dark:bg-white/5">
          <div>
            <p className="section-kicker">EduAgent chat</p>
            <h1 className="text-xl font-black">{mode === "academic" ? "Academic solver" : "Motivation coach"}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="grid grid-cols-2 rounded-lg bg-mist p-1 dark:bg-white/10">
              <button type="button" onClick={() => switchMode("academic")} className={`rounded-md px-3 py-2 text-sm font-black ${mode === "academic" ? "bg-white text-ink shadow-soft" : "text-ink/60 dark:text-white/60"}`}>Academic</button>
              <button type="button" onClick={() => switchMode("coach")} className={`rounded-md px-3 py-2 text-sm font-black ${mode === "coach" ? "bg-white text-ink shadow-soft" : "text-ink/60 dark:text-white/60"}`}>Coach</button>
            </div>
            <button onClick={() => { setMessages([]); setMessage(""); setFiles([]); }} className="focus-ring inline-flex items-center gap-2 rounded-lg border border-ink/10 bg-white px-3 py-2 text-sm font-black hover:text-fern dark:border-white/10 dark:bg-white/10"><MessageSquarePlus className="h-4 w-4" /> New</button>
          </div>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {messages.length ? messages.map((item) => item.role === "user" ? <UserBubble key={item.id} attachments={item.attachments}>{item.content}</UserBubble> : <AssistantBubble key={item.id}><MarkdownMessage content={item.content} />{item.planUpdates?.length ? <div className="mt-5 rounded-xl border border-fern/15 bg-fern/5 p-4 dark:bg-emerald-300/10"><p className="font-black">Plan adjustment ideas</p>{item.planUpdates.map((u) => <p key={u} className="mt-2 text-sm">{u}</p>)}</div> : null}</AssistantBubble>) : <div className="grid min-h-[360px] place-items-center px-6 text-center"><div><Bot className="mx-auto h-11 w-11 text-fern" /><h2 className="mt-4 text-2xl font-black">How can I help with your study today?</h2><p className="mt-2 max-w-md text-sm leading-6 text-ink/60 dark:text-white/60">Ask a question, paste code, or attach files in academic mode.</p></div></div>}
          {loading ? <AssistantBubble><div className="flex items-center gap-3 text-sm font-semibold"><Loader2 className="h-4 w-4 animate-spin text-fern" /> EduAgent is thinking...</div></AssistantBubble> : null}
          <div ref={endRef} />
        </div>
        <form onSubmit={submit} className="border-t border-ink/10 bg-white p-4 dark:border-white/10 dark:bg-[#111b26]">
          {files.length ? <div className="mb-3 flex flex-wrap gap-2">{files.map((item, index) => <span key={`${item.name}-${index}`} className="inline-flex max-w-full items-center gap-2 rounded-md border border-ink/10 bg-[#f8faf9] px-3 py-2 text-xs font-bold text-ink/65 dark:border-white/10 dark:bg-white/10 dark:text-white/65"><FileText className="h-3.5 w-3.5 text-fern" /><span className="max-w-[220px] truncate">{item.name}</span><button type="button" onClick={() => removeFile(index)} className="rounded p-0.5 hover:bg-ink/10 dark:hover:bg-white/10" aria-label={`Remove ${item.name}`}><X className="h-3.5 w-3.5" /></button></span>)}</div> : null}
          <div className="rounded-lg border border-ink/10 bg-[#f8faf9] p-2 dark:border-white/10 dark:bg-[#0f1720]">
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} placeholder={mode === "academic" ? "Message EduAgent, or attach files for analysis..." : "Share what is blocking your study momentum..."} className="min-h-20 w-full resize-none bg-transparent p-2 text-ink outline-none placeholder:text-ink/35 dark:text-white dark:placeholder:text-white/35" />
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {mode === "academic" ? <label className="focus-ring inline-flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm font-black text-ink/60 hover:bg-white hover:text-fern dark:text-white/60 dark:hover:bg-white/10"><Paperclip className="h-4 w-4" /> Upload anything<input type="file" multiple accept="*/*" className="sr-only" onChange={(e) => { addFiles(e.target.files); e.currentTarget.value = ""; }} /></label> : <span className="inline-flex items-center gap-2 px-3 py-2 text-sm font-bold text-ink/45 dark:text-white/45"><UploadCloud className="h-4 w-4" /> Uploads in academic mode</span>}
              </div>
              <button disabled={loading || (!message.trim() && !files.length)} className="focus-ring inline-flex h-10 w-10 items-center justify-center rounded-md bg-ink text-white hover:bg-fern disabled:opacity-60 dark:bg-fern dark:hover:bg-skydeep" aria-label="Send message">{loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}</button>
            </div>
          </div>
        </form>
      </section>
      {error ? <div className="panel mx-auto mt-6 max-w-5xl border-coral/20 p-5 text-coral">{error}</div> : null}
    </AppShell>
  );
}

function UserBubble({ children, attachments = [] }: { children: ReactNode; attachments?: string[] }) { return <div className="flex items-start justify-end gap-3"><div className="max-w-[82%] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-fern px-4 py-3 font-semibold leading-6 text-white shadow-soft">{attachments.length ? <div className="mb-3 flex flex-wrap gap-2">{attachments.map((name) => <span key={name} className="inline-flex max-w-[240px] items-center gap-2 rounded-md bg-white/15 px-2 py-1 text-xs"><FileText className="h-3.5 w-3.5" /><span className="truncate">{name}</span></span>)}</div> : null}{children}</div><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-ink text-white dark:bg-white dark:text-ink"><UserRound className="h-5 w-5" /></span></div>; }
function AssistantBubble({ children }: { children: ReactNode }) { return <div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-fern text-white"><Bot className="h-5 w-5" /></span><article className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-ink/10 bg-white p-5 shadow-soft dark:border-white/10 dark:bg-[#151f2a]"><div className="mb-3 flex items-center justify-between border-b border-ink/10 pb-3 dark:border-white/10"><h2 className="font-black">EduAgent response</h2><span className="rounded-full bg-fern/10 px-3 py-1 text-xs font-black text-fern">AI</span></div>{children}</article></div>; }

function MarkdownMessage({ content }: { content: string }) { const parts = content.split(/```([\w-]*)\n([\s\S]*?)```/g); return <div className="text-[15px] leading-7 text-ink/75 dark:text-white/75">{parts.map((part, i) => i % 3 === 2 ? <CodeBlock key={i} code={part} language={parts[i - 1] || "code"} /> : i % 3 === 1 ? null : <Fragment key={i}>{renderText(part)}</Fragment>)}</div>; }
function renderText(text: string) { return text.split("\n").filter((line) => line.trim() && !/^[-=]{3,}$/.test(line.trim())).map((line, i) => { const trimmed = line.trim(); if (/^#{1,3}\s/.test(trimmed) || /^\*\*.*\*\*$/.test(trimmed)) return <h3 key={i} className="mb-2 mt-4 text-xl font-black">{trimmed.replace(/^#{1,3}\s/, "").replace(/^\*\*|\*\*$/g, "")}</h3>; if (/^[-*]\s/.test(trimmed)) return <p key={i} className="ml-4 list-item">{inline(trimmed.replace(/^[-*]\s/, ""))}</p>; return <p key={i} className="mb-3">{inline(trimmed)}</p>; }); }
function inline(text: string) { return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((token, i) => token.startsWith("**") ? <strong key={i}>{token.slice(2, -2)}</strong> : token.startsWith("`") ? <code key={i} className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-skydeep dark:bg-white/10 dark:text-emerald-200">{token.slice(1, -1)}</code> : token); }
function CodeBlock({ code, language }: { code: string; language: string }) { const [copied, setCopied] = useState(false); async function copy() { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1200); } return <div className="mb-5 overflow-hidden rounded-xl border border-ink/10 bg-[#0b1220] dark:border-white/10"><div className="flex items-center justify-between border-b border-white/10 bg-white/5 px-4 py-2"><span className="text-xs font-black uppercase tracking-[0.14em] text-white/60">{language}</span><button type="button" onClick={copy} className="inline-flex items-center gap-2 rounded-md px-2 py-1 text-xs font-bold text-white/70 hover:bg-white/10">{copied ? <Check className="h-3.5 w-3.5" /> : <Clipboard className="h-3.5 w-3.5" />}{copied ? "Copied" : "Copy"}</button></div><pre className="max-h-[520px] overflow-x-auto p-4 text-sm leading-6 text-slate-100"><code>{code.trim()}</code></pre></div>; }
