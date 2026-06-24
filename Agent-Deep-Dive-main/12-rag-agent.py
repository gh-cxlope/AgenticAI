"""Beginner-friendly RAG agent using local .txt files.

RAG means:
    1. Split your documents into chunks.
    2. Turn each chunk into an embedding.
    3. Retrieve the chunks most similar to the question.
    4. Ask the model to answer using only those chunks.

Run from the repo root:
    python 12-rag-agent.py

Optional:
    python 12-rag-agent.py "How are sea lions different from seals?"

Try editing or adding `.txt` files in the `rag_docs` folder, then run the
script again.
"""

from __future__ import annotations

import asyncio
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from agents import Agent, Runner
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

DEFAULT_QUESTION = "How are sea lions different from seals?"
DOCS_FOLDER = Path("rag_docs")
MODEL = "gpt-4.1-mini"
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_CHARS_PER_CHUNK = 900
TOP_K = 3


@dataclass
class Chunk:
    filename: str
    text: str
    similarity: float = 0.0


def split_into_chunks(filename: str, text: str) -> list[Chunk]:
    """Split one document into small chunks that fit easily in a prompt."""
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[Chunk] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= MAX_CHARS_PER_CHUNK:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(Chunk(filename=filename, text=current))
            current = paragraph

    if current:
        chunks.append(Chunk(filename=filename, text=current))

    return chunks


def load_txt_chunks(folder: Path) -> list[Chunk]:
    """Load every .txt file in the RAG folder."""
    if not folder.exists():
        raise RuntimeError(f"Create a folder named {folder} with at least one .txt file.")

    chunks: list[Chunk] = []
    for path in sorted(folder.glob("*.txt")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            chunks.extend(split_into_chunks(path.name, text))

    if not chunks:
        raise RuntimeError(f"Add at least one non-empty .txt file to {folder}.")

    return chunks


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot_product = sum(a_value * b_value for a_value, b_value in zip(a, b))
    a_length = math.sqrt(sum(a_value * a_value for a_value in a))
    b_length = math.sqrt(sum(b_value * b_value for b_value in b))
    return dot_product / (a_length * b_length)


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def retrieve(
    question: str,
    chunks: list[Chunk],
    client: OpenAI,
    top_k: int = TOP_K,
) -> list[Chunk]:
    """Find chunks whose embeddings are closest to the question embedding."""
    texts = [question] + [chunk.text for chunk in chunks]
    embeddings = embed_texts(client, texts)
    question_embedding = embeddings[0]
    chunk_embeddings = embeddings[1:]

    ranked_chunks: list[Chunk] = []
    for chunk, chunk_embedding in zip(chunks, chunk_embeddings):
        ranked_chunks.append(
            Chunk(
                filename=chunk.filename,
                text=chunk.text,
                similarity=cosine_similarity(question_embedding, chunk_embedding),
            )
        )

    return sorted(ranked_chunks, key=lambda chunk: chunk.similarity, reverse=True)[:top_k]


def format_context(chunks: list[Chunk]) -> str:
    """Format retrieved chunks so the model can cite the source filenames."""
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Source {index}: {chunk.filename}]\n{chunk.text}"
        )

    return "\n\n---\n\n".join(context_blocks)


rag_agent = Agent(
    name="Local TXT RAG Assistant",
    instructions=(
        "You answer questions using only the provided document context. "
        "If the answer is not in the context, say you could not find it in the local documents. "
        "Cite the source filename or filenames you used."
    ),
    model=MODEL,
)


async def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    client = OpenAI()
    chunks = load_txt_chunks(DOCS_FOLDER)
    retrieved_chunks = retrieve(question, chunks, client)
    context = format_context(retrieved_chunks)

    print("\nRetrieved context:")
    for chunk in retrieved_chunks:
        print(f"- {chunk.filename} (similarity: {chunk.similarity:.3f})")

    prompt = f"""
Question:
{question}

Document context:
{context}
"""

    result = await Runner.run(rag_agent, prompt)
    print("\nAnswer:")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
