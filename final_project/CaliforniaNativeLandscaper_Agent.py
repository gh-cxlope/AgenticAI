#!/usr/bin/env python3
"""Multi-agent chatbot for California native plants and pollinator-friendly plants.

How to run from the terminal
----------------------------
1. Open a terminal and go to the project root:

       cd /Users/cristina/Developer/AgenticAI/final_project

2. Activate the virtual environment:

       source .venv/bin/activate

3. Install dependencies if needed:

       pip install -r requirements.txt

4. Make sure your OpenAI API key is saved in `.env`:

       OPENAI_API_KEY=your-key-here

5. Start the chatbot:

       python CaliforniaNativeLandscaper_Agent.py

6. Ask questions at the prompt. Type `quit`, `exit`, or `q` to stop.

Example questions
-----------------
- Plant agent: What is the height and spread of Arctostaphylos manzanita?
- Pollinator agent: What plants attract monarch butterflies?
- Both agents: Recommend drought-tolerant plants that also support hummingbirds
- Fun fact agent: Tell me a fun fact about monarch butterflies

Notes
-----
- The first run builds vector stores in `chroma_data/` and may take a little longer.
- The orchestrator routes each question to the plant expert, pollinator expert, fun fact agent, or both CSV experts.
"""

import os
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parent
PLANTS_CSV_PATH = PROJECT_ROOT / "plants.csv"
POLLINATORS_1_CSV_PATH = PROJECT_ROOT / "Polinators_1.csv"
POLLINATORS_2_CSV_PATH = PROJECT_ROOT / "polinators_2.csv"
PLANTS_CHROMA_PATH = PROJECT_ROOT / "chroma_data" / "plants_csv"
POLLINATORS_CHROMA_PATH = PROJECT_ROOT / "chroma_data" / "pollinators_csv"

PLANT_RETRIEVER_PROMPT = """You are a helpful assistant specializing in California native plants.
Answer questions using only the plant reference data provided below.
If the reference data does not contain enough information, say so clearly.
Answer in 200 words or fewer. Recommend at most 10 plants, but prefer 3 to 5 strong matches when possible.

Rules:
- Do not invent facts.
- If the data does not contain the answer, say: "I don't have that information in the plant data."
- Use common name and scientific name together.
- Include height and spread when recommending plants.
- Keep explanations short and practical.
- Do not include care details, pollinator information, medicinal uses, toxicity, or availability unless they appear in the retrieved plant records.

For recommendations, use this format:
- Common name (Scientific name): height, spread. Short reason it matches.

Reference data:
{context}
"""

POLLINATOR_EXPERT_PROMPT = """You are a pollinator expert specializing in California native plants.
Answer questions using only the pollinator reference data provided below.
If the reference data does not contain enough information, say so clearly.
Answer in 100 words or fewer. Recommend at most 10 plants, but prefer 3 to 5 strong matches when possible.

Rules:
- Do not invent facts.
- If the data does not contain the answer, say: "I don't have that information in the pollinator data."
- Use common name and scientific name together when available.
- Mention which pollinators each plant supports (bees, butterflies, hummingbirds, monarchs, etc.).
- Include plant type, height, and width when available.
- Focus on pollinator value, not general landscaping advice unless supported by the data.

For recommendations, use this format:
- Common name (Scientific name): pollinators supported. Short reason it matches.

Reference data:
{context}
"""

FUN_FACT_PROMPT = """You share one-sentence fun facts about California native plants or pollinators.
Use the web search results below as your source.
Write exactly ONE sentence. Make it surprising, playful, or little-known.
Do not use bullet points, lists, or multiple sentences.
If the search results are too thin, still give your best single-sentence fun fact and stay factual.

Web search results:
{search_results}

Question: {question}
"""

ROUTER_PROMPT = """You route user questions about California native plants to the right expert agent(s).

Available agents:
- plant: general plant characteristics, size, spread, landscaping use, plant identification, drought tolerance, garden design
- pollinator: bees, butterflies, hummingbirds, monarchs, pollinator gardens, nectar, host plants, wildlife habitat
- fun_fact: trivia, "tell me something interesting", "did you know", surprising facts, casual curiosity about plants or pollinators (not plant recommendations)
- both: if the question needs general plant information and pollinator information from the catalog data

Choose:
- plant: if the question is only about general plant traits or landscaping
- pollinator: if the question is only about pollinators or wildlife support
- fun_fact: if the user wants a fun fact, trivia, or a single interesting snippet rather than recommendations
- both: if the question needs general plant information and pollinator information

Respond with exactly one word: plant, pollinator, fun_fact, or both.

Question: {question}
"""

