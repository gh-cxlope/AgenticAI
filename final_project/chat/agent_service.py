"""Lazy loader for the existing multi-agent chatbot."""

from langchain_openai import ChatOpenAI

from CaliforniaNativeLandscaper_Agent import (
    agent_orchestrator,
    load_env,
    plant_retriever_agent,
    pollinator_expert_agent,
    route_question,
    web_search_fun_fact_agent,
)

_llm = None
_orchestrator = None
_fun_fact_agent = None


def get_agents():
    global _llm, _orchestrator, _fun_fact_agent

    if _orchestrator is None:
        load_env()
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        plant_agent = plant_retriever_agent()
        pollinator_agent = pollinator_expert_agent()
        _fun_fact_agent = web_search_fun_fact_agent()
        _orchestrator = agent_orchestrator(
            plant_agent, pollinator_agent, _fun_fact_agent, _llm
        )

    return _llm, _orchestrator, _fun_fact_agent


def ask_agent(question: str, agent: str | None = None) -> dict[str, str]:
    llm, orchestrator, fun_fact_agent = get_agents()

    if agent == "fun_fact":
        return {"route": "fun_fact", "answer": fun_fact_agent(question)}

    route = route_question(question, llm)
    answer = orchestrator(question)
    return {"route": route, "answer": answer}
