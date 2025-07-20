import requests
from datetime import date, datetime
from dataclasses import dataclass
import pandas as pd
import re
from urllib.parse import urlencode
from enum import Enum


class WikidataClaimRank(Enum):
    NORMAL = 1
    PREFERRED = 2
    DEPRECATED = 3


@dataclass
class WikidataQualifier:
    property: "WikidataEntity"
    valueEntity: "WikidataEntity | None"
    valueString: str

    def __str__(self):
        s = ""
        s += (
            f"{self.property.label} ({self.property.id}) "
            if len(self.property.label) > 0
            else f"{self.property.id} "
        )

        if self.valueEntity:
            s += (
                f"{self.valueEntity.label} ({self.valueEntity.id})"
                if len(self.valueEntity.label) > 0
                else f"{self.valueEntity.id}"
            )
        else:
            s += f"{self.valueString}"

        return s


@dataclass
class WikidataClaim:
    subject: "WikidataEntity"
    property: "WikidataEntity"
    valueEntity: "WikidataEntity | None"
    valueString: str
    rank: WikidataClaimRank = WikidataClaimRank.NORMAL
    qualifiers: list[WikidataQualifier] | None = None

    def __str__(self):
        s = ""

        if self.rank == WikidataClaimRank.DEPRECATED:
            s += "(deprecated) "
        elif self.rank == WikidataClaimRank.PREFERRED:
            s += "(preferred) "

        s += (
            f"{self.subject.label} ({self.subject.id}) "
            if len(self.subject.label) > 0
            else f"{self.subject.id} "
        )
        s += (
            f"{self.property.label} ({self.property.id}): "
            if len(self.property.label) > 0
            else f"{self.property.id}: "
        )

        if self.valueEntity:
            s += (
                f"{self.valueEntity.label} ({self.valueEntity.id})"
                if len(self.valueEntity.label) > 0
                else f"{self.valueEntity.id}"
            )
        else:
            s += f"{self.valueString}"

        if self.qualifiers:
            for qualifier in self.qualifiers:
                s += f", {qualifier}"

        return s


@dataclass
class WikidataEntity:
    id: str
    label: str
    description: str
    claims: list[WikidataClaim]

    def __init__(self, id, label, description, claims=[]):
        self.id = id
        self.label = label
        self.description = description
        self.claims = claims

    def __str__(self):
        s = f"{self.id}"
        if len(self.label):
            s += f": {self.label}"
        if len(self.description):
            s += f" ({self.description})"
        for claim in self.claims:
            s += f"\n{claim}"
        return s


async def search_entity(
    query: str, type: str = "item", limit: int = 7
) -> dict[str, WikidataEntity]:
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
    mapped = map(
        lambda x: WikidataEntity(
            id=x["id"],
            label=x.get("display", {}).get("label", {}).get("value", ""),
            description=x.get("display", {}).get("description", {}).get("value", ""),
        ),
        response_dict_search,
    )
    mapped_dict = {i.id: i for i in mapped}
    return mapped_dict


async def get_entities_labels_and_descriptions(
    entity_ids: list[str],
) -> dict[str, WikidataEntity]:
    if not entity_ids:
        raise ValueError("No entity IDs provided")

    MAX_ENTITIES_PER_REQUEST = 50

    remaining_ids = entity_ids
    result_list: dict[str, WikidataEntity] = {}

    while len(remaining_ids) > 0:
        this_request_ids = remaining_ids[:MAX_ENTITIES_PER_REQUEST]
        remaining_ids = remaining_ids[MAX_ENTITIES_PER_REQUEST:]
        ids_param = "|".join(list(set(this_request_ids)))  # Ensure unique IDs
        response = requests.get(
            "https://www.wikidata.org/w/api.php?"
            "action=wbgetentities&"
            "props=labels|descriptions&"
            f"ids={ids_param}&"
            f"languages=en|mul&"
            "format=json&"
            "origin=*",
            headers={"User-Agent": "Wikidata MCP Client"},
        )
        response.raise_for_status()
        entities_data = response.json().get("entities", {})
        if len(entities_data) == 0:
            raise ValueError("No entity resolved")

        for entity_id, entity_info in entities_data.items():
            entity = WikidataEntity(id=entity_id, label=entity_id, description="")
            result_list[entity_id] = entity

            if "labels" in entity_info:
                label_obj = entity_info["labels"].get("en")
                if label_obj is None:
                    label_obj = entity_info["labels"].get("mul")
                if label_obj and isinstance(label_obj, dict) and "value" in label_obj:
                    entity.label = label_obj["value"]

            if "descriptions" in entity_info:
                desc_obj = entity_info["descriptions"].get("en")
                if desc_obj is None:
                    desc_obj = entity_info["descriptions"].get("mul")
                if desc_obj and isinstance(desc_obj, dict) and "value" in desc_obj:
                    entity.description = desc_obj["value"]

    return result_list


