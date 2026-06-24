# Agent Deep Dive

Beginner-friendly examples for learning OpenAI Agent SDK concepts.

## Lesson Menu

| Lesson | File | What it covers |
| --- | --- | --- |
| 01 | `01-simple-agent.py` | A simple ISS agent that calls one function tool for live location data. |
| 02 | `02-two-tools-agent.py` | An agent with two tools, showing how the model chooses and combines tool calls. |
| 03A | `03-01-a-input-guardrail-simple.py` | A basic input guardrail that blocks questions outside the ISS topic. |
| 03B | `03-01-b-input-guardrail-classifier.py` | A model-based input guardrail that classifies whether a request is on topic. |
| 04A | `04-01-tool-guardrail.py` | A tool guardrail that checks tool inputs before a tool can run. |
| 04B | `04-02-hitl-approval.py` | Human-in-the-loop approval for a tool with a simulated side effect. |
| 05 | `05-output-guardrail.py` | An output guardrail that checks the agent's final answer before showing it. |
| 06 | `06-streaming-agent.py` | Streaming responses so final answer text appears as it is generated. |
| 07 | `07-tracing.py` | Tracing an agent run, including custom spans and tool call visibility. |
| 08 | `08-multiturn-conversation.py` | Multi-turn conversation using a session to remember earlier turns. |
| 09 | `09-handoff-agents.py` | Agent handoffs, where a triage agent routes work to specialist agents. |
| 10 | `10-web-search-agent-production.py` | A production-style agent using hosted web search for current information. |
| 11 | `11-mcp-agent-production.py` | A Google Calendar MCP agent using a hosted connector and OAuth token. |
| 12 | `12-rag-agent.py` | A local RAG agent that embeds and retrieves from text files in `rag_docs/`. |
| 13A | `13-01-iss-workflow.py` | The ISS example as a workflow where code controls the step-by-step path. |
| 13B | `13-02-iss-agent.py` | The ISS example as an agent where the model decides when to use tools. |

Extra note: `11-google_calendar_oauth_token.md` explains how to get the Google Calendar OAuth token used by lesson 11.

For scheduled runs, see `CRONJOBS.md` for examples of using cron jobs to run these scripts at a regular cadence.

## Setup

Install the Python dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

If you use Conda, create and activate the `aaaic` environment first:

```bash
conda create -n aaaic python=3.12
conda activate aaaic
pip install -r requirements.txt
```

## Run

Copy `.env.example` to `.env`, add your API key, then run the example:

```bash
cp .env.example .env
python 01-simple-agent.py
```
