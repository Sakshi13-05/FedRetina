/**
 * Prediction detail: everything recorded about one graded scan.
 *
 * WHAT IT DOES: shows the severity reading, how sure the model was, the likelihood
 * for each severity level, the suggested next step, and a review action.
 */
import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, AlertTriangle, CheckCircle2, FileDown } from "lucide-react";
import { AppShell } from "@/components/fedretina/layout/AppShell";
import { PageHeader } from "@/components/fedretina/PageHeader";
import { AmbientShapes } from "@/components/fedretina/motion/AmbientShapes";
import { Reveal } from "@/components/fedretina/motion/Reveal";
import {
  getPredictionById,
  gradeProbabilities,
  GRADE_LABELS,
  GRADE_COLOR_CLASS,
} from "@/lib/fedretina/mockData";

export const Route = createFileRoute("/_authenticated/predictions/$id")({
  head: () => ({
    meta: [
      { title: "Scan result — FedRetina" },
      {
        name: "description",
        content: "Full detail for a single graded retina scan.",
      },
      { property: "og:title", content: "Scan result — FedRetina" },
      {
        property: "og:description",
        content: "Full detail for a single graded retina scan.",
      },
    ],
  }),
  component: PredictionDetailPage,
});

const NEXT_STEPS = {
  0: "No follow-up needed beyond the usual yearly check.",
  1: "Repeat the check in 12 months.",
  2: "Book a review within 6 months.",
  3: "Refer to an eye specialist within 4 weeks.",
  4: "Refer urgently — same week if possible.",
};

function PredictionDetailPage() {
  const { id } = Route.useParams();
  const prediction = getPredictionById(id);
  const [reviewed, setReviewed] = useState(prediction?.status === "reviewed");
  const [note, setNote] = useState("");

  if (!prediction) {
    return (
      <AppShell>
        <PageHeader
          title="Scan not found"
          description="This scan is not in your site's records."
        />
        <Link
          to="/history"
          className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-primary"
        >
          <ArrowLeft size={16} aria-hidden />
          Back to history
        </Link>
      </AppShell>
    );
  }

  const bars = gradeProbabilities(prediction.grade, prediction.confidence);

  return (
    <AppShell>
      <AmbientShapes />
      <Link
        to="/history"
        className="fr-rise inline-flex items-center gap-2 text-sm font-medium text-secondary-text transition-transform duration-300 hover:-translate-x-1 hover:text-primary"
      >
        <ArrowLeft size={16} aria-hidden />
        Back to history
      </Link>

      <div className="mt-4">
        <PageHeader
          title={prediction.patientId}
          description={new Date(prediction.createdAt).toLocaleString()}
          action={
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                reviewed
                  ? "bg-success-light text-success"
                  : "bg-warning-light text-warning"
              }`}
            >
              {reviewed ? "Reviewed" : "Needs review"}
            </span>
          }
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Reveal className="rounded-lg border border-border bg-surface p-6 shadow-sm">
          <span className="label-xs">Reading</span>
          <p
            className={`mt-2 text-4xl font-bold tracking-tight ${GRADE_COLOR_CLASS[prediction.grade]}`}
          >
            Grade {prediction.grade} · {GRADE_LABELS[prediction.grade]}
          </p>
          <p className="mt-2 text-sm text-secondary-text">
            {NEXT_STEPS[prediction.grade]}
          </p>

          {prediction.uncertaintyFlag && (
            <p className="mt-4 inline-flex items-center gap-2 rounded-md bg-warning-light px-3 py-2 text-sm font-medium text-warning">
              <AlertTriangle size={15} aria-hidden />
              The model was unsure about this one — please confirm it yourself.
            </p>
          )}

          <h2 className="mt-7 text-sm font-semibold text-foreground">
            How the reading was spread
          </h2>
          <div className="mt-3 space-y-2">
            {bars.map((row) => (
              <div key={row.grade} className="flex items-center gap-3 text-xs">
                <span className="w-20 shrink-0 text-muted-foreground">
                  {row.label}
                </span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                  <span
                    className="block h-full rounded-full bg-primary transition-[width] duration-700"
                    style={{ width: `${Math.round(row.value * 100)}%` }}
                  />
                </span>
                <span className="w-10 text-right font-medium text-foreground">
                  {Math.round(row.value * 100)}%
                </span>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={120} className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="fr-lift rounded-md border border-border bg-surface p-4 shadow-sm">
              <span className="label-xs">Certainty</span>
              <p className="mt-2 text-2xl font-bold text-foreground">
                {Math.round(prediction.confidence * 100)}%
              </p>
            </div>
            <div className="fr-lift rounded-md border border-border bg-surface p-4 shadow-sm">
              <span className="label-xs">Spread</span>
              <p className="mt-2 text-2xl font-bold text-foreground">
                {prediction.uncertaintyScore.toFixed(3)}
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-surface p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-foreground">Your note</h2>
            <label className="mt-3 block text-sm">
              <span className="sr-only">Note about this scan</span>
              <textarea
                rows={4}
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add what you saw, or why you agree or disagree…"
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-ring"
              />
            </label>
            <button
              type="button"
              onClick={() => setReviewed(true)}
              disabled={reviewed}
              className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-primary text-sm font-semibold text-primary-foreground transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-hover disabled:opacity-50"
            >
              <CheckCircle2 size={16} aria-hidden />
              {reviewed ? "Marked as reviewed" : "Mark as reviewed"}
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="mt-2 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md border border-border text-sm font-medium text-secondary-text transition-colors hover:bg-primary-light hover:text-primary"
            >
              <FileDown size={16} aria-hidden />
              Save as report
            </button>
          </div>
        </Reveal>
      </div>
    </AppShell>
  );
}
