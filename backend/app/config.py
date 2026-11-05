from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

CLASS_NAMES = {
    0: "No DR",
    1: "Mild DR",
    2: "Moderate DR",
    3: "Severe DR",
    4: "Proliferative DR",
}
IMAGE_SIZE = (224, 224)
PREPROCESSING_VERSION = "edgeretina-preprocess-v1"
SEED = 42


def env_path(name: str, default: str) -> Path:
    value = os.getenv(name, default)
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    CSV_PATH = env_path("APTOS_CSV_PATH", "data/raw/train.csv")
    IMAGE_DIR = env_path("APTOS_IMAGE_DIR", "data/raw/train_images")
    MODEL_PATH = env_path("MODEL_PATH", "models/global/edgeretina_global.keras")
    MODEL_METADATA_PATH = env_path("MODEL_METADATA_PATH", "models/global/metadata.json")
    DATABASE_PATH = env_path("DATABASE_PATH", "data/edgeretina.db")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))
