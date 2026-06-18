# RAG, In Depth

Retrieval Augmented Generation. This doc teaches the concept the way an interviewer probes it: what it is, why it works, every way it fails, and what you do about each failure. By the end you can answer any RAG interview question.

---

## Part 1: What RAG is and why it exists

### The problem RAG solves

An LLM only knows what was in its training data. It does not know your company's carrier list, your lane pricing, your customer SOPs, or anything that happened after its training cutoff. If you ask Claude "what is our standard detention rate for Armstrong Transport," it cannot know. That information lives in your business, not in the model.

You have two options to give the model that knowledge:

1. **Fine-tuning.** Retrain the model on your data. Expensive, slow, has to be redone when data changes, and risks degrading the model's general ability. Wrong tool for facts that change.

2. **RAG.** Keep your knowledge in a searchable store. When a question comes in, retrieve the relevant pieces and put them in the prompt. The model answers using that retrieved context. Cheap, updates instantly when data changes, no retraining.

RAG is the right answer for "give the model access to a body of knowledge it can look things up in." Fine-tuning is for teaching the model new skills or styles, not new facts.

**The one-line definition:** RAG retrieves relevant documents from a knowledge base and adds them to the prompt so the model answers grounded in real, current information instead of only its training data.

### The core insight

The model is a reasoning engine, not a database. Stop trying to make it memorize facts. Instead, give it a way to look facts up at the moment it needs them, and let it reason over what it retrieves. That separation, reasoning in the model, facts in the retrieval layer, is the whole idea.

---

## Part 2: How RAG works, step by step

A RAG pipeline has two phases: indexing (done once, ahead of time) and retrieval (done per query).

### Indexing (ahead of time)

1. **Chunk.** Break your documents into pieces. A 50-page policy doc becomes dozens of chunks of a few hundred words each. You retrieve chunks, not whole documents, because you want the specific relevant passage, not the entire file.

2. **Embed.** Convert each chunk into a vector, a list of numbers that captures its meaning. An embedding model does this. Two chunks about the same topic produce vectors that are close together in vector space. This is the magic: meaning becomes geometry.

3. **Store.** Save the vectors in a vector store, along with the original text. The store is built to find vectors near a query vector quickly.

### Retrieval (per query)

4. **Embed the query.** The user's question becomes a vector using the same embedding model.

5. **Search.** Find the chunks whose vectors are closest to the query vector. Closeness in vector space means similarity in meaning. This is "semantic search": you find chunks that mean the same thing as the query, even if they share no exact words.

6. **Augment.** Put the retrieved chunks into the prompt as context. "Here is relevant information: [chunks]. Now answer this question: [query]."

7. **Generate.** The model answers using the retrieved context.

That is RAG. Retrieve relevant chunks by meaning, stuff them in the prompt, generate a grounded answer.

---

## Part 3: Embeddings, the heart of retrieval

An embedding is a vector, say 1536 numbers, that represents the meaning of a piece of text. The embedding model is trained so that texts with similar meaning get similar vectors.

"The carrier was late on delivery" and "the trucking company missed the delivery window" share almost no words, but a good embedding model gives them nearby vectors because they mean nearly the same thing. That is why semantic search beats keyword search: it matches meaning, not spelling.

**How similarity is measured:** usually cosine similarity, which measures the angle between two vectors. Vectors pointing the same direction (small angle) are similar. The result ranges from -1 (opposite) to 1 (identical meaning). You retrieve the chunks with the highest cosine similarity to the query.

**Interview question: "what is an embedding?"**
> An embedding is a vector representation of text where semantic similarity becomes geometric closeness. The embedding model is trained so texts with similar meaning produce nearby vectors. You measure closeness with cosine similarity. This lets you search by meaning rather than keywords, so a query retrieves relevant passages even when they share no exact words.

---

## Part 4: Chunking, the decision that quietly determines quality

Chunking is how you split documents before embedding. It is the most underrated decision in RAG, and bad chunking is the most common cause of bad retrieval.

### Why chunk size matters

**Chunks too large.** A chunk covering many topics produces a muddy embedding, an average of all those topics, that matches nothing well. You retrieve a big blob where only one sentence is relevant, wasting context and diluting the signal.

