# AI Agents, In Depth

This teaches the agent concept the way an interviewer probes it: what an agent actually is, how the loop works, how to design tools, every way agents fail, and what you do about each. By the end you can answer any agent interview question.

---

## Part 1: What an agent actually is

### The definition that matters

An agent is an LLM that runs in a loop, decides which tools to call, observes the results, and decides when it is done. The defining property is that the model controls the flow. The code does not decide the sequence of steps; the model does, at runtime, based on what it observes.

Contrast with a workflow, where the steps are fixed in code. Your Dispatch v1 was a workflow: extract, then validate, then act, every time, decided by the code. An agent is different: given a goal, it figures out the steps itself.

**The one-line definition:** an agent is an LLM in a loop with tools, where the model decides which tool to call next and when the task is complete.

### Why this distinction matters in interviews

The most common mistake is calling everything an "agent." A single LLM call is not an agent. A fixed pipeline of LLM calls is not an agent. An agent specifically has the loop and the runtime decision-making. Being precise about this signals you understand the architecture, not just the buzzword.

And the senior insight, straight from Atlas: most production "AI" should be workflows, not agents. Agents are powerful but harder to control, debug, and make reliable. You reach for an agent only when the task genuinely needs runtime adaptation, when you cannot predict the steps in advance. If you can write the steps as a fixed pipeline, do that instead.

---

## Part 2: The ReAct loop, the core pattern

ReAct stands for Reason and Act. It is the foundational agent pattern. The loop:

1. **Reason.** The model thinks about the goal and the current state. "I have a load missing its weight. I should look up this carrier's typical loads."
2. **Act.** The model calls a tool. "Call lookup_carrier with Armstrong Transport."
3. **Observe.** The tool returns a result. "Armstrong's typical dry van load is 40000 to 44000 lbs."
4. **Repeat.** Back to reason with the new information. "Now I know the typical range. The destination is still ambiguous. Let me check the lane."
5. **Stop.** When the model has enough to complete the goal, it produces a final answer instead of calling a tool.

The loop continues until the model decides it is done or hits a maximum iteration cap. That cap is essential, which we will get to in the failure section.

**The mechanics:** each turn, you send the model the conversation so far plus the available tools. The model either calls a tool (you execute it and feed back the result) or produces a final answer (you stop). The model's choice each turn is the "decides its own path" property that makes it an agent.

**Interview question: "what is the ReAct pattern?"**
> ReAct is reason and act. The agent loops: it reasons about the goal and current state, acts by calling a tool, observes the result, and repeats with the new information. It stops when it has enough to answer or hits an iteration cap. The model's per-turn choice of whether to call a tool and which one is what makes it an agent rather than a fixed pipeline.

---

## Part 3: Tool design, where agents succeed or fail

An agent is only as good as its tools. Tool design is the highest-leverage work in building an agent, and it is mostly prompt engineering in disguise.

### Tools are the agent's hands

A tool is a function the agent can call: search the web, query a database, look up a carrier, retrieve knowledge. Each tool has a name, a description, and an input schema. The model reads the descriptions to decide which tool fits the current need.

### The tool description IS prompt engineering

This is the key insight from Atlas. The model chooses tools based on their descriptions. A vague description ("gets data") leads to wrong tool choices. A precise description ("looks up a carrier's reliability score, typical load weights, and equipment types by carrier name") leads to correct ones. You are writing instructions for the model's decision-making every time you describe a tool. Treat tool descriptions with the same care as your main prompt.

### Tool design principles

- **One clear job per tool.** A tool that does many things is hard for the model to choose correctly. Narrow, well-named tools are chosen well.
- **Descriptive names and parameters.** lookup_carrier(carrier_name) is self-explanatory. fetch(x) is not.
- **Return structured, useful results.** The model has to reason over what the tool returns. Clean, relevant returns lead to good reasoning. Noisy returns confuse it.
- **Handle tool failure gracefully.** A tool that throws crashes the agent. A tool that returns "no carrier found for that name" lets the agent reason about the miss and recover.

**Interview question: "how do you design tools for an agent?"**
> Each tool should have one clear job, a descriptive name and parameters, and return clean structured results. The most important part is the description, because the model chooses tools by reading descriptions, so a tool description is really prompt engineering for the model's tool-selection decision. And tools should fail gracefully, returning a clear "not found" rather than throwing, so the agent can reason about the miss and recover instead of crashing.

---

## Part 4: Why agents fail, and what you do about each

This is the section that matters most in interviews. Agents have failure modes a single LLM call does not. There are six big ones.

### Failure 1: The agent loops forever

The agent keeps calling tools without converging. It checks the carrier, then the lane, then the carrier again, never deciding it has enough.

**Why it happens:**
- The goal is underspecified, so the model never feels "done."
- A tool keeps returning unhelpful results and the model keeps retrying.
- The model gets stuck reconsidering the same information.

**What you do:**
- **A maximum iteration cap.** The single most important agent safeguard. After N loops, force a stop and return the best answer so far. Never run an agent without a cap; an uncapped agent can burn unbounded time and money.
- **Clear completion criteria in the prompt.** Tell the agent what "done" looks like so it knows when to stop.
- **Detect repeated tool calls.** If the agent calls the same tool with the same arguments twice, that is a loop signal; you can break or intervene.

### Failure 2: The agent calls the wrong tool

The agent picks a tool that does not fit the need, gets an unhelpful result, and goes off track.

**Why it happens:**
- Tool descriptions are vague or overlapping, so the model cannot tell them apart.
- Too many tools, so the choice is hard.

**What you do:**
- **Sharpen tool descriptions** so each tool's purpose is unambiguous.
- **Reduce tool count.** Fewer, clearer tools beat many overlapping ones. If two tools do similar things, merge them.
- **Give examples** in the system prompt of when to use which tool.

