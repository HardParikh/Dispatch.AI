import { useState, useEffect } from "react";
import {
  ingestMessage,
  fetchLoads,
  changeLoadState,
  fetchKnowledge,
  fetchStats,
} from "./api.js";
import LoadCard from "./LoadCard.jsx";
import KnowledgeView from "./KnowledgeView.jsx";
import StatsBar from "./StatsBar.jsx";

const EXAMPLES = [
  "Dry van, 42000 lbs canned goods, Dayton OH to Columbus OH. Ref B-347363.",
  "Reefer, 45000 lbs frozen goods, Fresno CA to Phoenix AZ from Armstrong Transport.",
  "Flatbed out of Houston, steel coils about 47000 lbs.",
  "Need to move 50000 lbs retail goods, Atlanta GA to Nashville TN, dry van, pickup tomorrow.",
];

export default function App() {
  const [tab, setTab] = useState("board");
  const [message, setMessage] = useState("");
  const [loads, setLoads] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  async function refreshAll() {
    setBusy(true);
    try {
      const [l, s] = await Promise.all([fetchLoads(), fetchStats()]);
      setLoads(l);
      setStats(s);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshAll();
    fetchKnowledge().then(setKnowledge);
  }, []);

  async function handleIngest() {
  if (!message.trim()) return;
  setLoading(true);
  try {
    await ingestMessage(message);
    setMessage("");
  } catch (e) {
    console.error("ingest error:", e);
  } finally {
    await refreshAll();
    setLoading(false);
  }
}

  async function handleStateChange(loadId, newState) {
    await changeLoadState(loadId, newState);
    await refreshAll();
  }

  const reviewCount = loads.filter((l) => l.state === "needs_review").length;
  const confirmedCount = loads.filter((l) => l.state === "confirmed").length;

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <div className="logo">D</div>
          <div>
            <h1>Dispatch</h1>
            <p className="tagline">
              Agentic freight intake with retrieval and full observability
            </p>
          </div>
        </div>
        <StatsBar stats={stats} loadCount={loads.length} reviewCount={reviewCount} confirmedCount={confirmedCount} />
      </header>

      <nav className="tabs">
        <button className={tab === "board" ? "tab active" : "tab"} onClick={() => setTab("board")}>
          Load Board
        </button>
        <button className={tab === "knowledge" ? "tab active" : "tab"} onClick={() => setTab("knowledge")}>
          Knowledge Base
        </button>
      </nav>

      {tab === "board" && (
        <>
          <section className="ingest">
            <textarea
              className="message-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Paste a freight email or tender message..."
              rows={3}
            />
            <div className="ingest-row">
              <button className="primary" onClick={handleIngest} disabled={loading}>
                {loading ? "Processing through agent..." : "Ingest message"}
              </button>
              <div className="examples">
                <span>Examples:</span>
                {EXAMPLES.map((ex, i) => (
                  <button key={i} className="example-chip" onClick={() => setMessage(ex)}>
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="loads">
            <div className="loads-header">
              <h2>Loads</h2>
              <button className="ghost" onClick={refreshAll} disabled={busy}>
                {busy ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            {loads.length === 0 && (
              <p className="empty">No loads yet. Ingest a message to create one.</p>
            )}

            {loads.map((load) => (
              <LoadCard key={load.load_id} load={load} onStateChange={handleStateChange} />
            ))}
          </section>
        </>
      )}

      {tab === "knowledge" && <KnowledgeView knowledge={knowledge} />}
    </div>
  );
}
