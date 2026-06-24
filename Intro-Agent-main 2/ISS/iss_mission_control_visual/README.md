# ISS Mission Control Visual

This folder runs the ISS agent in a local Flask UI.

It uses the same OpenAI Agents SDK pattern as the notebook and script, but adds an interface where you can type a task, run the agent, see tool activity, and view a map visualization.

## Setup

From the repo root, create a `.env` file if you do not already have one:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4.1-mini
```

Install the UI dependencies:

```bash
python -m pip install -r ISS/iss_mission_control_visual/requirements.txt
```

## Run

From the repo root:

```bash
python ISS/iss_mission_control_visual/app.py
```

Then open:

```text
http://localhost:5050
```

If port `5050` is already in use, you can run it on another port:

```bash
PORT=5051 python ISS/iss_mission_control_visual/app.py
```

Then open:

```text
http://localhost:5051
```

Or you can stop whatever is already using port `5050`:

```bash
lsof -ti tcp:5050 | xargs kill
```

Then run the app again:

```bash
python ISS/iss_mission_control_visual/app.py
```
