# ISS Mission Control

This folder builds on what we learned in [Intro API](https://github.com/vivianamarquez/Intro-API): calling APIs, passing data to models, and building an agent loop ourselves.

The ISS example shows the same International Space Station agent idea in three forms:

1. A notebook version using the OpenAI Agents SDK
2. A terminal script version
3. A small visual UI version

The point is to compare what it feels like to build the agent loop ourselves versus using an SDK that handles more of the plumbing.

## What This Builds On

In [`04_Building_an_Agent_Loop.ipynb`](https://github.com/vivianamarquez/Intro-API/blob/main/04_Building_an_Agent_Loop.ipynb), we built an agent loop manually.

That meant we had to manage details like:

- calling the OpenAI API directly
- describing tools with JSON schemas
- checking whether the model wanted to call a tool
- running the matching Python function ourselves
- sending the tool result back to the model
- keeping track of the conversation loop
- deciding when the loop was finished

That was useful because it showed what an agent actually is: a model, a set of tools, and a loop that lets the model decide when to use those tools.

## Why Use the OpenAI Agents SDK?

The OpenAI Agents SDK lets us keep the same idea but write less infrastructure code.

Instead of manually building the tool schema and agent loop, we can write a normal Python function and decorate it:

```python
@function_tool
def get_iss_location() -> dict:
    ...
```

Then the SDK can expose that function to the agent as a tool.

So instead of manually doing all of this:

```python
response = requests.post(
    openai_url,
    headers=headers,
    json={
        "model": MODEL,
        "input": messages,
        "tools": tools,
    },
)
```

and then writing the loop that detects tool calls, runs functions, and sends tool results back, we can define:

```python
agent = Agent(
    name="ISS Mission Control",
    instructions="Use the ISS location tool before answering.",
    model=MODEL,
    tools=[get_iss_location],
)

result = await Runner.run(agent, task)
```

The SDK does not make the concept different. It packages the same pattern in a cleaner way:

- `Agent` defines the model, instructions, and tools
- `@function_tool` turns a Python function into a model-callable tool
- `Runner` runs the agent loop for us

For learning, building the loop manually first is helpful. For real projects, the SDK is usually nicer because it reduces repeated boilerplate and makes the code easier to extend.

## Setup

Create a `.env` file in the repo root:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4.1-mini
```

Install the main dependencies:

```bash
pip install openai-agents python-dotenv requests
```
