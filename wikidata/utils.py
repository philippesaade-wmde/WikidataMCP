from urllib.parse import urlencode
import requests
import pandas as pd
import re

async def keywordsearch(query: str,
                        type: str = "item",
                        limit: int = 10
                        ) -> list:
    """
    Searches for Wikidata items or properties that match the input text.

    Args:
        query (str): The text to search for in Wikidata items or properties.
        type (str, optional): Type of entity to search for, either "item" or "property". Defaults to "item".
        limit (int, optional): Maximum number of results to return. Defaults to 10.

    Returns:
        list: A list of dictionaries representing the matching Wikidata items or properties, each containing "id", "label", and "description".
    """
    response = requests.get(
        "https://www.wikidata.org/w/api.php?"
        "action=wbsearchentities&"
        f"type={type}&"
        f"search={query}&"
        f"limit={limit}&"
        "language=en&"
        "format=json&"
        "origin=*",
        headers={"User-Agent": "Wikidata MCP Client"},
    )
    response.raise_for_status()

    response_dict_search = response.json().get("search", {})

    item_dict = {
        x["id"]:
        {
            "label": x.get("display", {})\
                        .get("label", {})\
                        .get("value", ""),
            "description": x.get("display", {})\
                            .get("description", {})\
                            .get("value", ""),
        }
        for x in response_dict_search
    }
    return item_dict


async def vectorsearch_verify_apikey(x_api_key: str) -> list:
    """
    Verifies if the provided API key is valid for vector search.

    Args:
        x_api_key (str): API key for accessing the vector database.

    Returns:
        bool: True if the API key is valid, False otherwise.
    """
    if not x_api_key:
        return False

    response = requests.get(
        f"https://wd-vectordb.toolforge.org/item/query/?query=",
        headers={
            "x-api-secret": x_api_key,
            "User-Agent": "Wikidata MCP Client",
        },
    )
    return response.status_code != 401

async def vectorsearch(query: str,
                       x_api_key: str,
                       type: str = "item",
                       limit: int = 10
                       ) -> list:
    """
    Searches for Wikidata items or properties similar to the input text using a vector database.

    Args:
        query (str): The text to search for in Wikidata items or properties.
        x_api_key (str): API key for accessing the vector database.
        type (str, optional): Type of entity to search for, either "item" or "property". Defaults to "item".
        limit (int, optional): Maximum number of results to return. Defaults to 10.

    Returns:
        list: A list of dictionaries representing the matching Wikidata items or properties, each containing "id", "label", and "description".
    """

    id_name = "QID" if type == "item" else "PID"

    response = requests.get(
        f"https://wd-vectordb.toolforge.org/{type}/query/?query={query}&k={limit}",
        headers={
            "x-api-secret": x_api_key,
            "User-Agent": "Wikidata MCP Client",
        },
    )
    response.raise_for_status()

    vectordb_result = response.json()

    ids = [x[id_name] for x in vectordb_result]
    entities_dict = await get_entities_labels_and_descriptions(ids)
    return entities_dict

async def execute_sparql(sparql_query: str,
                         K: int = 10
                         ) -> pd.DataFrame:
    """
    Execute a SPARQL query on Wikidata.

    You may assume the following prefixes:
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX p: <http://www.wikidata.org/prop/>
    PREFIX ps: <http://www.wikidata.org/prop/statement/>

    Args:
        sparql_query (str): The SPARQL query to execute.

    Returns:
        pandas.DataFrame: A cleaned dataframe of the results.
    """
    url = "https://query.wikidata.org/sparql"
    params = urlencode({"query": sparql_query, "format": "json"})
    encoded_url = url + "?" + params
    result = requests.get(encoded_url)
    if result.status_code == 400:
        error_message = result.text.split("	at ")[0]
        raise ValueError(error_message)
    result.raise_for_status()

    result_bindings = result.json()["results"]["bindings"]
    df = pd.json_normalize(result_bindings)

    value_cols = {c: c.split(".")[0]
                  for c in df.columns if c.endswith(".value")
                  }
    df = df[list(value_cols)].rename(columns=value_cols)


    def shorten(val: str) -> str:
        URI_RE = re.compile(r"http://www\.wikidata\.org/entity/([A-Z]\d+)$")
        match = URI_RE.match(val)
        return match.group(1) if match else val

    df = df.applymap(shorten)
    df = df.head(K)
    return df


async def get_entities_labels_and_descriptions(ids) -> dict:
    """
    Fetches labels and descriptions for a list of Wikidata entity IDs.

    Args:
        ids (list[str]): List of Wikidata entity IDs (QIDs or PIDs).

    Returns:
        dict: A dictionary mapping entity IDs to WikidataEntity objects with labels and descriptions.
    """
    if not ids:
        return {}

    response = requests.get(
        "https://www.wikidata.org/w/api.php?"
        "action=wbgetentities&"
        f"ids={'|'.join(ids)}&"
        "props=labels|descriptions&"
        "languages=en&"
        "format=json&"
        "origin=*",
        headers={"User-Agent": "Wikidata MCP Client"},
    )
    response.raise_for_status()
    entities_data = response.json().get("entities", {})

    entities_dict = {
        id:
        {
            "label": val['labels']\
                        .get('en', val.get('mul', {}))\
                        .get('value', ''),
            "description": val['descriptions']\
                            .get('en', val.get('mul', {}))\
                            .get('value', '')
        }
        for id, val in entities_data.items()
    }
    return entities_dict


async def get_entities_triplets(ids: list[str]) -> dict:
    """
    Fetches triplet representations for claims of a list of Wikidata entity IDs.

    Args:
        ids (list[str]): A list of Wikidata entity IDs to fetch triplet data for.

    Returns:
        dict: A dictionary where keys are entity IDs and values are their RDF triplet representations as strings.
    """
    if not ids:
        return {}

    info = {}
    for id in ids:
        response = requests.get(
            "https://wd-textify.toolforge.org?"
            f"id={id}&"
            "external_ids=False&"
            "format=triplet&"
            "lang=en",
            headers={"User-Agent": "Wikidata MCP Client"},
        )
        response.raise_for_status()
        info[id] = response.json()

    return info


__all__ = [
    "keywordsearch",
    "vectorsearch",
    "execute_sparql"
    "get_entities_labels_and_descriptions",
    "get_entities_triplets",
]
