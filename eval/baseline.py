"""The single-call baseline the full pipeline is measured against.

This is deliberately the naive thing a reasonable person builds first: ONE LLM
call per (article, catalyst) pair — "does this news confirm this catalyst?" —
and the answer is taken at face value. No relevance pre-filter, no verbatim-quote
guard, no source-credibility check, no state machine.

Fairness note: it calls the SAME model as the full pipeline's Pass 2
(`pipeline.llm.PASS2_MODEL`) and even asks for a supporting quote, so the
comparison isolates the *architecture* (guards + state machine), not the model.
The difference in results is the value the agentic machinery adds.

Runs only when OPENAI_API_KEY is set. Import is safe without it (the client is
lazy, mirroring pipeline.llm).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from pipeline.llm import PASS2_MODEL, _call
from pipeline.news import Article

_BASELINE_SYSTEM = (
    "You judge whether a single news article confirms a specific investment "
    "catalyst. Answer confirmed=true only if the article states the catalyst "
    "has actually happened (not merely speculated). Provide a short supporting "
    "quote from the article. Be decisive."
)


class BaselineVerdict(BaseModel):
    confirmed: bool
    supporting_quote: str | None = Field(default=None)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


def classify_single_call(article: Article, catalyst: dict) -> BaselineVerdict:
    """One naive call, verdict trusted as-is (this is the point — no guards)."""
    body = article.summary if article.has_body else "(headline only)"
    user = (
        f"CATALYST: {catalyst.get('description', '')}\n\n"
        f"ARTICLE:\nHEADLINE: {article.headline}\nBODY: {body}"
    )
    return _call(
        model=PASS2_MODEL,
        system=_BASELINE_SYSTEM,
        user=user,
        schema=BaselineVerdict,
        max_tokens=2048,
        effort="low",
    )
