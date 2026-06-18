# Dispatch — Build Guide and Concept Walkthrough

A logistics operations agent that mirrors the core engineering challenge of Augment's Augie product. It reads unstructured freight messages, turns them into validated structured loads, takes follow up actions, and exposes everything through a React frontend you can host.

This single document teaches the concepts and walks you through running and deploying the whole thing. Read it once top to bottom, then build.

---

## Part 1: What you are building and why it matters

Augment's product, Augie, does one core thing at an engineering level: it takes the chaos of logistics communication (emails, PDFs, portal messages, phone calls) and turns it into structured, validated actions inside business systems. From their own product page, Augie "reads emails, PDFs, and portal messages and turns them into structured loads" and then chases documents, routes loads, and handles billing.

Dispatch is your scaled down version of that core loop. It demonstrates the exact engineering patterns Augment cares about, which makes it a far stronger interview asset than a generic chatbot or research agent.

The flow:

```
Unstructured freight message
        |
        v
   Extractor      LLM turns language into a structured Load (tool use)
        |
        v
   Validator      deterministic business rules, tested code
        |
        v
   Action engine  decide what to do: route to dispatch, or draft a
        |         clarification email and flag for review
        v
   Store          persist to Supabase over HTTPS
        |
        v
   Frontend       React UI to ingest messages and inspect loads
```

The single most important idea in the whole project: **the LLM extracts, deterministic code validates.** You never let the model be the source of truth for business rules. The model parses messy language, where some variability is fine. Tested code applies weight limits and required field checks, where correctness is non negotiable. When an interviewer asks "how do you keep the agent from making mistakes on critical logic," this architecture is your answer.

---

## Part 2: The concepts, one per component

### Concept 1: Structured extraction via tool use (extractor.py)

The naive way to get structured data from an LLM is to ask it to "return JSON" and parse the result. You hit this in Atlas and fought markdown fence bugs. The robust way is tool use.

When you give Claude a tool with a defined input schema and force it to call that tool, the API guarantees the response conforms to your schema. No fences, no preambles, no parsing fragility. You define a tool called `record_load` whose schema is your load fields, and the model returns its extraction as a structured tool call. You never execute the tool. You just read the structured input.

Two details that make this production grade:

- **Normalization lives in the schema.** Each field description tells the model how to canonicalize: "Convert '42k lbs' to 42000." The schema is doing prompt engineering for the extraction.
- **The `inferred_fields` array.** The model reports which fields it guessed rather than read. Kansas City's state is not in a message, but the model might fill it. Tracking that lets the validator treat inferred values with suspicion. A naive extractor cannot tell "the message said OH" from "the model guessed OH." Yours can.

### Concept 2: Deterministic validation (validator.py)

Extraction is probabilistic. Run the same message twice and you may get slightly different output. That is fine for parsing language, and unacceptable for business rules. So validation is pure, deterministic, testable code. No LLM, no network, no randomness. Given the same load, you always get the same result.

The validator checks required fields, weight against equipment limits, valid US state codes, known equipment, and whether any critical routing field was inferred. Clean loads get auto confirmed. Anything with a problem gets marked needs_review. This split is the heart of a trustworthy agent: the model proposes, the validator disposes.

### Concept 3: The action engine (actions.py)

After validation, the agent decides what to do. A clean load routes to dispatch. A problem load gets two actions: a clarification email drafted by the LLM, and a flag for human review.

Notice the division of labor again. The validator (deterministic) decides what is wrong. The LLM (generative) writes a natural language email about it. The email is grounded in real, code-detected issues, so it cannot hallucinate a problem that does not exist. This is the right way to use an LLM in a business workflow: let it generate language from structured facts, never let it invent the facts.

Every action is a recorded, inspectable artifact, not a silent side effect. That auditability is what makes an agent safe to deploy in a real operation.

### Concept 4: Orchestration with LangGraph (graph.py)

