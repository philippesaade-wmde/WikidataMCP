from fastmcp import FastMCP
from wikidata import utils
import os

x_api_key = os.environ.get("WD_VECTORDB_API_SECRET")
if x_api_key is None:
    pass
    # raise ValueError("WD_VECTORDB_API_SECRET env variable not set")


mcp = FastMCP("Wikidata MCP")


@mcp.tool()
async def vector_search_items(query: str) -> str:
    """Search Wikidata items (QIDs) using semantic vector similarity.

    Args:
        query: Natural-language text describing the concept to find.

    Returns:
        New-line-separated results in the form
            QID: label, description

    Example:
        >>> vector_search_items("English science-fiction novel")
        Q23163: A Scientific Romance, 1997 novel by Ronald Wright
        Q627333: The Time Machine, 1895 dystopian science fiction novella by H. G. Wells
    """

    results = await utils.vectorsearch(
        query,
        x_api_key,
    )

    text_val = [
        f"{id}: {val['label']}, {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def keyword_search_items(query: str) -> str:
    """Search Wikidata items (QIDs) by keyword match.

    Args:
        query: Label, alias, or phrase expected to exist verbatim in Wikidata.

    Returns:
        New-line-separated results in the form
            QID: label, description

    Example:
        >>> keyword_search_items("Douglas Adams")
        Q42: Douglas Adams, English science fiction writer and humorist
        Q28421831: Douglas Adams, American environmental engineer
    """

    results = await utils.keywordsearch(query, type="item")

    text_val = [
        f"{id}: {val['label']}, {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def keyword_search_properties(query: str) -> str:
    """Search Wikidata properties (PIDs) by keyword match.

    Args:
        query: Keyword describing the property (e.g., "occupation", "founded").

    Returns:
        New-line-separated results in the form
            PID: label, description

    Example:
        >>> keyword_search_properties("residence")
        P551: residence, the place where the person is or has been, resident
        P276: location, location of the object, structure or event
    """

    results = await utils.keywordsearch(query, type="property")

    text_val = [
        f"{id}: {val['label']}, {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def get_wikidata_entity(entity_id: str) -> str:
    """Expose all direct graph connections (list of statements) of a Wikidata entity.

    Args:
        entity_id: A QID or PID such as "Q42" or "P31".

    Returns:
        Claims encoded line-by-line as:
            Label (QID): Property (PID): Value [ | Qualifier (PID): Value ... ]
        If the entity is missing, returns
            "Entity <ID> not found".

    Example:
        >>> get_wikidata_entity("Q42")
        Douglas Adams (Q42): instance of (P31): human (Q5)
        Douglas Adams (Q42): occupation (P106): novelist (Q6625963) | start time (P580): 1979 AD)
    """

    result = await utils.get_entities_triplets([entity_id])
    return result.get(entity_id, f"Entity {entity_id} not found")


@mcp.tool()
async def execute_sparql(sparql: str) -> str:
    """Execute a SPARQL query against Wikidata.

    Args:
        sparql: A valid SPARQL string.

    Returns:
        Plain-text table of query results, identical to the `.to_string()`
        output of pandas. On error, returns the error message.

    Example:
        >>> execute_sparql("SELECT ?human WHERE { ?human wdt:P31 wd:Q5 } LIMIT 2")
        ?human
        Q42
        Q820
    """

    try:
        result = await utils.execute_sparql(sparql)
    except ValueError as e:
        return str(e)

    return result.to_string()


if __name__ == "__main__":
    import sys
    print("Using HTTP transport on 0.0.0.0:8000", file=sys.stderr)
    mcp.run(transport="http", host="0.0.0.0", port=8000, path='/mcp')
