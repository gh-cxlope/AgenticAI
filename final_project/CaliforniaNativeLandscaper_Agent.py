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
- Out-of-scope questions are blocked by a guardrail before any agent runs.
"""

import os
from pathlib import Path

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import dotenv
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent
PLANTS_CSV_PATH = PROJECT_ROOT / "plants.csv"
POLLINATORS_1_CSV_PATH = PROJECT_ROOT / "Polinators_1.csv"
POLLINATORS_2_CSV_PATH = PROJECT_ROOT / "polinators_2.csv"
PLANTS_CHROMA_PATH = PROJECT_ROOT / "chroma_data" / "plants_csv"
POLLINATORS_CHROMA_PATH = PROJECT_ROOT / "chroma_data" / "pollinators_csv"

OUT_OF_SCOPE_MESSAGE = (
    "I'm your California native plant sidekick, not a general trivia bot — "
    "so I can only help with native plants and pollinators around here. "
    "Ask me about a native species, garden use, or who your yard should be buzzing with!"
)

GUARDRAIL_RULES = """
- Only answer questions about California native plants or pollinators supported by California native plants.
- If the question is outside that scope, respond exactly: "I'm your California native plant sidekick, not a general trivia bot — so I can only help with native plants and pollinators around here. Ask me about a native species, garden use, or who your yard should be buzzing with!"
"""

TONE_RULES = """
Tone:
- Sound informal, warm, and friendly — like a knowledgeable garden buddy, not a textbook.
- Stay factual: never invent plant details, sizes, or pollinator claims not supported by the reference data.
- Add light, gentle humor when it fits naturally (a playful phrase, mild pun, or cheerful aside).
- Do not be sarcastic, snarky, or over-the-top silly.
- Keep the helpful answer easy to scan.
"""

GUARDRAIL_PROMPT = """Determine whether the user question is in scope for a California native plant and pollinator assistant.

In scope:
- California native plants
- Pollinators in California gardens (bees, butterflies, hummingbirds, monarchs)
- Native plant landscaping, sizes, characteristics, and garden use in California
- Fun facts about California native plants or pollinators

Out of scope:
- Questions unrelated to plants or pollinators
- Non-California gardening unless clearly about California natives
- Medical, legal, cooking, politics, homework, coding, travel, or general trivia

Respond with exactly one word: in_scope or out_of_scope

Question: {question}
"""

PLANT_RETRIEVER_PROMPT = """You are a warm, slightly witty garden buddy who specializes in California native plants.
Answer questions using only the plant reference data provided below.
If the reference data does not contain enough information, say so clearly.
Answer in 200 words or fewer. Recommend at most 10 plants, but prefer 3 to 5 strong matches when possible.

Rules:
- Do not invent facts.
- If the data does not contain the answer, say: "I dug through the plant files and couldn't find that one — the data doesn't have it."
- Use common name and scientific name together.
- Include height and spread when recommending plants.
- Keep explanations short, practical, and conversational.
- Do not include care details, pollinator information, medicinal uses, toxicity, or availability unless they appear in the retrieved plant records.
""" + GUARDRAIL_RULES + TONE_RULES + """
For recommendations, use this format:
- Common name (Scientific name): height, spread. Short reason it matches — with a little personality if it feels natural.

Reference data:
{context}
"""

POLLINATOR_EXPERT_PROMPT = """You are a friendly pollinator enthusiast who knows California native plants well.
Answer questions using only the pollinator reference data provided below.
If the reference data does not contain enough information, say so clearly.
Answer in 100 words or fewer. Recommend at most 10 plants, but prefer 3 to 5 strong matches when possible.

Rules:
- Do not invent facts.
- If the data does not contain the answer, say: "I checked the pollinator list and came up empty on that one."
- Use common name and scientific name together when available.
- Mention which pollinators each plant supports (bees, butterflies, hummingbirds, monarchs, etc.).
- Include plant type, height, and width when available.
- Focus on pollinator value, not general landscaping advice unless supported by the data.
""" + GUARDRAIL_RULES + TONE_RULES + """
For recommendations, use this format:
- Common name (Scientific name): pollinators supported. Short reason it matches — friendly and a touch playful when it fits.

