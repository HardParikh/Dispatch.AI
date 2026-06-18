// All backend calls in one place.
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function getJSON(path) {
  const res = await fetch(`${API}${path}`);
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export function ingestMessage(message) {
  return postJSON("/ingest", { message });
}

export async function fetchLoads() {
  const data = await getJSON("/loads");
  return data.loads || [];
}

export function changeLoadState(loadId, state) {
  return postJSON(`/loads/${loadId}/state`, { state });
}

export function fetchTrace(loadId) {
  return getJSON(`/traces/${loadId}`);
}

export async function fetchKnowledge() {
  const data = await getJSON("/knowledge");
  return data.knowledge || [];
}

export function fetchStats() {
  return getJSON("/stats");
}
