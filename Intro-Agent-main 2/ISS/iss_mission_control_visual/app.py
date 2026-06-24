"""Local visual UI for iss_mission_control_production.py.

Run from the repo root:

    python -m pip install -r ISS/iss_mission_control_visual/requirements.txt
    python ISS/iss_mission_control_visual/app.py

If the port is already in use, kill the process:
lsof -ti tcp:5050 | xargs kill     

Then open:

    http://localhost:5050
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading

from flask import Flask, Response, jsonify, render_template, request

import agent_runtime


DEFAULT_TASK = "Give me a current ISS mission update and show me where it is."

app = Flask(__name__)


@app.get("/")
def index():
    return render_template("index.html", default_task=DEFAULT_TASK)


@app.post("/api/run")
def api_run():
    body = request.get_json(silent=True) or {}
    task = (body.get("task") or DEFAULT_TASK).strip() or DEFAULT_TASK
    tools_enabled = bool(body.get("tools_enabled", True))

    try:
        result = asyncio.run(agent_runtime.run_agent(task, tools_enabled=tools_enabled))
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.post("/api/run_events")
def api_run_events():
    body = request.get_json(silent=True) or {}
    task = (body.get("task") or DEFAULT_TASK).strip() or DEFAULT_TASK
    tools_enabled = bool(body.get("tools_enabled", True))
    event_queue: queue.Queue[dict] = queue.Queue()

    def put_event(event: dict) -> None:
        event_queue.put(event)

    def worker() -> None:
        try:
            asyncio.run(
                agent_runtime.run_agent(
                    task,
                    tools_enabled=tools_enabled,
                    on_event=put_event,
                )
            )
        except Exception as exc:
            put_event({"type": "error", "message": str(exc)})
        finally:
            put_event({"type": "stream_end"})

    def stream():
        threading.Thread(target=worker, daemon=True).start()
        while True:
            event = event_queue.get()
            yield json.dumps(event) + "\n"
            if event.get("type") == "stream_end":
                break

    return Response(stream(), mimetype="application/x-ndjson")


if __name__ == "__main__":
    agent_runtime.configure_logging()
    port = int(os.getenv("PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