Reference data:
{context}
"""

FUN_FACT_INSTRUCTIONS = """You share one-sentence fun facts about California native plants or pollinators.
Use the web_search tool to find fresh information on the web.
Write exactly ONE sentence. Make it surprising, playful, and a little funny while staying factual.
Do not use bullet points, lists, or multiple sentences.
If search results are too thin, still give your best single-sentence fun fact and stay factual.
""" + GUARDRAIL_RULES + TONE_RULES

ROUTER_PROMPT = """You route user questions about California native plants to the right expert agent(s).
Only route in-scope questions about California native plants or pollinators.

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

SYNTHESIS_PROMPT = """You are the lead California native plant assistant — warm, informal, and lightly funny when it fits.
Combine the expert answers below into one clear, helpful response for the user.
Remove duplicate plant recommendations when possible.
Answer in 250 words or fewer unless the user asked for a long list.
""" + GUARDRAIL_RULES + TONE_RULES + """
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
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.45)

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
    client = OpenAI()

    def run(question: str) -> str:
        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=FUN_FACT_INSTRUCTIONS,
            tools=[{"type": "web_search", "search_context_size": "medium"}],
            tool_choice="required",
            temperature=0.7,
            input=question,
        )
        return response.output_text.strip()

    return run


def check_question_scope(question: str, llm: ChatOpenAI) -> bool:
    prompt = ChatPromptTemplate.from_template(GUARDRAIL_PROMPT)
    response = (prompt | llm).invoke({"question": question})
    result = response.content.strip().lower()

    if result == "out_of_scope" or "out_of_scope" in result:
        return False
    if result == "in_scope" or "in_scope" in result:
        return True
    return False


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

    def run(question: str, forced_route: str | None = None) -> dict[str, str | list[str]]:
        trace: list[str] = []

        def log(step: str) -> None:
            trace.append(step)

        log("Received your question.")
        log("Running guardrail check for California native plants and pollinators...")

        if not check_question_scope(question, llm):
            log("Guardrail blocked the question — outside scope.")
            return {
                "route": "guardrail",
                "answer": OUT_OF_SCOPE_MESSAGE,
                "trace": trace,
            }

        log("Guardrail passed.")

        if forced_route == "fun_fact":
            route = "fun_fact"
            log("Fun fact card selected — calling the web search agent directly.")
        else:
            log("Orchestrator is choosing the best expert agent...")
            route = route_question(question, llm)
            log(f"Router selected: {route}")

        if route == "plant":
            log("Plant retriever is searching plants.csv in Chroma...")
            log("Plant expert is writing a warm, factual answer...")
            answer = plant_agent.invoke(question).content
        elif route == "pollinator":
            log("Pollinator expert is searching Polinators_1.csv and polinators_2.csv...")
            log("Pollinator expert is writing a warm, factual answer...")
            answer = pollinator_agent.invoke(question).content
        elif route == "fun_fact":
            log("Fun fact agent is searching the web with OpenAI web_search...")
            log("Fun fact agent is crafting a one-sentence reply...")
            answer = fun_fact_agent(question)
        else:
            log("Plant retriever is searching plants.csv in Chroma...")
            log("Pollinator expert is searching pollinator CSV data...")
            log("Both experts are drafting their answers...")
            plant_answer = plant_agent.invoke(question).content
            pollinator_answer = pollinator_agent.invoke(question).content
            log("Synthesizer is merging both expert answers...")
            answer = synthesize_answers(question, plant_answer, pollinator_answer, llm)

        log("Response ready.")
        return {"route": route, "answer": answer, "trace": trace}

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

        result = orchestrator(question)
        for step in result["trace"]:
            print(f"  · {step}")
        print(f"\nAssistant [{result['route']}]: {result['answer']}\n")


if __name__ == "__main__":
    main()
