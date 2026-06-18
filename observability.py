"""
Observability for Dispatch agent runs.

This records everything an agent does during a run: each step, the tool it
called, the arguments, the result, retrievals with similarity scores, timing,
and token usage. A completed trace is stored and can be fetched by load id so
the frontend can show exactly what the agent did.

The concept doc (concept-observability.md) explains why this is non-negotiable
for agents: an agent makes many interdependent decisions, so a wrong answer
could originate at any step, and without a trace you cannot tell which.

A Trace is built up during a run via a small object, then saved as a plain
dict. We keep traces in memory here for simplicity. In production these go to
a platform like LangSmith or Langfuse, but the shape of what we capture is the
same.
"""

import time
import uuid


# In-memory trace store, keyed by load_id. Production would use a database or a
# dedicated tracing platform.
_traces = {}


class Trace:
    """
    Accumulates the record of one agent run. Create one at the start of a run,
    call add_step / add_retrieval as the agent works, then finish() to store it.
    """

    def __init__(self, load_id):
        self.trace_id = "T-" + uuid.uuid4().hex[:8].upper()
        self.load_id = load_id
        self.steps = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.started_at = time.time()
        self.finished_at = None
        self.final_decision = ""

    def add_step(self, kind, detail, duration_ms=0, input_tokens=0, output_tokens=0):
        """
        Record one step. kind is a short label like 'reason', 'tool_call',
        'tool_result'. detail is a dict with whatever is relevant to that step.
        """
        self.steps.append({
            "index": len(self.steps),
            "kind": kind,
            "detail": detail,
            "duration_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def add_retrieval(self, query, chunks, duration_ms=0):
        """
        Record a RAG retrieval: the query, what came back, and the similarity
        scores. This is what lets you debug retrieval failures from the trace.
        """
        self.steps.append({
            "index": len(self.steps),
            "kind": "retrieval",
            "detail": {
                "query": query,
                "retrieved": [
                    {"id": c["id"], "score": c["score"], "category": c["category"]}
                    for c in chunks
                ],
                "count": len(chunks),
            },
            "duration_ms": duration_ms,
            "input_tokens": 0,
            "output_tokens": 0,
        })

    def finish(self, final_decision):
        """Mark the run complete and store the trace."""
        self.finished_at = time.time()
        self.final_decision = final_decision
        _traces[self.load_id] = self.to_dict()

    def to_dict(self):
        total_ms = 0
        if self.finished_at:
            total_ms = round((self.finished_at - self.started_at) * 1000)
        return {
            "trace_id": self.trace_id,
            "load_id": self.load_id,
            "steps": self.steps,
            "step_count": len(self.steps),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_duration_ms": total_ms,
            "final_decision": self.final_decision,
        }


def get_trace(load_id):
    """Fetch the stored trace for a load, or None."""
    return _traces.get(load_id)


def list_traces():
    """Return all traces, for an overview. Newest activity is not tracked here,
    so we just return them all; the frontend pairs them with loads."""
    return list(_traces.values())
