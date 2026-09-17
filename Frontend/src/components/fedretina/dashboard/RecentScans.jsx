/**
 * Mini table of the five most recent scans.
 * INPUT: mock predictions. OUTPUT: compact table with patient reference, grade,
 * time and review status. Grade colour is always paired with its text label.
 */
import { LivePulse } from "@/components/fedretina/motion/LivePulse";
import { GRADE_COLOR_CLASS, GRADE_LABELS, MOCK_PREDICTIONS } from "@/lib/fedretina/mockData";
/** "3 hours ago" style relative time, kept dependency-free and simple. */
function relativeTime(iso) {
    const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (minutes < 60)
        return `${Math.max(minutes, 1)} min ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24)
        return `${hours} h ago`;
    return `${Math.round(hours / 24)} d ago`;
}
export function RecentScans() {
    const rows = MOCK_PREDICTIONS.slice(0, 5);
    return (<section className="fr-lift rounded-md border border-border bg-surface p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">Latest scans</h2>
        <LivePulse label="Updating" tone="success"/>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-border">
              <th className="label-xs pb-2 font-medium">Patient</th>
              <th className="label-xs pb-2 font-medium">Result</th>
              <th className="label-xs pb-2 font-medium">When</th>
              <th className="label-xs pb-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (<tr key={row.id} style={{ animationDelay: `${i * 70}ms` }} className="fr-rise border-b border-border/60 transition-colors last:border-0 hover:bg-primary-light/60">
                <td className="py-3 font-mono text-secondary-text">{row.patientId}</td>
                <td className={`py-3 font-semibold ${GRADE_COLOR_CLASS[row.grade]}`}>
                  Grade {row.grade} · {GRADE_LABELS[row.grade]}
                </td>
                <td className="py-3 text-muted-foreground">{relativeTime(row.createdAt)}</td>
                <td className="py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-1 text-[12px] font-semibold ${row.status === "reviewed"
                ? "bg-success-light text-success"
                : "bg-warning-light text-warning"}`}>
                    {row.status === "reviewed" ? "Checked" : "Needs review"}
                  </span>
                </td>
              </tr>))}
          </tbody>
        </table>
      </div>
    </section>);
}
