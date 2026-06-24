# Running Scripts with Cron Jobs

Cron jobs are scheduled commands that run automatically at a set cadence. They are useful when a script should run without someone opening a terminal each time, such as fetching fresh data, producing a daily report, refreshing a local index, or checking an external service on a schedule.

This project contains Python examples that can be run from the command line. Many of them are good candidates for cron because they run once and exit. Interactive examples, such as scripts that call `input()`, should not be scheduled with cron unless they are changed to accept arguments or configuration instead of waiting for a person.

## When Cron Is Helpful

Use cron when you want a script to run:

- every few minutes to monitor a changing value
- hourly to refresh data
- daily to create a status report
- weekly to run maintenance or cleanup
- at a specific time when API usage, system load, or reporting needs are predictable

For example, the ISS scripts could be scheduled to collect or print live ISS information at a regular cadence. A RAG script could be scheduled to rebuild or validate local context. A production-style web search or calendar script could run on a daily schedule if it has all required credentials available.

## Cron Syntax

A cron schedule has five time fields followed by the command:

```cron
* * * * * command-to-run
| | | | |
| | | | day of week, 0-7 where 0 and 7 are Sunday
| | | month, 1-12
| | day of month, 1-31
| hour, 0-23
minute, 0-59
```

Common schedules:

```cron
*/5 * * * *      every 5 minutes
0 * * * *        every hour
30 9 * * *       every day at 9:30 AM
0 8 * * 1        every Monday at 8:00 AM
0 0 1 * *        on the first day of every month
```

## Project Setup for Cron

Cron runs with a smaller environment than your normal terminal. Use absolute paths, activate the right Python environment, and write output to log files.

From this repository:

```bash
cd /Users/vivianamarquez/Desktop/Agent-Deep-Dive
pip install -r requirements.txt
```

Make sure required environment variables are available. For these examples, that usually means `OPENAI_API_KEY` in a `.env` file or exported directly in the cron command. The scripts use `python-dotenv`, so keeping a `.env` file in the project root is usually the simplest option.

## Editing Your Crontab

Open your user crontab:

```bash
crontab -e
```

Add one line per scheduled script. This example runs `01-simple-agent.py` every day at 9:00 AM and appends output to a log file:

```cron
0 9 * * * cd /Users/vivianamarquez/Desktop/Agent-Deep-Dive && /usr/bin/env python3 01-simple-agent.py >> logs/01-simple-agent.log 2>&1
```

Create the log directory before enabling the job:

```bash
mkdir -p /Users/vivianamarquez/Desktop/Agent-Deep-Dive/logs
```

If you use Conda, call Python from that environment directly. Replace the path with the result of `which python` after activating your environment:

```cron
0 9 * * * cd /Users/vivianamarquez/Desktop/Agent-Deep-Dive && /path/to/conda/envs/aaaic/bin/python 01-simple-agent.py >> logs/01-simple-agent.log 2>&1
```

## Example Cron Jobs

Run the simple ISS agent every morning:

```cron
0 8 * * * cd /Users/vivianamarquez/Desktop/Agent-Deep-Dive && /usr/bin/env python3 01-simple-agent.py >> logs/iss-daily.log 2>&1
```

Run the workflow example every 30 minutes:

```cron
*/30 * * * * cd /Users/vivianamarquez/Desktop/Agent-Deep-Dive && /usr/bin/env python3 13-01-iss-workflow.py >> logs/iss-workflow.log 2>&1
```

Run the RAG example once per week:

```cron
0 10 * * 1 cd /Users/vivianamarquez/Desktop/Agent-Deep-Dive && /usr/bin/env python3 12-rag-agent.py >> logs/rag-weekly.log 2>&1
```

## Scripts to Avoid Scheduling As-Is

Avoid scheduling scripts that require human input because cron cannot answer prompts:

- `04-02-hitl-approval.py`
- `08-multiturn-conversation.py`

These can become cron-friendly if they are refactored to read from command-line arguments, files, environment variables, or another non-interactive source.

## Good Cron Practices

- Use absolute paths for the repo, Python, and any files the script reads or writes.
- Redirect output with `>> logs/name.log 2>&1` so failures are visible later.
- Test the exact cron command in a normal terminal before adding it to `crontab`.
- Keep credentials out of the crontab when possible; prefer `.env` files with appropriate permissions.
- Make scheduled scripts idempotent, meaning they can run more than once without corrupting state or duplicating work unexpectedly.
- Be mindful of API usage and rate limits when choosing a cadence.
- Add timestamps to script output if logs need to be audited.

## Checking Scheduled Jobs

List current cron jobs:

```bash
crontab -l
```

Watch a log file:

```bash
tail -f /Users/vivianamarquez/Desktop/Agent-Deep-Dive/logs/iss-daily.log
```

Remove or edit jobs:

```bash
crontab -e
```

## macOS Note

Cron works on macOS, but `launchd` is Apple's native scheduler and may be better for long-running production tasks. For local learning, demos, and simple recurring script runs, cron is usually enough.
