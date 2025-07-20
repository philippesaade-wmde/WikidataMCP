import requests

from .utils import WikidataEntity
from . import utils


async def get_wikidata_items_similar_to(
    query: str, x_api_key: str, type: str = "item", resolve_labels: bool = False
) -> list[WikidataEntity]:
    """
    Get Wikidata items similar to a query.

    The returned Wikidata items will contain their english labels and descriptions if `resolve_labels` is `True`.
    """

    id_name = "QID" if type == "item" else "PID"

    response = requests.get(
        f"https://wd-vectordb.toolforge.org/{type}/query/?query={query}&k=10",
        headers={
            "x-api-secret": x_api_key,
            "User-Agent": "Wikidata MCP Client",
        },
    )

    vectordb_result: list[dict[str, str]] = response.json()
    # print(vectordb_result)

    if not resolve_labels:
        return list(
            map(
                lambda x: WikidataEntity(
                    id=x[id_name],
                    label="",
                    description="",
                    claims=[],
                ),
                vectordb_result,
            )
        )
    else:
        ids = [x[id_name] for x in vectordb_result]
        labels_descriptions = await utils.get_entities_labels_and_descriptions(ids)

        return list(
            map(
                lambda x: WikidataEntity(
                    id=x[id_name],
                    label=labels_descriptions[x[id_name]].label,
                    description=labels_descriptions[x[id_name]].description,
                    claims=[],
                ),
                vectordb_result,
            )
        )


__all__ = [
    "get_wikidata_items_similar_to",
]
