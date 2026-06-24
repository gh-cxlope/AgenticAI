# Deploying to Render

This Flask app can be deployed to Render as a Web Service.

Live site: [ISS Mission Control](https://iss-mission-control.onrender.com/)

## 1. Confirm dependencies

The app needs `gunicorn` for production hosting. Confirm `requirements.txt` includes:

```text
flask
openai-agents
python-dotenv
requests
gunicorn
```

## 2. Push the project to GitHub

Render deploys from a Git repository, so push this project to GitHub before creating the Render service.

## 3. Create the Render Web Service

In Render:

1. Create a new **Web Service**.
2. Connect the GitHub repository.
3. Use these settings:

```text
Root Directory:
ISS/iss_mission_control_visual

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn -b 0.0.0.0:$PORT app:app
```

## 4. Add environment variables

In the Render service settings, add:

```text
OPENAI_API_KEY=your OpenAI API key
OPENAI_MODEL=gpt-4.1-mini
```

`OPENAI_MODEL` is optional because the app defaults to `gpt-4.1-mini`.

## 5. Deploy

Click **Deploy Web Service**.

When the build finishes, Render will provide a public URL like:

```text
https://your-app-name.onrender.com
```

## Notes

- Render's free tier may sleep after inactivity, so the first request after a pause can be slower.
- OpenAI API usage is billed separately from Render hosting.
- The app does not need a database or frontend build step.
