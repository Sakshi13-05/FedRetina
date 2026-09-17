/**
 * Line chart of daily scan volume and flagged-case volume over the last 7 days.
 * INPUT: the weekly trend array. OUTPUT: two-line Recharts chart with a legend.
 */
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, } from "recharts";
import { WEEKLY_TREND } from "@/lib/fedretina/mockData";
export function WeeklyTrendLine() {
    return (<section className="fr-lift rounded-md border border-border bg-surface p-5 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Scans this week</h2>
      <p className="mt-0.5 text-[13px] text-muted-foreground">Total scans against cases needing a second look</p>

      <div className="mt-4 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={WEEKLY_TREND} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="var(--border)" vertical={false}/>
            <XAxis dataKey="day" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false}/>
            <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false}/>
            <Tooltip contentStyle={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            color: "var(--text-primary)",
            fontSize: 13,
        }}/>
            <Legend wrapperStyle={{ fontSize: 13, color: "var(--text-secondary)" }}/>
            <Line type="monotone" dataKey="total" name="Total scans" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--primary)" }}/>
            <Line type="monotone" dataKey="flagged" name="Needs review" stroke="var(--warning)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--warning)" }}/>
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>);
}

