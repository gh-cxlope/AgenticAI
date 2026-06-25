import os
import sys

from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chat"

    def ready(self) -> None:
        if "migrate" in sys.argv or "makemigrations" in sys.argv:
            return

        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        try:
            from .agent_service import warm_up_agents

            warm_up_agents()
        except Exception:
            # Missing API key or data files during setup should not block Django startup.
            pass
