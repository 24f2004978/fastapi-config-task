import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def to_value(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        return str(value).strip().lower() in {"true", "1", "yes", "on"}

    return str(value)


def normalize_key(key):
    key = key.strip()

    aliases = {
        "NUM_WORKERS": "workers",
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }

    return aliases.get(key, key)


def load_config(overrides):
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    yaml_path = Path("config.development.yaml")
    if yaml_path.exists():
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}

        for key, value in yaml_config.items():
            config[normalize_key(key)] = to_value(normalize_key(key), value)

    # Layer 3: .env
    env_file = Path(".env")
    if env_file.exists():
        dotenv_config = dotenv_values(env_file)

        for key, value in dotenv_config.items():
            if value is None:
                continue

            normalized = normalize_key(key)
            config[normalized] = to_value(normalized, value)

    # Layer 4: OS environment variables
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            normalized = normalize_key(key)
            config[normalized] = to_value(normalized, value)

    # Highest precedence: CLI/query overrides
    for item in overrides:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        config[key] = to_value(key, value)

    # Return only the required keys
    result = {
        "port": config["port"],
        "workers": config["workers"],
        "debug": config["debug"],
        "log_level": config["log_level"],
        "api_key": "****",
    }

    return result


@app.get("/effective-config")
def effective_config(set: list[str] | None = Query(default=None)):
    return load_config(set or [])
