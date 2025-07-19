from fastmcp import FastMCP
from wikidata import utils
from wikidata import vectordb
import os

x_api_key = os.environ.get("WD_VECTORDB_API_SECRET")
if x_api_key is None:
    raise ValueError("WD_VECTORDB_API_SECRET env variable not set")


mcp = FastMCP("FastMCP Server for wd-vectordb 🚀")


@mcp.tool()
async def vector_search_items(query: str) -> str:
    """
    Performs a semantic search over Wikidata items using a multilingual vector embedding model.
    Returns a list of items relevant to the input text, each with label, description, and QID.

    Use this as your **first step** to:
    - Interpret the user’s question.
    - Discover relevant entities even if names aren't exactly known.
    - Find example QIDs to analyze with `get_entity`.

    Assume the results are relevant unless proven otherwise. Always explore them before querying.
    """

    result = await vectordb.get_wikidata_items_similar_to(
        query,
        x_api_key,
        resolve_labels=True,
    )

    json_representations = map(lambda r: str(r), result)
    concatenated = "\n".join(json_representations)
    return concatenated


@mcp.tool()
async def keyword_search_items(query: str) -> str:
    """
    Searches Wikidata items by matching their labels and descriptions with the given text.
    Returns possible candidates with labels and descriptions.

    Use this when:
    - You need to confirm or find a known QID.
    - The entity name is highly specific.
    - You are verifying a result from vector search.

    Do not rely on this for open-ended exploration. Prefer semantic search first.
    """

    result = await utils.search_entity(query, type="item")
    result_values = result.values()
    result_strings = map(lambda r: str(r), result_values)
    concatenated = "\n".join(result_strings)
    return concatenated


@mcp.tool()
async def keyword_search_properties(query: str) -> str:
    """
    Searches for Wikidata properties (PIDs) that match the input text.
    Returns property labels, descriptions, and IDs.

    Use this to:
    - Discover properties to use in SPARQL queries.
    - Map natural language relationships (e.g. “occupation”, “birthplace”) to their PID.

    Validate property usage by inspecting actual entities with `get_entity`.
    """

    result = await utils.search_entity(query, type="property")
    result_values = result.values()
    result_strings = map(lambda r: str(r), result_values)
    concatenated = "\n".join(result_strings)
    return concatenated


@mcp.tool()
async def get_wikidata_entity(entity_id: str) -> str:
    """
    Retrieves all statements (claims) for a given QID or PID.
    Returns property-value pairs that define how the item is structured.

    Use this to:
    - Understand how an entity is connected in the graph.
    - Identify which PIDs are actually used and how.
    - Induce property combinations from example QIDs returned by vector search.

    Always do this before writing SPARQL.
    """

    result = await utils.get_entities_with_claims([entity_id])
    return str(result[entity_id])


@mcp.tool()
async def execute_sparql(sparql: str) -> str:
    """
    Executes a SPARQL query and returns the top results or an error message.

    Only use this after:
    - Retrieving example QIDs using semantic search.
    - Inspecting those QIDs with `get_entity`.
    - Discovering properties via `keyword_search_properties`.

    You must always validate your SPARQL query here before returning it to the user.
    If the query fails or returns no results, revise it based on prior tools.
    """

    try:
        result = await utils.execute_sparql(sparql)
    except ValueError as e:
        return str(e)
    return result.to_string()


if __name__ == "__main__":
    mcp.run()
