"""Beginner-friendly web search agent.

Run from the repo root:
    python 10-web-search-agent-production.py

Optional:
    python 10-web-search-agent-production.py "What are the latest NASA Artemis updates?"
    
"""

from __future__ import annotations

import asyncio
import os
import sys

from agents import Agent, Runner, WebSearchTool
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Search the web for one interesting space news story from this week."
MODEL = "gpt-4.1-mini"


# 1. Hosted tool: WebSearchTool gives the agent access to current web results.
web_search = WebSearchTool(search_context_size="low")


# 2. Agent: instructions + model + tools.
search_agent = Agent(
    name="Web Search Briefing",
    instructions=(
        "You are a concise research assistant. "
        "Use web search for current or factual questions. "
        "Answer in plain language, include the key facts, and cite sources when available."
    ),
    model=MODEL,
    tools=[web_search],
)


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    # 3. Runner: this starts the agent loop. The SDK handles the hosted web
    # search call and returns the final answer.
    result = await Runner.run(search_agent, task)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
