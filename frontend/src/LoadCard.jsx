import { useState } from "react";

// Maps a load state to a color for the status badge.
const STATE_COLORS = {
  draft: "#888",
  needs_review: "#d97706",
  confirmed: "#059669",
  in_transit: "#2563eb",
  delivered: "#7c3aed",
  billed: "#475569",
};

// Which manual transitions to offer from each state.
// Mirrors ALLOWED_TRANSITIONS on the backend so the buttons line up.
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

  const color = STATE_COLORS[load.state] || "#888";
  const lane =
    (load.origin_city || "?") +
    (load.origin_state ? ", " + load.origin_state : "") +
    "  to  " +
    (load.dest_city || "?") +
    (load.dest_state ? ", " + load.dest_state : "");

  const nextStates = NEXT_STATES[load.state] || [];

  return (
    <div className="load-card">
      <div className="load-top" onClick={() => setOpen(!open)}>
        <div className="load-id">{load.load_id}</div>
        <div className="load-lane">{lane}</div>
        <div className="load-meta">
          {load.weight_lbs ? load.weight_lbs + " lbs" : "no weight"} ·{" "}
          {load.equipment}
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
            <Field
              label="Inferred fields"
              value={(load.inferred_fields || []).join(", ")}
            />
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
              <h4>Agent actions</h4>
              {load.actions.map((a, i) => (
                <div key={i} className="action">
                  <div className="action-type">{a.type}</div>
                  <div className="action-summary">{a.summary}</div>
                  {a.content && (
                    <pre className="action-content">{a.content}</pre>
                  )}
                </div>
              ))}
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
                <button
                  key={s}
                  className="ghost small"
                  onClick={() => onStateChange(load.load_id, s)}
                >
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

function Field({ label, value }) {
  return (
    <div className="field">
      <div className="field-label">{label}</div>
      <div className="field-value">{value || "—"}</div>
    </div>
  );
}
