// A live stats strip in the header. Shows aggregate observability across all
// agent runs plus load counts. This is the operability view from the
// observability concept doc, surfaced at a glance.

export default function StatsBar({ stats, loadCount, reviewCount, confirmedCount }) {
  return (
    <div className="stats-bar">
      <Stat label="Loads" value={loadCount} />
      <Stat label="Confirmed" value={confirmedCount} accent="#059669" />
      <Stat label="Needs review" value={reviewCount} accent="#d97706" />
      <div className="stat-divider" />
      <Stat label="Agent runs" value={stats ? stats.agent_runs : "—"} />
      <Stat label="Avg steps" value={stats ? stats.avg_steps : "—"} />
      <Stat label="Avg latency" value={stats ? stats.avg_duration_ms + " ms" : "—"} />
      <Stat label="Total tokens" value={stats ? stats.total_tokens.toLocaleString() : "—"} />
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="stat">
      <div className="stat-value" style={accent ? { color: accent } : {}}>
        {value}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
