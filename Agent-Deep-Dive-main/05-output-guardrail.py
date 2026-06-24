"""Beginner-friendly agent with an output guardrail.

Run from the repo root:
    python 05-output-guardrail.py

Try:
    python 05-output-guardrail.py "Where is the ISS right now?"

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys

from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    Runner,
    output_guardrail,
)
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()

DEFAULT_TASK = "Where is the ISS right now?"
MODEL = "gpt-4.1-mini"


# ============================================================
# Output guardrail
# ============================================================
# 1. Output guardrails run after the agent writes its final answer.
# 2. LiveLocationCheck describes the structured yes/no answer we want.
# 3. live_location_guardrail_agent decides if the final answer invented live ISS data.
# 4. require_unknown_when_no_live_data blocks the final answer when the answer is yes.


class LiveLocationCheck(BaseModel):
    invented_live_location: bool
    reason: str


live_location_guardrail_agent = Agent(
    name="ISS Output Guardrail",
    instructions=(
        "Check whether the final answer invents the current live location of the ISS. "
        "If the user did not ask for the current location, invented_live_location should be false. "
        "If the answer says it does not know or does not have live data, invented_live_location should be false. "
        "If the answer gives a current place, country, ocean, latitude, longitude, or coordinates without live data, "
        "invented_live_location should be true."
    ),
    model=MODEL,
    output_type=LiveLocationCheck,
)


@output_guardrail
async def require_unknown_when_no_live_data(ctx, _agent, agent_output):
    """Block final answers that pretend to know the current ISS location."""
    user_input = " ".join(str(item) for item in ctx.turn_input)
    guardrail_task = (
        f"User asked:\n{user_input}\n\n"
        f"Agent answered:\n{agent_output}"
    )
    result = await Runner.run(live_location_guardrail_agent, guardrail_task)
    location_check = result.final_output

    return GuardrailFunctionOutput(
        output_info={"reason": location_check.reason},
        tripwire_triggered=location_check.invented_live_location,
    )


# ============================================================
# Main ISS agent
# ============================================================
# 1. This agent answers ISS questions without using a live location tool.
# 2. The output guardrail checks the final answer.
# 3. The answer only reaches the user if the agent admits it lacks live data.

iss_agent = Agent(
    name="ISS Explainer",
    instructions=(
        "You answer questions about the International Space Station. "
        "You do not have a live ISS location tool in this example. "
        "If the user asks where the ISS is right now, start with: I don't know because I do not have live data. "
        "Do not invent a current place, country, ocean, latitude, or longitude."
    ),
    model=MODEL,
    output_guardrails=[require_unknown_when_no_live_data],
)


# ============================================================
# Run the agent
# ============================================================
# 1. main checks for an API key and reads the user's task.
# 2. Runner.run starts the agent.
# 3. If the output guardrail blocks the answer, we print a friendly message.

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    try:
        result = await Runner.run(iss_agent, task)
        print(result.final_output)
    except OutputGuardrailTripwireTriggered:
        print("The final answer was blocked by the output guardrail.")
        print("This agent should say it does not know instead of inventing a live ISS location.")


if __name__ == "__main__":
    asyncio.run(main())