async def _parse_snak_value(datatype, value, entities) -> WikidataEntity | str:
    if value is None:
        return '<empty string>'

    if (datatype in ["wikibase-property", "wikibase-item"]):
        value_id = value.get("id")
        if value_id not in entities:
            value_entity = WikidataEntity(
                id=value_id,
                label="UNRESOLVED",
                description="UNRESOLVED",
            )
            entities[value_id] = value_entity
        else:
            value_entity = entities[value_id]

        return value_entity

    elif datatype == "string":
        return str(value)

    elif datatype == "monolingualtext":
        return f"{value.get('text', '<empty string>')} (language: {value.get('language', '')})"

    elif datatype == "quantity":
        try:
            return await _quantity_to_text(value)
        except ValueError:
            return value["time"]

    elif datatype == "time":
        try:
            return _time_to_text(value)
        except ValueError:
            return value["time"]

    elif datatype in \
        ['wikibase-sense', 'wikibase-lexeme', 'wikibase-form', 'entity-schema']:
        return value.get("id", '<empty string>')

    elif datatype == 'globe-coordinate':
        try:
            return _globalcoordinate_to_text(value)
        except ValueError:
            return f"{value}"

    else:
        return f"{value}"


def _get_or_create_unresolved_entity(
    entity_id: str, entities_to_resolve: dict[str, WikidataEntity]
) -> WikidataEntity:
    if entity_id not in entities_to_resolve:
        entity = WikidataEntity(
            id=entity_id,
            label="UNRESOLVED",
            description="UNRESOLVED",
        )
        entities_to_resolve[entity_id] = entity
    else:
        entity = entities_to_resolve[entity_id]
    return entity


async def _parse_qualifiers(
    qualifiers_data: dict, entities: dict[str, WikidataEntity]
) -> list[WikidataQualifier]:
    parsed_qualifiers: list[WikidataQualifier] = []
    for (
        qualifier_prop_id,
        qualifier_statement_group,
    ) in qualifiers_data.items():
        for qualifier_statement_data in qualifier_statement_group:
            qualifier_property_entity = _get_or_create_unresolved_entity(
                qualifier_prop_id, entities
            )

            qualifier = WikidataQualifier(
                property=qualifier_property_entity,
                valueEntity=None,
                valueString="",
            )

            datavalue = qualifier_statement_data.get("datavalue", {})
            datatype = qualifier_statement_data.get("datatype")
            value = datavalue.get("value")

            resolved_qualifier_value = await _parse_snak_value(
                datatype, value, entities
            )
            if isinstance(resolved_qualifier_value, WikidataEntity):
                qualifier.valueEntity = resolved_qualifier_value
            else:
                qualifier.valueString = str(resolved_qualifier_value)

            parsed_qualifiers.append(qualifier)
    return parsed_qualifiers


async def _parse_claim(
    statement_data: dict,
    subject_entity: WikidataEntity,
    property_entity: WikidataEntity,
    entities: dict[str, WikidataEntity],
) -> WikidataClaim:
    claim = WikidataClaim(
        subject=subject_entity,
        property=property_entity,
        valueEntity=None,
        valueString="",
    )

    rank = statement_data.get("rank", None)
    if rank == "deprecated":
        claim.rank = WikidataClaimRank.DEPRECATED
    elif rank == "preferred":
        claim.rank = WikidataClaimRank.PREFERRED

    mainsnak = statement_data.get("mainsnak", {})
    mainsnak_datavalue = mainsnak.get("datavalue", {})
    mainsnak_value = mainsnak_datavalue.get("value")
    mainsnak_datatype = mainsnak.get("datatype")

    resolved_claim_value = await _parse_snak_value(
        mainsnak_datatype, mainsnak_value, entities
    )
    if isinstance(resolved_claim_value, WikidataEntity):
        claim.valueEntity = resolved_claim_value
    else:
        claim.valueString = str(resolved_claim_value)

    qualifiers_data = statement_data.get("qualifiers", {})
    if qualifiers_data:
        claim.qualifiers = await _parse_qualifiers(qualifiers_data, entities)

    return claim


