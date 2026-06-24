"""Beginner-friendly agent with streaming.

Run from the repo root:
    python 06-streaming-agent.py

Optional:
    python 06-streaming-agent.py "Where is the ISS and how fast is it moving?"

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys
from datetime import datetime

import requests
from agents import Agent, Runner, function_tool
from agents.stream_events import RawResponsesStreamEvent, RunItemStreamEvent
from dotenv import load_dotenv
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station and how fast is it moving?"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TIMEOUT = 60


def current_time():
    return datetime.now().strftime("%H:%M:%S")


# ============================================================
# Function tools
# ============================================================
# 1. These are the same two tools from 02.
# 2. The agent can call one or both before writing its final answer.
# 3. Streaming lets us see the final answer appear a little at a time.

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
# 1. iss_agent has the same tools as the 02 example.
# 2. The difference is how we run it.
# 3. In main, we use Runner.run_streamed instead of Runner.run.

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
# Run the agent with streaming
# ============================================================
# 1. Runner.run_streamed starts the agent and returns a streaming result.
# 2. result.stream_events() yields events as the run progresses.
# 3. ResponseTextDeltaEvent contains pieces of the final answer text.

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    result = Runner.run_streamed(iss_agent, task)
    tool_names_by_call_id = {}

    async for event in result.stream_events():
        # RawResponsesStreamEvent: low-level model stream events, like text chunks.
        if isinstance(event, RawResponsesStreamEvent):
            if isinstance(event.data, ResponseTextDeltaEvent):
                print(event.data.delta, end="", flush=True)

        # RunItemStreamEvent: higher-level agent events, like tool calls and tool outputs.
        elif isinstance(event, RunItemStreamEvent):
            if event.item.type == "tool_call_item":
                tool_names_by_call_id[event.item.call_id] = event.item.tool_name
                print(f"\n[{current_time()}] tool called: {event.item.tool_name}", flush=True)
            elif event.item.type == "tool_call_output_item":
                tool_name = tool_names_by_call_id.get(event.item.call_id, "unknown tool")
                print(f"[{current_time()}] tool finished: {tool_name}\n", flush=True)

    print()


if __name__ == "__main__":
    asyncio.run(main())
