import os, yaml
from typing import Dict, Any

DISORDERS_DIR = os.path.join(os.path.dirname(__file__), "..", "disorders")

def load_disorders() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for fn in os.listdir(DISORDERS_DIR):
        if fn.endswith(".yaml") or fn.endswith(".yml"):
            path = os.path.join(DISORDERS_DIR, fn)
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            out[data["id"]] = data
    return out
