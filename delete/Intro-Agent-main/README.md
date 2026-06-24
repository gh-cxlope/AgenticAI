# Intro Agent

This repo continues the agent-building work from [Intro API](https://github.com/vivianamarquez/Intro-API).

The goal is to move from calling APIs directly toward building agentic apps: programs where a model can reason, call tools, use external data, and return a useful final answer.

## Modules

### `ISS/`

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

## Setup

Create a `.env` file:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4.1-mini
```

Each module may have its own extra setup instructions in its folder.
