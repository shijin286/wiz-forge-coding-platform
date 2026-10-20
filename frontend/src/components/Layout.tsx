import { FilePlus2, History, LayoutDashboard, LogOut, Menu, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/review/new", label: "New review", icon: FilePlus2, end: false },
  { to: "/history", label: "History", icon: History, end: false },
];

export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-500/15 text-brand-400">
        <ShieldCheck size={18} />
      </div>
      <span className="font-semibold tracking-tight">
        WizForge <span className="text-brand-400">AI</span>
      </span>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
              isActive ? "bg-ink-800 text-ink-100" : "text-ink-400 hover:bg-ink-850 hover:text-ink-100"
            }`
          }
        >
          <Icon size={16} />
          {label}
        </NavLink>
      ))}
    </nav>
  );

  const account = (
    <div className="flex items-center justify-between gap-2 border-t border-ink-700/70 pt-4">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{user?.name}</div>
        <div className="truncate text-xs text-ink-400">{user?.email}</div>
      </div>
      <button onClick={logout} className="rounded-lg p-2 text-ink-400 hover:bg-ink-800 hover:text-ink-100" title="Sign out">
        <LogOut size={16} />
      </button>
    </div>
  );

  return (
    <div className="flex min-h-full">
      {/* desktop sidebar */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col justify-between border-r border-ink-700/70 bg-ink-900 p-4 md:flex">
        <div className="flex flex-col gap-6">
          <Logo />
          {nav}
        </div>
        {account}
      </aside>

      {/* mobile header + drawer */}
      <div className="fixed inset-x-0 top-0 z-30 flex items-center justify-between border-b border-ink-700/70 bg-ink-900/95 px-4 py-3 backdrop-blur md:hidden">
        <Logo />
        <button onClick={() => setOpen(!open)} className="rounded-lg p-2 text-ink-300 hover:bg-ink-800" aria-label="Menu">
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>
      {open && (
        <div className="fixed inset-x-0 top-[57px] z-20 flex flex-col gap-4 border-b border-ink-700/70 bg-ink-900 p-4 md:hidden">
          {nav}
          {account}
        </div>
      )}

      <main className="min-w-0 flex-1 px-4 pb-10 pt-20 md:px-8 md:pt-8">
        <Outlet />
      </main>
    </div>
  );
}
