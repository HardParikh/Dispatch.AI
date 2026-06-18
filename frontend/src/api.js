// Central place for talking to the backend.
// In development this points at your local FastAPI server.
// When you deploy, set VITE_API_URL in the hosting dashboard to your
// deployed backend URL, and this picks it up automatically.

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function ingestMessage(message) {
  const res = await fetch(`${API}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

export async function fetchLoads() {
  const res = await fetch(`${API}/loads`);
  const data = await res.json();
  return data.loads || [];
}

export async function changeLoadState(loadId, state) {
  const res = await fetch(`${API}/loads/${loadId}/state`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  });
  return res.json();
}
