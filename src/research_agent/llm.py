from __future__ import annotations

from openai import OpenAI


class LLMClient:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)

    def generate(self, prompt: str, temperature: float = 0.2, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        return (content or "").strip()
