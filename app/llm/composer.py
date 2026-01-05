from .openai_client import chat_completion
from .prompts import SYSTEM, COMPOSER_INSTRUCTIONS

async def compose(
    user_text: str,
    intent: str,
    question: str | None,
    progress_hint: str | None,
    extra_explanation: str | None,
) -> str:
    prompt_parts = [
        f"Intent: {intent}",
        f"User said: {user_text}",
    ]
    if progress_hint:
        prompt_parts.append(f"Progress hint to incorporate (brief): {progress_hint}")
    if extra_explanation:
        prompt_parts.append(f"Explanation (brief, only if relevant): {extra_explanation}")
    if question:
        prompt_parts.append(f"Ask this question (one question max): {question}")
    else:
        prompt_parts.append("Do not ask a question unless needed.")
    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"system","content":COMPOSER_INSTRUCTIONS},
        {"role":"user","content":"\n".join(prompt_parts)},
    ]
    text = await chat_completion(messages, temperature=0.4)
    return text.strip()
