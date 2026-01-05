from dataclasses import dataclass
from .acts import ActResult, ACT_CONFUSION, ACT_RESIST, ACT_CRISIS

UNREADY="UNREADY"
WARMING="WARMING"
READY="READY"

@dataclass
class Readiness:
    level: str
    signals: dict

def update_readiness(prev_level: str, act: ActResult, user_text: str) -> Readiness:
    # deterministic: confusion/distress/resistance keeps relational.
    signals = {
        "confusion": act.act == ACT_CONFUSION,
        "resistance": act.act == ACT_RESIST,
        "crisis": act.act == ACT_CRISIS,
        "answered_factually": act.act in ("DIRECT_ANSWER","SYMPTOM_DISCLOSURE"),
    }

    if signals["crisis"]:
        return Readiness(UNREADY, signals)

    if signals["confusion"] or signals["resistance"]:
        return Readiness(UNREADY, signals)

    if prev_level == UNREADY:
        # needs one turn of calm factual response to warm
        if signals["answered_factually"]:
            return Readiness(WARMING, signals)
        return Readiness(UNREADY, signals)

    if prev_level == WARMING:
        if signals["answered_factually"] and len(user_text.strip()) > 1:
            return Readiness(READY, signals)
        return Readiness(WARMING, signals)

    # READY
    if signals["answered_factually"]:
        return Readiness(READY, signals)
    return Readiness(WARMING, signals)
