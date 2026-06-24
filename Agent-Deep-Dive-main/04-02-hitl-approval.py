"""Beginner-friendly agent with human-in-the-loop approval.

Run from the repo root:
    python 04-02-hitl-approval.py

Try:
    python 04-02-hitl-approval.py "Cancel order 123."

Requires:
    pip install -r requirements.txt
"""

import asyncio
import os
import sys

from agents import Agent, Runner, function_tool
from dotenv import load_dotenv


load_dotenv()

DEFAULT_TASK = "Cancel order 123."
MODEL = "gpt-4.1-mini"


# ============================================================
# Tool that needs approval
# ============================================================
# 1. cancel_order is a tool with a real side effect.
# 2. needs_approval=True pauses the run before the tool executes.
# 3. The tool only runs after the pending tool call is approved.

@function_tool(needs_approval=True)
def cancel_order(order_id: int):
    """Cancel a customer order."""
    return f"Cancelled order {order_id}"


# ============================================================
# Main support agent
# ============================================================
# 1. support_agent can use cancel_order.
# 2. The agent may decide a cancellation is needed.
# 3. The SDK pauses before the cancellation tool actually runs.

support_agent = Agent(
    name="Support Agent",
    instructions=(
        "You are a helpful support agent. "
        "When the user asks to cancel an order, use cancel_order. "
        "Keep your final answer short and clear."
    ),
    model=MODEL,
    tools=[cancel_order],
)


# ============================================================
# Run the agent
# ============================================================
# 1. First run: the agent asks to use cancel_order, then pauses.
# 2. A human types yes or no.
# 3. If approved, the same paused run resumes and the tool executes.

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK

    result = await Runner.run(support_agent, task)

    if result.interruptions:
        print("Approval needed before the tool can run.")

        state = result.to_state()
        for interruption in result.interruptions:
            answer = input("Approve this tool call? Type yes or no: ").strip().lower()

            if answer == "yes":
                state.approve(interruption)
            else:
                print("Tool call was not approved. Order was not cancelled.")
                return

        result = await Runner.run(support_agent, state)

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
