"""Kid-friendly space agent with ISS tools, NASA tools, guardrails, streaming, and tracing.

Run:
    python space_agent.py

Try:
    Where is the ISS right now?
    Show me the ISS on a map.
    Search NASA for Artemis news.
    Find Earthdata datasets about wildfires.

Type "goodbye", "bye", "quit", or "exit" when you are done.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any

import requests
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
    WebSearchTool,
    function_tool,
    gen_trace_id,
    handoff,
    input_guardrail,
    output_guardrail,
    trace,
)
from agents.stream_events import RawResponsesStreamEvent, RunItemStreamEvent
from agents.tool import WebSearchToolFilters
from dotenv import load_dotenv
from openai import APIError
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from pydantic import BaseModel


load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
NASA_MODEL = os.getenv("OPENAI_NASA_MODEL", "gpt-5.5")
TIMEOUT_SECONDS = int(os.getenv("SPACE_AGENT_TIMEOUT_SECONDS", "60"))
NASA_ALLOWED_DOMAINS = [
    "nasa.gov",
    "www.nasa.gov",
    "science.nasa.gov",
    "earthdata.nasa.gov",
    "earthobservatory.nasa.gov",
    "cmr.earthdata.nasa.gov",
]
CMR_SEARCH_URL = "https://cmr.earthdata.nasa.gov/search"
KMS_URL = "https://cmr.earthdata.nasa.gov/kms"

GOODBYE_WORDS = {"bye", "goodbye", "quit", "exit", "see you", "see ya"}
CAPABILITY_QUESTIONS = {
    "what can you do",
    "what can you do?",
    "help",
    "what do you do",
    "what do you do?",
    "who are you",
    "who are you?",
}


class TopicCheck(BaseModel):
    is_space_related: bool
    reason: str


class KidToneCheck(BaseModel):
    kid_friendly: bool
    reason: str


topic_guardrail_agent = Agent(
    name="Space Topic Guardrail",
    instructions=(
        "Decide if the user's message is about space, astronomy, NASA, Earth science from space, "
        "rockets, planets, stars, astronauts, satellites, the ISS, or space exploration. "
        "Allow questions about what this space agent can do, because the answer should describe "
        "space, NASA, and ISS capabilities. "
        "Small talk is allowed only when it keeps the space conversation going. "
        "Goodbye messages are allowed. Block unrelated homework, recipes, sports, games, gossip, "
        "or general internet searches that are not about space."
    ),
    model=MODEL,
    output_type=TopicCheck,
)


kid_tone_guardrail_agent = Agent(
    name="Kid Tone Output Guardrail",
    instructions=(
        "Check whether the answer is appropriate for children: clear, friendly, exciting, safe, "
        "not scary or graphic, and not too technical. It may include real facts and numbers, "
        "but should explain them simply. Mark kid_friendly false if the answer is confusing, "
        "too adult, mean, unsafe, or unrelated to space. Capability-list answers are okay when "
        "they describe space, NASA, Earthdata, maps, or ISS features."
    ),
    model=MODEL,
    output_type=KidToneCheck,
)


@input_guardrail
async def only_space_topics(_ctx: Any, _agent: Agent, user_input: str) -> GuardrailFunctionOutput:
    """Block non-space conversations before the triage agent runs."""
    result = await Runner.run(topic_guardrail_agent, user_input)
    check = result.final_output
    return GuardrailFunctionOutput(
        output_info={"reason": check.reason},
        tripwire_triggered=not check.is_space_related,
    )


@output_guardrail
async def kid_friendly_output(ctx: Any, _agent: Agent, agent_output: str) -> GuardrailFunctionOutput:
    """Block answers that do not sound safe and exciting for kids."""
    user_input = " ".join(str(item) for item in ctx.turn_input)
    task = f"User asked:\n{user_input}\n\nAgent answered:\n{agent_output}"
    result = await Runner.run(kid_tone_guardrail_agent, task)
    check = result.final_output
    return GuardrailFunctionOutput(
        output_info={"reason": check.reason},
        tripwire_triggered=not check.kid_friendly,
    )


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": "kid-space-agent/1.0"},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _place_name(latitude: float, longitude: float) -> str:
    data = _get_json(
        "https://api.bigdatacloud.net/data/reverse-geocode-client",
        {
            "latitude": latitude,
            "longitude": longitude,
            "localityLanguage": "en",
        },
    )
    place_parts = [
        data.get("locality") or data.get("city"),
        data.get("principalSubdivision"),
        data.get("countryName"),
    ]
    return ", ".join(part for part in place_parts if part) or "open ocean or a remote area"


def _fetch_iss_location() -> dict[str, Any]:
    data = _get_json("https://api.wheretheiss.at/v1/satellites/25544")
    latitude = float(data["latitude"])
    longitude = float(data["longitude"])
    return {
        "place_name": _place_name(latitude, longitude),
        "latitude": round(latitude, 2),
        "longitude": round(longitude, 2),
        "altitude_km": round(float(data["altitude"]), 2),
        "velocity_km_per_hour": round(float(data["velocity"]), 2),
        "timestamp_utc": datetime.utcfromtimestamp(int(data["timestamp"])).isoformat() + "Z",
    }


@function_tool
def get_iss_location() -> dict[str, Any]:
    """Get the ISS current latitude, longitude, altitude, velocity, nearby place name, and timestamp."""
    return _fetch_iss_location()


@function_tool
def find_location_by_name(place_name: str) -> dict[str, Any]:
    """Look up an Earth place by name and return its latitude, longitude, and display name."""
    data = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place_name, "format": "json", "limit": 1},
        headers={"User-Agent": "kid-space-agent/1.0"},
        timeout=TIMEOUT_SECONDS,
    )
    data.raise_for_status()
    matches = data.json()
    if not matches:
        return {
            "found": False,
            "message": f"I could not find a place named {place_name!r}. Try a city, country, ocean, or landmark.",
        }

    match = matches[0]
    return {
        "found": True,
        "display_name": match["display_name"],
        "latitude": round(float(match["lat"]), 4),
        "longitude": round(float(match["lon"]), 4),
    }


@function_tool
def visualize_location(latitude: float, longitude: float, label: str = "Space spot") -> dict[str, str]:
    """Create map links for a latitude and longitude so the user can visualize the location."""
    zoom = 4
    marker = f"mlat={latitude}&mlon={longitude}"
    openstreetmap = f"https://www.openstreetmap.org/?{marker}#map={zoom}/{latitude}/{longitude}"
    google_maps = f"https://www.google.com/maps?q={latitude},{longitude}"
    return {
        "label": label,
        "openstreetmap_url": openstreetmap,
        "google_maps_url": google_maps,
        "kid_tip": "Open either map link to see the spot on Earth. The ISS moves fast, so refresh for a new position!",
    }


nasa_web_search = WebSearchTool(
    search_context_size="low",
    filters=WebSearchToolFilters(allowed_domains=NASA_ALLOWED_DOMAINS),
)


@function_tool
def get_earthdata_keywords(query: str, scheme: str | None = None, limit: int = 8) -> dict[str, Any]:
    """Search NASA KMS for official Earthdata science keywords and vocabulary."""
    safe_limit = max(1, min(limit, 20))
    if scheme:
        url = f"{KMS_URL}/concepts/concept_scheme/{scheme}/pattern/{query}"
    else:
        url = f"{KMS_URL}/concepts/pattern/{query}"

    data = _get_json(url, {"format": "json"})
    keywords = []
    for concept in data.get("concepts", [])[:safe_limit]:
        definitions = concept.get("definitions") or []
        definition = definitions[0].get("text") if definitions and isinstance(definitions[0], dict) else None
        keywords.append(
            {
                "uuid": concept.get("uuid"),
                "prefLabel": concept.get("prefLabel"),
                "scheme": concept.get("scheme", {}).get("name"),
                "definition": definition,
            }
        )

    return {
        "source": "NASA Keyword Management System",
        "query": query,
        "total_hits": data.get("hits", len(keywords)),
        "keywords": keywords,
    }


@function_tool
def search_earthdata_collections(keyword: str, limit: int = 5, has_granules: bool = True) -> dict[str, Any]:
    """Search NASA CMR Earthdata collections by keyword."""
    safe_limit = max(1, min(limit, 10))
    data = _get_json(
        f"{CMR_SEARCH_URL}/collections.json",
        {
            "keyword": keyword,
            "page_size": safe_limit,
            "has_granules": str(has_granules).lower(),
        },
    )
    entries = data.get("feed", {}).get("entry", [])
    collections = []
    for entry in entries:
        collections.append(
            {
                "title": entry.get("title"),
                "short_name": entry.get("short_name"),
                "concept_id": entry.get("id"),
                "version_id": entry.get("version_id"),
                "provider": entry.get("data_center"),
                "summary": entry.get("summary"),
                "time_start": entry.get("time_start"),
                "time_end": entry.get("time_end"),
                "cloud_hosted": entry.get("cloud_hosted"),
            }
        )
    return {
        "source": "NASA Common Metadata Repository",
        "keyword": keyword,
        "collections": collections,
    }


@function_tool
def search_earthdata_granules(collection_concept_id: str, limit: int = 5) -> dict[str, Any]:
    """Search NASA CMR granules/files for a known collection concept ID."""
    safe_limit = max(1, min(limit, 10))
    data = _get_json(
        f"{CMR_SEARCH_URL}/granules.json",
        {
            "collection_concept_id": collection_concept_id,
            "page_size": safe_limit,
        },
    )
    entries = data.get("feed", {}).get("entry", [])
    granules = []
    for entry in entries:
        links = [link.get("href") for link in entry.get("links", []) if link.get("href")]
        granules.append(
            {
                "title": entry.get("title"),
                "granule_id": entry.get("id"),
                "producer_granule_id": entry.get("producer_granule_id"),
                "time_start": entry.get("time_start"),
                "time_end": entry.get("time_end"),
                "links": links[:5],
            }
        )
    return {
        "source": "NASA Common Metadata Repository",
        "collection_concept_id": collection_concept_id,
        "granules": granules,
    }


ISS_INSTRUCTIONS = (
    "You are Orbit Owl, a friendly ISS guide for kids. "
    "Answer only space-related questions. "
    "Use get_iss_location for live ISS latitude, longitude, altitude, velocity, or nearby place questions. "
    "Use find_location_by_name when the user asks where a named Earth place is. "
    "Use visualize_location when the user asks to see, map, visualize, or get a link for a location. "
    "If visualizing the ISS, call get_iss_location first, then visualize_location with those coordinates. "
    "Use simple words, short paragraphs, and excitement, but stay factual."
)

NASA_NEWS_INSTRUCTIONS = (
    "You are Comet Scout, a friendly NASA guide for kids. "
    "Answer only space, NASA, astronomy, Earth science from space, and space exploration questions. "
    "Use web search for NASA news or NASA page lookups, but only NASA domains are allowed. "
    "Do not cite or rely on non-NASA websites. "
    "Keep answers easy for kids: bright, curious, and clear."
)

NASA_EARTHDATA_INSTRUCTIONS = (
    "You are Terra Scout, a friendly NASA Earthdata guide for kids. "
    "Answer only space, NASA, astronomy, Earth science from space, and space exploration questions. "
    "Use the direct NASA Earthdata tools for Earth science dataset discovery. Follow Discover, Verify, Access: "
    "use get_earthdata_keywords for broad everyday words, search_earthdata_collections to find datasets, "
    "and search_earthdata_granules to verify actual data files for a collection before explaining access simply. "
    "When the user asks for NASA or Earthdata keywords, vocabulary terms, search labels, or science words, "
    "use get_earthdata_keywords instead of inventing a list yourself. "
    "Use web search only if the user also needs a NASA page lookup, and only NASA domains are allowed. "
    "Do not cite or rely on non-NASA websites. "
    "Keep answers easy for kids: bright, curious, and clear."
)

TRIAGE_INSTRUCTIONS = (
    "You are Starbase Triage, the front desk for a kid-friendly space agent. "
    "Keep the conversation going until the user says goodbye. "
    "Route live ISS, map, coordinates, altitude, speed, and place lookup questions to the ISS agent. "
    "Route NASA news, missions, and NASA web search questions to the NASA news agent. "
    "Route Earthdata, Earth science dataset, keyword, vocabulary, search label, granule, collection, citation, "
    "variable, service, or data-access questions to the NASA Earthdata agent. "
    "If a question is general space trivia and does not need tools, answer briefly yourself. "
    "If the user says goodbye, give a warm short goodbye and stop inviting another question. "
    "Every answer must be space-related, kid-appropriate, easy to understand, and exciting."
)


iss_agent = Agent(
    name="ISS Agent",
    handoff_description="Use for live ISS location, latitude, longitude, altitude, velocity, maps, and Earth place lookups.",
    instructions=ISS_INSTRUCTIONS,
    model=MODEL,
    tools=[get_iss_location, find_location_by_name, visualize_location],
    output_guardrails=[kid_friendly_output],
)

nasa_news_agent = Agent(
    name="NASA News Agent",
    handoff_description="Use for NASA news, missions, and NASA-only web search.",
    instructions=NASA_NEWS_INSTRUCTIONS,
    model=NASA_MODEL,
    tools=[nasa_web_search],
    output_guardrails=[kid_friendly_output],
)

nasa_earthdata_agent = Agent(
    name="NASA Earthdata Agent",
    handoff_description="Use for NASA Earthdata dataset, collection, granule, variable, service, and data-access questions.",
    instructions=NASA_EARTHDATA_INSTRUCTIONS,
    model=NASA_MODEL,
    tools=[nasa_web_search, get_earthdata_keywords, search_earthdata_collections, search_earthdata_granules],
    output_guardrails=[kid_friendly_output],
)

triage_agent = Agent(
    name="Space Triage Agent",
    instructions=TRIAGE_INSTRUCTIONS,
    model=MODEL,
    handoffs=[
        handoff(iss_agent, tool_name_override="transfer_to_iss_agent"),
        handoff(nasa_news_agent, tool_name_override="transfer_to_nasa_news_agent"),
        handoff(nasa_earthdata_agent, tool_name_override="transfer_to_nasa_earthdata_agent"),
    ],
    input_guardrails=[only_space_topics],
    output_guardrails=[kid_friendly_output],
)


def _is_goodbye(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in GOODBYE_WORDS


def _guardrail_safe_input(text: str) -> str:
    """Add space context to common meta questions that are otherwise ambiguous."""
    normalized = text.strip().lower()
    if normalized in CAPABILITY_QUESTIONS:
        return (
            "The user asked what this kid-friendly space agent can do. "
            "Answer with the agent's space-only capabilities: ISS live location, maps, "
            "NASA information, NASA-only web search, Earthdata dataset discovery, and space Q&A."
        )
    if "keyword" in normalized and ("nasa" in normalized or "earthdata" in normalized):
        return (
            f"{text}\n\n"
            "Routing note: The user is asking for official NASA Earthdata science keywords or vocabulary. "
            "Use get_earthdata_keywords through the NASA Earthdata Agent."
        )
    return text


def _print_tool_event(event: RunItemStreamEvent, tool_names_by_call_id: dict[str, str]) -> None:
    item = event.item
    if item.type == "tool_call_item":
        tool_name = getattr(item, "tool_name", "tool")
        tool_names_by_call_id[item.call_id] = tool_name
        print(f"\n[tool: {tool_name}]", flush=True)
    elif item.type == "tool_call_output_item":
        tool_name = tool_names_by_call_id.get(item.call_id, "tool")
        print(f"[done: {tool_name}]\n", flush=True)
    elif item.type == "handoff_call_item":
        print("\n[mission control is routing your question...]\n", flush=True)
    elif item.type == "handoff_output_item":
        agent_name = getattr(item.target_agent, "name", "specialist")
        print(f"[now talking with {agent_name}]\n", flush=True)


async def run_streamed_turn(user_input: str, session: SQLiteSession) -> None:
    trace_id = gen_trace_id()
    print(f"\nTrace: https://platform.openai.com/traces/{trace_id}")
    print("Agent: ", end="", flush=True)

    with trace(
        "Kid Space Agent",
        trace_id=trace_id,
        metadata={"audience": "kids", "topic": "space"},
    ):
        result = Runner.run_streamed(triage_agent, user_input, session=session, max_turns=12)
        tool_names_by_call_id: dict[str, str] = {}

        async for event in result.stream_events():
            if isinstance(event, RawResponsesStreamEvent):
                if isinstance(event.data, ResponseTextDeltaEvent):
                    print(event.data.delta, end="", flush=True)
            elif isinstance(event, RunItemStreamEvent):
                _print_tool_event(event, tool_names_by_call_id)

    print()


async def chat() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file before running the agent.")

    session = SQLiteSession("kid-space-agent", os.getenv("SPACE_AGENT_SESSION_DB", ":memory:"))

    print("Kid Space Agent")
    print("Ask me about space, NASA, Earthdata, or the ISS. I will keep chatting until you say goodbye.")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except EOFError:
            print("\nAgent: Goodbye, space explorer! Keep looking up.")
            break
        if not user_input:
            continue

        if _is_goodbye(user_input):
            print("\nAgent: Goodbye, space explorer! Keep looking up.")
            break

        try:
            await run_streamed_turn(_guardrail_safe_input(user_input), session)
        except InputGuardrailTripwireTriggered:
            print(
                "\nAgent: I can only chat about space here. Try asking about planets, rockets, NASA, "
                "Earth from space, or where the ISS is right now!"
            )
        except OutputGuardrailTripwireTriggered:
            print(
                "\nAgent: I caught an answer that was not quite kid-ready, so I stopped it. "
                "Ask again and I will make it clearer and more space-tastic."
            )
        except APIError as exc:
            print(
                "\nAgent: A space data service had a launch-pad wobble, so I could not finish that turn. "
                "Try a NASA news question, an ISS location question, or ask again in a moment."
            )
            print(f"[debug: {exc}]")


if __name__ == "__main__":
    asyncio.run(chat())
