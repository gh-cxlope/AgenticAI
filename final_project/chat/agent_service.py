"""Lazy loader for the existing multi-agent chatbot."""

import threading

from langchain_openai import ChatOpenAI

from CaliforniaNativeLandscaper_Agent import (
    agent_orchestrator,
    load_env,
    plant_retriever_agent,
    pollinator_expert_agent,
    web_search_fun_fact_agent,
)

_init_lock = threading.Lock()
_request_lock = threading.Lock()
_llm = None
_orchestrator = None


def get_agents():
    global _llm, _orchestrator

    if _orchestrator is not None:
        return _llm, _orchestrator

    with _init_lock:
        if _orchestrator is None:
            load_env()
            _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            plant_agent = plant_retriever_agent()
            pollinator_agent = pollinator_expert_agent()
            fun_fact_agent = web_search_fun_fact_agent()
            _orchestrator = agent_orchestrator(
                plant_agent, pollinator_agent, fun_fact_agent, _llm
            )

    return _llm, _orchestrator


def warm_up_agents() -> None:
    """Load agents once at startup so the first chat request is not racy."""
    get_agents()


def ask_agent(question: str, agent: str | None = None) -> dict:
    _, orchestrator = get_agents()
    forced_route = "fun_fact" if agent == "fun_fact" else None

    with _request_lock:
        return orchestrator(question, forced_route=forced_route)
