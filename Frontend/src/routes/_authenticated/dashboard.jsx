/**
 * Signed-in dashboard: headline metrics, severity mix, weekly trend, latest scans.
 */
import { createFileRoute } from "@tanstack/react-router";
import { Activity, AlertTriangle, Gauge, ScanEye } from "lucide-react";
import { AppShell } from "@/components/fedretina/layout/AppShell";
import { StatCard } from "@/components/fedretina/dashboard/StatCard";
import { GradeDonut } from "@/components/fedretina/dashboard/GradeDonut";
import { WeeklyTrendLine } from "@/components/fedretina/dashboard/WeeklyTrendLine";
import { RecentScans } from "@/components/fedretina/dashboard/RecentScans";
import { DASHBOARD_STATS } from "@/lib/fedretina/mockData";
import { useProfile } from "@/lib/fedretina/useProfile";
import { Reveal } from "@/components/fedretina/motion/Reveal";
import { AmbientShapes } from "@/components/fedretina/motion/AmbientShapes";
import { LivePulse } from "@/components/fedretina/motion/LivePulse";
import { RotatingQuote } from "@/components/fedretina/motion/RotatingQuote";
/** Short rotating reminders shown under the dashboard content. */
const TIPS = [
  {
    text: "Cases marked \u201cneeds review\u201d are shown first so nothing urgent waits.",
    source: "Screening guidance",
  },
  {
    text: "Patient photos never leave this site \u2014 only anonymous learning is shared.",
    source: "Privacy note",
  },
  {
    text: "A result is a second opinion, never the final word on care.",
    source: "Clinical safety",
  },
];
export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — FedRetina" },
      {
        name: "description",
        content:
          "Today's retina screening activity, severity mix and latest scans.",
      },
      { property: "og:title", content: "Dashboard — FedRetina" },
      {
        property: "og:description",
        content:
          "Today's retina screening activity, severity mix and latest scans.",
      },
    ],
  }),
  component: DashboardPage,
});
function DashboardPage() {
  const { data: profile } = useProfile();
  const s = DASHBOARD_STATS;
  const trend = Math.round(
    ((s.scansToday - s.scansYesterday) / Math.max(s.scansYesterday, 1)) * 100,
  );
  return (
    <AppShell>
      <AmbientShapes />
      <header className="fr-rise mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Welcome back{profile?.fullName ? `, ${profile.fullName}` : ""}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            A quick view of screening activity at{" "}
            {profile?.hospitalName || "your site"}.
          </p>
        </div>
        <LivePulse label="Live activity" />
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {/* each tile fades up in sequence */}
        <StatCard
          label="Scans today"
          value={String(s.scansToday)}
          detail="vs yesterday"
          trend={trend}
          icon={<ScanEye size={18} aria-hidden className="text-primary" />}
        />
        <StatCard
          label="Needs a second look"
          value={String(s.flaggedCases)}
          detail="uncertain results"
          tone="warning"
          icon={
            <AlertTriangle size={18} aria-hidden className="text-warning" />
          }
        />
        <StatCard
          label="Average confidence"
          value={`${s.averageConfidence}%`}
          detail="across recent scans"
          tone="success"
          icon={<Gauge size={18} aria-hidden className="text-success" />}
        />
        <StatCard
          label="Model status"
          value={s.modelStatus}
          detail={s.modelUpdated}
          icon={<Activity size={18} aria-hidden className="text-primary" />}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Reveal>
          <GradeDonut />
        </Reveal>
        <Reveal delay={120}>
          <WeeklyTrendLine />
        </Reveal>
      </div>

      <Reveal className="mt-6">
        <RecentScans />
      </Reveal>

      <Reveal className="mt-6" delay={100}>
        <RotatingQuote items={TIPS} interval={7000} />
      </Reveal>
    </AppShell>
  );
}
