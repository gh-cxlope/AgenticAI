"""Beginner-friendly agent with a tool guardrail.

Run from the repo root:
    python 04-01-tool-guardrail.py

Try an allowed tool call:
    python 04-01-tool-guardrail.py "Preheat the oven to 350 degrees."

Try a blocked tool call:
    python 04-01-tool-guardrail.py "Preheat the oven to 900 degrees."

Requires:
    pip install -r requirements.txt
"""

import asyncio
import json
import os
import sys

from agents import (
    Agent,
    Runner,
    ToolGuardrailFunctionOutput,
    ToolInputGuardrailTripwireTriggered,
    function_tool,
    tool_input_guardrail,
)
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Preheat the oven to 350 degrees."
MODEL = "gpt-4.1-mini"
MAX_OVEN_TEMPERATURE = 500


# ============================================================
# Tool guardrail
# ============================================================
# 1. Tool guardrails run when the agent tries to use a tool.
# 2. This one checks the temperature before preheat_oven runs.
# 3. Unsafe temperatures are blocked before the tool can do anything.

@tool_input_guardrail
def oven_temperature_guardrail(data):
    """Block oven temperatures above the safety limit."""
    tool_arguments = json.loads(data.context.tool_arguments)
    temperature_f = tool_arguments.get("temperature_f", 0)

    if temperature_f <= MAX_OVEN_TEMPERATURE:
        return ToolGuardrailFunctionOutput.allow()

    return ToolGuardrailFunctionOutput.raise_exception(
        output_info={"reason": "The requested oven temperature is too high."}
    )


# ============================================================
# Main kitchen agent
# ============================================================
# 1. preheat_oven is the tool the kitchen agent can call.
# 2. The tool guardrail checks the temperature before the tool runs.
# 3. kitchen_agent can preheat safely, but unsafe temperatures get blocked.

@function_tool(tool_input_guardrails=[oven_temperature_guardrail])
def preheat_oven(temperature_f: int):
    """Preheat the oven to a temperature in Fahrenheit."""
    return {
        "status": "oven preheating",
        "temperature_f": temperature_f,
    }


kitchen_agent = Agent(
    name="Kitchen Assistant",
    instructions=(
        "You are a helpful kitchen assistant. "
        "When the user asks to preheat the oven, always use preheat_oven with the requested temperature. "
        "The tool guardrail will decide whether the temperature is allowed. "
        "Keep your final answer short and clear."
    ),
    model=MODEL,
    tools=[preheat_oven],
)


# ============================================================
# Run the agent
# ============================================================
# 1. main checks for an API key and reads the user's task.
# 2. Runner.run starts the agent.
# 3. If the tool guardrail blocks the oven tool, we print a friendly message.

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    try:
        result = await Runner.run(kitchen_agent, task)
        print(result.final_output)
    except ToolInputGuardrailTripwireTriggered:
        print("The oven tool did not run.")
        print(f"This example only allows oven temperatures up to {MAX_OVEN_TEMPERATURE} degrees.")


if __name__ == "__main__":
    asyncio.run(main())
