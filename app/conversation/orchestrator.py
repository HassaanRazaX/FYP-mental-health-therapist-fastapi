from __future__ import annotations
from typing import Any, Dict, Tuple, List
import json

from .acts import classify_act
from .readiness import update_readiness
from .planner import plan_next
from .hypotheses import ema_update, softmax, apply_gating, pick_top
from ..rubric.loader import load_disorders
from ..rubric.engine import evaluate_disorder, missing_slots as rubric_missing_slots
from ..llm.extractor import extract
from ..llm.composer import compose

DISCLAIMER = "I’m not a clinician and I can’t diagnose. I can help with an educational, structured symptom screening and suggest next steps."

def _default_hypotheses(disorders: Dict[str,Any]) -> Dict[str,float]:
    # start broad among depressive disorders implemented
    base = {did: 1.0 for did in disorders.keys()}
    return softmax(base)

def _domain_scores(domain: str, disorders: Dict[str,Any]) -> Dict[str,float]:
    # domain-> priors (simple, deterministic)
    scores = {did: 0.2 for did in disorders.keys()}
    if domain == "anger":
        scores["dmdd"] = 1.0
    if domain in ("sadness","mixed"):
        scores["mdd"] = 1.0
        scores["pdd"] = 0.7
    if domain == "unknown":
        scores["unspecified"] = 0.6
    return softmax(scores)

def _progress_hint(state: Dict[str,Any], active: str|None, last_eval: Dict[str,Any]|None) -> str|None:
    if not active or not last_eval:
        return None
    cov = int(last_eval.get("coverage",0)*100)
    return f"So far I’ve understood a bit about what you’re experiencing. (Coverage: ~{cov}% of the structured questions.)"

def _intent_to_question(intent: str, slot_targets: List[str], disorders: Dict[str,Any], active: str|None) -> str|None:
    # YAML provides slot intent context (signals), NOT fixed wording.
    if intent == "rapport_open":
        return "What’s been going on for you lately?"
    if intent == "reflect_and_gentle_narrow":
        return "Would you say this has been more about mood, anxiety, irritability/anger, or a mix?"
    if intent == "ask_age_soft":
        return "Before we go further, roughly how old is the person we’re talking about? A number is enough."
    if intent == "progress_summary":
        return None
    if intent == "closure_checkin":
        return "Before I share a structured summary, do you feel like I’ve understood you reasonably well so far?"
    if intent == "offer_report":
        return "If you’d like, I can generate a structured screening summary now. Want me to do that?"
    if intent.startswith("clarify_") and slot_targets:
        slot = slot_targets[0]
        spec = disorders.get(active or "", {})
        slot_spec = (spec.get("slots", {}) or {}).get(slot) or {}
        signals = slot_spec.get("signals", [])
        if slot == "duration_weeks":
            return "About how many weeks has this been going on?"
        if slot == "duration_years":
            return "Roughly how many years has this been going on?"
        if slot in ("age_now","age_years"):
            return "How old are they?"
        # generic
        hint = signals[0] if signals else slot.replace("_"," ")
        return f"Could you tell me a bit about {hint}?"
    return None

