# WikidataMCP
The **Wikidata MCP (Model Context Protocol)** provides a set of standardized tools that allow large language models (LLMs) to explore and query Wikidata programmatically. It is designed for agentic AI or AI workflows that need to search, inspect, and query Wikidata, without relying on hardcoded assumptions about its structure or content.

---

## 🧰 Tools
1. `vector_search_items(query: str) -> str`
Performs semantic search over Wikidata items using vector embeddings.
Returns a list of semantically similar QIDs with labels and descriptions.

**Use When**: Starting the exploration process with vague, conceptual, or open-ended queries.

2. `keyword_search_items(query: str) -> str`
Performs keyword search over Wikidata item labels, aliases, and descriptions.
Returns matching QIDs with their labels and descriptions.

**Use When**: You know the expected label or terminology used in a Wikidata item.

3. `vector_search_properties(query: str) -> str`
Performs semantic search over Wikidata properties using vector embeddings.
Returns a list of semantically similar PIDs with labels and descriptions.

**Use When**: You want to identify relevant properties for building claims or SPARQL queries.

5. `keyword_search_properties(query: str) -> str`
Performs keyword search over Wikidata property labels, aliases, and descriptions.
Returns matching PIDs with their labels and descriptions.

**Use When**: You know the expected label or terminology used in a Wikidata property.

5. `get_entity_claims(entity_id: str) -> str`
Returns all direct graph connections (statements) of a Wikidata entity in a triplet format, includes all claim values and their qualifiers.

**Use When**: You need to understand the structure of a Wikidata entity and how it connects to other items.

6. `get_claim_values(entity_id: str, property_id: str) -> str`
Get all values for a specific claim (entity-property pair), including all qualifiers, ranks and references. This is the only tool that gets references and values that are deprecated.

**Use When**: References or deprecated values are relevant, for example in fact-checking systems.

7. `execute_sparql(sparql: str) -> str`
Executes any valid SPARQL query against Wikidata and returns the results as a plain-text table.

**Use when**: You want to test, verify, or retrieve structured results based on conditions.

---

## 🌐 Services
### Vector Search

This service interfaces with the [Wikidata Vector Database](https://wd-vectordb.toolforge.org/), enabling semantic search over Wikidata items using natural language. It is ideal for discovering relevant items without needing to know exact labels. This serves as a first step in exploratory or context-rich workflows.

🚀 API: [wd-vectordb.toolforge.org](https://wd-vectordb.toolforge.org/) \
📚 Docs: [wd-vectordb.toolforge.org/docs](https://wd-vectordb.toolforge.org/docs) \
📄 Project Page: [Wikidata Embedding Project](https://www.wikidata.org/wiki/Wikidata:Embedding_Project)



### Wikidata Textifier

This service returns readable triplet or textual representations of Wikidata entities, with resolved lables, optimized for use by language models.

🚀 API: [wd-textify.toolforge.org](https://wd-textify.toolforge.org/) \
📚 Docs: [wd-textify.toolforge.org/docs](https://wd-textify.toolforge.org/docs)

---

## 📅 Future Updates
* **Hybrid Search**: The upcoming update of the vector search will integrate keyword search, eliminating the need for separate tools.
* **API Key Removal**: Future versions of the vector database will drop the requirement for an API key.
* **Get Entity Hierarchy Tool**: When writing a SPARQL query, users tend to explore the "instance of" and "subclass of" hierarchy of entities to understand what classification level to filter for. This new tool will output the full hierarchical path of an entity.
* **Property Example Tool**: Inspired by [SPINACH](https://spinach.genie.stanford.edu/), a new tool will provide examples of how specific properties are used in Wikidata.

