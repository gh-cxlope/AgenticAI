"""Beginner-friendly multi-turn conversation agent.

Run from the repo root:
    python 08-multiturn-conversation.py

Try:
    You: Where is the ISS right now?
    You: What about its speed?
    You: Why does it move so fast?

Type "exit" to stop.

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os

import requests
from agents import Agent, Runner, SQLiteSession, function_tool
from dotenv import load_dotenv


load_dotenv()

MODEL = "gpt-4.1-mini"
TIMEOUT = 60


# ============================================================
# Function tools
# ============================================================
# 1. These are the same ISS tools from earlier examples.
# 2. The agent can use them in any turn of the conversation.
# 3. The session remembers earlier turns, but tools still fetch fresh data.

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
# 1. This is a normal agent with tools.
# 2. The multi-turn behavior comes from the session in main.
# 3. The same agent can answer follow-up questions using conversation history.

iss_agent = Agent(
    name="ISS Conversation Agent",
    instructions=(
        "You are a friendly ISS mission-control guide. "
        "Use get_iss_position for live location questions. "
        "Use get_iss_speed for live speed questions. "
        "For follow-up questions, use the conversation history to understand what the user means. "
        "Keep answers concise and factual."
    ),
    model=MODEL,
    tools=[get_iss_position, get_iss_speed],
)


# ============================================================
# Multi-turn conversation loop
# ============================================================
# 1. SQLiteSession stores the conversation history.
# 2. Every Runner.run call receives the same session.
# 3. That lets the agent understand follow-ups like "What about its speed?"

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    session = SQLiteSession("iss-multiturn-demo", ":memory:")

    print("ISS Conversation Agent")
    print('Ask a question, or type "exit" to stop.')

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not user_input:
            continue

        result = await Runner.run(iss_agent, user_input, session=session)
        print(f"\nAgent: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
