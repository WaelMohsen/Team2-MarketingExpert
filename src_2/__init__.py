"""Version-two marketing reporting architecture.

The existing ``src`` package remains operational while this package evolves
behind stable data and intelligence contracts.
"""

from .paths import ARTIFACT_DIR, CONFIG_DIR, INPUT_DIR, PROMPT_DIR, V2_ROOT

__all__ = ["ARTIFACT_DIR", "CONFIG_DIR", "INPUT_DIR", "PROMPT_DIR", "V2_ROOT"]
