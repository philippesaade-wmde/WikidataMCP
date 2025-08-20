from fastmcp import FastMCP
from wikidata import utils
import os

mcp = FastMCP("Wikidata MCP")

x_api_key = os.environ.get("WD_VECTORDB_API_SECRET")
VECTOR_ENABLED = utils.vectorsearch_verify_apikey(x_api_key)

# Enable vector search if the API key is set
if VECTOR_ENABLED:

    @mcp.tool()
    async def vector_search_items(query: str) -> str:
        """Search Wikidata items (QIDs) using semantic search trained on question-answering.
        Find conceptually similar Wikidata items from a natural-language query. Matches are based on meaning, not exact words.

        Args:
            query: Natural-language description of the concept to find.

        Returns:
            Newline-separated results in the form:
                QID: label — description

        Example:
            >>> vector_search_items("English science-fiction novel")
            Q23163: A Scientific Romance — 1997 novel by Ronald Wright
            Q627333: The Time Machine — 1895 dystopian science fiction novella by H. G. Wells
        """

        results = await utils.vectorsearch(
            query,
            x_api_key,
        )

        text_val = [
            f"{id}: {val['label']} — {val['description']}"
            for id, val in results.items()
        ]
        text_val = '\n'.join(text_val)
        return text_val


    @mcp.tool()
    async def vector_search_properties(query: str) -> str:
        """Search Wikidata properties (PIDs) using semantic search trained on question-answering.
        Find relevant Wikidata properties from a natural-language description of the relationship you need. Matches are based on meaning, not exact words.

        Args:
            query: Natural-language description of the concept to find.

        Returns:
            Newline-separated results in the form:
                PID: label — description

        Example:
            >>> vector_search_properties("residence of a person")
            P551: residence — the place where the person is or has been, resident
            P276: location — location of the object, structure or event
        """

        results = await utils.vectorsearch(
            query,
            x_api_key,
            type="property",
        )

        text_val = [
            f"{id}: {val['label']} — {val['description']}"
            for id, val in results.items()
        ]
        text_val = '\n'.join(text_val)
        return text_val

else:
    print(
        "WD_VECTORDB_API_SECRET not set: \
        vector search tools are not registered."
    )

@mcp.tool()
async def keyword_search_items(query: str) -> str:
    """Search Wikidata items (QIDs) with exact text matching.
    Looks up items by label/alias or literal phrases expected to appear in Wikidata. Useful when you already know the entity you're looking for.

    Args:
        query: Label, alias, or phrase expected to appear verbatim.

    Returns:
        Newline-separated lines in the form:
        QID: label — description

    Example:
        >>> keyword_search_items("Douglas Adams")
        Q42: Douglas Adams — English science fiction writer and humorist
        Q28421831: Douglas Adams — American environmental engineer
    """

    results = await utils.keywordsearch(query, type="item")

    text_val = [
        f"{id}: {val['label']} — {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def keyword_search_properties(query: str) -> str:
    """Search Wikidata properties (PIDs) with exact text matching.
    Looks up properties by label/alias or literal phrases expected to appear in Wikidata. Useful when expected property name is already known.

    Args:
        query: Label, alias, or phrase expected to appear verbatim.

    Returns:
        Newline-separated lines in the form:
          PID: label — description

    Example:
        >>> keyword_search_properties("residence")
        P551: residence — the place where the person is or has been, resident
        P276: location — location of the object, structure or event
    """

    results = await utils.keywordsearch(query, type="property")

    text_val = [
        f"{id}: {val['label']} — {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def get_entity_claims(entity_id: str) -> str:
    """Return the direct statements (property→value pairs, with qualifiers) for an entity.
    Expose all direct graph connections of a Wikidata entity to inspect its factual context.

    Args:
        entity_id: A QID or PID such as "Q42" or "P31".

    Returns:
        One statement per line in the form:
          Label (QID): Property (PID): Value (item (QID) or literal) [ | Qualifier (PID): Value ... ]

    Example:
        >>> get_entity_claims("Q42")
        Douglas Adams (Q42): instance of (P31): human (Q5)
        Douglas Adams (Q42): occupation (P106): novelist (Q6625963) | start time (P580): 1979 AD)
    """

    result = await utils.get_entities_triplets([entity_id])
    return result.get(entity_id, f"Entity {entity_id} not found")


@mcp.tool()
async def execute_sparql(sparql: str, K: int = 10) -> str:
    """Execute a SPARQL query against Wikidata and return up to K rows as CSV.

    Args:
        sparql: A valid SPARQL string.
        K: Maximum number of rows to return.

    Returns:
        CSV text (semicolon-separated) of the results with up to K rows. On error, returns the error message.

    Example:
        >>> execute_sparql("SELECT ?human WHERE { ?human wdt:P31 wd:Q5 } LIMIT 2")
        ;human
        0;Q42
        1;Q820
    """

    try:
        result = await utils.execute_sparql(sparql, K=K)
    except ValueError as e:
        return str(e)

    return result.to_csv(sep=';', index=True, header=True)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000, path='/mcp')
