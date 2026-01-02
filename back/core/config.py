"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import json
from typing import Any, List
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def env_flag(name: str) -> bool:
    """Convert an environment variable to a boolean flag (default is False).

    Args:
        name: The name of the environment variable.

    Returns:
        bool: True if the environment variable equals 'true'
            (case-insensitive), False otherwise.
    """
    return os.getenv(name, "false").strip().lower() == "true"


def compose_database_url_from_env(default: str) -> str:
    """Compose the database URL from its individual components. This is neccesary when
    some parts of the URLs are kept as secrets in cloud environments.

    Args:
        default: The default database URL to use if environment variables are not set.

    Returns:
        str: The composed database URL or the default if components are missing.
    """
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    if (
        host is None
        or port is None
        or username is None
        or password is None
        or name is None
    ):
        return default
    return f"postgresql://{username}:{password}@{host}:{port}/{name}"


class Settings(BaseSettings):
    """Application settings."""

    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database
    DATABASE_URL: str = compose_database_url_from_env(
        os.getenv("DATABASE_URL", "postgresql://velosim:velosim@localhost:5433/velosim")
    )

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React Dev Server
        "http://localhost:5173",  # Vite Dev Server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> Any:
        """
        Needed to pass this parameter via CLI, because it is a string and not a List:
        - JSON array string: '["https://a.com","https://b.com"]'
        - Comma-separated string: "https://a.com, https://b.com"
        - Single string: "https://a.com"
        - List[str]

        Args:
            v: The value to parse (can be str, list, or None).

        Returns:
            Any: Parsed list of allowed origins or the original value.
        """
        if v is None:
            return v
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            s = v.strip()
            # Try JSON array first
            if s.startswith("["):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed]
                except Exception:
                    pass
            # Fallback to comma-separated or single value
            if "," in s:
                return [p.strip() for p in s.split(",") if p.strip()]
            return [s]
        return v

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Runtime behaviour settings
    # Controls how long (in seconds) that a simulation may remain idle without
    # an active WebSocket connection and subscriber, before being shut down.
    # Defaults to 15 seconds.
    SIMULATION_IDLE_TIMEOUT_SECONDS: int = int(
        os.getenv("SIMULATION_IDLE_TIMEOUT_SECONDS", "15")
    )

    # Keyframe persistence settings
    # Controls the interval for persisting keyframes to the database.
    # For example, a value of 5 means every 5th keyframe is persisted.
    # Defaults to 5 (persist every 5th keyframe).
    # Must be between 1 and 1000 to prevent system issues.
    KEYFRAME_PERSIST_INTERVAL: int = Field(
        default=int(os.getenv("KEYFRAME_PERSIST_INTERVAL", "5")),
        ge=1,
        le=1000,
    )

    # Maximum size of the keyframe persistence queue.
    # If the queue fills up, random frames will be dropped with a warning.
    # Defaults to 1000 frames.
    KEYFRAME_QUEUE_MAX_SIZE: int = int(os.getenv("KEYFRAME_QUEUE_MAX_SIZE", "1000"))

    # Maximum time to wait for keyframe queue to drain during shutdown (seconds).
    # This allows pending keyframes to be persisted before simulation deletion.
    # Defaults to 5 seconds.
    KEYFRAME_DRAIN_TIMEOUT: float = float(os.getenv("KEYFRAME_DRAIN_TIMEOUT", "5.0"))

    # Feature flags
    FEATURE_RESOURCES_API_ROUTER: bool = env_flag("FEATURE_RESOURCES_API_ROUTER")

    model_config = SettingsConfigDict(case_sensitive=True)


# Global settings instance
settings = Settings()
