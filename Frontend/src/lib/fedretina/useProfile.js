/**
 * Signed-in clinician profile hook.
 *
 * WHAT IT DOES: loads the current user's profile row (name, hospital, role, node)
 * from the database through the browser client, and reports whether they hold the
 * admin role. Returns loading state plus a display-friendly set of initials.
 */
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
/** Turns "Asha Menon" into "AM"; falls back to the first email character. */
function initialsFrom(name, email) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return (email[0] ?? "?").toUpperCase();
  return parts
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}
export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data: userData } = await supabase.auth.getUser();
      const user = userData.user;
      if (!user) return null;
      // Profile row is created automatically when the account is created.
      const { data: profile } = await supabase
        .from("profiles")
        .select("full_name, hospital_name, professional_role, hospital_node")
        .eq("id", user.id)
        .maybeSingle();
      // Admin rights live in a separate roles table, never on the profile.
      const { data: roles } = await supabase
        .from("user_roles")
        .select("role")
        .eq("user_id", user.id);
      const fullName =
        profile?.full_name?.trim() || (user.email ?? "Clinician");
      return {
        fullName,
        hospitalName: profile?.hospital_name ?? "",
        professionalRole: profile?.professional_role ?? "Clinician",
        hospitalNode: profile?.hospital_node ?? "Node 01",
        email: user.email ?? "",
        isAdmin: (roles ?? []).some((r) => r.role === "admin"),
        initials: initialsFrom(fullName, user.email ?? ""),
      };
    },
  });
}
