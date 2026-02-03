# Graph Layer Plan (Working Document)

Status: draft  
Owner: team  
Scope: add a graph index to improve relation‑type queries and support future GraphRAG.

---

## 0) Why a Graph (Critical Summary)

**What a graph can add**
- Relationship retrieval: “who is related to X”, “what depends on Y”, “A causes B”.
- Structure‑aware answers: connects entities across documents/sections.
- Better recall for queries that are about **links**, not just content.

**What a graph will NOT fix**
- General Q&A quality for non‑relational questions.
- Hallucinations from the LLM (that’s still a generation problem).
- Poor chunking/ingest quality.

**Key risks**
- Graph extraction quality (NER/errors) may reduce trust.
- Maintenance cost: additional storage, ingestion time, monitoring.
- Hard to evaluate without a dedicated “relation” test set.

Conclusion: a graph is justified only if we target relation‑style questions and can measure impact.

---

## 1) Definitions (Keep Scope Tight)

We use two distinct concepts:

1. **Knowledge Graph (KG)**  
   Nodes + edges stored in Neo4j (or similar).  
   Used to retrieve related entities/sections.

2. **GraphRAG**  
   Retrieval pipeline that expands through the graph and returns text chunks.

**Phase 1 = Knowledge Graph MVP**  
**Phase 2+ = GraphRAG (optional)**

---

## 2) MVP Goals (Phase 1)

Deliverable: minimal KG that improves relation‑type queries without breaking current system.

### MVP success criteria
- Can answer relation‑style questions better than baseline RAG.
- Adds < 20% ingestion time overhead for typical KB sizes.
- Graph retrieval is optional and does not impact normal queries.

---

## 3) Phase Plan

### Phase 1 — KG MVP (Neo4j)
**Goal:** add a graph index with basic entity mentions and relations.

**Nodes**
- Document
- Section (or chunk)
- Entity (Person, Org, Place, Topic)

**Edges**
- `MENTIONS`: (Section -> Entity)
- `IN_DOC`: (Section -> Document)
- `CO_OCCURS`: (Entity <-> Entity) within a window/section

**Extraction**
- Start with NER (spaCy or LLM) + simple co‑occurrence.
- Link back to `document_id` and `chunk_id` for retrieval.

**Usage**
- Query graph when user question contains entities.
- Pull related sections/chunks → feed into RAG as extra context.

**Evaluation**
- Create a small “relation” QA set (20–50 questions).
- Compare: baseline vs graph‑augmented (Recall + No‑answer).

---

### Phase 2 — Graph Retrieval Integration (GraphRAG Lite)
**Goal:** integrate graph‑expanded candidates into retrieval pipeline.

**Steps**
- Use graph expansion to fetch top related sections.
- Merge with vector/BM25 results using weighted fusion.
- Track source provenance (graph vs dense vs bm25).

**Evaluation**
- Compare overall metrics: Recall + No‑answer + “recommended score”.

---

### Phase 3 — Advanced Graph (Optional)
**Possible upgrades**
- Typed relations (causes, supports, contradicts).
- Event extraction.
- Argumentation chains.
- Graph‑based reranking.

This phase is only worth it if Phase 1–2 show clear gains.

---

## 4) Technical Architecture

### Containers
- Add `neo4j` container in `docker-compose.yml`.

### Services
- `graph_indexer`: build graph from chunks on ingest.
- `graph_retriever`: query graph and return relevant chunk IDs.

### Data Flow
1. Ingest → chunk text  
2. Extract entities & relations  
3. Store in Neo4j  
4. On query → graph lookup → chunk IDs → merge into retrieval

---

## 5) API & Settings

**New KB settings**
- `use_graph`: boolean
- `graph_max_nodes`: int (limit to avoid noise)
- `graph_max_depth`: int

**New endpoints (draft)**
- `POST /api/v1/graph/index` (rebuild graph for KB)
- `GET /api/v1/graph/query?kb_id=...&q=...`

---

## 6) Evaluation Plan

1. Build a “relation” QA set (manual or synthetic).
2. Baseline: dense/hybrid only.
3. Graph‑augmented: compare metrics.
4. Decide keep / iterate / rollback.

---

## 7) Open Questions

- Which entity extractor? (spaCy vs LLM)
- How to store section granularity? (chunk vs section vs heading)
- How to avoid noisy co‑occurrence edges?
- What volume is acceptable for Neo4j in our deployments?

---

## 8) Immediate Next Actions

1. Confirm MVP scope (Phase 1 only).
2. Decide extraction method (spaCy or LLM).
3. Add Neo4j container + connection config.
4. Build indexer and query API.
5. Create relation QA test set.

---

## 9) Decision Log

| Date | Decision | Notes |
|------|----------|-------|
| 2026-02-03 | Keep Graph work in phases (KG MVP → GraphRAG) | Avoid scope creep, measure impact early. |
