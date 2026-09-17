/**
 * FedRetina mark: a stylised eye with a federated-node ring.
 * INPUT: optional size + whether to show the wordmark. OUTPUT: inline SVG + text.
 */
export function Logo({ size = 32, showWordmark = true }) {
    return (<span className="flex items-center gap-2.5">
      <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label="FedRetina logo" className="shrink-0">
        {/* Outer ring = the federation of hospital sites */}
        <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="1.5" className="text-primary"/>
        {/* Eye outline */}
        <path d="M4 16c3.6-5.2 7.6-7.8 12-7.8S24.4 10.8 28 16c-3.6 5.2-7.6 7.8-12 7.8S7.6 21.2 4 16Z" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary"/>
        {/* Pupil */}
        <circle cx="16" cy="16" r="3.4" fill="currentColor" className="text-primary"/>
        {/* Three node dots on the ring */}
        <circle cx="16" cy="2.6" r="1.8" fill="currentColor" className="text-primary-mid"/>
        <circle cx="27.6" cy="23" r="1.8" fill="currentColor" className="text-primary-mid"/>
        <circle cx="4.4" cy="23" r="1.8" fill="currentColor" className="text-primary-mid"/>
      </svg>
      {showWordmark && (<span className="text-[17px] font-bold tracking-tight text-foreground">
          Fed<span className="text-primary">Retina</span>
        </span>)}
    </span>);
}
