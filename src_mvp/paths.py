"""Default paths for the standalone MVP package."""

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = PACKAGE_DIR / "config"
INPUT_DIR = PACKAGE_DIR / "data" / "input" / "sample_2"
ARTIFACT_DIR = PACKAGE_DIR / "artifacts"
PROMPT_DIR = PACKAGE_DIR / "prompts"
OUTPUT_DIR = PACKAGE_DIR / "outputs"

