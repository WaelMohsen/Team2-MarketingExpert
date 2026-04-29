import json
import os
from datetime import datetime
from typing import Dict, List, Optional

_JSON_EXT = ".json"


def list_json_files(directory: str) -> List[str]:
    if not os.path.exists(directory):
        return []
    return sorted(
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.endswith(_JSON_EXT)
    )


def safe_read_json(path: str) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extract_timestamp_from_filename(path: str) -> Optional[datetime]:
    basename = os.path.basename(path)
    if not basename.startswith("eval_") or not basename.endswith(_JSON_EXT):
        return None
    raw = basename.replace("eval_", "").replace(_JSON_EXT, "")
    try:
        return datetime.strptime(raw, "%Y%m%d_%H%M%S")
    except ValueError:
        return None
