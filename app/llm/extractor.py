import json
from .openai_client import chat_completion
from .prompts import SYSTEM, EXTRACTOR_INSTRUCTIONS

async def extract(user_text: str, known_slot_names: list[str]) -> dict:
    # Provide known slots so the model maps correctly.
    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"system","content":EXTRACTOR_INSTRUCTIONS},
        {"role":"user","content":f"Known slots: {known_slot_names}\n\nUser message: {user_text}"},
    ]
    raw = await chat_completion(
        messages,
        temperature=0.0,
        response_format={"type":"json_object"}
    )
    try:
        return json.loads(raw)
    except Exception:
        return {"facts": {"slots": {}}, "answers": {"answered_intent": False, "refusal": False, "confusion": False}}
