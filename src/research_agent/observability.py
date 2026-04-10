from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from time import perf_counter
from typing import Callable, Iterator


@dataclass
class LLMUsageRecord:
    provider: str
    model: str
    operation: str
    duration_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    success: bool
    error_message: str = ""


Recorder = Callable[[LLMUsageRecord], None]

_usage_recorder: ContextVar[Recorder | None] = ContextVar("usage_recorder", default=None)
_operation_name: ContextVar[str] = ContextVar("operation_name", default="llm.generate")


@contextmanager
def usage_recorder(recorder: Recorder | None) -> Iterator[None]:
    token = _usage_recorder.set(recorder)
    try:
        yield
    finally:
        _usage_recorder.reset(token)


@contextmanager
def llm_operation(name: str) -> Iterator[None]:
    token = _operation_name.set(name)
    try:
        yield
    finally:
        _operation_name.reset(token)


def timer_start() -> float:
    return perf_counter()


def emit_llm_usage(
    *,
    provider: str,
    model: str,
    started_at: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    success: bool = True,
    error_message: str = "",
) -> None:
    recorder = _usage_recorder.get()
    if recorder is None:
        return
    duration_ms = int((perf_counter() - started_at) * 1000)
    recorder(
        LLMUsageRecord(
            provider=provider,
            model=model,
            operation=_operation_name.get(),
            duration_ms=duration_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            success=success,
            error_message=error_message,
        )
    )
