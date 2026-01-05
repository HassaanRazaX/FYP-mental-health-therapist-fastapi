from __future__ import annotations
from typing import Any, Dict, List, Tuple
from .eval import safe_eval
import math

STATUS_MET="MET"
STATUS_NOT_MET="NOT_MET"
STATUS_UNKNOWN="UNKNOWN"

OUTCOME_INSUFFICIENT="INSUFFICIENT"
OUTCOME_POSSIBLE="POSSIBLE_MATCH"
OUTCOME_PROBABLE="PROBABLE_MATCH"
OUTCOME_EXCLUDED="EXCLUDED"

def _coverage(required_slots: List[str], slots: Dict[str, Any]) -> float:
    if not required_slots:
        return 1.0
    have = sum(1 for s in required_slots if slots.get(s) is not None)
    return have / len(required_slots)

def evaluate_disorder(spec: Dict[str, Any], slots: Dict[str, Any]) -> Dict[str, Any]:
    criteria_table = {}
    core = spec.get("criteria", {}).get("core", [])
    exclusions = spec.get("criteria", {}).get("exclusions", [])
    all_crit = core + exclusions

    total_required = 0
    total_have = 0
    core_met = 0
    core_known = 0

    # evaluate criteria
    for c in all_crit:
        cid = c["id"]
        required = c.get("slots_required", [])
        total_required += len(required)
        total_have += sum(1 for s in required if slots.get(s) is not None)

        names = {k: slots.get(k) for k in set(required + list(slots.keys()))}
        status = STATUS_UNKNOWN
        rationale = "Missing required information."
        missing = [s for s in required if slots.get(s) is None]

        if not missing:
            try:
                ok = safe_eval(c["rule"], names)
            except Exception as e:
                ok = False
            status = STATUS_MET if ok else STATUS_NOT_MET
            rationale = "Rule evaluated deterministically."
        if c in core:
            if status != STATUS_UNKNOWN:
                core_known += 1
            if status == STATUS_MET:
                core_met += 1

        criteria_table[cid] = {
            "label": c.get("label",""),
            "status": status,
            "evidence": {s: slots.get(s) for s in required},
            "missing": missing,
        }

    coverage = (total_have / total_required) if total_required else 0.0

    # exclusions
    for c in exclusions:
        cid = c["id"]
        row = criteria_table[cid]
        if row["status"] == STATUS_MET and c.get("effect") == OUTCOME_EXCLUDED:
            return {
                "outcome": OUTCOME_EXCLUDED,
                "confidence": 0.05,
                "coverage": coverage,
                "core_met": core_met,
                "core_known": core_known,
                "criteria_table": criteria_table,
            }

    thr = spec.get("thresholds", {})
    probable_min_core = int(thr.get("probable_min_core_met", max(1, len(core)//2)))
    probable_min_cov = float(thr.get("probable_min_coverage", 0.7))

    # Determine rubric sufficiency: need some core known
    if core_known == 0 or coverage < 0.34:
        return {
            "outcome": OUTCOME_INSUFFICIENT,
            "confidence": 0.1 + 0.2*coverage,
            "coverage": coverage,
            "core_met": core_met,
            "core_known": core_known,
            "criteria_table": criteria_table,
        }

    # Probable only if enough evidence AND enough core criteria MET
    if core_met >= probable_min_core and coverage >= probable_min_cov:
        conf = min(0.95, 0.35 + 0.6*coverage)
        return {
            "outcome": OUTCOME_PROBABLE,
            "confidence": conf,
            "coverage": coverage,
            "core_met": core_met,
            "core_known": core_known,
            "criteria_table": criteria_table,
        }

    # Possible if at least 1 core met and some coverage
    if core_met >= 1 and coverage >= 0.5:
        conf = min(0.8, 0.25 + 0.5*coverage)
        return {
            "outcome": OUTCOME_POSSIBLE,
            "confidence": conf,
            "coverage": coverage,
            "core_met": core_met,
            "core_known": core_known,
            "criteria_table": criteria_table,
        }

    return {
        "outcome": OUTCOME_INSUFFICIENT,
        "confidence": min(0.6, 0.15 + 0.4*coverage),
        "coverage": coverage,
        "core_met": core_met,
        "core_known": core_known,
        "criteria_table": criteria_table,
    }

def missing_slots(spec: Dict[str, Any], slots: Dict[str, Any]) -> List[str]:
    missing = []
    for c in spec.get("criteria", {}).get("core", []):
        for s in c.get("slots_required", []):
            if slots.get(s) is None and s not in missing:
                missing.append(s)
    for c in spec.get("criteria", {}).get("exclusions", []):
        for s in c.get("slots_required", []):
            if slots.get(s) is None and s not in missing:
                missing.append(s)
    return missing
