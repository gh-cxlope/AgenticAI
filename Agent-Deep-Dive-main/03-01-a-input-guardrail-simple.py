"""Beginner-friendly agent with a simple input guardrail.

Run from the repo root:
    python 03-01-a-input-guardrail-simple.py

Try an allowed request:
    python 03-01-a-input-guardrail-simple.py "Where is the ISS right now?"

Try a blocked request:
    python 03-01-a-input-guardrail-simple.py "Write me a cookie recipe."

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys

import requests
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    Runner,
    function_tool,
    input_guardrail,
)
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station right now?"
MODEL = "gpt-4.1-mini"
TIMEOUT = 60


# ============================================================
# Input guardrail
# ============================================================
# 1. This guardrail looks at the user's input before the agent answers.
# 2. If the text mentions "iss" or "international space station", it allows it.
# 3. Otherwise, it triggers the tripwire and blocks the main agent.

@input_guardrail
def only_iss_questions(_ctx, _agent, user_input):
    """Block requests that are not about the ISS."""
    text = str(user_input).lower()

    if "iss" in text or "international space station" in text:
        is_about_iss = True
    else:
        is_about_iss = False

    return GuardrailFunctionOutput(
        output_info={"reason": "This example only answers ISS questions."},
        tripwire_triggered=not is_about_iss,
    )


# ============================================================
# Main ISS agent
# ============================================================
# 1. get_iss_location is the tool the main agent can call.
# 2. iss_agent uses that tool to answer ISS questions.
# 3. input_guardrails connects the topic check to this agent.

@function_tool
def get_iss_location():
    """Get the current latitude, longitude, altitude, and speed of the International Space Station."""
    response = requests.get("https://api.wheretheiss.at/v1/satellites/25544", timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    return {
        "latitude": round(data["latitude"], 2),
        "longitude": round(data["longitude"], 2),
        "altitude_km": round(data["altitude"], 2),
        "velocity_km_per_hour": round(data["velocity"], 2),
    }


iss_agent = Agent(
    name="ISS Mission Control",
    instructions=(
        "You are a concise mission-control communicator. "
        "For live ISS location questions, use get_iss_location before answering. "
        "Report the current coordinates, altitude, and speed. "
        "Keep the answer exciting but factual."
    ),
    model=MODEL,
    tools=[get_iss_location],
    input_guardrails=[only_iss_questions],
)


# ============================================================
# Run the agent
# ============================================================
# 1. main checks for an API key and reads the user's task.
# 2. Runner.run starts the agent.
# 3. If the guardrail blocks the input, we print a friendly message.

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    try:
        result = await Runner.run(iss_agent, task)
        print(result.final_output)
    except InputGuardrailTripwireTriggered:
        print("I can help with ISS questions in this example.")
        print("Try asking where the ISS is right now, how fast it is moving, or how high it is.")


if __name__ == "__main__":
    asyncio.run(main())
