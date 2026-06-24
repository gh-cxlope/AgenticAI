"""Beginner-friendly agent with an input guardrail.

Run from the repo root:
    python 03-01-b-input-guardrail-classifier.py

Try an allowed request:
    python 03-01-b-input-guardrail-classifier.py "Where is the ISS right now?"

Try a blocked request:
    python 03-01-b-input-guardrail-classifier.py "Write me a cookie recipe."

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
from pydantic import BaseModel


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station right now?"
MODEL = "gpt-4.1-mini"
TIMEOUT = 60


# ============================================================
# Input guardrail
# ============================================================
# 1. TopicCheck describes the structured yes/no answer we want.
# 2. topic_guardrail_agent decides whether the user asked about the ISS.
# 3. only_iss_questions blocks the main agent when the answer is no.

class TopicCheck(BaseModel):
    is_iss_question: bool
    reason: str


topic_guardrail_agent = Agent(
    name="ISS Topic Guardrail",
    instructions=(
        "Decide if the user's request is about the International Space Station. "
        "Allow questions about its location, speed, altitude, orbit, crew, science, "
        "history, or general ISS facts. "
        "Do not allow unrelated topics."
    ),
    model=MODEL,
    output_type=TopicCheck,
)


@input_guardrail
async def only_iss_questions(_ctx, _agent, user_input):
    """Block requests that are not about the ISS."""
    result = await Runner.run(topic_guardrail_agent, user_input)
    topic_check = result.final_output

    return GuardrailFunctionOutput(
        output_info={"reason": topic_check.reason},
        tripwire_triggered=not topic_check.is_iss_question,
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
