"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  Eye,
  EyeOff,
  Flame,
  GraduationCap,
  Loader2,
  LockKeyhole,
  LogIn,
  Mail,
  ShieldCheck,
  Trophy,
  User,
  UserPlus
} from "lucide-react";
import { googleLogin, login, logout, saveAuth, signup } from "@/lib/api";

const promiseCards = [
  { title: "Plans", value: "Saved", icon: BookOpenCheck },
  { title: "Streaks", value: "Synced", icon: Flame },
  { title: "Badges", value: "Earned", icon: Trophy }
];

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    logout();
    setMode(new URLSearchParams(window.location.search).get("mode") === "login" ? "login" : "signup");
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) return;

    const initializeGoogle = () => {
      window.google?.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            const auth = await googleLogin(response.credential);
            saveAuth(auth);
            router.replace("/plans");
          } catch (exc) {
            setError(exc instanceof Error ? exc.message : "Google sign-in failed.");
          }
        }
      });
    };

    if (window.google?.accounts.id) {
      initializeGoogle();
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>('script[src="https://accounts.google.com/gsi/client"]');
    if (existingScript) {
      existingScript.addEventListener("load", initializeGoogle, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = initializeGoogle;
    document.body.appendChild(script);
  }, [router]);

  function switchMode(nextMode: "signup" | "login") {
    setMode(nextMode);
    setError("");
    window.history.replaceState(null, "", `/login?mode=${nextMode}`);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const auth = mode === "signup" ? await signup(name, email, password) : await login(email, password);
      saveAuth(auth);
      router.replace("/plans");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  function continueWithGoogle() {
    setError("");
    if (!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) {
      setError("Google sign-in is not configured yet.");
      return;
    }
    if (!window.google?.accounts.id) {
      setError("Google sign-in is still loading. Try again in a moment.");
      return;
    }
    window.google.accounts.id.prompt();
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-ink text-white">
      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=80')] bg-cover bg-center" />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(9,16,24,.92)_0%,rgba(9,16,24,.76)_50%,rgba(9,16,24,.58)_100%)]" />
      <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-white/8 backdrop-blur-[1px] lg:block" />
      <div className="hero-grid absolute inset-0" />
      <Link
        href="/"
        className="focus-ring group absolute left-4 top-4 z-20 inline-flex items-center gap-2 rounded-full border border-white/16 bg-white/10 px-4 py-2 text-sm font-black text-white/88 shadow-soft backdrop-blur-md transition hover:-translate-y-0.5 hover:bg-white/16 hover:text-white sm:left-6 sm:top-6"
      >
        <ArrowLeft className="h-4 w-4 transition group-hover:-translate-x-0.5" /> Back to welcome
      </Link>

      <div className="relative mx-auto grid min-h-screen max-w-7xl items-center gap-8 px-5 pb-7 pt-20 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(460px,560px)]">
        <section className="py-8">
          <div className="inline-flex items-center gap-3">
            <span className="grid h-14 w-14 place-items-center rounded-lg bg-fern shadow-panel">
              <GraduationCap className="h-7 w-7" />
            </span>
            <div>
              <span className="text-2xl font-black">EduAgent</span>
              <p className="text-sm font-bold text-white/60">Account workspace</p>
            </div>
          </div>
          <h1 className="mt-8 max-w-3xl text-5xl font-black leading-[1.08] sm:text-6xl">
            Sign in to your study brain.
          </h1>
          <p className="mt-5 max-w-2xl text-xl leading-9 text-white/78">
            Plans, quizzes, streaks, coins, badges, revision, and weak areas stay attached to your account.
          </p>
          <div className="mt-7 flex max-w-2xl flex-wrap gap-3">
            {["Fresh login", "Saved dashboards", "Groq-ready quizzes"].map((label) => (
              <span key={label} className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-black text-white/78 backdrop-blur-md">
                <CheckCircle2 className="h-4 w-4 text-emerald-200" /> {label}
              </span>
            ))}
          </div>
          <div className="mt-8 grid max-w-2xl gap-3 sm:grid-cols-3">
            {promiseCards.map(({ title, value, icon: Icon }) => (
              <div key={title} className="rounded-lg border border-white/16 bg-white/10 p-4 backdrop-blur-md transition hover:-translate-y-1 hover:border-amber/45 hover:bg-white/15">
                <Icon className="h-5 w-5 text-amber" />
                <p className="mt-4 text-xs font-black uppercase tracking-[0.18em] text-white/45">{title}</p>
                <p className="mt-1 text-xl font-black text-white">{value}</p>
              </div>
            ))}
          </div>
        </section>

        <form onSubmit={submit} className="max-h-[calc(100vh-3.5rem)] overflow-y-auto rounded-lg border border-white/70 bg-white/95 p-5 text-ink shadow-panel backdrop-blur-xl sm:p-7 dark:border-white/10 dark:bg-[#111b26]/95 dark:text-white">
          <div className="relative grid grid-cols-2 overflow-hidden rounded-lg bg-ink/5 p-1 dark:bg-white/10">
            <span
              aria-hidden="true"
              className="absolute bottom-1 left-1 top-1 w-[calc(50%-0.25rem)] rounded-md bg-[var(--auth-tab-active-bg)] shadow-soft transition-transform duration-300"
              style={{ transform: mode === "login" ? "translateX(100%)" : "translateX(0)" }}
            />
            <button
              type="button"
              aria-pressed={mode === "signup"}
              onClick={() => switchMode("signup")}
              className="focus-ring relative z-10 inline-flex items-center justify-center gap-2 rounded-md px-3 py-3 font-black transition"
              style={{ color: mode === "signup" ? "var(--auth-tab-active-text)" : "var(--auth-tab-inactive-text)" }}
            >
              <UserPlus className="h-5 w-5" /> Sign up
            </button>
            <button
              type="button"
              aria-pressed={mode === "login"}
              onClick={() => switchMode("login")}
              className="focus-ring relative z-10 inline-flex items-center justify-center gap-2 rounded-md px-3 py-3 font-black transition"
              style={{ color: mode === "login" ? "var(--auth-tab-active-text)" : "var(--auth-tab-inactive-text)" }}
            >
              <LogIn className="h-5 w-5" /> Login
            </button>
          </div>

          <div className="mt-7 flex items-start justify-between gap-4">
            <div>
              <p className="section-kicker">{mode === "signup" ? "New workspace" : "Welcome back"}</p>
              <h2 className="mt-2 text-3xl font-black sm:text-4xl">{mode === "signup" ? "Create your study account" : "Open your saved plans"}</h2>
            </div>
            <span className="hidden rounded-full border border-fern/20 bg-fern/10 p-3 text-fern dark:border-emerald-200/20 dark:bg-emerald-200/10 dark:text-emerald-100 sm:inline-flex">
              <ShieldCheck className="h-6 w-6" />
            </span>
          </div>

          {error ? <div className="mt-5 rounded-lg border border-coral/30 bg-coral/10 p-3 font-bold text-coral">{error}</div> : null}

          <button
            type="button"
            onClick={continueWithGoogle}
            className="focus-ring mt-5 flex h-14 w-full items-center justify-center gap-3 rounded-lg border border-ink/10 bg-white px-4 py-3 font-bold text-ink/75 shadow-sm transition hover:-translate-y-0.5 hover:border-fern/30 hover:text-ink hover:shadow-soft dark:border-white/10 dark:bg-white dark:text-ink/80"
          >
            <span className="grid h-8 w-8 place-items-center rounded-full bg-white text-xl font-black text-[#4285f4] shadow-sm">G</span>
            Continue with Google
          </button>

          <div className="my-6 flex items-center gap-3 text-xs font-black uppercase tracking-[0.18em] text-ink/35 dark:text-white/35">
            <span className="h-px flex-1 bg-ink/10 dark:bg-white/10" /> or use email <span className="h-px flex-1 bg-ink/10 dark:bg-white/10" />
          </div>

          <div className="space-y-4">
            {mode === "signup" ? (
              <label className="block">
                <span className="text-sm font-black">Name</span>
                <div className="relative mt-2">
                  <User className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink/35 dark:text-white/35" />
                  <input value={name} onChange={(e) => setName(e.target.value)} className="auth-input pl-12" required />
                </div>
              </label>
            ) : null}

            <label className="block">
              <span className="text-sm font-black">Email</span>
              <div className="relative mt-2">
                <Mail className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink/35 dark:text-white/35" />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="auth-input pl-12" required />
              </div>
            </label>

            <label className="block">
              <span className="text-sm font-black">Password</span>
              <div className="relative mt-2">
                <LockKeyhole className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink/35 dark:text-white/35" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="auth-input pl-12 pr-12"
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="focus-ring absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-md text-ink/45 transition hover:bg-ink/5 hover:text-ink dark:text-white/45 dark:hover:bg-white/10 dark:hover:text-white"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </label>
          </div>

          <div className="mt-5 rounded-lg border border-fern/15 bg-fern/10 p-3 dark:border-emerald-200/10 dark:bg-white/5">
            <div className="flex items-center gap-2 text-sm font-bold text-ink/70 dark:text-white/72">
              <CheckCircle2 className="h-5 w-5 text-fern dark:text-emerald-200" />
              Progress, badges, and plans persist after project restarts.
            </div>
          </div>

          <button disabled={loading} className="focus-ring group mt-5 inline-flex h-14 w-full items-center justify-center gap-2 rounded-lg bg-ink px-5 font-black text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-fern disabled:translate-y-0 disabled:opacity-60 dark:bg-fern dark:hover:bg-skydeep">
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : mode === "signup" ? <UserPlus className="h-5 w-5" /> : <LogIn className="h-5 w-5" />}
            {mode === "signup" ? "Create account" : "Login"}
          </button>

        </form>
      </div>
    </main>
  );
}
