from __future__ import annotations

from openai import OpenAI

from .observability import emit_llm_usage, timer_start


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider: str = "openai",
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
    ) -> None:
        self.model = model
        self.provider = provider
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million
        self.client = OpenAI(api_key=api_key, base_url=base_url or None)

    def generate(self, prompt: str, temperature: float = 0.2, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        started_at = timer_start()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
        except Exception as exc:
            emit_llm_usage(
                provider=self.provider,
                model=self.model,
                started_at=started_at,
                success=False,
                error_message=str(exc),
            )
            raise

        usage = response.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        total_tokens = getattr(usage, "total_tokens", 0) or prompt_tokens + completion_tokens
        estimated_cost_usd = (
            (prompt_tokens / 1_000_000) * self.input_cost_per_million
            + (completion_tokens / 1_000_000) * self.output_cost_per_million
        )
        emit_llm_usage(
            provider=self.provider,
            model=self.model,
            started_at=started_at,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            success=True,
        )
        content = response.choices[0].message.content
        return (content or "").strip()