**Chunks too small.** A chunk that is one sentence loses surrounding context. "The rate is $2.40 per mile" is useless if the chunk does not say which lane or customer it refers to. You retrieve a fragment that is technically relevant but missing the context needed to use it.

**The goal:** each chunk should be one coherent idea, big enough to stand alone, small enough to be about one thing. A few hundred words is a common starting point, but it depends on your documents.

### Chunking strategies

- **Fixed size.** Split every N characters. Simple, but cuts mid-sentence and mid-idea. Crude.
- **By structure.** Split on natural boundaries: paragraphs, sections, headings. Respects the document's own organization. Usually better.
- **Overlapping.** Each chunk shares some text with its neighbors, so an idea that spans a boundary is not lost. Common refinement.

**Interview question: "how do you decide chunk size?"**
> Chunk size trades off context against precision. Too large and the embedding averages many topics and matches nothing well. Too small and the chunk loses the context needed to be useful. The goal is one coherent idea per chunk. I prefer splitting on natural structure like paragraphs or sections over fixed character counts, often with a little overlap so an idea spanning a boundary is not lost. And I tune it empirically by looking at what actually gets retrieved for real queries.

---

## Part 5: Why RAG fails, and what you do about each failure

This is the section interviewers care about most. Anyone can describe the happy path. Knowing the failure modes shows you have actually shipped RAG. There are five main ways RAG fails.

### Failure 1: Retrieval misses the relevant chunk

The most common failure. The answer is in your knowledge base, but retrieval did not surface it. The model then answers without the key fact, often by guessing.

**Why it happens:**
- The query and the relevant chunk are phrased very differently, so their embeddings are not close.
- Chunking split the relevant information across two chunks, so neither alone is a strong match.
- You retrieved too few chunks (top 3) and the right one ranked 4th.

**What you do:**
- **Retrieve more chunks** (top 5 or 10) and let the model sift. More recall at the cost of more context.
- **Hybrid search.** Combine semantic search with keyword search. Semantic catches meaning, keyword catches exact terms like part numbers or carrier names that embeddings sometimes blur.
- **Query rewriting.** Use the LLM to rephrase the query into a form more likely to match the documents before retrieving.
- **Better chunking.** Fix the upstream cause if information is being split badly.

### Failure 2: Retrieval returns irrelevant chunks

The opposite problem. Retrieval surfaces chunks that are not actually relevant, and they distract or mislead the model. The model may anchor on a plausible-looking but wrong chunk.

**Why it happens:**
- The knowledge base does not actually contain the answer, so the closest chunks are still not relevant. Retrieval always returns *something*, even when nothing fits.
- The query is vague, so many chunks look equally mediocre matches.

**What you do:**
- **A similarity threshold.** Only use chunks above a minimum similarity score. If nothing clears the bar, retrieve nothing and let the model say it does not know. This is critical. Without it, you always feed the model the closest chunks even when they are garbage.
- **Tell the model it may get irrelevant context.** Instruct it to ignore retrieved chunks that do not actually address the question, rather than forcing an answer from them.

### Failure 3: The model ignores the retrieved context

You retrieved the right chunk, but the model answered from its own training knowledge anyway, possibly contradicting the retrieved fact.

**Why it happens:**
- The prompt did not make clear the retrieved context is authoritative.
- The model has a strong prior belief that overrides the provided context.

**What you do:**
- **Explicit grounding instructions.** "Answer using only the provided context. If the context does not contain the answer, say so. Do not use outside knowledge." This is the single most important RAG prompt instruction.
- **Cite sources.** Ask the model to quote or reference which chunk it used. This forces it to actually read the context and makes it auditable.

### Failure 4: Hallucination despite retrieval

The model invents facts even with good context, or blends retrieved facts with made-up ones.

**Why it happens:**
- The context was incomplete, so the model filled gaps with plausible invention.
- The model was pushed to answer a question the context does not fully cover.

**What you do:**
- **Permission to say "I do not know."** Models hallucinate partly because they are implicitly pushed to always answer. Explicitly allowing "the information is not available" reduces invention dramatically.
- **Grounding with citations** (as above) makes invented facts obvious because they cannot be cited.
- **Lower the stakes of each answer.** Retrieve enough that the model rarely has to stretch.

### Failure 5: Stale or wrong knowledge

