from dataclasses import dataclass
from typing import Dict, Any
import math

@dataclass
class HypState:
    scores: Dict[str, float]

def softmax(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    mx = max(scores.values())
    exps = {k: math.exp(v-mx) for k,v in scores.items()}
    s = sum(exps.values()) or 1.0
    return {k: exps[k]/s for k in exps}

def ema_update(prev: Dict[str,float], new: Dict[str,float], alpha: float=0.35) -> Dict[str,float]:
    out = dict(prev)
    for k,v in new.items():
        out[k] = out.get(k,0.0)*(1-alpha) + v*alpha
    return out

def apply_gating(scores: Dict[str,float], disorders: Dict[str,Any], age_years: int|None) -> Dict[str,float]:
    gated = dict(scores)
    for did,s in list(gated.items()):
        spec = disorders.get(did)
        if not spec:
            gated[did]=0.0
            continue
        g = spec.get("gating",{})
        if age_years is not None:
            age_min = g.get("age_min")
            age_max = g.get("age_max")
            if age_min is not None and age_years < int(age_min):
                gated[did]=0.0
            if age_max is not None and age_years > int(age_max):
                gated[did]=0.0
    return gated

def pick_top(scores: Dict[str,float]) -> str|None:
    if not scores:
        return None
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else None
