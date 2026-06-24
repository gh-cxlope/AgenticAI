"""Production-style ISS Mission Control agent.

Run from the repo root:

    python ISS/iss_mission_control_production.py

Optional:

    python ISS/iss_mission_control_production.py "Where is the ISS right now?"
    python ISS/iss_mission_control_production.py --no-stream

Requires:

    pip install openai-agents python-dotenv requests

Create a .env file with:

    OPENAI_API_KEY=your-key-here
    OPENAI_MODEL=gpt-4.1-mini
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

import requests  # pip install requests
from agents import Agent, Runner, function_tool # pip install openai-agents
from dotenv import load_dotenv  # pip install python-dotenv
from openai.types.responses import ResponseTextDeltaEvent  # pip install openai-agents


DEFAULT_TASK = (
    "Where is the International Space Station right now? "
)

logger = logging.getLogger("iss_mission_control")


@dataclass(frozen=True)
class Settings:
    model: str
    timeout_seconds: float

    @classmethod
    def from_env(cls, model_override: str | None = None) -> "Settings":
        load_dotenv()

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

        return cls(
            model=model_override or os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
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
    """Send operational progress to stderr so stdout can stay user-facing."""
    print(f"[progress] {message}", file=sys.stderr, flush=True)


def build_agent(settings: Settings, iss_client: ISSLocationClient) -> Agent:
    @function_tool
    def get_iss_location() -> dict:
        """Get the current place name, latitude, longitude, altitude, and speed of the International Space Station."""
        progress("Calling get_iss_location tool")
        logger.info("Fetching live ISS location")

        try:
            location = iss_client.get_location()
        except requests.RequestException as exc:
            logger.exception("ISS location lookup failed")
            raise RuntimeError("Could not fetch live ISS location data.") from exc

        logger.info("ISS location lookup succeeded")
        progress("ISS data received")
        return location

    return Agent(
        name="ISS Mission Control",
        instructions=(
            "You are a concise mission-control communicator. "
            "For live ISS location questions, use get_iss_location before answering. "
            "Report the current place name, coordinates, altitude, and speed. "
            "Make the update exciting but factual. "
        ),
        model=settings.model,
        tools=[get_iss_location],
    )


async def run_streamed(agent: Agent, task: str) -> str:
    """Run the agent and stream visible answer text as it arrives."""
    progress("Starting agent run")
    stream = Runner.run_streamed(agent, task)

    progress("Waiting for model/tool activity")
    async for event in stream.stream_events():
        if (
            event.type == "raw_response_event"
            and isinstance(event.data, ResponseTextDeltaEvent)
        ):
            print(event.data.delta, end="", flush=True)

    print()
    progress("Run complete")
    return stream.final_output or ""


async def run_once(agent: Agent, task: str) -> str:
    """Run the agent without streaming, useful for tests or batch jobs."""
    progress("Starting non-streaming agent run")
    result = await Runner.run(agent, task)
    progress("Run complete")
    print(result.final_output)
    return result.final_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a production-style ISS tracking agent."
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=DEFAULT_TASK,
        help="User task to send to the agent.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override OPENAI_MODEL for this run.",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Wait for the final result instead of streaming visible text deltas.",
    )
    return parser.parse_args()


async def main() -> int:
    configure_logging()
    args = parse_args()

    settings = Settings.from_env(model_override=args.model)
    iss_client = ISSLocationClient(timeout_seconds=settings.timeout_seconds)
    agent = build_agent(settings, iss_client)

    logger.info("Using model %s", settings.model)
    if args.no_stream:
        await run_once(agent, args.task)
    else:
        await run_streamed(agent, args.task)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        raise SystemExit(130)
