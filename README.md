# Dispatch v2 — Build and Run Guide

This builds on your working v1. It adds a real agent loop, a RAG layer, and full observability, plus a professional dynamic frontend. This guide covers what changed, how to run it, and how each piece maps to an interview answer.

Read the three concept docs first (concept-agents, concept-rag, concept-observability). They teach the concepts in depth, including every failure mode and the interview question bank. This file is the practical build guide.

---

## What changed from v1

**New backend files:**
- `knowledge.py` — the freight knowledge base (carrier profiles, lane pricing, SOPs, policy)
- `rag.py` — retrieval: embeds knowledge, retrieves by similarity, with a threshold
- `agent.py` — the ReAct agent loop with four tools, RAG, tracing, and an iteration cap
- `observability.py` — tracing: records every agent step, retrieval, timing, and token use

**Updated backend files:**
- `models.py` — adds an `agent_trace_id` field linking a load to its agent trace
- `graph.py` — adds a conditional branch: clean loads skip the agent, loads needing judgment go through it
- `api.py` — adds `/traces/{load_id}`, `/knowledge`, and `/stats` endpoints

**Carried over unchanged:**
- `extractor.py`, `validator.py`, `actions.py`, `store.py`

**Rebuilt frontend:**
- Tabbed UI (Load Board, Knowledge Base)
- Live stats bar (agent runs, avg steps, avg latency, total tokens, load counts)
- A trace inspector inside each load that went through the agent: step by step view of reasoning, retrievals with similarity scores, tool calls with arguments and results, timing, and tokens
- A knowledge browser showing every document the RAG layer can retrieve

---

## The architecture in one picture

```
message
   |
extract  (LLM structured output)
   |
validate  (deterministic rules)
   |
   +--- clean load (confirmed) ---------------------+
   |                                                 |
   +--- needs judgment (needs_review) --> AGENT      |
                                            |        |
                                   ReAct loop with:  |
                                   - retrieve_knowledge (RAG)
                                   - lookup_carrier
                                   - check_lane
                                   - finalize
                                   (traced end to end)
                                            |        |
                                            +--------+
                                                 |
                                                act
                                                 |
                                              persist
```

The deterministic spine (extract, validate) always runs. The agent handles only the open ended part, and only when a load needs it. This is the workflow-plus-agent discipline: use the agent where runtime judgment helps, skip it where it does not.

---

## Running it locally

### Backend

```powershell
cd C:\Users\ParikH01\Downloads\dispatch-v2

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, add your Anthropic key. Supabase is optional (in-memory fallback works).

Test the agent pipeline directly:

```powershell
python -m graph
```

You will see a clean load skip the agent, and two loads route through it with full agent processing.

Run the API:

```powershell
uvicorn api:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Ingest example 2 (the overweight Armstrong reefer). Watch it route through the agent. Expand the load, click "Inspect agent trace," and see the full step by step: the agent looking up the carrier, retrieving freight policy, reasoning, and finalizing, with similarity scores and timing on every step.

---

## If you have the v1 Supabase table

Run `schema_v2_migration.sql` in the Supabase SQL editor to add the new `agent_trace_id` column. If you are starting fresh, `schema.sql` already includes everything except that column, so run both, or just add the column.

Note: traces themselves are stored in memory in `observability.py`, so they reset on server restart. That is fine for a demo. Persisting traces to a database is a natural next step and a good thing to mention in an interview as the production upgrade.

---

## How to demo this in an interview

The flow that shows everything in 90 seconds:

1. Open the app. Point at the stats bar: "every agent run is traced, these are the aggregate numbers."
2. Ingest the overweight Armstrong reefer example.
3. "This load failed validation because 45000 lbs exceeds the reefer limit and it is from a known carrier, so it routes to the agent rather than auto confirming."
4. Expand it, inspect the trace. "Here is exactly what the agent did. It looked up Armstrong's profile, retrieved the reefer weight policy from the knowledge base with these similarity scores, reasoned about the overweight situation, and finalized a recommendation. Every step, every retrieval, every tool call, the timing and token cost, all visible."
5. Switch to the Knowledge Base tab. "This is the RAG layer the agent retrieves from. In production this is company specific knowledge, which is how an assistant like this knows how a particular brokerage operates."

That demo hits agent, RAG, and observability in one minute, with a working system behind it.

---

## The three concepts, one line each for the interview

- **Agent:** an LLM in a loop that chooses tools and decides when it is done. I use it only for loads needing judgment, with an iteration cap, graceful tool failure, and the deterministic validator still owning business rules.
- **RAG:** retrieve relevant company knowledge by semantic similarity and ground the agent's reasoning in it, with a similarity threshold so irrelevant chunks are dropped rather than fed to the model.
- **Observability:** every agent run is fully traced, because an agent makes many interdependent decisions and a wrong answer could come from any step, so you cannot operate it without seeing inside it.

Read the concept docs for the full failure-mode coverage and the interview question banks. That is where the depth is.
