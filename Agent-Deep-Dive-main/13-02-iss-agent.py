"""ISS example as an agent.

An agent can choose whether to call a tool.
Here, the model sees the user question and decides if it needs live ISS data.

Run from the repo root:
    python 13-02-iss-agent.py

Optional:
    python 13-02-iss-agent.py "Where is the ISS right now?"
"""

from __future__ import annotations

import asyncio
import os
import sys

import requests
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station right now?"
MODEL = "gpt-4.1-mini"
TIMEOUT = 60


def get_place_name(latitude: float, longitude: float) -> str:
    reverse_geocode_url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "localityLanguage": "en",
    }
    response = requests.get(reverse_geocode_url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    place_parts = [
        data.get("locality") or data.get("city"),
        data.get("principalSubdivision"),
        data.get("countryName"),
    ]
    place_name = ", ".join(part for part in place_parts if part)

    return place_name or "an area with no nearby place name"


def fetch_iss_location() -> dict:
    iss_url = "https://api.wheretheiss.at/v1/satellites/25544"
    response = requests.get(iss_url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    latitude = data["latitude"]
    longitude = data["longitude"]

    return {
        "place_name": get_place_name(latitude, longitude),
        "latitude": round(latitude, 2),
        "longitude": round(longitude, 2),
        "altitude_km": round(data["altitude"], 2),
        "velocity_km_per_hour": round(data["velocity"], 2),
    }


@function_tool
def get_iss_location() -> dict:
    """Get the current place name, latitude, longitude, altitude, and speed of the International Space Station."""
    return fetch_iss_location()


iss_agent = Agent(
    name="ISS Mission Control",
    instructions=(
        "You are a concise mission-control communicator. "
        "Use get_iss_location for live ISS location questions. "
        "If the user asks a general question that does not need live location data, answer without using the tool. "
        "When you use the tool, report the place name, coordinates, altitude, and speed. "
        "Keep the answer exciting but factual."
    ),
    model=MODEL,
    tools=[get_iss_location],
)


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    # In an agent, the model can choose whether this task needs a tool call.
    result = await Runner.run(iss_agent, task)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
