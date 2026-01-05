from dataclasses import dataclass
from typing import Dict, Any, List
import hashlib

RELATIONAL="RELATIONAL"
CLINICAL="CLINICAL"

@dataclass
class Plan:
    track: str
    intent: str
    slot_targets: List[str]
    protected: List[str]
    fingerprint: str

PROTECTED_SLOTS_DEFAULT = {"age_years"}  # can extend: trauma, abuse, etc.

def fingerprint_intent(intent: str, slot_targets: List[str]) -> str:
    raw = intent + "|" + ",".join(slot_targets)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def plan_next(
    readiness: str,
    act: str,
    session_state: Dict[str, Any],
    missing_slots: List[str],
    last_fp: str|None,
) -> Plan:
    # Control inversion: planner decides what to explore next.
    # Rubric only supplies missing evidence; it never dictates phrasing or strict ordering.
    protected = list(PROTECTED_SLOTS_DEFAULT)

    # 1) Crisis / confusion / resistance -> relational
    if act in ("CRISIS",):
        return Plan(RELATIONAL, "crisis_referral", [], protected, fingerprint_intent("crisis_referral", []))
    if readiness != "READY" or act in ("GREETING","SMALL_TALK","CONFUSION","RESISTANCE"):
        # don't ask age here. build rapport and get presenting concern.
        if not session_state.get("presenting_concern"):
            return Plan(RELATIONAL, "rapport_open", [], protected, fingerprint_intent("rapport_open", []))
        return Plan(RELATIONAL, "reflect_and_gentle_narrow", [], protected, fingerprint_intent("reflect_and_gentle_narrow", []))

    # 2) READY: start clinical narrowing but still empathetic
    # avoid repeated same question intent
    # priority slots: presenting concern -> subject -> age after rapport
    if session_state.get("presenting_concern") and session_state.get("age_years") is None:
        # ask age conversationally after rapport. Not first-turn.
        return Plan(RELATIONAL, "ask_age_soft", ["age_years"], protected, fingerprint_intent("ask_age_soft", ["age_years"]))

    # slot follow-up logic (clinical but one at a time)
    targets = []
    for s in missing_slots:
        if s in protected:
            continue
        targets.append(s)
        break

    if not targets:
        # if rubric sufficient, move to closure gate
        if session_state.get("closure_prompted") and not session_state.get("closure_ack"):
            return Plan(RELATIONAL, "closure_checkin", [], protected, fingerprint_intent("closure_checkin", []))
        if not session_state.get("closure_prompted"):
            return Plan(RELATIONAL, "progress_summary", [], protected, fingerprint_intent("progress_summary", []))
        return Plan(RELATIONAL, "offer_report", [], protected, fingerprint_intent("offer_report", []))

    intent = f"clarify_{targets[0]}"
    fp = fingerprint_intent(intent, targets)
    if last_fp and fp == last_fp:
        # paraphrase / soften if repeated
        intent = f"clarify_{targets[0]}_rephrase"
        fp = fingerprint_intent(intent, targets)
    return Plan(CLINICAL, intent, targets, protected, fp)
