import json
from app.core.db import SessionLocal
from app.models import User
from app.core.security import hash_password

def signup_and_login(client):
    r = client.post("/auth/signup", json={
        "name":"Test User",
        "email":"t@example.com",
        "password":"P@ssw0rd!",
        "gender":"Male",
        "dateOfBirth":"01/01/2000",
        "profileImage": None
    })
    assert r.status_code == 200, r.text
    data = r.json()
    return data["token"]["accessToken"], data["token"]["refreshToken"]

def patch_llm(monkeypatch, extracted_map, composed_text):
    async def fake_extract(user_text, known_slots):
        return extracted_map.get(user_text, {"facts":{"slots":{}}, "answers":{"answered_intent": False, "refusal": False, "confusion": False}})
    async def fake_compose(user_text, intent, question, progress_hint, extra_explanation):
        # return the question appended so tests can check it
        if question:
            return f"ACK. {question}"
        return "ACK."
    monkeypatch.setattr("app.llm.extractor.extract", fake_extract)
    monkeypatch.setattr("app.llm.composer.compose", fake_compose)

def test_greeting_does_not_trigger_age(client, monkeypatch):
    token,_ = signup_and_login(client)
    extracted = {
        "hi": {"facts":{"presenting_concern": None, "subject_type":"unknown", "domain":"unknown", "slots":{}}, "answers":{"answered_intent": False, "refusal": False, "confusion": False}},
    }
    patch_llm(monkeypatch, extracted, None)
    r = client.post("/chat/message", headers={"Authorization": f"Bearer {token}"}, json={"sessionId": None, "message":"hi"})
    assert r.status_code == 200
    text = r.json()["assistantMessage"]["text"].lower()
    assert "old" not in text  # no age question first
    assert "what" in text  # rapport_open

def test_confusion_triggers_relational(client, monkeypatch):
    token,_ = signup_and_login(client)
    extracted = {
        "i don't understand": {"facts":{"slots":{}}, "answers":{"confusion": True, "answered_intent": False, "refusal": False}},
    }
    patch_llm(monkeypatch, extracted, None)
    r = client.post("/chat/message", headers={"Authorization": f"Bearer {token}"}, json={"sessionId": None, "message":"i don't understand"})
    meta = r.json()["assistantMessage"]["meta"]
    assert meta["track"] == "RELATIONAL"

def test_age_gating_dmdd(client, monkeypatch):
    token,_ = signup_and_login(client)
    extracted = {
        "i feel low": {"facts":{"presenting_concern":"feeling low", "domain":"sadness", "slots":{}}, "answers":{"answered_intent": False, "refusal": False, "confusion": False}},
        "22": {"facts":{"age_years":22, "slots":{}}, "answers":{"answered_intent": True, "refusal": False, "confusion": False}},
    }
    patch_llm(monkeypatch, extracted, None)
    r1 = client.post("/chat/message", headers={"Authorization": f"Bearer {token}"}, json={"sessionId": None, "message":"i feel low"})
    sid = r1.json()["session"]["id"]
    r2 = client.post("/chat/message", headers={"Authorization": f"Bearer {token}"}, json={"sessionId": sid, "message":"22"})
    meta = r2.json()["assistantMessage"]["meta"]
    # DMDD should be gated out for adult
    assert meta["activeHypotheses"].get("dmdd",0) == 0.0

def test_no_probable_match_with_one_symptom(client, monkeypatch):
    token,_ = signup_and_login(client)
    extracted = {
        "i feel low": {"facts":{"presenting_concern":"feeling low", "domain":"sadness", "slots":{"depressed_mood": True, "duration_weeks": 1}}, "answers":{"answered_intent": False, "refusal": False, "confusion": False}},
        "ok": {"facts":{"slots":{}}, "answers":{"answered_intent": True, "refusal": False, "confusion": False}},
    }
    patch_llm(monkeypatch, extracted, None)
    r1 = client.post("/chat/message", headers={"Authorization": f"Bearer {token}"}, json={"sessionId": None, "message":"i feel low"})
    meta1 = r1.json()["assistantMessage"]["meta"]
    assert meta1["rubricOutcome"] in ("INSUFFICIENT","POSSIBLE_MATCH")