async def _parse_entity(
    current_subject_entity_with_claims: WikidataEntity,
    raw_entity_item_data: dict,
    all_entities_being_resolved: dict[str, WikidataEntity],
) -> None:
    """
    Parses claims for a single entity from raw API data and populates the
    current_subject_entity_with_claims object.
    """
    statement_groups = raw_entity_item_data.get("claims", {})

    for prop_id, statement_group_data in statement_groups.items():
        property_entity = _get_or_create_unresolved_entity(
            prop_id, all_entities_being_resolved
        )
        for statement_data in statement_group_data:
            claim = await _parse_claim(
                statement_data,
                current_subject_entity_with_claims,  # This is the subject entity
                property_entity,
                all_entities_being_resolved,
            )
            current_subject_entity_with_claims.claims.append(claim)

def _time_to_text(time_data):
    """
    Converts Wikidata time data into a human-readable string.

    Parameters:
    - time_data (dict): A dictionary containing the time string, precision, and calendar model.

    Returns:
    - str: A textual representation of the time with appropriate granularity.
    """
    if time_data is None:
        return None

    time_value = time_data['time']
    precision = time_data['precision']
    calendarmodel = time_data.get('calendarmodel', 'http://www.wikidata.org/entity/Q1985786')

    # Use regex to parse the time string
    pattern = r'([+-])(\d{1,16})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z'
    match = re.match(pattern, time_value)

    if not match:
        raise ValueError("Malformed time string")

    sign, year_str, month_str, day_str, hour_str, minute_str, second_str = match.groups()
    year = int(year_str) * (1 if sign == '+' else -1)

    # Convert Julian to Gregorian if necessary
    if 'Q1985786' in calendarmodel and year > 1 and len(str(abs(year))) <= 4:  # Julian calendar
        try:
            month = 1 if month_str == '00' else int(month_str)
            day = 1 if day_str == '00' else int(day_str)
            julian_date = date(year, month, day)
            gregorian_ordinal = julian_date.toordinal() + (datetime(1582, 10, 15).toordinal() - datetime(1582, 10, 5).toordinal())
            gregorian_date = date.fromordinal(gregorian_ordinal)
            year, month, day = gregorian_date.year, gregorian_date.month, gregorian_date.day
        except ValueError:
            raise ValueError("Invalid date for Julian calendar")
    else:
        month = int(month_str) if month_str != '00' else 1
        day = int(day_str) if day_str != '00' else 1

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month_str = months[month - 1] if month != 0 else ''
    era = 'AD' if year > 0 else 'BC'

    if precision == 14:
        return f"{year} {month_str} {day} {hour_str}:{minute_str}:{second_str}"
    elif precision == 13:
        return f"{year} {month_str} {day} {hour_str}:{minute_str}"
    elif precision == 12:
        return f"{year} {month_str} {day} {hour_str}:00"
    elif precision == 11:
        return f"{day} {month_str} {year}"
    elif precision == 10:
        return f"{month_str} {year}"
    elif precision == 9:
        return f"{abs(year)} {era}"
    elif precision == 8:
        decade = (year // 10) * 10
        return f"{abs(decade)}s {era}"
    elif precision == 7:
        century = (abs(year) - 1) // 100 + 1
        return f"{century}th century {era}"
    elif precision == 6:
        millennium = (abs(year) - 1) // 1000 + 1
        return f"{millennium}th millennium {era}"
    elif precision == 5:
        tens_of_thousands = abs(year) // 10000
        return f"{tens_of_thousands} ten thousand years {era}"
    elif precision == 4:
        hundreds_of_thousands = abs(year) // 100000
        return f"{hundreds_of_thousands} hundred thousand years {era}"
    elif precision == 3:
        millions = abs(year) // 1000000
        return f"{millions} million years {era}"
    elif precision == 2:
        tens_of_millions = abs(year) // 10000000
        return f"{tens_of_millions} tens of millions of years {era}"
    elif precision == 1:
        hundreds_of_millions = abs(year) // 100000000
        return f"{hundreds_of_millions} hundred million years {era}"
    elif precision == 0:
        billions = abs(year) // 1000000000
        return f"{billions} billion years {era}"
    else:
        raise ValueError(f"Unknown precision value {precision}")

async def _quantity_to_text(value):
    """
    Converts Wikidata quantity data into a human-readable string.

    Parameters:
    - value (dict): A dictionary with 'amount' and optionally 'unit' (often a QID).

    Returns:
    - str: A textual representation of the quantity (e.g., "5 kg").
    """
    quantity_string = str(value["amount"]).replace("+", "")
    unit_url = value["unit"]

    match = re.search(
        r"http://www\.wikidata\.org/entity/(Q\d+)",
        unit_url,
    )
    if match:
        unit_entity_id = match.group(1)
        # TODO: optimize, cache?
        unit_entity_result = await get_entities_labels_and_descriptions(
            [unit_entity_id]
        )
        unit_entity = unit_entity_result[unit_entity_id]
        unit_string = f"{unit_entity.label} ({unit_entity})"
        quantity_string += " " + unit_string
    return quantity_string

def _globalcoordinate_to_text(coor_data):
        """
        Convert a single decimal degree value to DMS with hemisphere suffix.
        `hemi_pair` is ("N", "S") for latitude or ("E", "W") for longitude.
        """

        latitude = abs(coor_data['latitude'])
        hemi = 'N' if coor_data['latitude'] >= 0 else 'S'

        degrees = int(latitude)
        minutes_full = (latitude - degrees) * 60
        minutes = int(minutes_full)
        seconds = (minutes_full - minutes) * 60

        # Round to-tenth of a second, drop trailing .0
        seconds = round(seconds, 1)
        seconds_str = f"{seconds}".rstrip("0").rstrip(".")

        lat_str = f"{degrees}°{minutes}'{seconds_str}\"{hemi}"

        longitude = abs(coor_data['longitude'])
        hemi = 'E' if coor_data['longitude'] >= 0 else 'W'

        degrees = int(longitude)
        minutes_full = (longitude - degrees) * 60
        minutes = int(minutes_full)
        seconds = (minutes_full - minutes) * 60

        # Round to-tenth of a second, drop trailing .0
        seconds = round(seconds, 1)
        seconds_str = f"{seconds}".rstrip("0").rstrip(".")

        lon_str = f"{degrees}°{minutes}'{seconds_str}\"{hemi}"

        return f'{lat_str}, {lon_str}'

async def get_entities_with_claims(entity_ids: list[str]) -> dict[str, WikidataEntity]:
    if not entity_ids:
        return {}

    response = requests.get(
        "https://www.wikidata.org/w/api.php?"
        "action=wbgetentities&"
        "props=claims&"
        f"ids={'|'.join(entity_ids)}&"
        "format=json&"
        "origin=*",
        headers={"User-Agent": "Wikidata MCP Client"},
    )
    response.raise_for_status()
    raw_api_data = response.json()

    result_entities_with_claims: dict[str, WikidataEntity] = {}
    entities: dict[str, WikidataEntity] = {}

    # Initialize result entities
    for entity_id in entity_ids:
        entity_placeholder = WikidataEntity(
            id=entity_id,
            label="UNRESOLVED",
            description="UNRESOLVED",
            claims=[],
        )
        result_entities_with_claims[entity_id] = entity_placeholder
        entities[entity_id] = entity_placeholder

    raw_entities_data = raw_api_data.get("entities", {})

    for entity_id in entity_ids:
        current_subject_entity_with_claims = result_entities_with_claims[entity_id]
        raw_entity_item_data = raw_entities_data.get(entity_id, {})
        await _parse_entity(
            current_subject_entity_with_claims,
            raw_entity_item_data,
            entities,
        )

    # Resolve labels and descriptions for all collected entities
    if entities:
        resolved_label_data = await get_entities_labels_and_descriptions(
            list(entities.keys())
        )
        for entity_id_key, resolved_entity_data in resolved_label_data.items():
            entity_obj_to_update = entities[entity_id_key]
            entity_obj_to_update.label = resolved_entity_data.label
            entity_obj_to_update.description = resolved_entity_data.description

    return result_entities_with_claims


async def execute_sparql(sparql_query: str, K: int = 10) -> pd.DataFrame:
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
        str: The JSON-formatted result of the SPARQL query execution. If there are no results, an empty JSON object will be returned.
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

    df = df.iloc[:K]
    return df


__all__ = [
    "search_entity",
    "get_entities_labels_and_descriptions",
    "get_entities_with_claims",
    "execute_sparql",
    "WikidataEntity",
    "WikidataClaim",
    "WikidataClaimRank",
    "WikidataQualifier",
]
