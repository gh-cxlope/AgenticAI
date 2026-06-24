"""Kawaii browser UI for the kid-friendly space agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator

from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
    gen_trace_id,
    trace,
)
from agents.stream_events import RawResponsesStreamEvent, RunItemStreamEvent
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import APIError
from openai.types.responses.response_text_delta_event import ResponseTextDeltaEvent
from pydantic import BaseModel

from space_agent import _guardrail_safe_input, triage_agent


load_dotenv()

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"

app = FastAPI(title="Kid Space Agent")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "kawaii-space-agent"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _session(session_id: str) -> SQLiteSession:
    safe_id = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_"})[:64]
    return SQLiteSession(safe_id or "kawaii-space-agent", ":memory:")


async def _stream_agent_turn(payload: ChatRequest) -> AsyncIterator[str]:
    trace_id = gen_trace_id()
    yield _sse("trace", {"trace_id": trace_id, "url": f"https://platform.openai.com/traces/{trace_id}"})

    tool_names_by_call_id: dict[str, str] = {}
    user_input = _guardrail_safe_input(payload.message)

    try:
        with trace(
            "Kid Space Agent UI",
            trace_id=trace_id,
            metadata={"audience": "kids", "surface": "kawaii-web-ui"},
        ):
            result = Runner.run_streamed(
                triage_agent,
                user_input,
                session=_session(payload.session_id),
                max_turns=12,
            )

            async for event in result.stream_events():
                if isinstance(event, RawResponsesStreamEvent) and isinstance(event.data, ResponseTextDeltaEvent):
                    yield _sse("delta", {"text": event.data.delta})
                elif isinstance(event, RunItemStreamEvent):
                    item = event.item
                    if item.type == "tool_call_item":
                        tool_name = getattr(item, "tool_name", "tool")
                        tool_names_by_call_id[item.call_id] = tool_name
                        yield _sse("status", {"text": f"Using {tool_name}"})
                    elif item.type == "tool_call_output_item":
                        tool_name = tool_names_by_call_id.get(item.call_id, "tool")
                        yield _sse("status", {"text": f"Finished {tool_name}"})
                    elif item.type == "handoff_call_item":
                        yield _sse("status", {"text": "Routing to a space specialist"})
                    elif item.type == "handoff_output_item":
                        agent_name = getattr(item.target_agent, "name", "specialist")
                        yield _sse("status", {"text": f"Now with {agent_name}"})

        yield _sse("done", {})
    except InputGuardrailTripwireTriggered:
        yield _sse(
            "error",
            {
                "text": (
                    "I can only chat about space here. Try planets, rockets, NASA, Earth from space, "
                    "or where the ISS is right now."
                )
            },
        )
    except OutputGuardrailTripwireTriggered:
        yield _sse(
            "error",
            {"text": "I caught an answer that was not quite kid-ready. Ask again and I will make it clearer."},
        )
    except APIError as exc:
        yield _sse(
            "error",
            {
                "text": (
                    "A space data service had a launch-pad wobble. Try a NASA news question, "
                    "an ISS location question, or ask again in a moment."
                ),
                "debug": str(exc),
            },
        )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> StreamingResponse:
    return StreamingResponse(_stream_agent_turn(payload), media_type="text/event-stream")
