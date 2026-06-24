"""Agent runtime used only by the local visual demo.

This intentionally lives beside the Flask app so the production script can stay
unchanged while the UI demonstrates running with and without tools.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

import requests
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv


DEFAULT_MODEL = "gpt-4.1-mini"
LOCATION_TOOL_NAME = "get_iss_location"
VISUALIZATION_TOOL_NAME = "visualize_iss_location"

logger = logging.getLogger("iss_mission_control_visual")


@dataclass(frozen=True)
class Settings:
    model: str
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

        return cls(
            model=os.getenv("OPENAI_MODEL") or DEFAULT_MODEL,
            timeout_seconds=float(os.getenv("ISS_HTTP_TIMEOUT", "15")),
        )


class ISSLocationClient:
    """Small client for the external APIs this agent depends on."""

    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def get_place_name(self, latitude: float, longitude: float) -> str:
        response = self.session.get(
            "https://api.bigdatacloud.net/data/reverse-geocode-client",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "localityLanguage": "en",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        place_parts = [
            data.get("locality") or data.get("city"),
            data.get("principalSubdivision"),
            data.get("countryName"),
        ]
        place_name = ", ".join(part for part in place_parts if part)
        return place_name or "an area with no nearby place name"

    def get_location(self) -> dict[str, Any]:
        response = self.session.get(
            "https://api.wheretheiss.at/v1/satellites/25544",
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        latitude = data["latitude"]
        longitude = data["longitude"]

        return {
            "place_name": self.get_place_name(latitude, longitude),
            "latitude": round(latitude, 2),
            "longitude": round(longitude, 2),
            "altitude_km": round(data["altitude"], 2),
            "velocity_km_per_hour": round(data["velocity"], 2),
        }


def configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def progress(message: str) -> None:
    print(f"[progress] {message}", file=sys.stderr, flush=True)


def emit_event(on_event: Callable[[dict[str, Any]], None] | None, event: dict[str, Any]) -> None:
    if on_event:
        on_event(event)


def map_url(latitude: float, longitude: float) -> str:
    span = 35
    min_lon = max(-180, longitude - span)
    min_lat = max(-85, latitude - span)
    max_lon = min(180, longitude + span)
    max_lat = min(85, latitude + span)
    return (
        "https://www.openstreetmap.org/export/embed.html"
        f"?bbox={min_lon}%2C{min_lat}%2C{max_lon}%2C{max_lat}"
        f"&layer=mapnik&marker={latitude}%2C{longitude}"
    )


def build_agent(
    settings: Settings,
    iss_client: ISSLocationClient,
    tools_enabled: bool,
    visualizations: list[dict[str, Any]],
    used_tools: list[str],
    on_event: Callable[[dict[str, Any]], None] | None,
) -> Agent:
    @function_tool
    def get_iss_location() -> dict:
        """Get the current place name, latitude, longitude, altitude, and speed of the International Space Station."""
        progress("Calling get_iss_location tool")
        logger.info("Fetching live ISS location")
        used_tools.append(LOCATION_TOOL_NAME)
        emit_event(
            on_event,
            {
                "type": "tool_start",
                "message": "Calling get_iss_location",
                "tool": LOCATION_TOOL_NAME,
            },
        )

        try:
            location = iss_client.get_location()
        except requests.RequestException as exc:
            logger.exception("ISS location lookup failed")
            raise RuntimeError("Could not fetch live ISS location data.") from exc

        logger.info("ISS location lookup succeeded")
        progress("ISS data received")
        emit_event(
            on_event,
            {
                "type": "tool_done",
                "message": "Live ISS data received",
                "tool": LOCATION_TOOL_NAME,
            },
        )
        return location

    @function_tool
    def visualize_iss_location() -> dict:
        """Create a map visualization for the current International Space Station location."""
        progress("Calling visualize_iss_location tool")
        logger.info("Creating live ISS map visualization")
        used_tools.append(VISUALIZATION_TOOL_NAME)
        emit_event(
            on_event,
            {
                "type": "tool_start",
                "message": "Calling visualize_iss_location",
                "tool": VISUALIZATION_TOOL_NAME,
            },
        )

        try:
            location = iss_client.get_location()
        except requests.RequestException as exc:
            logger.exception("ISS visualization lookup failed")
            raise RuntimeError("Could not fetch live ISS location data.") from exc

        visualization = {
            "title": "Current ISS position",
            "place_name": location["place_name"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "map_url": map_url(location["latitude"], location["longitude"]),
        }
        visualizations.append(visualization)
        progress("ISS visualization ready")
        emit_event(
            on_event,
            {
                "type": "tool_done",
                "message": "ISS map visualization ready",
                "tool": VISUALIZATION_TOOL_NAME,
            },
        )
        return visualization

    if tools_enabled:
        tool_instructions = (
            "You have access to get_iss_location and visualize_iss_location. "
            "Use get_iss_location before answering live ISS location questions. "
            "Use visualize_iss_location when the user asks to see, map, or visualize where the ISS is. "
            "Do not include raw map URLs in your final answer; the app renders maps separately. "
            "Do not ask follow-up questions or offer visuals at the end. "
            "If a visualization is useful, call the visualization tool directly instead of asking. "
        )
        tools = [get_iss_location, visualize_iss_location]
    else:
        tool_instructions = ""
        tools = []

    return Agent(
        name="ISS Mission Control",
        instructions=(
            "You are a concise mission-control communicator. "
            f"{tool_instructions}"
            "Make the update exciting but factual."
        ),
        model=settings.model,
        tools=tools,
    )


async def run_agent(
    task: str,
    tools_enabled: bool,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    settings = Settings.from_env()
    client = ISSLocationClient(timeout_seconds=settings.timeout_seconds)
    visualizations: list[dict[str, Any]] = []
    used_tools: list[str] = []
    emit_event(
        on_event,
        {
            "type": "run_start",
            "message": "Starting agent run",
            "tools_enabled": tools_enabled,
        },
    )
    agent = build_agent(
        settings,
        client,
        tools_enabled=tools_enabled,
        visualizations=visualizations,
        used_tools=used_tools,
        on_event=on_event,
    )
    emit_event(
        on_event,
        {
            "type": "model_start",
            "message": f"Sending task to {settings.model}",
            "model": settings.model,
        },
    )
    result = await Runner.run(agent, task)

    final_result = {
        "answer": result.final_output or "",
        "model": settings.model,
        "tools_enabled": tools_enabled,
        "available_tools": (
            [LOCATION_TOOL_NAME, VISUALIZATION_TOOL_NAME] if tools_enabled else []
        ),
        "used_tools": used_tools,
        "visualizations": visualizations,
    }
    emit_event(
        on_event,
        {
            "type": "run_done",
            "message": "Final answer ready",
            "result": final_result,
        },
    )
    return final_result
