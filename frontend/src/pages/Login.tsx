import { Bot, Cpu, ShieldAlert } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { Logo } from "../components/Layout";
import { ErrorBox } from "../components/ui";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, name, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const features = [
    { icon: Cpu, title: "Deterministic static checks", text: "AST and pattern rules for bugs, injection risks and leaked secrets." },
    { icon: Bot, title: "AI-assisted review", text: "Claude explains deeper logic and design issues, each with a confidence level." },
    { icon: ShieldAlert, title: "Safe by design", text: "Submitted code is parsed and inspected. It is never executed." },
  ];

  return (
    <div className="grid min-h-full lg:grid-cols-2">
      <div className="hidden flex-col justify-between border-r border-ink-700/70 bg-ink-900 p-10 lg:flex">
        <Logo />
        <div className="max-w-md space-y-8">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Catch bugs and vulnerabilities <span className="text-brand-400">before</span> they ship.
          </h1>
          <div className="space-y-5">
            {features.map(({ icon: Icon, title, text }) => (
              <div key={title} className="flex gap-3">
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ink-800 text-brand-400"><Icon size={17} /></div>
                <div>
                  <div className="text-sm font-medium">{title}</div>
                  <div className="text-sm text-ink-400">{text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-xs text-ink-400">AI findings are suggestions, not guarantees. Always verify them.</p>
      </div>

      <div className="flex items-center justify-center px-4 py-12">
        <form onSubmit={submit} className="w-full max-w-sm space-y-5">
          <div className="lg:hidden"><Logo /></div>
          <div>
            <h2 className="text-xl font-semibold">{mode === "login" ? "Welcome back" : "Create your account"}</h2>
            <p className="mt-1 text-sm text-ink-400">
              {mode === "login" ? "Sign in to review your code." : "Start reviewing code in seconds."}
            </p>
          </div>
          {error && <ErrorBox message={error} />}
          {mode === "register" && (
            <label className="block space-y-1.5">
              <span className="text-sm text-ink-300">Name</span>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
            </label>
          )}
          <label className="block space-y-1.5">
            <span className="text-sm text-ink-300">Email</span>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm text-ink-300">Password</span>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              minLength={mode === "register" ? 8 : undefined} autoComplete={mode === "login" ? "current-password" : "new-password"} />
            {mode === "register" && <span className="text-xs text-ink-400">At least 8 characters.</span>}
          </label>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
          <p className="text-center text-sm text-ink-400">
            {mode === "login" ? "New to WizForge?" : "Already have an account?"}{" "}
            <button type="button" className="text-brand-400 hover:underline"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
