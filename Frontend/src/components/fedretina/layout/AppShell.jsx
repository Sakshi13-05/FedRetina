/**
 * Signed-in app shell: sidebar + top bar + page content.
 *
 * WHAT IT DOES: loads the current profile, owns theme state, handles sign-out
 * (cancelling and clearing cached data first so no protected data lingers), and
 * renders the sidebar as a slide-over drawer on small screens.
 */
import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { Menu, X } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { Logo } from "@/components/fedretina/Logo";
import { Sidebar } from "@/components/fedretina/layout/Sidebar";
import { useProfile } from "@/lib/fedretina/useProfile";
import { useTheme } from "@/lib/fedretina/useTheme";
export function AppShell({ children }) {
    const { data: profile } = useProfile();
    const { theme, toggleTheme } = useTheme();
    const [drawerOpen, setDrawerOpen] = useState(false);
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    // Ordered sign-out: stop in-flight reads, drop cached data, end session, replace history.
    async function handleSignOut() {
        await queryClient.cancelQueries();
        queryClient.clear();
        await supabase.auth.signOut();
        navigate({ to: "/auth", replace: true });
    }
    const sidebar = (<Sidebar profile={profile ?? null} theme={theme} onToggleTheme={toggleTheme} onSignOut={handleSignOut}/>);
    return (<div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex">{sidebar}</div>

      {/* Mobile drawer */}
      {drawerOpen && (<div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="h-full">{sidebar}</div>
          <button type="button" aria-label="Close navigation" onClick={() => setDrawerOpen(false)} className="flex-1 bg-foreground/30"/>
        </div>)}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar — only shows the menu button below the sidebar breakpoint */}
        <header className="flex h-16 items-center gap-3 border-b border-border bg-surface px-4 lg:hidden">
          <button type="button" aria-label={drawerOpen ? "Close navigation" : "Open navigation"} onClick={() => setDrawerOpen((open) => !open)} className="flex size-11 items-center justify-center rounded-md border border-border text-secondary-text">
            {drawerOpen ? <X size={18} aria-hidden/> : <Menu size={18} aria-hidden/>}
          </button>
          <Logo size={26}/>
        </header>

        <main className="relative isolate mx-auto w-full max-w-[1100px] flex-1 overflow-hidden px-4 py-8 sm:px-6">{children}</main>
      </div>
    </div>);
}
