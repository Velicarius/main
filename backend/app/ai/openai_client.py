from __future__ import annotations
import os
from typing import Optional
from openai import OpenAI

_client: Optional[OpenAI] = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            # клиент будет создан «пустым», но мы явно проверим в роутере
            raise RuntimeError("OPENAI_API_KEY is not set")
        base_url = os.getenv("OPENAI_BASE_URL")  # можно не задавать
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client

def default_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")




