
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware


BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

ALLOWED_KEYS = set(DEFAULTS.keys())


def coerce(key, value):
    """Convert configuration values to their required types."""

    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true", "1", "yes", "on"
        }

    return str(value)


def normalize_layer(layer):
    """Normalize keys and convert values for one config layer."""

    normalized = {}

    for raw_key, value in layer.items():
        if value is None:
            continue

        key = str(raw_key).strip().lower()

        if key.startswith("app_"):
            key = key[4:]

        if key == "num_workers":
            key = "workers"

        # Ignore keys outside the five required settings.
        if key not in ALLOWED_KEYS:
            continue

        normalized[key] = coerce(key, value)

    return normalized


def read_effective_config(cli_sets):
    """Merge config layers in increasing priority order."""

    # 1. Hardcoded defaults
    config = DEFAULTS.copy()

    # 2. Environment-specific YAML
    environment = os.getenv("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{environment}.yaml"

    if yaml_path.is_file():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_layer = yaml.safe_load(file) or {}

        if isinstance(yaml_layer, dict):
            config.update(normalize_layer(yaml_layer))

    # 3. .env file
    env_path = BASE_DIR / ".env"

    if env_path.is_file():
        dotenv_layer = dotenv_values(env_path)
        config.update(normalize_layer(dotenv_layer))

    # 4. OS-level APP_* environment variables
    os_layer = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("APP_")
    }
    config.update(normalize_layer(os_layer))

    # 5. CLI query overrides (highest priority)
    for item in cli_sets or []:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = key.strip().lower()

        if key.startswith("app_"):
            key = key[4:]

        if key == "num_workers":
            key = "workers"

        if key not in ALLOWED_KEYS:
            continue

        config[key] = coerce(key, value)

    # Never reveal the actual API key.
    config["api_key"] = "****"

    return config


app = FastAPI(title="Layered Configuration Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/effective-config")
def effective_config(
    set: list[str] | None = Query(default=None),
):
    return read_effective_config(set)
