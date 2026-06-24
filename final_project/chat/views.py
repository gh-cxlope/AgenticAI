import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .agent_service import ask_agent


@require_GET
def index(request):
    return render(request, "chat/index.html")


@require_POST
def chat_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    question = payload.get("question", "").strip()
    if not question:
        return JsonResponse({"error": "Please enter a question."}, status=400)

    agent = payload.get("agent")
    if agent and agent not in {"fun_fact"}:
        return JsonResponse({"error": "Unsupported agent value."}, status=400)

    try:
        result = ask_agent(question, agent=agent)
    except EnvironmentError as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    except Exception as exc:
        return JsonResponse({"error": f"Something went wrong: {exc}"}, status=500)

    return JsonResponse(result)