async def handle_turn(state: Dict[str,Any], user_text: str) -> Tuple[Dict[str,Any], str, Dict[str,Any]]:
    disorders = load_disorders()

    act_res = classify_act(user_text)
    readiness_res = update_readiness(state.get("readiness","WARMING"), act_res, user_text)
    state["readiness"] = readiness_res.level

    # known slots across disorders for extraction
    known_slots = set()
    for d in disorders.values():
        for s in (d.get("slots") or {}).keys():
            known_slots.add(s)
        for s in (d.get("exclusion_slots") or {}).keys():
            known_slots.add(s)
    known_slots.update(["age_years","presenting_concern","subject_type","domain"])
    extracted = await extract(user_text, sorted(known_slots))

    facts = extracted.get("facts", {}) or {}
    slots_update = facts.get("slots", {}) or {}
    # update high-level session facts
    if facts.get("presenting_concern") and not state.get("presenting_concern"):
        state["presenting_concern"] = str(facts["presenting_concern"]).strip()[:1000]
    if facts.get("subject_type"):
        state["subject_type"] = facts["subject_type"]
    if facts.get("age_years") is not None:
        try:
            state["age_years"] = int(facts["age_years"])
        except Exception:
            pass
    domain = facts.get("domain")
    if domain and domain != "unknown":
        state["domain"] = domain

    # update slot values and slot states deterministically
    slots = json.loads(state.get("slots_json","{}") or "{}")
    slot_states = json.loads(state.get("slot_state_json","{}") or "{}")
    for k,v in slots_update.items():
        slots[k] = v
        slot_states[k] = "RESOLVED"
    state["slots_json"] = json.dumps(slots)
    state["slot_state_json"] = json.dumps(slot_states)

    # hypothesis update
    prev_h = json.loads(state.get("hypotheses_json","{}") or "{}")
    if not prev_h:
        prev_h = _default_hypotheses(disorders)
    dom = state.get("domain","unknown")
    new_h = _domain_scores(dom, disorders)
    h = ema_update(prev_h, new_h, alpha=0.35)
    h = apply_gating(h, disorders, state.get("age_years"))
    h = softmax(h)
    state["hypotheses_json"] = json.dumps(h)

    active = pick_top(h)
    state["active_disorder_id"] = active

    # evaluate rubric silently
    eval_res = None
    missing = []
    if active:
        eval_res = evaluate_disorder(disorders[active], slots)
        missing = rubric_missing_slots(disorders[active], slots)

    # phase transitions are deterministic and NOT hard-coded by disorder
    state["turns"] = int(state.get("turns",0)) + 1
    if state.get("presenting_concern") and state["readiness"] == "READY":
        if state.get("phase") == "INTAKE":
            state["phase"] = "SCREENING"  # still uses planner for relational/clinical

    # Report readiness gate
    # 1) require rubric probable/possible AND interaction requirements AND closure ack
    report_ready = False
    if active and eval_res:
        req = disorders[active].get("interaction_requirements",{})
        min_turns = int(req.get("min_turns", 6))
        if eval_res["outcome"] in ("PROBABLE_MATCH","POSSIBLE_MATCH"):
            if state["turns"] >= min_turns and state.get("progress_summaries",0) >= (1 if req.get("require_progress_summary",True) else 0):
                if (not req.get("require_closure_ack",True)) or state.get("closure_ack"):
                    report_ready = True
    if report_ready:
        state["phase"] = "REPORT_READY"

    # planner decides next
    plan = plan_next(state["readiness"], act_res.act, state, missing, state.get("last_question_fingerprint"))
    state["track"] = plan.track
    state["last_intent"] = plan.intent
    state["last_question_fingerprint"] = plan.fingerprint

    # update progress summary / closure prompts
    if plan.intent == "progress_summary":
        state["progress_summaries"] = int(state.get("progress_summaries",0)) + 1
        state["closure_prompted"] = True
    if plan.intent == "closure_checkin":
        state["closure_prompted"] = True
    # if user acknowledges closure after closure_checkin
    if state.get("closure_prompted") and not state.get("closure_ack"):
        if act_res.act in ("DIRECT_ANSWER",) and user_text.strip().lower() in ("yes","yeah","yep","ok","okay","sure"):
            state["closure_ack"] = True

    # Build question and progress hint
    question = _intent_to_question(plan.intent, plan.slot_targets, disorders, active)

    # FAQ handling: if user asked definitional question
    extra_expl = None
    if act_res.act == "QUESTION_FAQ":
        # short generic explanation, composer will tailor
        extra_expl = "I can explain in plain language, then we can continue."

    # crisis safety message
    if act_res.act == "CRISIS":
        reply = "I’m really sorry you’re feeling this way. If you might be in immediate danger or thinking about harming yourself, please seek urgent help right now (local emergency services), or reach out to a trusted person or a local crisis hotline. If you tell me your country, I can suggest options.\n\nIf you feel safe to continue, what’s going on right now?"
    else:
        reply = await compose(
            user_text=user_text,
            intent=plan.intent if act_res.act != "QUESTION_FAQ" else "faq",
            question=question,
            progress_hint=_progress_hint(state, active, eval_res),
            extra_explanation=extra_expl,
        )

    meta = {
        "phase": state.get("phase"),
        "readiness": state.get("readiness"),
        "track": state.get("track"),
        "activeHypotheses": h,
        "activeDisorderId": active,
        "missingSlots": missing,
        "nextIntent": plan.intent,
        "rubricOutcome": eval_res["outcome"] if eval_res else None,
        "rubricConfidence": eval_res["confidence"] if eval_res else None,
    }

    return state, reply, meta

def build_report(state: Dict[str,Any]) -> Dict[str,Any]:
    disorders = load_disorders()
    active = state.get("active_disorder_id")
    slots = json.loads(state.get("slots_json","{}") or "{}")
    h = json.loads(state.get("hypotheses_json","{}") or "{}")
    if not active or active not in disorders:
        return {
            "active_disorder": None,
            "outcome": "INSUFFICIENT",
            "confidence": 0.0,
            "plain_summary": "Not enough information for a structured screening summary.",
            "disclaimer": DISCLAIMER,
            "hypotheses": h,
        }
    ev = evaluate_disorder(disorders[active], slots)
    return {
        "active_disorder": active,
        "disorder_name": disorders[active]["name"],
        "outcome": ev["outcome"],
        "confidence": ev["confidence"],
        "criteria_table": ev["criteria_table"],
        "hypotheses": h,
        "plain_summary": f"From a structured, criterion-based screening, the pattern appears most consistent with {disorders[active]['name']}. (Confidence: {int(ev['confidence']*100)}%. Educational screening — not a diagnosis.)",
        "disclaimer": DISCLAIMER,
    }
