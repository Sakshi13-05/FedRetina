/**
 * Small "live" indicator: a coloured dot with an expanding ring behind it.
 * INPUT: an optional label and tone. OUTPUT: an inline status chip.
 */
export function LivePulse({ label = "Live", tone = "success", }) {
    const dot = tone === "warning" ? "bg-warning" : tone === "primary" ? "bg-primary" : "bg-success";
    const text = tone === "warning" ? "text-warning" : tone === "primary" ? "text-primary" : "text-success";
    return (<span className={`inline-flex items-center gap-2 text-xs font-semibold ${text}`}>
      <span className="relative flex size-2.5 items-center justify-center">
        <span className={`fr-ring absolute size-2.5 rounded-full ${dot}`} aria-hidden/>
        <span className={`relative size-2.5 rounded-full ${dot}`} aria-hidden/>
      </span>
      {label}
    </span>);
}