You already know LangGraph from Atlas. Here it ties the pipeline together as a state machine: extract, validate, act, persist. Each node does one job and writes to a shared state dict.

Why a graph instead of just calling functions in sequence? Observability (each node is a named, inspectable step), state management (the shared state flows cleanly), and extensibility (adding a credit check later means adding a node, not rewriting a function). Today the flow is linear. The graph structure means you can add conditional routing later without restructuring.

### Concept 5: The state machine (models.py)

A load moves through a lifecycle: draft, needs_review, confirmed, in_transit, delivered, billed. The `ALLOWED_TRANSITIONS` map defines which moves are legal. The API enforces them, so a load can never jump from draft straight to billed. This is the same state-machine discipline every production agent converges on, applied to a domain object.

### Concept 6: Persistence over HTTPS (store.py)

This is the part that finally sidesteps all your Supabase pain. Instead of the direct Postgres connection that needs the pooler and fails on IPv4-only corporate networks, `store.py` uses the Supabase Python client, which talks to Supabase over plain HTTPS through its REST API. It needs only the project URL and an API key. It works everywhere, including the corporate laptop.

If you do not configure Supabase, the app falls back to an in-memory store so it still runs for local demos.

---

## Part 3: Running it locally

### Backend

```powershell
cd C:\Users\ParikH01\Downloads\dispatch-logistics-agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Anthropic key. Leave the Supabase vars blank for now to use the in-memory store.

Test the pipeline directly from the project root:

```powershell
python -m graph
```

You should see three sample messages processed: extracted, validated, and acted on. One will route to dispatch, others will be flagged with drafted clarification emails.

Now run the API:

```powershell
uvicorn api:app --reload --port 8000
```

Visit `http://localhost:8000/docs` to see the endpoints. Try `/ingest` with a freight message.

### Frontend

In a second terminal:

```powershell
cd C:\Users\ParikH01\Downloads\dispatch-logistics-agent\frontend

npm install
npm run dev
```

Open `http://localhost:5173`. Paste a freight message or click an example number, hit Ingest, and watch the load appear. Click a load to expand its details, validation issues, and the agent's drafted actions. Use the "Move to" buttons to walk a load through its lifecycle.

---

## Part 4: Wiring up Supabase (optional but recommended for hosting)

The in-memory store resets on restart, so for a hosted demo you want real persistence.

1. Create a free project at supabase.com using whatever account you can log into. You do NOT need the GitHub-linked account, since we use the REST API not the database login.
2. In the dashboard, open SQL Editor, paste the contents of `schema.sql`, and run it. This creates the `loads` table.
3. Go to Settings, then API. Copy the Project URL and the anon public key.
4. Put them in your `.env`:

```
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_KEY=your_anon_key
```

Restart the backend. Now loads persist. The console will no longer print the in-memory warning.

Because this uses HTTPS, none of the connection pooler, region, or IPv4 problems from your Atlas Postgres setup apply here.

---

## Part 5: Hosting it

You want this live so you can put a link on your resume and show it in interviews. Two pieces to deploy: the backend (FastAPI) and the frontend (React).

### Backend on Render (free tier)

1. Push the project to a GitHub repo (make sure `.env` is gitignored).
2. On render.com, create a new Web Service from your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in the Render dashboard: `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`.
6. Deploy. Render gives you a URL like `https://dispatch-api.onrender.com`.

Note: do not use the `verify=False` cert bypass concern here. On Render there is no corporate proxy, so normal TLS works. The code keeps `verify=False` which is harmless on a normal host, though for a polished production app you would make it conditional.

### Frontend on Vercel (free tier)

1. On vercel.com, import the same repo, set the root directory to `frontend`.
2. Framework preset: Vite. Build command `npm run build`, output directory `dist`.
3. Add an environment variable `VITE_API_URL` set to your Render backend URL.
4. Deploy. Vercel gives you a URL like `https://dispatch.vercel.app`.

