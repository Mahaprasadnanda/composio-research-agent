"""Configuration management for Composio Research Agent.

Loads environment variables from .env using python-dotenv and validates
required credentials with strict security practices to prevent secret leakage.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Base directories
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
PLACEHOLDER_MARKERS = {
    "your_groq_api_key_here",
    "your_composio_api_key_here",
    "placeholder",
    "xxx",
    "todo",
}


class ConfigurationError(ValueError):
    """Raised when application configuration or required credentials are invalid or missing."""


def mask_secret(secret: Optional[str], visible_prefix: int = 3, visible_suffix: int = 2) -> str:
    """Safely mask a secret string for logging or debugging.

    Never exposes full secret content. Returns '[NOT SET]' if None or empty/whitespace.
    """
    if not secret or not secret.strip():
        return "[NOT SET]"
    cleaned = secret.strip()
    if len(cleaned) <= (visible_prefix + visible_suffix):
        return "***REDACTED***"
    return f"{cleaned[:visible_prefix]}...{cleaned[-visible_suffix:]}"


@dataclass(frozen=True)
class Settings:
    """Immutable application settings container.

    Secrets are masked in __repr__ and __str__ to prevent accidental leaks in logs.
    """

    groq_api_key: str
    composio_api_key: str
    groq_model: str = DEFAULT_GROQ_MODEL
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    output_dir: Path = OUTPUT_DIR

    def __repr__(self) -> str:
        """Return safe string representation masking all credentials."""
        return (
            f"Settings("
            f"groq_api_key='{mask_secret(self.groq_api_key)}', "
            f"composio_api_key='{mask_secret(self.composio_api_key)}', "
            f"groq_model='{self.groq_model}', "
            f"project_root='{self.project_root}', "
            f"data_dir='{self.data_dir}', "
            f"output_dir='{self.output_dir}'"
            f")"
        )

    def __str__(self) -> str:
        """Return safe string representation."""
        return self.__repr__()


def check_missing_credentials(
    env: Optional[dict[str, str]] = None,
) -> list[str]:
    """Inspect environment dictionary for missing or placeholder credentials.

    Returns a list of human-readable error descriptions for missing variables.
    """
    source = os.environ if env is None else env
    missing: list[str] = []

    groq_key = source.get("GROQ_API_KEY", "").strip()
    if not groq_key or groq_key.lower() in PLACEHOLDER_MARKERS:
        missing.append(
            "GROQ_API_KEY is not set or contains placeholder text. "
            "Get a free API key at https://console.groq.com/keys and configure it in .env."
        )

    composio_key = source.get("COMPOSIO_API_KEY", "").strip()
    if not composio_key or composio_key.lower() in PLACEHOLDER_MARKERS:
        missing.append(
            "COMPOSIO_API_KEY is not set or contains placeholder text. "
            "Get your Composio key at https://app.composio.dev/settings and configure it in .env."
        )

    return missing


def load_settings(
    env_file: Optional[Path | str] = None,
    override: bool = False,
) -> Settings:
    """Load and validate settings from environment variables and .env file.

    Args:
        env_file: Optional path to an explicit .env file. Defaults to PROJECT_ROOT / .env.
        override: Whether to override existing environment variables with values from .env.

    Returns:
        Settings: Validated, immutable Settings instance.

    Raises:
        ConfigurationError: If any required credentials are missing or set to placeholder text.
    """
    if env_file is not None:
        target_path = Path(env_file)
        if target_path.exists():
            load_dotenv(dotenv_path=target_path, override=override)
    else:
        default_env = PROJECT_ROOT / ".env"
        if default_env.exists():
            load_dotenv(dotenv_path=default_env, override=override)

    errors = check_missing_credentials()
    if errors:
        bullet_points = "\n  - ".join(errors)
        raise ConfigurationError(
            f"Application configuration failed due to missing required credentials:\n  - {bullet_points}\n\n"
            f"Action required: Copy .env.example to .env and configure real credentials."
        )

    groq_api_key = os.environ["GROQ_API_KEY"].strip()
    composio_api_key = os.environ["COMPOSIO_API_KEY"].strip()
    groq_model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL

    return Settings(
        groq_api_key=groq_api_key,
        composio_api_key=composio_api_key,
        groq_model=groq_model,
        project_root=PROJECT_ROOT,
        data_dir=DATA_DIR,
        output_dir=OUTPUT_DIR,
    )
