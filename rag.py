"""
The RAG retrieval layer for Dispatch.

This embeds the knowledge base once at startup, then for any query embeds the
query and returns the most semantically similar knowledge chunks. It includes
the production-safety pieces that the concept doc describes:

- A similarity threshold, so irrelevant chunks are dropped rather than fed to
  the model. If nothing clears the bar, we return nothing and let the caller
  say it has no relevant knowledge.
- Returned similarity scores, so retrieval is debuggable and traceable.

We use Anthropic's API for the LLM elsewhere, but Anthropic does not currently
offer an embeddings endpoint, so for embeddings we use a small local approach:
we ask Voyage AI style embeddings via a simple hashing-based fallback if no
embedding provider is configured. To keep this dependency-free and always
runnable, the default uses a deterministic local embedding so the whole RAG
pipeline works offline. If you set an embedding provider later, you swap one
function.

The local embedding is not as good as a real model, but it demonstrates the
full RAG mechanism, retrieval by vector similarity with a threshold, and the
concepts and code structure are identical to production. The teaching note in
concept-rag.md explains the real failure modes either way.
"""

import math
import re

from knowledge import all_knowledge


# ---- Embedding -------------------------------------------------------------
# A deterministic local embedding so the whole pipeline runs with no extra
# services. It maps text to a fixed-length vector based on word hashing. This
# is a "bag of hashed words" embedding. It captures word overlap, which is
# enough to demonstrate retrieval. In production you replace embed_text with a
# call to a real embedding model (Voyage, OpenAI, Cohere) and nothing else
# changes.

EMBED_DIM = 256


def embed_text(text):
    """
    Turn text into a fixed-length vector.

    Local deterministic embedding: lowercase, split into words, hash each word
    into one of EMBED_DIM buckets, and count. Then L2 normalize so cosine
    similarity behaves. This rewards shared vocabulary between query and chunk.

    To use a real embedding model in production, replace the body of this
    function with a call to that model's embeddings endpoint. The rest of the
    RAG code is unchanged.
    """
    vec = [0.0] * EMBED_DIM
    words = re.findall(r"[a-z0-9]+", text.lower())
    for w in words:
        bucket = hash(w) % EMBED_DIM
        vec[bucket] += 1.0

    # L2 normalize so cosine similarity is just the dot product.
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec


def cosine_similarity(a, b):
    """Cosine similarity of two equal-length vectors. Both are L2 normalized,
    so this is just the dot product."""
    return sum(x * y for x, y in zip(a, b))


# ---- Index -----------------------------------------------------------------
# Embed the knowledge base once at import. Each indexed entry keeps its text,
# category, id, and precomputed vector.

_index = []


def build_index():
    global _index
    _index = []
    for entry in all_knowledge():
        _index.append({
            "id": entry["id"],
            "category": entry["category"],
            "text": entry["text"],
            "vector": embed_text(entry["text"]),
        })


build_index()


# ---- Retrieval -------------------------------------------------------------

# Only return chunks at least this similar to the query. Below this, a chunk is
# treated as irrelevant and dropped. This is the single most important RAG
# safety knob: it prevents feeding the model garbage chunks when nothing in the
# knowledge base actually matches.
SIMILARITY_THRESHOLD = 0.15


def retrieve(query, top_k=3, threshold=SIMILARITY_THRESHOLD):
    """
    Retrieve the most relevant knowledge chunks for a query.

    Returns a list of dicts: {id, category, text, score}, highest score first,
    only including chunks above the similarity threshold. If nothing clears the
    threshold, returns an empty list, and the caller should treat that as "no
    relevant knowledge found" rather than forcing an answer.
    """
    if not query or not query.strip():
        return []

    query_vec = embed_text(query)

    scored = []
    for entry in _index:
        score = cosine_similarity(query_vec, entry["vector"])
        scored.append({
            "id": entry["id"],
            "category": entry["category"],
            "text": entry["text"],
            "score": round(score, 4),
        })

    # Sort by score descending, keep only those above threshold, take top_k.
    scored.sort(key=lambda x: x["score"], reverse=True)
    relevant = [s for s in scored if s["score"] >= threshold]
    return relevant[:top_k]


def format_context(chunks):
    """
    Turn retrieved chunks into a context string for the prompt. Each chunk is
    labeled with its id so the model can cite which knowledge it used, which is
    one of the anti-hallucination techniques from the concept doc.
    """
    if not chunks:
        return "No relevant knowledge was found in the knowledge base."
    parts = []
    for c in chunks:
        parts.append(f"[{c['id']}] {c['text']}")
    return "\n\n".join(parts)
