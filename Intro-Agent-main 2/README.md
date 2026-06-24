# Intro Agent

This repo continues the agent-building work from [Intro API](https://github.com/vivianamarquez/Intro-API).

The goal is to move from calling APIs directly toward building agentic apps: programs where a model can reason, call tools, use external data, and return a useful final answer.

---

## Practice

### 1. `ISS/`

The `ISS/` folder rebuilds the International Space Station agent from the manual agent-loop lesson, but now with the OpenAI Agents SDK.

It includes:

- a notebook version for learning the SDK step by step
- a terminal script version for running the agent from the command line
- a visual UI version for interacting with the same agent in a local web app

Start here:

```text
ISS/README.md
```

More modules will be added here as the repo grows.

### 2. Using web search

The root-level `web_search_agent_production.py` script shows a very simple agent that uses the OpenAI Agents SDK hosted web search tool.

Run it from the repo root:

```bash
python web_search_agent_production.py
```

### 3. Using a Google Calendar MCP tool

The root-level `mcp_agent_production.py` script shows a very simple agent that uses the Google Calendar MCP connector.
It also sends the current date and timezone to the agent so questions like "Wednesday" mean the upcoming Wednesday.

Run it from the repo root:

```bash
python mcp_agent_production.py
```

### 4. Using RAG

The root-level `rag_agent_production.py` script shows a very simple retrieval-augmented generation pattern. It searches a tiny local knowledge base first, then answers from the retrieved notes.

Run it from the repo root:

```bash
python rag_agent_production.py
```

---


## Setup

Create a `.env` file:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4.1-mini
GOOGLE_CALENDAR_OAUTH_ACCESS_TOKEN=your-google-oauth-access-token
```

The Google Calendar token is only needed for the MCP connector example. Each module may have its own extra setup instructions in its folder.
