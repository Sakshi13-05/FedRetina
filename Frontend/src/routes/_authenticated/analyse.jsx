/**
 * Analyse page: choose a retina photo, run the (simulated) grading, read the result.
 *
 * WHAT IT DOES: accepts one image, shows a live preview with a moving scan line,
 * steps through the analysis stages, then shows the grade, how sure the model is,
 * and a plain-English next step. Nothing is submitted automatically — the person
 * always presses "Start analysis".
 */
import { useEffect, useRef, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Upload,
  ImageIcon,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { AppShell } from "@/components/fedretina/layout/AppShell";
import { PageHeader } from "@/components/fedretina/PageHeader";
import { AmbientShapes } from "@/components/fedretina/motion/AmbientShapes";
import { Reveal } from "@/components/fedretina/motion/Reveal";
import { LivePulse } from "@/components/fedretina/motion/LivePulse";
import { RotatingQuote } from "@/components/fedretina/motion/RotatingQuote";
import {
  GRADE_LABELS,
  GRADE_COLOR_CLASS,
  gradeProbabilities,
} from "@/lib/fedretina/mockData";

export const Route = createFileRoute("/_authenticated/analyse")({
  head: () => ({
    meta: [
      { title: "Analyse a scan — FedRetina" },
      {
        name: "description",
        content:
          "Upload one retina photo and get a severity reading with a confidence score.",
      },
      { property: "og:title", content: "Analyse a scan — FedRetina" },
      {
        property: "og:description",
        content:
          "Upload one retina photo and get a severity reading with a confidence score.",
      },
    ],
  }),
  component: AnalysePage,
});

/** The stages shown while the photo is being read. */
const STAGES = [
  "Checking image quality",
  "Preparing the photo",
  "Reading the retina",
  "Estimating certainty",
  "Preparing your summary",
];

const NEXT_STEPS = {
  0: "No follow-up needed beyond the usual yearly check.",
  1: "Repeat the check in 12 months.",
  2: "Book a review within 6 months.",
  3: "Refer to an eye specialist within 4 weeks.",
  4: "Refer urgently — same week if possible.",
};

function AnalysePage() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [stage, setStage] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const running = stage >= 0 && stage < STAGES.length;

  // Release the preview URL when the photo changes or the page closes.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // Walk through the stages one at a time, then produce a result.
  useEffect(() => {
    if (!running) return;
    const id = window.setTimeout(() => setStage((s) => s + 1), 750);
    return () => window.clearTimeout(id);
  }, [stage, running]);

  useEffect(() => {
    if (stage !== STAGES.length) return;
    const grade = Math.floor(Math.random() * 5);
    const confidence = Number((0.55 + Math.random() * 0.42).toFixed(2));
    setResult({ grade, confidence, uncertain: confidence < 0.7 });
  }, [stage]);

  function pickFile(nextFile) {
    setError(null);
    setResult(null);
    setStage(-1);
    if (!nextFile) return;
    if (!nextFile.type.startsWith("image/")) {
      setError("That file is not a photo. Please choose a JPG or PNG image.");
      return;
    }
    if (nextFile.size > 12 * 1024 * 1024) {
      setError(
        "That photo is larger than 12 MB. Please choose a smaller file.",
      );
      return;
    }
    setFile(nextFile);
    setPreviewUrl(URL.createObjectURL(nextFile));
  }

  function reset() {
    setFile(null);
    setPreviewUrl(null);
    setStage(-1);
    setResult(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <AppShell>
      <AmbientShapes />
      <PageHeader
        title="Analyse a scan"
        description="One photo at a time. The reading is a second opinion — never the final word."
        action={running ? <LivePulse label="Reading" tone="primary" /> : null}
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        {/* Left: photo picker + preview */}
        <Reveal className="rounded-lg border border-border bg-surface p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-foreground">
            Retina photo
          </h2>

          <label
            className="fr-lift mt-4 flex min-h-56 cursor-pointer flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed border-border bg-surface-2 p-6 text-center transition-colors hover:border-primary"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              pickFile(e.dataTransfer.files?.[0]);
            }}
          >
            {previewUrl ? (
              <span className="relative block w-full overflow-hidden rounded-md">
                <img
                  src={previewUrl}
                  alt="Selected retina photo"
                  className="mx-auto max-h-64 rounded-md object-contain"
                />
                {running && (
                  <span
                    aria-hidden
                    className="fr-scanline absolute inset-x-0 top-0 h-10 bg-primary/25"
                  />
                )}
              </span>
            ) : (
              <>
                <ImageIcon size={28} aria-hidden className="text-primary" />
                <span className="text-sm font-medium text-foreground">
                  Drop a photo here, or choose a file
                </span>
                <span className="text-xs text-muted-foreground">
                  JPG or PNG, up to 12 MB
                </span>
              </>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              className="sr-only"
              onChange={(e) => pickFile(e.target.files?.[0])}
            />
          </label>

          {file && (
            <p className="mt-3 truncate text-xs text-muted-foreground">
              {file.name}
            </p>
          )}
          {error && (
            <p
              role="alert"
              className="mt-3 rounded-md bg-danger/10 px-3 py-2 text-sm text-danger"
            >
              {error}
            </p>
          )}

          <div className="mt-5 flex gap-3">
            <button
              type="button"
              disabled={!file || running}
              onClick={() => {
                setResult(null);
                setStage(0);
              }}
              className="min-h-11 flex-1 rounded-md bg-primary text-sm font-semibold text-primary-foreground transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-hover disabled:opacity-50"
            >
              {running ? "Reading the photo…" : "Start analysis"}
            </button>
            <button
              type="button"
              onClick={reset}
              className="flex min-h-11 items-center gap-2 rounded-md border border-border px-4 text-sm font-medium text-secondary-text transition-colors hover:bg-primary-light hover:text-primary"
            >
              <RefreshCw size={16} aria-hidden />
              Clear
            </button>
          </div>
        </Reveal>

        {/* Right: progress + result */}
        <Reveal delay={120} className="space-y-6">
          <div className="rounded-lg border border-border bg-surface p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-foreground">Progress</h2>
            <ol className="mt-4 space-y-3">
              {STAGES.map((label, index) => {
                const done = stage > index;
                const active = stage === index;
                return (
                  <li key={label} className="flex items-center gap-3 text-sm">
                    <span
                      aria-hidden
                      className={`flex size-6 shrink-0 items-center justify-center rounded-full border transition-all duration-300 ${
                        done
                          ? "border-success bg-success text-primary-foreground"
                          : active
                            ? "border-primary bg-primary-light text-primary"
                            : "border-border text-muted-foreground"
                      }`}
                    >
                      {done ? <CheckCircle2 size={14} /> : index + 1}
                    </span>
                    <span
                      className={
                        done || active
                          ? "text-foreground"
                          : "text-muted-foreground"
                      }
                    >
                      {label}
                    </span>
                    {active && (
                      <span className="ml-auto">
                        <LivePulse label="" tone="primary" />
                      </span>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>

          {result ? (
            <div className="fr-rise rounded-lg border border-border bg-surface p-5 shadow-md">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-foreground">
                  Result
                </h2>
                {result.uncertain && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-warning-light px-3 py-1 text-xs font-semibold text-warning">
                    <AlertTriangle size={13} aria-hidden />
                    Needs a human check
                  </span>
                )}
              </div>
              <p
                className={`mt-3 text-3xl font-bold tracking-tight ${GRADE_COLOR_CLASS[result.grade]}`}
              >
                Grade {result.grade} · {GRADE_LABELS[result.grade]}
              </p>
              <p className="mt-1 text-sm text-secondary-text">
                {NEXT_STEPS[result.grade]}
              </p>

              <div className="mt-5 space-y-2">
                {gradeProbabilities(result.grade, result.confidence).map(
                  (row) => (
                    <div
                      key={row.grade}
                      className="flex items-center gap-3 text-xs"
                    >
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
                  ),
                )}
              </div>

              <Link
                to="/history"
                className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-md border border-border px-4 text-sm font-medium text-secondary-text transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary-light hover:text-primary"
              >
                <Upload size={16} aria-hidden />
                See past scans
              </Link>
            </div>
          ) : (
            <RotatingQuote
              items={[
                {
                  text: "Good lighting and a steady camera give the clearest reading.",
                  source: "Imaging tip",
                },
                {
                  text: "Photos stay on this site — only anonymous learning is shared.",
                  source: "Privacy note",
                },
                {
                  text: "Low certainty means a colleague should look, not that it is wrong.",
                  source: "Clinical safety",
                },
              ]}
            />
          )}
        </Reveal>
      </div>
    </AppShell>
  );
}
