/**
 * Sign in / create account page.
 *
 * WHAT IT DOES: email + password sign-in and sign-up against the built-in backend.
 * Sign-up also stores the person's name, hospital, professional role and site so the
 * profile row is filled in automatically.
 */
import { useEffect, useState } from "react";
import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { supabase } from "@/integrations/supabase/client";
import { Logo } from "@/components/fedretina/Logo";
import { AmbientShapes } from "@/components/fedretina/motion/AmbientShapes";
export const Route = createFileRoute("/auth")({
    ssr: false,
    head: () => ({
        meta: [
            { title: "Sign in — FedRetina" },
            { name: "description", content: "Sign in or create your FedRetina account to grade retina scans." },
            { property: "og:title", content: "Sign in — FedRetina" },
            { property: "og:description", content: "Sign in or create your FedRetina account to grade retina scans." },
        ],
    }),
    component: AuthPage,
});
const inputClass = "mt-1 w-full rounded-md border border-border bg-surface px-3 py-2.5 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-ring";
function AuthPage() {
    const navigate = useNavigate();
    const [mode, setMode] = useState("signin");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [hospitalName, setHospitalName] = useState("");
    const [professionalRole, setProfessionalRole] = useState("Ophthalmologist");
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(null);
    const [notice, setNotice] = useState(null);
    // Already signed in? Go straight to the dashboard.
    useEffect(() => {
        supabase.auth.getSession().then(({ data }) => {
            if (data.session)
                navigate({ to: "/dashboard", replace: true });
        });
    }, [navigate]);
    async function handleSubmit(event) {
        event.preventDefault();
        setBusy(true);
        setError(null);
        setNotice(null);
        if (mode === "signin") {
            const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
            if (signInError)
                setError(signInError.message);
            else
                navigate({ to: "/dashboard", replace: true });
        }
        else {
            const { data, error: signUpError } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    emailRedirectTo: `${window.location.origin}/dashboard`,
                    data: { full_name: fullName, hospital_name: hospitalName, professional_role: professionalRole },
                },
            });
            if (signUpError)
                setError(signUpError.message);
            else if (data.session)
                navigate({ to: "/dashboard", replace: true });
            else
                setNotice("Check your email to confirm your account, then sign in.");
        }
        setBusy(false);
    }
    return (<main className="relative isolate flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-10">
      <AmbientShapes dense/>
      <div className="fr-rise w-full max-w-md rounded-lg border border-border bg-surface p-7 shadow-md">
        <Link to="/" className="inline-flex">
          <Logo />
        </Link>
        <h1 className="mt-6 text-2xl font-bold tracking-tight text-foreground">
          {mode === "signin" ? "Sign in" : "Create your account"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {mode === "signin"
            ? "Use your work email to reach your screening dashboard."
            : "Tell us where you work so results stay with your site."}
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          {mode === "signup" && (<>
              <label className="block text-sm font-medium text-secondary-text">
                Full name
                <input className={inputClass} value={fullName} onChange={(e) => setFullName(e.target.value)} required autoComplete="name"/>
              </label>
              <label className="block text-sm font-medium text-secondary-text">
                Hospital or clinic
                <input className={inputClass} value={hospitalName} onChange={(e) => setHospitalName(e.target.value)} required/>
              </label>
              <label className="block text-sm font-medium text-secondary-text">
                Your role
                <select className={inputClass} value={professionalRole} onChange={(e) => setProfessionalRole(e.target.value)}>
                  <option>Ophthalmologist</option>
                  <option>Optometrist</option>
                  <option>Screening technician</option>
                  <option>Researcher</option>
                </select>
              </label>
            </>)}

          <label className="block text-sm font-medium text-secondary-text">
            Email
            <input type="email" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email"/>
          </label>
          <label className="block text-sm font-medium text-secondary-text">
            Password
            <input type="password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete={mode === "signin" ? "current-password" : "new-password"}/>
          </label>

          {error && (<p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </p>)}
          {notice && (<p role="status" className="rounded-md bg-primary-light px-3 py-2 text-sm text-primary">
              {notice}
            </p>)}

          <button type="submit" disabled={busy} className="min-h-11 w-full rounded-md bg-primary text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60">
            {busy ? "Please wait…" : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-muted-foreground">
          {mode === "signin" ? "New to FedRetina?" : "Already have an account?"}{" "}
          <button type="button" className="font-semibold text-primary underline-offset-4 hover:underline" onClick={() => {
            setMode(mode === "signin" ? "signup" : "signin");
            setError(null);
            setNotice(null);
        }}>
            {mode === "signin" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </div>
    </main>);
}