Retrieval works perfectly, but the underlying document is out of date or incorrect. The model faithfully reports a wrong fact.

**Why it happens:**
- The knowledge base was not updated when the business changed.
- A document had an error that nobody caught.

**What you do:**
- **Treat the knowledge base as a maintained asset.** It needs an update process, ownership, and versioning, like any production data.
- **Timestamp and source chunks.** Knowing when a fact was last updated and where it came from lets you judge and refresh it.
- This is an operational failure, not a technical one, and naming it as such in an interview shows maturity.

---

## Part 6: The RAG interview question bank

**"What is RAG and when would you use it over fine-tuning?"**
> RAG retrieves relevant documents and adds them to the prompt so the model answers grounded in current, specific information. Use RAG when you need to give the model access to a body of facts, especially facts that change, like company knowledge. Use fine-tuning to teach new skills, styles, or formats, not new facts. RAG updates instantly when data changes and needs no retraining; fine-tuning bakes knowledge in and has to be redone when data changes.

**"Walk me through a RAG pipeline."**
> Two phases. Indexing, done ahead of time: chunk the documents, embed each chunk into a vector, store the vectors with their text. Retrieval, per query: embed the query, find the chunks with the highest similarity, put them in the prompt as context, and generate a grounded answer. The model reasons; the retrieval layer supplies facts.

**"Your RAG system gives wrong answers. How do you debug it?"**
> I isolate which stage failed. First I check retrieval: for the failing query, did the right chunk get retrieved at all? If not, it is a retrieval problem, and I look at chunking, embedding quality, the number of chunks retrieved, or whether I need hybrid search. If the right chunk was retrieved but the answer is still wrong, it is a generation problem: the model ignored the context or hallucinated, and I fix it with stronger grounding instructions and citations. Separating retrieval failure from generation failure is the first move, because the fixes are completely different.

**"How do you stop a RAG system from hallucinating?"**
> Three things. Explicit grounding: instruct the model to answer only from the provided context and to say so when the answer is not there. Permission to not answer: models hallucinate partly because they are pushed to always produce an answer, so allowing "I do not know" reduces invention. And citations: asking the model to reference which chunk it used forces it to actually read the context and makes invented facts obvious because they cannot be cited.

**"What do you do when retrieval returns nothing relevant?"**
> Use a similarity threshold. Retrieval always returns its closest matches even when none are actually relevant, so I only pass chunks above a minimum similarity score. If nothing clears the bar, I pass no context and let the model say the information is not available, rather than feeding it garbage chunks it will try to answer from. Returning nothing is better than returning misleading context.

**"How do you evaluate a RAG system?"**
> On two axes, because there are two stages. Retrieval quality: for a set of test queries with known relevant documents, measure whether retrieval surfaces them, using recall and precision at K. Generation quality: given good retrieved context, does the model produce a correct, grounded answer, measured against reference answers and checked for faithfulness to the context. You evaluate the stages separately because a bad answer could come from bad retrieval or bad generation, and you need to know which.

**"What is chunking and why does it matter?"**
> Chunking is splitting documents before embedding. It quietly determines retrieval quality. Chunks too large produce muddy embeddings that match nothing well. Chunks too small lose the context that makes them useful. The goal is one coherent idea per chunk, split on natural structure like paragraphs, often with slight overlap so ideas spanning boundaries are not lost. It is the most common hidden cause of bad RAG.

---

## Part 7: How RAG shows up in Dispatch

In Dispatch v2, the knowledge base holds freight business knowledge: carrier reliability profiles, lane pricing benchmarks, customer SOPs, and freight policy. When the agent processes a load, it retrieves relevant knowledge before deciding. For a load from Armstrong Transport, it retrieves Armstrong's SOP. For a Dayton to Columbus lane, it retrieves that lane's pricing benchmark.

This is exactly how Augie "knows" a specific brokerage's way of working. The general model plus retrieved company-specific knowledge equals an assistant that behaves like it understands your business. The model supplies reasoning; the knowledge base supplies your facts.

You will see every failure mode handled in the code: a similarity threshold so irrelevant knowledge is dropped, grounding instructions so the agent uses retrieved context faithfully, and traceable retrieval so you can see exactly what was retrieved for any decision.
