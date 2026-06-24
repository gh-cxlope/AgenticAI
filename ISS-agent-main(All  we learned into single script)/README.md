# Kid Space Agent

A fully working, kid-friendly space agent built with the OpenAI Agents SDK.

It includes:

- A conversational triage agent that keeps chatting until the user says goodbye.
- An input guardrail that keeps the conversation space-related.
- An ISS agent with tools for live ISS location, named Earth locations, and map links.
- NASA specialists for NASA-only web search and direct Earthdata API dataset discovery.
- An output guardrail for kid-friendly tone.
- Streaming responses and OpenAI trace links for every turn.

## Setup

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate kid-space-agent
```

Create your local `.env` file:

```bash
cp .env.example .env
```

Then edit `.env` and set `OPENAI_API_KEY`.

`OPENAI_MODEL` controls the triage, guardrail, and ISS agents. `OPENAI_NASA_MODEL`
defaults to `gpt-5.5` because the NASA specialists use hosted web search domain filters.

## Run

```bash
python space_agent.py
```

For the kawaii browser UI:

```bash
uvicorn web_app:app --reload --port 8001
```

Try questions like:

```text
Where is the ISS right now?
Show me the ISS on a map.
Where is Kennedy Space Center?
Search NASA for the latest Artemis update.
Find NASA Earthdata datasets about wildfires.
Show me NASA Earthdata keywords for rain.
```

Say `goodbye`, `bye`, `quit`, or `exit` to stop.

## Notes

NASA web search is constrained to NASA domains through the hosted web search tool filters.

Earthdata keyword, collection, and granule searches use direct NASA CMR/KMS APIs instead of the hosted Earthdata MCP endpoint.
