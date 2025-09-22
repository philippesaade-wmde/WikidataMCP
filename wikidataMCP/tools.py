from fastmcp import FastMCP
from wikidataMCP import utils
import os

mcp = FastMCP("Wikidata MCP")

WD_VECTORDB_API_SECRET = os.environ.get("WD_VECTORDB_API_SECRET")
VECTOR_ENABLED = utils.vectorsearch_verify_apikey(WD_VECTORDB_API_SECRET)

# Enable vector search if the API key is set
if VECTOR_ENABLED:

    @mcp.tool()
    async def vector_search_items(query: str, lang: str = 'en') -> str:
        """Search Wikidata items (QIDs) using semantic search trained on question-answering.
        Find conceptually similar Wikidata items from a natural-language query. Matches are based on meaning, not exact words.

        Args:
            query: Natural-language description of the concept to find.
            lang: Language code for the search (default: 'en').

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
            WD_VECTORDB_API_SECRET,
            lang=lang
        )

        text_val = [
            f"{id}: {val['label']} — {val['description']}"
            for id, val in results.items()
        ]
        text_val = '\n'.join(text_val)
        return text_val


    @mcp.tool()
    async def vector_search_properties(query: str, lang: str = 'en') -> str:
        """Search Wikidata properties (PIDs) using semantic search trained on question-answering.
        Find relevant Wikidata properties from a natural-language description of the relationship you need. Matches are based on meaning, not exact words.

        Args:
            query: Natural-language description of the concept to find.
            lang: Language code for the search (default: 'en').

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
            WD_VECTORDB_API_SECRET,
            type="property",
            lang=lang
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
async def keyword_search_items(query: str, lang: str = 'en') -> str:
    """Search Wikidata items (QIDs) with exact text matching.
    Looks up items by label/alias or literal phrases expected to appear in Wikidata. Useful when you already know the entity you're looking for.

    Args:
        query: Label, alias, or phrase expected to appear verbatim.
        lang: Language code for the search (default: 'en').

    Returns:
        Newline-separated lines in the form:
        QID: label — description

    Example:
        >>> keyword_search_items("Douglas Adams")
        Q42: Douglas Adams — English science fiction writer and humorist
        Q28421831: Douglas Adams — American environmental engineer
    """

    results = await utils.keywordsearch(
        query,
        type="item",
        lang=lang
    )

    text_val = [
        f"{id}: {val['label']} — {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def keyword_search_properties(query: str, lang: str = 'en') -> str:
    """Search Wikidata properties (PIDs) with exact text matching.
    Looks up properties by label/alias or literal phrases expected to appear in Wikidata. Useful when expected property name is already known.

    Args:
        query: Label, alias, or phrase expected to appear verbatim.
        lang: Language code for the search (default: 'en').

    Returns:
        Newline-separated lines in the form:
          PID: label — description

    Example:
        >>> keyword_search_properties("residence")
        P551: residence — the place where the person is or has been, resident
        P276: location — location of the object, structure or event
    """

    results = await utils.keywordsearch(
        query,
        type="property",
        lang=lang
    )

    text_val = [
        f"{id}: {val['label']} — {val['description']}"
        for id, val in results.items()
    ]
    text_val = '\n'.join(text_val)
    return text_val


@mcp.tool()
async def get_entity_claims(entity_id: str,
                            include_external_ids: bool = False,
                            lang: str = 'en') -> str:
    """Return the direct statements (property-value pairs, with qualifiers) of an entity. Expose all direct graph connections of a Wikidata entity to inspect its factual context. This tool does not include deprecated values and references (use `get_claim_values` instead).

    Args:
        entity_id: A QID or PID such as "Q42" or "P31".
        include_external_ids: Whether to include external identifiers linking to other databases.
        lang: Language code for labels and descriptions (default: 'en').

    Returns:
        One statement per line in the form:
          Entity (QID): Property (PID): Value (item (QID) or literal) [ | Qualifier (PID): Value ... ]

    Example:
        >>> get_entity_claims("Q42")
        Douglas Adams (Q42): instance of (P31): human (Q5)
        Douglas Adams (Q42): occupation (P106): novelist (Q6625963) | start time (P580): 1979 AD)
    """

    result = await utils.get_entities_triplets(
        [entity_id],
        external_ids=include_external_ids,
        all_ranks=False,
        lang=lang
    )
    return result.get(entity_id, f"Entity {entity_id} not found")


@mcp.tool()
async def get_claim_values(entity_id: str,
                           property_id: str,
                           lang: str = 'en') -> str:
    """Get all values for a specific claim (entity-property pair), including all qualifiers, ranks and references. Returns complete claim information including deprecated values and reference data that are excluded from `get_entity_claims`.

    Args:
        entity_id: A QID or PID such as "Q42" or "P31".
        property_id: A PID such as "P31".
        lang: Language code for labels and descriptions (default: 'en').

    Returns:
        Complete claim details with hierarchical structure showing:
          Entity (QID): Property (PID): Value (QID or literal)
          Rank: preferred/normal/deprecated
          Qualifier:
            - qualifier_property (PID): qualifier_value
          Reference N:
            - reference_property (PID): reference_value

    Example:
        >>> get_claim_values("Q42", "P106")
        Douglas Adams (Q42): occupation (P106): novelist (Q6625963)
          Rank: normal
          Qualifier:
            - start time (P580): 1979
          Reference 1:
            - stated in (P248): Who's Who (Q2567271)
            - Who's Who UK ID (P4789): U4994
    """

    result = await utils.get_triplet_values(
        [entity_id],
        pid=property_id,
        external_ids=True,
        references=True,
        all_ranks=True,
        lang=lang
    )

    entity = result.get(entity_id)
    if not entity:
        return f"Entity {entity_id} not found"

    claims = entity.get("claims")
    if not claims:
        return f"No statement found for {entity_id} with property {property_id}"

    output = ""
    for claim in claims:
        for claim_value in claim.get("values", []):
            if output:
                output += "\n"

            output += f"{entity['label']} ({entity_id}): "
            output += f"{claim['property_label']} ({property_id}): "
            output += f"{utils.stringify(claim_value['value'])}\n"

            output += f"  Rank: {claim_value.get('rank', 'normal')}\n"

            qualifiers = claim_value.get("qualifiers", [])
            if qualifiers:
                output += f"  Qualifier:\n"
                for qualifier in qualifiers:
                    output += f"    - {qualifier['property_label']} ({qualifier['PID']}): "
                    output += utils.stringify(qualifier)
                    output += "\n"

            references = claim_value.get("references", [])
            if references:
                i = 1
                for reference in references:
                    output += f"  Reference {i}:\n"
                    for reference_claim in reference:
                        output += f"    - {reference_claim['property_label']} ({reference_claim['PID']}): "
                        output += utils.stringify(reference_claim)
                        output += "\n"
                    i += 1

    return output.strip()


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


@mcp.prompt
def explore_wikidata(query: str) -> str:
    """Instruct the model to explore Wikidata without assumptions."""

    return f"""
    You are an assistant that explores Wikidata on behalf of the user.
    The user's request is: '{query}'.

    IMPORTANT: All QIDs (items) and PIDs (properties) are randomly shuffled, so you cannot rely on any prior knowledge of Wikidata identifiers or schema. The only way to retrieve information is by using the provided tools.

    Follow this step-by-step workflow:
    1. **Identify Candidate Items**
        - If the query is a name or title, start with a keyword search.
        - If the query is a concept or description, start with a vector search.
        - Collect a few top candidate QIDs and PIDs to examine.

    2. **Inspect Entity Structure**
        - Retrieve entity claims for several representative QIDs.
        - Identify which PIDs represent the key relationship(s) you care about.
        - Look for patterns across multiple items (which properties repeat, how values are modeled).

    3. **Refine Understanding with Claim Details**
        - When qualifiers, deprecated values, or references matter, retrieve claim values for a specific entity and property pair.
        - If the retrieved claims already answer the user's request, stop here and present the results.

    4. **Write and Test SPARQL**
        - Construct and execute a SPARQL query using the discovered QIDs & PIDs.
        - Inspect the returned rows for missing or incorrect values, unexpected types, or empty columns.
        - If the results are not as expected, iteratively refine the SPARQL query and repeat until the results are satisfactory.
    """