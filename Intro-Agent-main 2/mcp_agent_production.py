"""Beginner-friendly Google Calendar MCP agent.
https://developers.openai.com/api/docs/guides/tools-connectors-mcp

Run from the repo root:

    python mcp_agent_production.py

Optional:

    python mcp_agent_production.py "What is on my Google Calendar today?"

Requires:

    pip install openai-agents python-dotenv

Create a .env file with:

    OPENAI_API_KEY=your-key-here
    OPENAI_MODEL=gpt-4.1-mini
    GOOGLE_CALENDAR_OAUTH_ACCESS_TOKEN=your-google-oauth-access-token
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from agents import Agent, HostedMCPTool, Runner
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "What is on my Google Calendar today?"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
TIMEZONE = os.getenv("TIMEZONE", "America/Los_Angeles")
TIMEOUT_SECONDS = 60


# 1. Hosted MCP tool: this connects the agent to the Google Calendar connector.
google_calendar_mcp = HostedMCPTool(
    tool_config={
        "type": "mcp",
        "server_label": "google_calendar",
        "connector_id": "connector_googlecalendar",
        "authorization": os.getenv("GOOGLE_CALENDAR_OAUTH_ACCESS_TOKEN"),
        "allowed_tools": ["search_events", "read_event"],
        "require_approval": "never",
    }
)


# 2. Agent: instructions + model + tools.
mcp_agent = Agent(
    name="Google Calendar MCP Assistant",
    instructions=(
        "You are a concise calendar assistant. "
        "Use the Google Calendar MCP tool when the user asks about calendar events. "
        "When a user gives a relative date like today, tomorrow, or Wednesday, "
        "use the current date provided in the task. "
        "Treat weekday names as the upcoming weekday unless the user clearly asks for a past date. "
        "Summarize events with dates, times, and titles."
    ),
    model=MODEL,
    tools=[google_calendar_mcp],
)


def add_date_context(task: str) -> str:
    now = datetime.now(ZoneInfo(TIMEZONE))
    current_date = f"{now:%A, %B} {now.day}, {now:%Y}"

    return (
        f"Current date: {current_date}\n"
        f"Timezone: {TIMEZONE}\n\n"
        f"User question: {task}"
    )


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")
    if not os.getenv("GOOGLE_CALENDAR_OAUTH_ACCESS_TOKEN"):
        raise RuntimeError("Set GOOGLE_CALENDAR_OAUTH_ACCESS_TOKEN in your .env file.")

    task = add_date_context(" ".join(sys.argv[1:]) or DEFAULT_TASK)

    # 3. Runner: this starts the agent loop. The SDK handles listing and
    # calling tools from the Google Calendar MCP connector.
    try:
        result = await asyncio.wait_for(
            Runner.run(mcp_agent, task),
            timeout=TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            "The MCP agent timed out. The Google Calendar connector may be slow or unavailable."
        ) from exc

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
