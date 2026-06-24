"""Beginner-friendly agent with tracing.

Run from the repo root:
    python 07-tracing.py

Optional:
    python 07-tracing.py "Where is the ISS and how fast is it moving?"

View traces:
    https://platform.openai.com/traces

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys

import requests
from agents import Agent, Runner, custom_span, flush_traces, function_tool, trace
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station and how fast is it moving?"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TIMEOUT = 60


# ============================================================
# Function tools
# ============================================================
# 1. These are the same two tools from 02.
# 2. Tracing records when the agent calls these tools.
# 3. In the trace dashboard, you can inspect tool calls and tool outputs.

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


# ============================================================
# Main ISS agent
# ============================================================
# 1. iss_agent is a normal agent.
# 2. You do not need special tracing code inside the agent.
# 3. The trace is added around the run in main.

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


# ============================================================
# Run the agent with tracing
# ============================================================
# 1. trace gives this workflow a name in the traces dashboard.
# 2. custom_span adds your own labeled step inside the trace.
# 3. flush_traces sends any buffered trace data before the script exits.

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    with trace("07 ISS tracing demo", metadata={"lesson": "07", "topic": "tracing"}):
        with custom_span("prepare user task", {"task": task}):
            print("Task prepared:", task)

        result = await Runner.run(iss_agent, task)

    print(result.final_output)

    # Traces are sent automatically, but flushing is helpful in short scripts.
    flush_traces()


if __name__ == "__main__":
    asyncio.run(main())
