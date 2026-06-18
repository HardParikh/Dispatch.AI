# Agent Observability, In Depth

You cannot operate an agent you cannot see. This teaches what observability is, what to trace, how to read a trace, and the interview questions. It is shorter than the agent and RAG docs because the concept is simpler, but it is what separates a demo from a system you can run in production.

---

## Part 1: Why observability exists

A single LLM call is easy to debug: one input, one output, look at both. An agent is not. An agent makes many decisions across many steps, each depending on the last. When an agent gives a wrong final answer, the bug could be in any step: a wrong tool choice three steps back, a misread tool result, a bad retrieval, a hallucinated argument. Without a record of every step, you are guessing.

Observability is the practice of recording everything an agent does so you can see inside its decision-making. Every reasoning step, every tool call with its arguments, every tool result, every retrieval, the timing of each, and the cost. With that record, debugging an agent becomes reading a trace instead of guessing.

**The one-line definition:** observability is the recorded, inspectable trace of everything an agent did during a run, so you can debug, audit, and improve it.

### Why it is non-negotiable for agents specifically

You can ship a single LLM call without observability and mostly get away with it. You cannot ship an agent without it. The whole value of an agent, that it decides its own path, is also what makes it unpredictable, and unpredictable systems must be observable or they cannot be operated. The first thing a senior engineer asks about an agent in production is "how do we see what it is doing." If the answer is "we cannot," the agent is not production-ready.

---

## Part 2: What to trace

A good trace captures, for each agent run:

- **The input.** What started the run. For Dispatch, the load.
- **Each step.** For every loop iteration: what the agent reasoned, which tool it chose, what arguments it passed, and what the tool returned.
- **Retrievals.** For RAG steps: what the query was, which chunks were retrieved, and their similarity scores. This is how you debug retrieval failures.
- **Timing.** How long each step took. This is how you find latency bottlenecks.
- **Token usage and cost.** Input and output tokens per call. This is how you find cost problems and the runaway-agent failure mode.
- **The final output.** What the agent ultimately decided.
- **Errors.** Any tool failure or exception, captured rather than swallowed.

The principle: capture enough that you can reconstruct exactly what happened and why, without rerunning it. A trace you cannot debug from is not detailed enough.

---

## Part 3: How to read a trace to debug

When an agent gives a wrong answer, you read the trace top to bottom and ask at each step: is this what should have happened?

- Did the agent reason correctly about the goal? If not, the system prompt or the goal framing is wrong.
- Did it choose the right tool? If not, the tool descriptions are unclear.
- Did it pass the right arguments? If not, the model misunderstood the input or hallucinated.
- Did the tool return the right thing? If not, the tool itself is buggy, or for retrieval, the chunk it needed was not retrieved.
- Did it correctly use the tool result in the next step? If not, the result format confused it.

The bug is almost always visible at one specific step. Observability turns "the agent is wrong, why" into "step 3 retrieved the wrong chunk, here is why." That specificity is the entire value.

**Interview question: "how do you debug an agent that gives wrong answers?"**
> I read the trace. For each step I check whether the agent reasoned correctly, chose the right tool, passed correct arguments, got a correct tool result, and used it correctly in the next step. The failure is almost always visible at one specific step. Without a trace you are guessing across many steps; with one, debugging becomes reading a record. This is why I consider observability non-negotiable for agents.

---

## Part 4: Observability in production

In a real system, traces go to a dedicated platform (LangSmith, Langfuse, or similar) that stores them, lets you search them, aggregates metrics across many runs, and alerts on anomalies. The concepts are the same as what you build in Dispatch; the platform just scales the storage and querying.

What aggregate observability gives you beyond single-run debugging:

- **Latency percentiles** across runs, so you find the slow path, not just one slow run.
- **Cost per run** trends, so you catch a regression that made the agent more expensive.
- **Tool usage patterns,** so you see which tools are called most, which fail most, which are never used.
- **Failure rates** by type, so you know what is breaking in production before users tell you.

This connects directly to your E15 work: SLO dashboards, error budgets, p99 latency, MTTR. Agent observability is the same operational discipline applied to AI systems. You can say that in an interview and it lands, because it shows you treat AI systems with the same production rigor as any other infrastructure.

---

## Part 5: The observability interview question bank

**"Why do agents need observability more than a single LLM call?"**
> A single call has one input and one output; you debug it by looking at both. An agent makes many interdependent decisions across many steps, so a wrong final answer could originate at any step. Without a trace of every step you cannot tell where it went wrong. The agent's defining property, deciding its own path, is exactly what makes it unpredictable and therefore what makes observability non-negotiable.

**"What would you trace in an agent run?"**
> The input, each reasoning step, each tool call with its arguments and result, retrievals with their queries and similarity scores, timing per step, token usage and cost, the final output, and any errors. Enough to reconstruct exactly what happened and why without rerunning it. Retrievals and per-step timing especially, because retrieval failures and latency bottlenecks are common and invisible without them.

**"How does observability connect to running a system in production?"**
> Single-run traces are for debugging; aggregate observability is for operating. Across many runs I want latency percentiles to find the slow path, cost trends to catch regressions, tool usage and failure rates to know what is breaking before users report it. It is the same operational discipline as SLO dashboards, error budgets, and MTTR applied to AI systems. An agent you cannot observe is an agent you cannot operate.

---

## Part 6: How observability shows up in Dispatch v2

Every agent run in Dispatch is traced. The trace records each step the agent took: what it reasoned, which tool it called, what the tool returned, what it retrieved from the knowledge base and with what similarity scores, how long each step took, and the final decision. The traces are stored and exposed through an API, and the frontend has a trace inspector where you can open any load and see the complete record of how the agent processed it.

This means when a load gets an odd result, you do not guess. You open its trace and see exactly what the agent did: "it looked up the carrier, retrieved the wrong SOP because the similarity was borderline, and drafted a clarification based on that." The fix becomes obvious because the failure is visible. That is the entire point of observability, and having it built in is what makes Dispatch a system you could actually operate rather than a demo.
