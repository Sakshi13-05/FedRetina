/**
 * Fixed navigation sidebar (240px) for the signed-in app.
 *
 * WHAT IT DOES: renders the brand mark, the main navigation, and a bottom block
 * with the person's assigned hospital site, theme toggle and sign-out.
 */
import { Link } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Microscope,
  ClipboardList,
  RadioTower,
  Settings,
  ShieldCheck,
  LogOut,
  Moon,
  Sun,
} from "lucide-react";
import { Logo } from "@/components/fedretina/Logo";

/** Main navigation entries, in order. */
const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analyse", label: "Analyse", icon: Microscope },
  { to: "/history", label: "History", icon: ClipboardList },
  { to: "/network", label: "Network monitor", icon: RadioTower },
  { to: "/settings", label: "Settings", icon: Settings },
];

const linkClass =
  "flex min-h-11 items-center gap-3 rounded-md border-l-[3px] border-transparent px-3 text-sm font-medium text-secondary-text transition-all duration-300 hover:translate-x-1 hover:bg-primary-light hover:text-primary";

export function Sidebar({ profile, theme, onToggleTheme, onSignOut }) {
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-surface-2">
      {/* Brand */}
      <div className="flex h-16 items-center px-5">
        <Logo />
      </div>
      <div className="mx-5 border-t border-border" />

      {/* Main navigation */}
      <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Main">
        {NAV.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className={linkClass}
            activeProps={{
              className: "border-primary bg-primary-light text-primary",
            }}
          >
            <Icon size={18} aria-hidden />
            {label}
          </Link>
        ))}

        {profile?.isAdmin && (
          <Link
            to="/admin"
            className={linkClass}
            activeProps={{
              className: "border-primary bg-primary-light text-primary",
            }}
          >
            <ShieldCheck size={18} aria-hidden />
            Admin
          </Link>
        )}
      </nav>

      {/* Bottom block: site badge, identity, theme, sign out */}
      <div className="space-y-3 border-t border-border p-4">
        <span className="inline-flex rounded-full bg-primary-light px-3 py-1 text-xs font-semibold text-primary">
          {profile?.hospitalNode ?? "Unassigned site"}
        </span>
        <div className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
            {profile?.initials ?? "–"}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-foreground">
              {profile?.fullName ?? "Loading…"}
            </span>
            <span className="block truncate text-xs text-muted-foreground">
              {profile?.professionalRole ?? ""}
            </span>
          </span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={
              theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
            }
            className="flex size-11 items-center justify-center rounded-md border border-border bg-surface text-secondary-text transition-colors hover:bg-primary-light hover:text-primary"
          >
            {theme === "dark" ? (
              <Sun size={18} aria-hidden />
            ) : (
              <Moon size={18} aria-hidden />
            )}
          </button>
          <button
            type="button"
            onClick={onSignOut}
            className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-md border border-border bg-surface text-sm font-medium text-secondary-text transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-light hover:text-primary"
          >
            <LogOut size={16} aria-hidden />
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}