### Failure 3: The agent hallucinates tool results or arguments

The agent invents a tool result instead of calling the tool, or calls a tool with made-up arguments.

**Why it happens:**
- The model "knows" the answer from training and skips the tool.
- The prompt did not make clear that tools are the source of truth.

**What you do:**
- **Instruct the agent to always use tools for facts**, never its own knowledge, for the domains the tools cover.
- **Use forced tool use** where appropriate (like the extraction in Dispatch), so the model must call the tool rather than answer from memory.
- **Validate tool arguments** before executing, so a hallucinated argument is caught rather than acted on.

### Failure 4: Error cascades

One tool fails or returns something unexpected, and the agent's subsequent reasoning compounds the error across many steps.

**Why it happens:**
- A tool returned an error string the model misread as data.
- An early wrong step poisoned everything after it.

**What you do:**
- **Tools fail gracefully** with clear, unambiguous error returns the model can recognize as failures.
- **The iteration cap** bounds how far a cascade can go.
- **Checkpointing** (from Atlas) lets you inspect state at each step and see where it went wrong.

### Failure 5: Cost and latency explosion

Each agent step is an LLM call. A multi-step agent on a complex task can make many calls, each adding cost and latency. A single user request might cost ten model calls.

**Why it happens:**
- The nature of agents: iterations compound cost linearly.
- An agent used where a workflow would do, paying agent overhead for no benefit.

**What you do:**
- **Use an agent only where you need one.** This is the biggest lever. If the steps are predictable, use a workflow. Most tasks do not need an agent.
- **Cap iterations** to bound worst-case cost.
- **Use a smaller, cheaper model** for the agent loop where the reasoning is simple, reserving the large model for hard steps.
- **Cache** retrievals and tool results that repeat.

### Failure 6: The agent does something unintended

An agent with tools that take real actions (send email, modify records) could take a wrong action with real consequences.

**Why it happens:**
- The agent misjudged the situation and acted on it.
- A tool had more power than the task needed.

**What you do:**
- **Human in the loop for consequential actions.** The agent proposes, a human approves before anything irreversible happens. This is exactly the needs_review flow in Dispatch.
- **Least privilege.** Give the agent only the tools the task requires. Do not give it a delete tool if it never needs to delete.
- **Make actions auditable** (observability), so every action is recorded and inspectable.

---

## Part 5: The agent interview question bank

**"What is the difference between an agent and a workflow?"**
> A workflow has fixed steps decided in code. An agent runs in a loop where the model decides which tool to call next and when it is done, so the control flow is determined at runtime by the model. The key property of an agent is that the model controls the path. And the senior point is that most production AI should be workflows; you use an agent only when the task genuinely needs runtime adaptation you cannot script in advance.

**"How do you keep an agent from running forever?"**
> A maximum iteration cap is the essential safeguard; after N loops you force a stop and return the best answer so far. I also put clear completion criteria in the prompt so the agent knows what done looks like, and I detect repeated identical tool calls as a loop signal. You never run an agent without a cap, because an uncapped agent can burn unbounded time and money.

**"How do you design good tools for an agent?"**
> One clear job per tool, descriptive names and parameters, clean structured returns, and graceful failure that returns a clear not-found rather than throwing. The most important part is the description, because the model selects tools by reading descriptions, so writing a tool description is prompt engineering for the model's tool-selection decision.

**"An agent is giving wrong results. How do you debug it?"**
> I trace the run and look at each step: what the agent reasoned, which tool it called, what arguments it passed, and what the tool returned. The failure is usually visible at one specific step, a wrong tool choice, a hallucinated argument, or a misread tool result. This is why observability is essential for agents; without a trace you are guessing. Once I see the bad step, the fix is usually a sharper tool description, a grounding instruction, or better tool error handling.

**"When should you NOT use an agent?"**
> When the steps are predictable. If you can write the task as a fixed pipeline, use a workflow, because it is cheaper, faster, and far easier to make reliable. Agents add cost, latency, and unpredictability. The temptation is to use an agent because it sounds sophisticated, but the right question is whether the task actually needs runtime adaptation. Most do not.

**"How do you control agent cost?"**
> The biggest lever is not using an agent where a workflow would do, since each agent step is an LLM call and iterations compound cost linearly. Beyond that: cap iterations to bound worst-case cost, use a smaller model for simple reasoning steps and reserve the large model for hard ones, and cache repeated retrievals and tool results.

**"How do you make an agent safe to take real actions?"**
> Human in the loop for anything consequential or irreversible: the agent proposes, a human approves before it acts. Least privilege: give the agent only the tools the task needs, nothing more. And make every action auditable through tracing, so you can see exactly what the agent did and why. The agent should never silently take an irreversible action.

---

## Part 6: How the agent shows up in Dispatch v2

In v2, loads that pass extraction but need judgment or enrichment go to an agent. The agent has tools: retrieve_knowledge (RAG over freight business knowledge), lookup_carrier (carrier reliability and typical loads), check_lane (lane pricing benchmarks), and validate_load (the deterministic validator, exposed as a tool).

Given a load missing its weight from a known carrier, the agent reasons: look up the carrier, see their typical load range, retrieve any relevant SOP, then produce an enriched assessment or a precise clarification. The model decides which tools to call and in what order. That is the agent loop.

Every safeguard from this doc is in the code: an iteration cap so it cannot loop forever, graceful tool failures so a miss does not crash it, the deterministic validator still owning business rules so the agent cannot override them, and full tracing so you can see every step it took. The agent enriches and reasons; it never gets to be the source of truth for business decisions. That stays in deterministic code.
