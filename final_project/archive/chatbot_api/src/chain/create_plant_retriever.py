import os

# Chroma/OpenTelemetry need this when protobuf versions conflict in the venv.
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import dotenv
from langchain_community.document_loaders import CSVLoader, DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PLANT_DESCRIPTIONS_PATH = PROJECT_ROOT / "descriptions"
PLANTS_CSV_PATH = PROJECT_ROOT / "plants.csv"
PLANTS_CHROMA_PATH = PROJECT_ROOT / "chroma_data" / "plants"

dotenv.load_dotenv(PROJECT_ROOT / ".env")

if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError(
        f"OPENAI_API_KEY is not set. Add it to {PROJECT_ROOT / '.env'}"
    )

if not PLANT_DESCRIPTIONS_PATH.is_dir():
    raise FileNotFoundError(f"Descriptions folder not found: {PLANT_DESCRIPTIONS_PATH}")

if not PLANTS_CSV_PATH.is_file():
    raise FileNotFoundError(f"Plants CSV not found: {PLANTS_CSV_PATH}")

description_loader = DirectoryLoader(
    str(PLANT_DESCRIPTIONS_PATH),
    glob="*.txt",
    loader_cls=TextLoader,
    loader_kwargs={"encoding": "utf-8"},
)

csv_loader = CSVLoader(file_path=str(PLANTS_CSV_PATH))

plant_descriptions = description_loader.load()
plant_records = csv_loader.load()
all_plant_documents = plant_descriptions + plant_records

plants_vector_db = Chroma.from_documents(
    all_plant_documents,
    OpenAIEmbeddings(),
    persist_directory=str(PLANTS_CHROMA_PATH),
)

print(f"Loaded {len(plant_descriptions)} description files from {PLANT_DESCRIPTIONS_PATH}")
print(f"Loaded {len(plant_records)} plant records from {PLANTS_CSV_PATH}")
print(f"Vector store saved to {PLANTS_CHROMA_PATH}")
