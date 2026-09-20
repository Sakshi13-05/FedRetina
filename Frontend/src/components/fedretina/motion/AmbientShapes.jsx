/**
 * Slow-moving background shapes used behind hero and page sections.
 * Purely decorative: sits behind content, ignores pointer events, and is
 * hidden from screen readers.
 */
export function AmbientShapes({ dense = false }) {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10 overflow-hidden"
    >
      <span
        className="fr-float absolute -left-24 top-[-10%] size-72 rounded-full bg-primary/15 blur-3xl"
        style={{ animationDuration: "22s" }}
      />
      <span
        className="fr-float absolute right-[-8%] top-1/4 size-96 rounded-full bg-primary-mid/15 blur-3xl"
        style={{ animationDuration: "28s", animationDelay: "-6s" }}
      />
      <span
        className="fr-float absolute bottom-[-15%] left-1/3 size-80 rounded-full bg-success/10 blur-3xl"
        style={{ animationDuration: "34s", animationDelay: "-12s" }}
      />
      {dense && (
        <>
          {/* Slowly rotating rings, echoing a retina scan target */}
          <span className="fr-drift absolute left-1/2 top-1/2 size-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/60" />
          <span
            className="fr-drift absolute left-1/2 top-1/2 size-[760px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/40"
            style={{ animationDuration: "60s", animationDirection: "reverse" }}
          />
        </>
      )}
    </div>
  );
}