Now you have a live, shareable logistics agent.

### One tweak before hosting

In `api.py`, the CORS config allows all origins for local development. Before going live, change `allow_origins=["*"]` to your actual Vercel URL so only your frontend can call the API.

---

## Part 6: How to talk about this in the Augment interview

When relevant experience comes up:

> Beyond my day job, I built a project called Dispatch that mirrors the core engineering challenge I understand Augie is solving. It takes unstructured freight messages, emails and tender text, and turns them into validated structured loads, then takes follow up actions like drafting clarification emails or flagging loads for human review.
>
> The design decision I am most deliberate about is the separation between extraction and validation. The LLM extracts the load details from the language using structured output, but deterministic code I can test applies the business rules: weight limits per equipment type, required fields, valid lanes. I never let the model be the source of truth for business logic. The model proposes, the validator disposes.
>
> It is orchestrated as a LangGraph state machine, persists over Supabase, and has a React frontend. I built it in Python because that is my fastest iteration language, but the architecture maps directly onto a Node and SQS based stack. The patterns are identical: structured extraction, deterministic validation, a state machine for the load lifecycle, and a recorded action layer.

That answer shows you understand their product at an engineering level, not a marketing level. Very few candidates walk in with that.

### The follow ups you can now handle

- **"How do you handle a message the model parses wrong?"** The validator catches structural problems (missing fields, impossible weights, invalid states), and inferred critical fields are flagged for human review rather than auto dispatched.
- **"What if the model hallucinates?"** It cannot hallucinate business decisions because those are deterministic code. It can only mis-parse language, which the validator catches, and the clarification email is grounded in code-detected issues.
- **"How would this scale to thousands of messages?"** The extractor and validator are stateless, so they scale horizontally. The store is the only shared state. You would put ingestion behind a queue (their stack uses SQS) and run worker pools, exactly the pattern I use for Kafka consumers at E15.
- **"How do you know it works?"** That is the eval layer, which is the natural next step: a labeled set of freight messages with known correct extractions, measuring extraction accuracy and validation precision.

---

## Part 7: File map

```
dispatch-logistics-agent/
  models.py          plain Python data structures and the state machine map
  extractor.py       LLM structured extraction via tool use
  validator.py       deterministic business rules (testable, pure)
  actions.py         action engine: route, draft clarification, flag
  graph.py           LangGraph orchestration of the full pipeline
  store.py           Supabase over HTTPS, with in-memory fallback
  api.py             FastAPI endpoints for the frontend
  schema.sql         the Supabase table definition
  requirements.txt   backend dependencies
  .env.example       environment variable template
  .gitignore
  frontend/
    package.json     Vite plus React, plain JSX
    vite.config.js
    index.html
    src/
      main.jsx       React entry point
      App.jsx        main component: ingest box plus load list
      LoadCard.jsx   expandable card per load
      api.js         talks to the backend
      styles.css     styling
```

---

## Part 8: The natural next steps (if you want to keep going)

You do not need these for the interview, but they are the obvious extensions, and naming them shows you see the full picture:

1. **Evaluation suite.** A labeled set of messages with known extractions. Measure accuracy. This is what turns a demo into a system.
2. **PDF ingestion.** Extract text from a rate confirmation PDF, then run the same extractor. Augie does this.
3. **Conversation memory.** When a broker replies to a clarification email, thread it back to the same load and re-extract. This reuses the memory concepts from Atlas Day 10.
4. **Multi-step agent for document chasing.** After delivery, an agent that checks whether a POD arrived and drafts a follow up if not. This is the multi-agent and tool-use work from Atlas applied to the back office.

You have built the core. These are the layers that would turn it into something close to the real product.

---

You now have a working, hostable, genuinely impressive project that maps directly onto what Augment does, built on the agent fundamentals you already learned. Run it locally first, get it green, then host it and put the link in front of Cherice.
