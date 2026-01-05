import httpx
from ..core.config import settings

async def chat_completion(messages, temperature: float = 0.2, response_format: dict | None = None):
    url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format:
        payload["response_format"] = response_format
    async with httpx.AsyncClient(timeout=settings.OPENAI_TIMEOUT_SECONDS) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
