/**
 * Donut chart of scan results by severity grade, with a counted legend below.
 * INPUT: the grade distribution array. OUTPUT: Recharts pie + legend rows.
 */
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { GRADE_DISTRIBUTION } from "@/lib/fedretina/mockData";
export function GradeDonut() {
  const total = GRADE_DISTRIBUTION.reduce((sum, slice) => sum + slice.count, 0);
  return (
    <section className="fr-lift rounded-md border border-border bg-surface p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">
        Results by severity
      </h2>
      <p className="mt-0.5 text-[13px] text-muted-foreground">
        All scans from the past week
      </p>

      <div className="mt-4 h-52">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={GRADE_DISTRIBUTION}
              dataKey="count"
              nameKey="label"
              innerRadius="58%"
              outerRadius="88%"
              paddingAngle={3}
              stroke="none"
            >
              {GRADE_DISTRIBUTION.map((slice) => (
                <Cell key={slice.grade} fill={slice.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: 12,
                color: "var(--text-primary)",
                fontSize: 13,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <ul className="mt-4 space-y-2">
        {GRADE_DISTRIBUTION.map((slice) => (
          <li key={slice.grade} className="flex items-center gap-2 text-[13px]">
            <span
              className="size-2.5 rounded-full"
              style={{ background: slice.color }}
              aria-hidden
            />
            <span className="text-secondary-text">{slice.label}</span>
            <span className="ml-auto font-semibold text-foreground">
              {slice.count}
              <span className="ml-1 font-normal text-muted-foreground">
                ({total ? Math.round((slice.count / total) * 100) : 0}%)
              </span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
