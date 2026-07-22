"""Central resource paths for the self-contained v2 workspace."""

from pathlib import Path

V2_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = V2_ROOT / "config"
PROMPT_DIR = V2_ROOT / "prompts"
INPUT_DIR = V2_ROOT / "data" / "input" / "sampe_2"
ARTIFACT_DIR = V2_ROOT / "artifacts"
