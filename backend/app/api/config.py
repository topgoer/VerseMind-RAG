# backend/app/api/config.py
from pathlib import Path
from fastapi import APIRouter, HTTPException
import toml

router = APIRouter()

# 明确项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def get_config_path() -> Path:
    config_path = PROJECT_ROOT / "config" / "config.toml"
    example_path = PROJECT_ROOT / "config" / "config.example.toml"
    print(f"[DEBUG] PROJECT_ROOT={PROJECT_ROOT}")
    if config_path.exists():
        return config_path
    if example_path.exists():
        return example_path
    raise FileNotFoundError("No configuration file found in config directory")

@router.get("/config")
def get_config():
    print("[DEBUG] get_config() called")
    try:
        config_path = get_config_path()
        with config_path.open("r", encoding="utf-8") as f:
            config = toml.load(f)
        return config
    except Exception as e:
        print(f"[API/config] Error loading config: {e}")
        raise HTTPException(status_code=500, detail=f"Config load error: {e}")

