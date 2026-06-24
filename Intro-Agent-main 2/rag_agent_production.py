"""Beginner-friendly RAG agent.

Run from the repo root:

    python rag_agent_production.py

Optional:

    python rag_agent_production.py "What does the ISS example teach?"

Requires:

    pip install openai-agents python-dotenv

Create a .env file with:

    OPENAI_API_KEY=your-key-here
    OPENAI_MODEL=gpt-4.1-mini
"""

from __future__ import annotations

import asyncio
import os
import re
import sys

from agents import Agent, Runner, function_tool
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "What does this repo teach about building agents?"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


KNOWLEDGE_BASE = [
    {
        "title": "Repo goal",
        "text": (
            "Intro Agent teaches how to move from direct API calls toward agentic apps. "
            "The examples show models reasoning, using tools, getting external data, "
            "and returning useful final answers."
        ),
    },
    {
        "title": "ISS example",
        "text": (
            "The ISS example uses the OpenAI Agents SDK with a Python function tool. "
            "The tool fetches the live International Space Station location, and the "
            "agent explains the result in a mission-control style."
        ),
    },
    {
        "title": "Web search example",
        "text": (
            "The web search example uses the hosted WebSearchTool. It lets the agent "
            "search the internet for current information before answering."
        ),
    },
    {
        "title": "MCP example",
        "text": (
            "The MCP example uses a Google Calendar connector. It shows how an agent "
            "can use an external tool provider through MCP instead of a local Python function."
        ),
    },
    {
        "title": "RAG pattern",
        "text": (
            "RAG means retrieval-augmented generation. First, the app retrieves relevant "
            "context from a knowledge source. Then, the model uses that retrieved context "
            "to generate a grounded answer."
        ),
    },
]


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve_notes(query: str) -> list[dict]:
    query_words = tokenize(query)
    scored_notes = []

    for note in KNOWLEDGE_BASE:
        note_words = tokenize(f"{note['title']} {note['text']}")
        score = len(query_words & note_words)
        if score:
            scored_notes.append((score, note))

    scored_notes.sort(key=lambda item: item[0], reverse=True)
    top_notes = [note for _score, note in scored_notes[:3]]

    if top_notes:
        return top_notes

    return [{"title": "No direct match", "text": "No matching note was found."}]


# 1. Retrieval tool: the agent can search a tiny local knowledge base.
@function_tool
def search_knowledge_base(query: str) -> list[dict]:
    """Search the local knowledge base for notes related to the user's question."""
    return retrieve_notes(query)


# 2. Agent: instructions + model + tools.
rag_agent = Agent(
    name="RAG Study Guide",
    instructions=(
        "You are a concise study-guide assistant. "
        "Use search_knowledge_base before answering. "
        "Answer only from the retrieved notes. "
        "If the notes do not contain the answer, say you do not know from the knowledge base."
    ),
    model=MODEL,
    tools=[search_knowledge_base],
)


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    # 3. Runner: this starts the agent loop. The SDK handles the retrieval
    # tool call and returns the final answer.
    result = await Runner.run(rag_agent, task)
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
