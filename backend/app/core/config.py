# d:\\Github\\VerseMind-RAG\\backend\\app\\core\\config.py
from pathlib import Path
import toml

# BACKEND_ROOT is d:/Github/VerseMind-RAG/backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE_PATH = BACKEND_ROOT.parent / "config" / "config.toml"
EXAMPLE_CONFIG_FILE_PATH = BACKEND_ROOT.parent / "config" / "config.example.toml"

class Settings:
    def __init__(self, config_data: dict):
        storage_config = config_data.get("STORAGE", {})
        
        # Get raw values from config or use defaults (relative to BACKEND_ROOT)
        raw_embeddings_dir = storage_config.get("EMBEDDINGS_DIR", "04-embedded-docs/")
        raw_indices_dir = storage_config.get("INDICES_DIR", "storage/indices/")
        raw_documents_dir = storage_config.get("DOCUMENTS_DIR", "01-loaded_docs/") # Example default
        raw_chunks_dir = storage_config.get("CHUNKS_DIR", "02-chunked-docs/")    # Example default
        raw_parsed_dir = storage_config.get("PARSED_DIR", "03-parsed-docs/")      # Example default

        # Construct absolute paths by joining with BACKEND_ROOT
        self.EMBEDDINGS_DIR = str(BACKEND_ROOT / raw_embeddings_dir)
        self.INDICES_DIR = str(BACKEND_ROOT / raw_indices_dir)
        self.DOCUMENTS_DIR = str(BACKEND_ROOT / raw_documents_dir)
        self.CHUNKS_DIR = str(BACKEND_ROOT / raw_chunks_dir)
        self.PARSED_DIR = str(BACKEND_ROOT / raw_parsed_dir)
        
        # Add other settings as needed, for example:
        # self.LOG_LEVEL = config_data.get("LOGGING", {}).get("LEVEL", "INFO")

def load_settings_from_file() -> Settings:
    config_path_to_load = None
    if CONFIG_FILE_PATH.exists():
        config_path_to_load = CONFIG_FILE_PATH
    elif EXAMPLE_CONFIG_FILE_PATH.exists():
        print(f"WARNING: Configuration file {CONFIG_FILE_PATH.name} not found in {CONFIG_FILE_PATH.parent}. "
              f"Falling back to {EXAMPLE_CONFIG_FILE_PATH.name}.")
        config_path_to_load = EXAMPLE_CONFIG_FILE_PATH
    else:
        print(f"ERROR: No configuration file found (checked {CONFIG_FILE_PATH} and {EXAMPLE_CONFIG_FILE_PATH}). "
              "Using default internal paths which might be incorrect.")
        # Return Settings with default relative paths if no config file is found
        # These defaults inside Settings class will be used, resolved against BACKEND_ROOT
        return Settings({})

    try:
        with config_path_to_load.open("r", encoding="utf-8") as f:
            config_data = toml.load(f)
        print(f"INFO: Successfully loaded configuration from {config_path_to_load}")
        return Settings(config_data)
    except Exception as e:
        print(f"ERROR: Could not load TOML file {config_path_to_load}: {e}. "
              "Using default internal paths which might be incorrect.")
        return Settings({})

settings = load_settings_from_file()

# For debugging purposes during startup:
print(f"DEBUG [core.config]: Initialized settings. Effective paths:")
print(f"DEBUG [core.config]:   EMBEDDINGS_DIR='{settings.EMBEDDINGS_DIR}'")
print(f"DEBUG [core.config]:   INDICES_DIR='{settings.INDICES_DIR}'")
print(f"DEBUG [core.config]:   DOCUMENTS_DIR='{settings.DOCUMENTS_DIR}'")
print(f"DEBUG [core.config]:   CHUNKS_DIR='{settings.CHUNKS_DIR}'")
print(f"DEBUG [core.config]:   PARSED_DIR='{settings.PARSED_DIR}'")

