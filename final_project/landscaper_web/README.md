# California Native Plant Web App

This folder contains the Django project configuration for the California Native Plant Assistant web app.

The web interface lives in the Django `chat` app and uses `CaliforniaNativeLandscaper_Agent.py` in the project root as the chatbot backend.

## Prerequisites

- Python 3.11 or newer
- An OpenAI API key

## Project layout

```text
final_project/
├── manage.py
├── .env
├── requirements.txt
├── CaliforniaNativeLandscaper_Agent.py
├── plants.csv
├── Polinators_1.csv
├── polinators_2.csv
├── chat/                         # Django chat app
└── landscaper_web/               # Django project settings (this folder)
    ├── settings.py
    ├── urls.py
    └── static/landscaper/images/ # Hero and pollinator images
```

## Setup

1. Open a terminal and go to the project root:

   ```bash
   cd /Users/cristina/Developer/AgenticAI/final_project
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root if you do not already have one:

   ```bash
   cp .env.example .env
   ```

5. Add your OpenAI API key to `.env`:

   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   ```

   Optional Django settings:

   ```env
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
   ```

6. Run database migrations:

   ```bash
   python manage.py migrate
   ```

## Run the web app

From the project root:

```bash
source .venv/bin/activate
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

To use a different port:

```bash
python manage.py runserver 8080
```

## What to expect

- The first question may take a little longer while the plant and pollinator agents load.
- If vector stores do not exist yet, the agent will build them from:
  - `plants.csv`
  - `Polinators_1.csv`
  - `polinators_2.csv`
- The orchestrator routes each question to:
  - `plant`
  - `pollinator`
  - `both`

## Example questions

- What is the height and spread of Arctostaphylos manzanita?
- What plants attract monarch butterflies?
- Recommend drought-tolerant plants that also support hummingbirds

## Troubleshooting

### Missing API key

If you see an error about `OPENAI_API_KEY`, confirm that `.env` exists in the project root and contains a valid key.

### Protobuf / Chroma error

If you see a protobuf-related error, make sure dependencies are installed from `requirements.txt`. The agent script includes a compatibility workaround for Chroma.

### Static images not showing

Confirm these files exist:

```text
landscaper_web/static/landscaper/images/bee.jpeg
landscaper_web/static/landscaper/images/humminbird.jpeg
landscaper_web/static/landscaper/images/monarch.jpeg
landscaper_web/static/landscaper/images/plants_image.jpg
```

Then restart the Django server.

## Notes

- Run all commands from the project root (`final_project`), not from inside `landscaper_web/`.
- The terminal chatbot can still be run separately with:

  ```bash
  python CaliforniaNativeLandscaper_Agent.py
  ```
