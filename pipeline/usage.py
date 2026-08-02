"""Token-usage + cost accounting for LLM calls (used by pipeline/llm.py).

Non-invasive: `llm._call` calls `record()` after every model call, but it is a
no-op unless a tally is active (see `track_usage`). Production paths open no
tally, so they pay nothing. Only the eval harness (or an explicit caller) wraps
work in `track_usage()` to measure it.

Token COUNTS are measured and exact. The dollar figure is only as correct as
PRICING below — VERIFY those rates against the live price sheet before quoting a
cost number in the write-up. If a model isn't in PRICING, cost_usd() returns
None (tokens are still reported).
"""

from __future__ import annotations

import contextlib
import contextvars
from dataclasses import dataclass, field

# $ per 1,000,000 tokens: (uncached_input, output, cached_input).
# Seed values from the model comments in llm.py — CONFIRM before publishing cost.
PRICING: dict[str, tuple[float, float, float]] = {
    "gpt-5.4": (2.50, 15.00, 0.25),
    "gpt-5.4-mini": (0.75, 4.50, 0.075),
}


@dataclass
class UsageTally:
    """Accumulates token usage across one or more calls."""
    calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    # model -> [calls, input, cached_input, output]
    per_model: dict[str, list[int]] = field(default_factory=dict)

    def add_call(self, model: str, inp: int, cached: int, out: int) -> None:
        self.calls += 1
        self.input_tokens += inp
        self.cached_input_tokens += cached
        self.output_tokens += out
        row = self.per_model.setdefault(model, [0, 0, 0, 0])
        row[0] += 1
        row[1] += inp
        row[2] += cached
        row[3] += out

    def merge(self, other: "UsageTally") -> None:
        self.calls += other.calls
        self.input_tokens += other.input_tokens
        self.cached_input_tokens += other.cached_input_tokens
        self.output_tokens += other.output_tokens
        for model, v in other.per_model.items():
            row = self.per_model.setdefault(model, [0, 0, 0, 0])
            for i in range(4):
                row[i] += v[i]

    def cost_usd(self, pricing: dict | None = None) -> float | None:
        """Total cost in USD, or None if any model used has no price set."""
        pricing = pricing or PRICING
        total = 0.0
        for model, (_calls, inp, cached, out) in self.per_model.items():
            if model not in pricing:
                return None
            p_in, p_out, p_cached = pricing[model]
            uncached = max(inp - cached, 0)
            total += uncached / 1e6 * p_in + cached / 1e6 * p_cached + out / 1e6 * p_out
        return round(total, 6)

    def summary(self, pricing: dict | None = None) -> dict:
        cost = self.cost_usd(pricing)
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "tokens_per_call": round((self.input_tokens + self.output_tokens) / self.calls, 1)
            if self.calls else 0.0,
            "cost_usd": cost,
            "cost_per_call_usd": round(cost / self.calls, 6) if (cost is not None and self.calls) else None,
        }


# ContextVar (not a plain global) so nested/async callers don't clobber each other.
_active: contextvars.ContextVar[UsageTally | None] = contextvars.ContextVar(
    "kestrel_usage_tally", default=None
)


@contextlib.contextmanager
def track_usage():
    """Collect usage from every `_call` made inside this block.

        with track_usage() as tally:
            pass2_confirm(article, catalyst)
        print(tally.summary())
    """
    tally = UsageTally()
    token = _active.set(tally)
    try:
        yield tally
    finally:
        _active.reset(token)


def record(model: str, usage) -> None:
    """Record one call's usage into the active tally (no-op if none active).

    `usage` is the OpenAI SDK usage object (or None); we read prompt/completion
    tokens and, when present, the cached-prompt token count from
    prompt_tokens_details (prefix caching, which llm.py enables via
    prompt_cache_key).
    """
    tally = _active.get()
    if tally is None or usage is None:
        return
    inp = getattr(usage, "prompt_tokens", 0) or 0
    out = getattr(usage, "completion_tokens", 0) or 0
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", 0) or 0
    tally.add_call(model, inp, cached, out)