SYNTHESIS_PROMPT = """You are the lead California native plant assistant.
Combine the expert answers below into one clear, helpful response for the user.
Remove duplicate plant recommendations when possible.
Answer in 250 words or fewer unless the user asked for a long list.

Question: {question}

Plant expert answer:
{plant_answer}

Pollinator expert answer:
{pollinator_answer}
"""


def load_env() -> None:
    dotenv.load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError(
            f"OPENAI_API_KEY is not set. Add it to {PROJECT_ROOT / '.env'}"
        )


def format_docs(documents) -> str:
    return "\n\n".join(doc.page_content for doc in documents)


def load_or_build_vector_store(csv_paths: list[Path], chroma_path: Path, label: str) -> Chroma:
    embeddings = OpenAIEmbeddings()

    if chroma_path.exists():
        return Chroma(
            persist_directory=str(chroma_path),
            embedding_function=embeddings,
        )

    documents = []
    for csv_path in csv_paths:
        if not csv_path.is_file():
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        documents.extend(CSVLoader(file_path=str(csv_path)).load())

    print(f"Building {label} vector store from {len(csv_paths)} file(s)...")
    vector_store = Chroma.from_documents(
        documents,
        embeddings,
        persist_directory=str(chroma_path),
    )
    print(f"Saved {len(documents)} records to {chroma_path}")
    return vector_store


def build_rag_agent(vector_store: Chroma, system_prompt: str):
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{question}"),
        ]
    )
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    return (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
    )


def plant_retriever_agent():
    vector_store = load_or_build_vector_store(
        [PLANTS_CSV_PATH],
        PLANTS_CHROMA_PATH,
        "plant",
    )
    return build_rag_agent(vector_store, PLANT_RETRIEVER_PROMPT)


def pollinator_expert_agent():
    vector_store = load_or_build_vector_store(
        [POLLINATORS_1_CSV_PATH, POLLINATORS_2_CSV_PATH],
        POLLINATORS_CHROMA_PATH,
        "pollinator",
    )
    return build_rag_agent(vector_store, POLLINATOR_EXPERT_PROMPT)


def web_search_fun_fact_agent():
    search = DuckDuckGoSearchRun()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    prompt = ChatPromptTemplate.from_template(FUN_FACT_PROMPT)

    def run(question: str) -> str:
        search_query = f"California native plants pollinators fun fact {question}"
        search_results = search.run(search_query)
        response = (prompt | llm).invoke(
            {"question": question, "search_results": search_results}
        )
        return response.content.strip()

    return run


def route_question(question: str, llm: ChatOpenAI) -> str:
    prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT)
    response = (prompt | llm).invoke({"question": question})
    route = response.content.strip().lower()

    if route in {"plant", "pollinator", "both", "fun_fact"}:
        return route

    if "both" in route:
        return "both"
    if "fun_fact" in route or "fun fact" in route:
        return "fun_fact"
    if "pollinator" in route:
        return "pollinator"
    return "plant"


def synthesize_answers(question: str, plant_answer: str, pollinator_answer: str, llm: ChatOpenAI) -> str:
    prompt = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT)
    response = (prompt | llm).invoke(
        {
            "question": question,
            "plant_answer": plant_answer,
            "pollinator_answer": pollinator_answer,
        }
    )
    return response.content


def agent_orchestrator(plant_agent, pollinator_agent, fun_fact_agent, llm: ChatOpenAI | None = None):
    llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def run(question: str) -> str:
        route = route_question(question, llm)

        if route == "plant":
            return plant_agent.invoke(question).content

        if route == "pollinator":
            return pollinator_agent.invoke(question).content

        if route == "fun_fact":
            return fun_fact_agent(question)

        plant_answer = plant_agent.invoke(question).content
        pollinator_answer = pollinator_agent.invoke(question).content
        return synthesize_answers(question, plant_answer, pollinator_answer, llm)

    return run


def main() -> None:
    load_env()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    print("Loading agents...")
    plant_agent = plant_retriever_agent()
    pollinator_agent = pollinator_expert_agent()
    fun_fact_agent = web_search_fun_fact_agent()
    orchestrator = agent_orchestrator(plant_agent, pollinator_agent, fun_fact_agent, llm)

    print("California Native Plants Multi-Agent Chatbot")
    print("Ask about native plants, pollinators, fun facts, or both. Type 'quit' to exit.\n")

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        route = route_question(question, llm)
        print(f"[Routing to: {route}]")

        response = orchestrator(question)
        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    main()
