"""Beginner-friendly ISS agent handoff example.

Run from the repo root:
    python 09-handoff-agents.py

Optional:
    python 09-handoff-agents.py "Where is the ISS right now?"

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys

import requests
from agents import Agent, Runner, function_tool, handoff
from dotenv import load_dotenv


# A handoff is useful when a different agent should take over the answer.
# Here the triage agent routes ISS questions to either a facts specialist or
# a live-location specialist.

load_dotenv()

DEFAULT_TASK = "Where is the ISS right now?"
MODEL = "gpt-4.1-mini"
TIMEOUT = 60


@function_tool
def get_iss_position():
    """Get the current latitude, longitude, and altitude of the International Space Station."""
    print("Tool called: get_iss_position()")
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
    print("Tool called: get_iss_speed()")
    response = requests.get("https://api.wheretheiss.at/v1/satellites/25544", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    return {"velocity_km_per_hour": round(data["velocity"], 2)}


facts_specialist = Agent(
    name="ISS facts specialist",
    handoff_description="Use this for general questions about what the ISS is, history, crew, or science.",
    instructions=(
        "Answer general questions about the International Space Station. "
        "Do not answer live location or speed questions."
    ),
    model=MODEL,
)


location_specialist = Agent(
    name="ISS location specialist",
    handoff_description="Use this for live ISS location, altitude, or speed questions.",
    instructions=(
        "Answer live ISS location and speed questions. "
        "Use get_iss_position for current location or altitude. "
        "Use get_iss_speed for current speed. "
        "Keep the answer concise and factual."
    ),
    model=MODEL,
    tools=[get_iss_position, get_iss_speed],
)


triage_agent = Agent(
    name="ISS triage",
    instructions=(
        "Route each ISS question to the best specialist. "
        "Use ISS facts specialist for general ISS background questions. "
        "Use ISS location specialist for live location, altitude, or speed questions."
    ),
    model=MODEL,
    handoffs=[
        handoff(facts_specialist, tool_name_override="transfer_to_iss_facts_specialist"),
        handoff(location_specialist, tool_name_override="transfer_to_iss_location_specialist"),
    ],
)


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    user_question = " ".join(sys.argv[1:]).strip() or DEFAULT_TASK

    result = await Runner.run(triage_agent, user_question)

    print()
    print(result.final_output)
    print()
    print("Specialist that answered:", result.last_agent.name)


if __name__ == "__main__":
    asyncio.run(main())
