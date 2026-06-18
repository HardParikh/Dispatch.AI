import { useState, useEffect } from "react";
import { ingestMessage, fetchLoads, changeLoadState } from "./api.js";
import LoadCard from "./LoadCard.jsx";

// A few example messages so the demo is one click to try.
const EXAMPLES = [
  "Need a dry van to grab 42k lbs of canned goods out of Dayton OH Tuesday morning, deliver to Kansas City. Ref# B-347363.",
  "Can you cover a flatbed out of Houston? Steel coils, about 47000 lbs.",
  "Reefer load. 40k of frozen veggies. Pickup Fresno CA, drop in Phoenix AZ. Pickup 12/15. Order RF-5521.",
  "Load available: dry van, fifty thousand pounds of retail goods, Atlanta GA to Nashville TN, pickup tomorrow.",
];

export default function App() {
  const [message, setMessage] = useState("");
  const [loads, setLoads] = useState([]);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    const data = await fetchLoads();
    setLoads(data);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleIngest() {
    if (!message.trim()) return;
    setLoading(true);
    try {
      await ingestMessage(message);
      setMessage("");
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  async function handleStateChange(loadId, newState) {
    await changeLoadState(loadId, newState);
    await refresh();
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Dispatch</h1>
        <p className="tagline">
          Turn unstructured freight messages into validated, structured loads.
        </p>
      </header>

      <section className="ingest">
        <textarea
          className="message-input"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Paste a freight email or tender message here..."
          rows={4}
        />
        <div className="ingest-row">
          <button className="primary" onClick={handleIngest} disabled={loading}>
            {loading ? "Processing..." : "Ingest message"}
          </button>
          <div className="examples">
            <span>Try an example:</span>
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                className="example-chip"
                onClick={() => setMessage(ex)}
              >
                {i + 1}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="loads">
        <div className="loads-header">
          <h2>Loads ({loads.length})</h2>
          <button className="ghost" onClick={refresh}>
            Refresh
          </button>
        </div>

        {loads.length === 0 && (
          <p className="empty">No loads yet. Ingest a message to create one.</p>
        )}

        {loads.map((load) => (
          <LoadCard
            key={load.load_id}
            load={load}
            onStateChange={handleStateChange}
          />
        ))}
      </section>
    </div>
  );
}
