# d:\\Github\\VerseMind-RAG\\backend\\app\\core\\config.py
from pathlib import Path
import toml
import logging
from app.core.logger import get_logger_with_env_level

# Initialize logger for core.config
# Import here to avoid circular imports
# Will be updated to use get_logger_with_env_level after settings are loaded
logger = logging.getLogger("core.config")

# BACKEND_ROOT is d:/Github/VerseMind-RAG/backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE_PATH = BACKEND_ROOT.parent / "config" / "config.toml"
EXAMPLE_CONFIG_FILE_PATH = BACKEND_ROOT.parent / "config" / "config.example.toml"


class Settings:
    def __init__(self, config_data: dict):
        storage_config = config_data.get(
            "STORAGE", {}
        )  # Get raw values from config or use defaults (relative to BACKEND_ROOT)
        # These paths should be relative to the backend directory, not project root
        raw_embeddings_dir = storage_config.get("EMBEDDINGS_DIR", "04-embedded-docs/")
        raw_indices_dir = storage_config.get(
            "INDICES_DIR", "../storage/indices/"
        )  # Updated path to match with vector_store paths
        raw_documents_dir = storage_config.get(
            "DOCUMENTS_DIR", "01-loaded_docs/"
        )  # Relative to backend directory
        raw_chunks_dir = storage_config.get(
            "CHUNKS_DIR", "02-chunked-docs/"
        )  # Relative to backend directory
        raw_parsed_dir = storage_config.get(
            "PARSED_DIR", "03-parsed-docs/"
        )  # Relative to backend directory

        # Construct absolute paths by joining with BACKEND_ROOT
        self.EMBEDDINGS_DIR = str(BACKEND_ROOT / raw_embeddings_dir)
        self.INDICES_DIR = str(BACKEND_ROOT / raw_indices_dir)
        self.DOCUMENTS_DIR = str(BACKEND_ROOT / raw_documents_dir)
        self.CHUNKS_DIR = str(BACKEND_ROOT / raw_chunks_dir)
        self.PARSED_DIR = str(BACKEND_ROOT / raw_parsed_dir)

        # Vector store configuration
        vector_store_config = config_data.get("vector_store", {})
        self.VECTOR_STORE_TYPE = vector_store_config.get("type", "faiss")
        raw_persist_directory = vector_store_config.get(
            "persist_directory", "./storage/vector_db"
        )
        self.VECTOR_STORE_PERSIST_DIR = str(
            BACKEND_ROOT.parent / raw_persist_directory.lstrip("./")
        )

        # FAISS specific configuration
        faiss_config = vector_store_config.get("faiss", {})
        self.FAISS_INDEX_TYPE = faiss_config.get("index_type", "HNSW32")
        self.FAISS_METRIC = faiss_config.get("metric", "cosine")

        # Chroma specific configuration
        chroma_config = vector_store_config.get("chroma", {})
        self.CHROMA_COLLECTION_NAME = chroma_config.get(
            "collection_name", "versemind_docs"
        )
        self.CHROMA_DISTANCE_FUNCTION = chroma_config.get("distance_function", "cosine")

        # Add other settings as needed, for example:
        # self.LOG_LEVEL = config_data.get("LOGGING", {}).get("LEVEL", "INFO")


def load_settings_from_file() -> Settings:
    config_path_to_load = None
    if CONFIG_FILE_PATH.exists():
        config_path_to_load = CONFIG_FILE_PATH
    elif EXAMPLE_CONFIG_FILE_PATH.exists():
        logger.warning(
            f"Configuration file {CONFIG_FILE_PATH.name} not found in {CONFIG_FILE_PATH.parent}. "
            f"Falling back to {EXAMPLE_CONFIG_FILE_PATH.name}."
        )
        config_path_to_load = EXAMPLE_CONFIG_FILE_PATH
    else:
        logger.error(
            f"No configuration file found (checked {CONFIG_FILE_PATH} and {EXAMPLE_CONFIG_FILE_PATH}). "
            "Using default internal paths which might be incorrect."
        )
        # Return Settings with default relative paths if no config file is found
        # These defaults inside Settings class will be used, resolved against BACKEND_ROOT
        return Settings({})

    try:
        with config_path_to_load.open("r", encoding="utf-8") as f:
            config_data = toml.load(f)
        logger.info(f"Successfully loaded configuration from {config_path_to_load}")
        return Settings(config_data)
    except Exception as e:
        logger.error(
            f"Could not load TOML file {config_path_to_load}: {e}. "
            "Using default internal paths which might be incorrect."
        )
        return Settings({})


settings = load_settings_from_file()

# For debugging purposes during startup:
logger.debug("Initialized settings. Effective paths:")
logger.debug(f"  EMBEDDINGS_DIR='{settings.EMBEDDINGS_DIR}'")
logger.debug(f"  INDICES_DIR='{settings.INDICES_DIR}'")
logger.debug(f"  DOCUMENTS_DIR='{settings.DOCUMENTS_DIR}'")
logger.debug(f"  CHUNKS_DIR='{settings.CHUNKS_DIR}'")
logger.debug(f"  PARSED_DIR='{settings.PARSED_DIR}'")

# At this point, we can safely import the logger utility without circular import concerns
# Update the logger to use our environment-based logging utility
logger = get_logger_with_env_level(__name__)
