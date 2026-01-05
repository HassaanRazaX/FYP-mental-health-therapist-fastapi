from dataclasses import dataclass
import re

ACT_GREETING="GREETING"
ACT_SMALL_TALK="SMALL_TALK"
ACT_SYMPTOM="SYMPTOM_DISCLOSURE"
ACT_DIRECT_ANSWER="DIRECT_ANSWER"
ACT_FAQ="QUESTION_FAQ"
ACT_CONFUSION="CONFUSION"
ACT_RESIST="RESISTANCE"
ACT_REFUSAL="REFUSAL"
ACT_OFFTOPIC="OFF_TOPIC"
ACT_CRISIS="CRISIS"

CRISIS_PATTERNS = [
    r"\b(suicide|kill myself|end my life|self[- ]?harm|hurt myself)\b",
    r"\b(kill (him|her|them)|hurt someone|homicide)\b",
]

FAQ_PATTERNS = [
    r"\bwhat is\b",
    r"\bwhy (are|do) you\b",
    r"\bmeaning of\b",
    r"\bexplain\b",
]

GREETING_PATTERNS = [
    r"^\s*(hi|hello|hey|assalam|salam|yo)\b",
]

CONFUSION_PATTERNS = [
    r"\b(i don't understand|dont understand|confus|huh\?|what\?)\b",
]

RESIST_PATTERNS = [
    r"\b(why do you ask|stop asking|don't ask|dont ask|none of your business)\b",
]

REFUSAL_PATTERNS = [
    r"\b(no|nah|prefer not|don't want|dont want)\b",
]

SYMPTOM_PATTERNS = [
    r"\b(feel(ing)? (low|sad|down|depressed|anxious|stressed)|sleepy|tired|no energy|hopeless|irritat|angry)\b"
]

ANSWER_LIKE = [
    r"^\s*\d+\s*$",
    r"\b(yes|no)\b",
]

@dataclass
class ActResult:
    act: str
    signals: dict

def classify_act(user_text: str) -> ActResult:
    t=user_text.strip().lower()

    for pat in CRISIS_PATTERNS:
        if re.search(pat,t):
            return ActResult(ACT_CRISIS, {"matched": pat})

    for pat in GREETING_PATTERNS:
        if re.search(pat,t):
            return ActResult(ACT_GREETING, {"matched": pat})

    for pat in CONFUSION_PATTERNS:
        if re.search(pat,t):
            return ActResult(ACT_CONFUSION, {"matched": pat})

    for pat in RESIST_PATTERNS:
        if re.search(pat,t):
            return ActResult(ACT_RESIST, {"matched": pat})

    for pat in FAQ_PATTERNS:
        if re.search(pat,t) and len(t.split()) <= 10:
            return ActResult(ACT_FAQ, {"matched": pat})

    for pat in SYMPTOM_PATTERNS:
        if re.search(pat,t):
            return ActResult(ACT_SYMPTOM, {"matched": pat})

    for pat in ANSWER_LIKE:
        if re.search(pat,t):
            return ActResult(ACT_DIRECT_ANSWER, {"matched": pat})

    if len(t.split()) <= 4:
        return ActResult(ACT_SMALL_TALK, {})

    return ActResult(ACT_OFFTOPIC, {})
