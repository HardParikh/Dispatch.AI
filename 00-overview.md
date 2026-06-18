# Dispatch v2 — Agentic, RAG-Powered, Observable

This builds on your working v1. Three major additions, each with deep teaching:

1. **A real agent loop.** v1 was a fixed pipeline (extract, validate, act). v2 adds an agent that reasons in a loop, chooses tools, and decides when it is done. This is the leap from a workflow to an agent.

2. **A RAG layer.** The agent can look up business knowledge: carrier history, lane pricing, customer rules, freight policy. It retrieves relevant context before deciding, instead of relying only on what is in the message. This is what makes Augie "know" how a specific brokerage operates.

3. **Observability.** Every agent run is traced: which tools it called, how long each took, what it retrieved, what it decided, and what it cost. You can see inside the agent's head. This is what separates a toy from a system you can operate.

Read this overview, then the three concept docs (agent, RAG, observability), then build the files. The code files are all complete and ready to drop in.

---

## The shift from v1 to v2: workflow to agent

In v1, the control flow was fixed. Every message went extract, then validate, then act, in that exact order, every time. The code decided the path. That is a workflow.

In v2, you add an agent that decides its own path. Given a load that failed validation, the agent reasons: "weight is missing, let me check the carrier's typical loads. Destination is ambiguous, let me look up this lane. Now I have enough to draft a precise clarification." The agent chooses which tools to call, in what order, and when to stop. The model decides the path. That is an agent.

Both still exist in v2. The fixed pipeline handles the deterministic spine (extract and validate always happen). The agent handles the open-ended part (what to do about a load that needs enrichment or judgment). This mirrors the real lesson from Atlas: use a workflow where the steps are known, use an agent only where runtime adaptation is genuinely needed.

---

## What each new file does

**knowledge.py** — the RAG knowledge base. Seeds a set of freight business documents (carrier profiles, lane pricing, customer SOPs, freight policy) and provides semantic retrieval over them.

**rag.py** — the retrieval layer. Embeds a query, finds the most relevant knowledge chunks, returns them. Includes the failure handling that makes RAG production-safe.

**agent.py** — the agent loop. A ReAct-style agent with tools: retrieve_knowledge, lookup_carrier, check_lane, validate_load. It reasons, calls tools, and produces an enriched decision.

**observability.py** — tracing. Records every step of every agent run: tool calls, durations, token usage, retrieved context, final decision. Stored and queryable.

**graph.py (updated)** — now routes loads that need enrichment through the agent, and traces the whole run.

**api.py (updated)** — new endpoints for traces and knowledge.

**Frontend (rebuilt)** — a professional, dynamic UI with three views: the load board, a trace inspector (see inside any agent run), and a knowledge browser. Tabs, live status, expandable traces, a much more polished feel.

---

## The teaching plan

Three concept documents accompany the code:

- **concept-agents.md** — what an agent loop really is, ReAct, tool design, why agents fail and how to handle it, the interview questions.
- **concept-rag.md** — what RAG is, embeddings, chunking, retrieval, why RAG fails and how to handle each failure mode, the interview questions.
- **concept-observability.md** — why you cannot operate an agent you cannot see, what to trace, how to read a trace, the interview questions.

Build order: read the three concept docs, then drop in the code files, then the frontend. I will give you all of it.
