"""Beginner-friendly agent with two function tools.

Run from the repo root:
    python 02-two-function-agent.py

Optional:
    python 02-two-function-agent.py "Where is the ISS and how fast is it moving?"

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys

import requests
from agents import Agent, Runner, function_tool
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station and how fast is it moving?"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TIMEOUT = 60


@function_tool
def get_iss_position():
    """Get the current latitude, longitude, and altitude of the International Space Station."""
    response = requests.get("https://api.wheretheiss.at/v1/satellites/25544", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    return {
        "latitude": round(data["latitude"], 2),
        "longitude": round(data["longitude"], 2),
        "altitude_km": round(data["altitude"], 2),
    }


@function_tool
def get_iss_speed():
    """Get the current speed of the International Space Station."""
    response = requests.get("https://api.wheretheiss.at/v1/satellites/25544", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    return {"velocity_km_per_hour": round(data["velocity"], 2)}


iss_agent = Agent(
    name="ISS Mission Control",
    instructions=(
        "You are a concise mission-control communicator. "
        "Use get_iss_position for location questions. "
        "Use get_iss_speed for speed questions. "
        "Keep the answer exciting but factual."
    ),
    model=MODEL,
    tools=[get_iss_position, get_iss_speed],
)


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    result = await Runner.run(iss_agent, task)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
