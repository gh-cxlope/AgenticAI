"""ISS example as a workflow.

A workflow is a structured sequence of steps.
It can use the model, but the code controls the path:

    1. Get the user question.
    2. Classify what kind of question it is.
    3. If it asks for live ISS location, fetch live ISS data.
    4. Format a standard report.

This is more autonomous than a simple chatbot, but less autonomous than an
agent because the model does not decide what step to take next.

Run from the repo root:
    python 13-01-iss-workflow.py

Optional:
    python 13-01-iss-workflow.py "Where is the ISS right now?"
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

DEFAULT_TASK = "Where is the International Space Station right now?"
MODEL = "gpt-4.1-mini"
TIMEOUT = 60
LIVE_LOCATION = "LIVE_LOCATION"
OTHER = "OTHER"


def get_place_name(latitude: float, longitude: float) -> str:
    reverse_geocode_url = "https://api.bigdatacloud.net/data/reverse-geocode-client"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "localityLanguage": "en",
    }
    response = requests.get(reverse_geocode_url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    place_parts = [
        data.get("locality") or data.get("city"),
        data.get("principalSubdivision"),
        data.get("countryName"),
    ]
    place_name = ", ".join(part for part in place_parts if part)

    return place_name or "an area with no nearby place name"


def fetch_iss_location() -> dict:
    iss_url = "https://api.wheretheiss.at/v1/satellites/25544"
    response = requests.get(iss_url, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    latitude = data["latitude"]
    longitude = data["longitude"]

    return {
        "place_name": get_place_name(latitude, longitude),
        "latitude": round(latitude, 2),
        "longitude": round(longitude, 2),
        "altitude_km": round(data["altitude"], 2),
        "velocity_km_per_hour": round(data["velocity"], 2),
    }


def classify_question(client: OpenAI, task: str) -> str:
    """Use the model for one small workflow step: routing the request."""
    response = client.responses.create(
        model=MODEL,
        input=(
            "Classify this user question as LIVE_LOCATION if it asks where the "
            "International Space Station is right now. Otherwise classify it as OTHER. "
            f"Reply with only LIVE_LOCATION or OTHER.\n\nQuestion: {task}"
        ),
    )
    label = response.output_text.strip().upper()
    return LIVE_LOCATION if LIVE_LOCATION in label else OTHER


def format_iss_report(iss_location: dict) -> str:
    return (
        "Mission Control update: the International Space Station is currently over "
        f"{iss_location['place_name']}.\n\n"
        f"- Coordinates: {iss_location['latitude']}, {iss_location['longitude']}\n"
        f"- Altitude: {iss_location['altitude_km']} km\n"
        f"- Speed: {iss_location['velocity_km_per_hour']} km/h"
    )


def format_out_of_scope_message(task: str) -> str:
    return (
        "This workflow is only designed for live ISS location questions.\n\n"
        f"Your question was: {task}\n\n"
        "Try: Where is the ISS right now?"
    )


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in your .env file.")

    task = " ".join(sys.argv[1:]) or DEFAULT_TASK
    client = OpenAI()

    # In a workflow, the code chooses the path. The model helps inside each
    # step, but it does not decide what step happens next.
    print("Step 1: Get user question")
    print(f"Question: {task}")

    print("Step 2: Classify question")
    question_type = classify_question(client, task)
    print(f"Question type: {question_type}")

    if question_type == LIVE_LOCATION:
        print("Step 3: Fetch live ISS data")
        iss_location = fetch_iss_location()
        print("Step 4: Format standard ISS report")
        answer = format_iss_report(iss_location)
    else:
        print("Step 3: Skip ISS API")
        print("Step 4: Format out-of-scope message")
        answer = format_out_of_scope_message(task)

    print("\nFinal answer:")
    print(answer)


if __name__ == "__main__":
    main()
