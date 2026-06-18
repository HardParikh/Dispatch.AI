import { useState } from "react";
import { fetchTrace } from "./api.js";

const STATE_COLORS = {
  draft: "#888",
  needs_review: "#d97706",
  confirmed: "#059669",
  in_transit: "#2563eb",
  delivered: "#7c3aed",
  billed: "#475569",
};

const NEXT_STATES = {
  draft: ["needs_review", "confirmed"],
  needs_review: ["confirmed", "draft"],
  confirmed: ["in_transit"],
  in_transit: ["delivered"],
  delivered: ["billed"],
  billed: [],
};

export default function LoadCard({ load, onStateChange }) {
  const [open, setOpen] = useState(false);
  const [trace, setTrace] = useState(null);
  const [traceOpen, setTraceOpen] = useState(false);
  const [traceLoading, setTraceLoading] = useState(false);

  const color = STATE_COLORS[load.state] || "#888";
  const lane =
    (load.origin_city || "?") +
    (load.origin_state ? ", " + load.origin_state : "") +
    "  to  " +
    (load.dest_city || "?") +
    (load.dest_state ? ", " + load.dest_state : "");

  const nextStates = NEXT_STATES[load.state] || [];
  const hasTrace = load.agent_trace_id && load.agent_trace_id.length > 0;

  async function loadTrace() {
    if (trace) {
      setTraceOpen(!traceOpen);
      return;
    }
    setTraceLoading(true);
    try {
      const t = await fetchTrace(load.load_id);
      setTrace(t);
      setTraceOpen(true);
    } finally {
      setTraceLoading(false);
    }
  }

  return (
    <div className="load-card">
      <div className="load-top" onClick={() => setOpen(!open)}>
        <div className="load-id">{load.load_id}</div>
        <div className="load-lane">{lane}</div>
        <div className="load-meta">
          {load.weight_lbs ? load.weight_lbs.toLocaleString() + " lbs" : "no weight"} · {load.equipment}
          {hasTrace && <span className="agent-tag">agent</span>}
        </div>
        <span className="badge" style={{ backgroundColor: color }}>
          {load.state.replace("_", " ")}
        </span>
      </div>

      {open && (
        <div className="load-detail">
          <div className="detail-grid">
            <Field label="Commodity" value={load.commodity} />
            <Field label="Pickup" value={load.pickup_date} />
            <Field label="Reference" value={load.reference_number} />
            <Field label="Inferred" value={(load.inferred_fields || []).join(", ")} />
          </div>

          {load.validation_errors && load.validation_errors.length > 0 && (
            <div className="errors">
              <h4>Validation issues</h4>
              <ul>
                {load.validation_errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {load.actions && load.actions.length > 0 && (
            <div className="actions">
              <h4>Actions</h4>
              {load.actions.map((a, i) => (
                <div key={i} className="action">
                  <div className="action-type">{a.type.replace(/_/g, " ")}</div>
                  <div className="action-summary">{a.summary}</div>
                  {a.content && <pre className="action-content">{a.content}</pre>}
                </div>
              ))}
            </div>
          )}

          {hasTrace && (
            <div className="trace-section">
              <button className="ghost small" onClick={loadTrace}>
                {traceLoading
                  ? "Loading trace..."
                  : traceOpen
                  ? "Hide agent trace"
                  : "Inspect agent trace"}
              </button>
              {traceOpen && trace && !trace.error && <TraceView trace={trace} />}
            </div>
          )}

          <div className="source">
            <h4>Original message</h4>
            <p>{load.source_message}</p>
          </div>

          {nextStates.length > 0 && (
            <div className="transitions">
              <span>Move to:</span>
              {nextStates.map((s) => (
                <button key={s} className="ghost small" onClick={() => onStateChange(load.load_id, s)}>
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// The trace inspector. This is the observability centerpiece: a step by step
// view of exactly what the agent did, including retrievals with similarity
// scores, tool calls with arguments and results, and timing and token usage.
function TraceView({ trace }) {
  return (
    <div className="trace">
      <div className="trace-summary">
        <span>{trace.step_count} steps</span>
        <span>{trace.total_duration_ms} ms</span>
        <span>{(trace.total_input_tokens + trace.total_output_tokens).toLocaleString()} tokens</span>
      </div>

      <div className="trace-steps">
        {trace.steps.map((step, i) => (
          <div key={i} className={`trace-step kind-${step.kind}`}>
            <div className="trace-step-head">
              <span className="trace-step-kind">{step.kind.replace(/_/g, " ")}</span>
              {step.duration_ms > 0 && <span className="trace-step-time">{step.duration_ms} ms</span>}
            </div>
            <TraceStepDetail step={step} />
          </div>
        ))}
      </div>

      <div className="trace-decision">
        <strong>Final decision:</strong> {trace.final_decision}
      </div>
    </div>
  );
}

function TraceStepDetail({ step }) {
  const d = step.detail;

  if (step.kind === "reason") {
    return <div className="trace-detail">{d.text}</div>;
  }

  if (step.kind === "retrieval") {
    return (
      <div className="trace-detail">
        <div className="trace-query">Query: "{d.query}"</div>
        {d.retrieved.length === 0 && <div className="trace-miss">Nothing above similarity threshold</div>}
        {d.retrieved.map((r, i) => (
          <div key={i} className="trace-chunk">
            <span className="chunk-id">{r.id}</span>
            <span className="chunk-score">score {r.score}</span>
          </div>
        ))}
      </div>
    );
  }

  if (step.kind === "tool_call") {
    return (
      <div className="trace-detail">
        <div className="trace-tool">{d.tool}({JSON.stringify(d.args)})</div>
        <div className="trace-result">{d.result}</div>
      </div>
    );
  }

  if (step.kind === "finalize") {
    return (
      <div className="trace-detail">
        <div><strong>Assessment:</strong> {d.assessment}</div>
        <div><strong>Action:</strong> {d.recommended_action}</div>
      </div>
    );
  }

  return <div className="trace-detail">{JSON.stringify(d)}</div>;
}

function Field({ label, value }) {
  return (
    <div className="field">
      <div className="field-label">{label}</div>
      <div className="field-value">{value || "—"}</div>
    </div>
  );
}
