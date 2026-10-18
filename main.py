import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS: dict[str, Any] = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

TYPE_RULES = {
    "port": "int",
    "workers": "int",
    "debug": "bool",
}

def coerce(key: str, value: Any) -> Any:
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "on"}
    return str(value)

def normalize_layer(layer: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for raw_key, value in layer.items():
        key = str(raw_key).strip().lower()
        if key.startswith("app_"):
            key = key[4:]
        if key == "num_workers":
            key = "workers"
        normalized[key] = coerce(key, value)
    return normalized

def read_effective_config(cli_sets: list[str]) -> dict[str, Any]:
    # 1. Hardcoded defaults (lowest precedence)
    config = dict(DEFAULTS)

    # 2. Environment-specific YAML
    environment = os.getenv("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{environment}.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_layer = yaml.safe_load(file) or {}
        config.update(normalize_layer(yaml_layer))

    # 3. .env layer (read separately so OS values remain higher precedence)
    env_path = BASE_DIR / ".env"
    dotenv_layer = dotenv_values(env_path) if env_path.exists() else {}
    config.update(normalize_layer({k: v for k, v in dotenv_layer.items() if v is not None}))

    # 4. OS-level APP_* variables, which override .env
    os_layer = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("APP_")
    }
    config.update(normalize_layer(os_layer))
    if os.getenv("PORT"):
    config["port"] = int(os.getenv("PORT"))

    # 5. CLI query overrides; repeat ?set=key=value as needed
    for item in cli_sets:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key.startswith("app_"):
            key = key[4:]
        if key == "num_workers":
            key = "workers"
        if key:
            config[key] = coerce(key, value)

    # Always mask secrets, regardless of the actual value or source.
    config["api_key"] = "****"
    return config

app = FastAPI(title="TDS Effective Configuration API")

# Allow the assignment page to call the service from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "endpoint": "/effective-config"}

@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    return read_effective_config(set)
