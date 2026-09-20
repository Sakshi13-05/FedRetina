/**
 * A short rotating quote / note strip.
 * INPUT: a list of quote lines with an attribution.
 * OUTPUT: one line at a time, cross-fading every few seconds.
 */
import { useEffect, useState } from "react";
import { Quote } from "lucide-react";
export function RotatingQuote({ items, interval = 6000 }) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const id = window.setInterval(
      () => setIndex((i) => (i + 1) % items.length),
      interval,
    );
    return () => window.clearInterval(id);
  }, [items.length, interval]);
  const current = items[index];
  return (
    <figure
      aria-live="polite"
      className="relative overflow-hidden rounded-lg border border-border bg-surface px-5 py-4 shadow-sm"
    >
      <Quote size={16} aria-hidden className="text-primary" />
      <blockquote
        key={index}
        className="fr-rise mt-2 text-sm text-secondary-text"
      >
        {current.text}
      </blockquote>
      <figcaption
        key={`${index}-src`}
        className="fr-rise mt-1 text-xs text-muted-foreground"
      >
        — {current.source}
      </figcaption>
      {/* progress bar that refills for each quote */}
      <span aria-hidden className="absolute inset-x-0 bottom-0 h-0.5 bg-border">
        <span
          key={`${index}-bar`}
          className="block h-full bg-primary"
          style={{
            animation: `fr-fill ${interval}ms linear`,
            width: "100%",
            transformOrigin: "left",
          }}
        />
      </span>
    </figure>
  );
}
