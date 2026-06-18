// The knowledge base browser. Shows every document the RAG layer can retrieve,
// grouped by category. This makes the RAG layer visible: you can see exactly
// what knowledge the agent has access to.

const CATEGORY_LABELS = {
  carrier_profile: "Carrier Profiles",
  lane_pricing: "Lane Pricing",
  customer_sop: "Customer SOPs",
  freight_policy: "Freight Policy",
};

export default function KnowledgeView({ knowledge }) {
  const categories = {};
  for (const k of knowledge) {
    if (!categories[k.category]) categories[k.category] = [];
    categories[k.category].push(k);
  }

  return (
    <section className="knowledge">
      <p className="knowledge-intro">
        These documents power the RAG layer. When the agent processes a load it
        retrieves the most semantically relevant entries and grounds its
        assessment in them.
      </p>
      {Object.keys(categories).map((cat) => (
        <div key={cat} className="knowledge-group">
          <h3>{CATEGORY_LABELS[cat] || cat}</h3>
          {categories[cat].map((k) => (
            <div key={k.id} className="knowledge-card">
              <div className="knowledge-id">{k.id}</div>
              <div className="knowledge-text">{k.text}</div>
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
