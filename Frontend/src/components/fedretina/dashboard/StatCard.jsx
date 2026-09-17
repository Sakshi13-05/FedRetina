import { ArrowDownRight, ArrowUpRight } from "lucide-react";
const TONE_CLASS = {
    default: "text-foreground",
    warning: "text-warning",
    success: "text-success",
};
export function StatCard({ label, value, detail, trend, tone = "default", icon, }) {
    const trendUp = (trend ?? 0) >= 0;
    return (<div className="fr-lift group relative overflow-hidden rounded-md border border-border bg-surface p-5 shadow-sm">
      {/* light sweep on hover */}
      <span aria-hidden className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-hover:fr-shimmer"/>
      <div className="flex items-start justify-between gap-3">
        <span className="label-xs">{label}</span>
        <span className="transition-transform duration-300 group-hover:scale-110">{icon}</span>
      </div>
      <p className={`mt-3 text-3xl font-bold tracking-tight ${TONE_CLASS[tone]}`}>{value}</p>
      <div className="mt-1 flex items-center gap-1.5 text-[13px] text-muted-foreground">
        {typeof trend === "number" && (<span className={`flex items-center gap-0.5 font-medium ${trendUp ? "text-success" : "text-danger"}`}>
            {trendUp ? <ArrowUpRight size={14} aria-hidden/> : <ArrowDownRight size={14} aria-hidden/>}
            {trendUp ? "+" : ""}
            {trend}
          </span>)}
        {detail && <span>{detail}</span>}
      </div>
    </div>);
}
