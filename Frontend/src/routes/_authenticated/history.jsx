/**
 * History page: every past scan for this site, searchable and filterable.
 *
 * WHAT IT DOES: lists the stand-in predictions with search by patient reference,
 * a severity filter and a "needs review only" switch. Rows animate in one after
 * another and open the detail page.
 */
import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Search, ChevronRight } from "lucide-react";
import { AppShell } from "@/components/fedretina/layout/AppShell";
import { PageHeader } from "@/components/fedretina/PageHeader";
import { AmbientShapes } from "@/components/fedretina/motion/AmbientShapes";
import { Reveal } from "@/components/fedretina/motion/Reveal";
import {
  MOCK_PREDICTIONS,
  GRADE_LABELS,
  GRADE_COLOR_CLASS,
} from "@/lib/fedretina/mockData";

export const Route = createFileRoute("/_authenticated/history")({
  head: () => ({
    meta: [
      { title: "Scan history — FedRetina" },
      {
        name: "description",
        content: "Search and filter every retina scan graded at your site.",
      },
      { property: "og:title", content: "Scan history — FedRetina" },
      {
        property: "og:description",
        content: "Search and filter every retina scan graded at your site.",
      },
    ],
  }),
  component: HistoryPage,
});

/** Turns an ISO timestamp into a short, readable date and time. */
function formatWhen(iso) {
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function HistoryPage() {
  const [query, setQuery] = useState("");
  const [grade, setGrade] = useState("all");
  const [reviewOnly, setReviewOnly] = useState(false);

  const rows = useMemo(() => {
    return MOCK_PREDICTIONS.filter((p) => {
      const matchesQuery = p.patientId
        .toLowerCase()
        .includes(query.trim().toLowerCase());
      const matchesGrade = grade === "all" || p.grade === Number(grade);
      const matchesReview = !reviewOnly || p.status === "needs_review";
      return matchesQuery && matchesGrade && matchesReview;
    });
  }, [query, grade, reviewOnly]);

  return (
    <AppShell>
      <AmbientShapes />
      <PageHeader
        title="Scan history"
        description={`${rows.length} of ${MOCK_PREDICTIONS.length} scans shown.`}
      />

      {/* Filters */}
      <Reveal className="mt-6 flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface p-4 shadow-sm">
        <label className="relative flex min-w-56 flex-1 items-center">
          <Search
            size={16}
            aria-hidden
            className="pointer-events-none absolute left-3 text-muted-foreground"
          />
          <span className="sr-only">Search by patient reference</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search patient reference…"
            className="min-h-11 w-full rounded-md border border-border bg-surface pl-9 pr-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-ring"
          />
        </label>

        <label className="text-sm text-secondary-text">
          <span className="sr-only">Filter by severity</span>
          <select
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
            className="min-h-11 rounded-md border border-border bg-surface px-3 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-ring"
          >
            <option value="all">All severities</option>
            {[0, 1, 2, 3, 4].map((g) => (
              <option key={g} value={g}>
                Grade {g} · {GRADE_LABELS[g]}
              </option>
            ))}
          </select>
        </label>

        <label className="flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-border px-3 text-sm text-secondary-text transition-colors hover:bg-primary-light hover:text-primary">
          <input
            type="checkbox"
            checked={reviewOnly}
            onChange={(e) => setReviewOnly(e.target.checked)}
            className="size-4 accent-[var(--primary)]"
          />
          Needs review only
        </label>
      </Reveal>

      {/* Table */}
      <Reveal
        delay={100}
        className="mt-6 overflow-hidden rounded-lg border border-border bg-surface shadow-sm"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <caption className="sr-only">Past retina scans</caption>
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="label-xs px-4 py-3">
                  Patient
                </th>
                <th scope="col" className="label-xs px-4 py-3">
                  Severity
                </th>
                <th scope="col" className="label-xs px-4 py-3">
                  Certainty
                </th>
                <th scope="col" className="label-xs px-4 py-3">
                  Status
                </th>
                <th scope="col" className="label-xs px-4 py-3">
                  When
                </th>
                <th scope="col" className="label-xs px-4 py-3 text-right">
                  Open
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p, index) => (
                <tr
                  key={p.id}
                  className="fr-rise border-b border-border last:border-0 transition-colors hover:bg-primary-light/60"
                  style={{ animationDelay: `${index * 45}ms` }}
                >
                  <td className="px-4 py-3 font-medium text-foreground">
                    {p.patientId}
                  </td>
                  <td
                    className={`px-4 py-3 font-semibold ${GRADE_COLOR_CLASS[p.grade]}`}
                  >
                    Grade {p.grade} · {GRADE_LABELS[p.grade]}
                  </td>
                  <td className="px-4 py-3 text-secondary-text">
                    {Math.round(p.confidence * 100)}%
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        p.status === "needs_review"
                          ? "bg-warning-light text-warning"
                          : "bg-success-light text-success"
                      }`}
                    >
                      {p.status === "needs_review"
                        ? "Needs review"
                        : "Reviewed"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatWhen(p.createdAt)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to="/predictions/$id"
                      params={{ id: p.id }}
                      className="inline-flex items-center gap-1 font-medium text-primary transition-transform duration-300 hover:translate-x-1"
                    >
                      View
                      <ChevronRight size={15} aria-hidden />
                    </Link>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-sm text-muted-foreground"
                  >
                    No scans match those filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Reveal>
    </AppShell>
  );
}
