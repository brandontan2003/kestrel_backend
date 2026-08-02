"""Unit tests for the anti-hallucination guards (pipeline/llm.py).

No OpenAI call is made: the guards run *after* the model returns, so we build a
`_Pass2Output` (what the model would have emitted) and an `Article`, then assert
`_apply_guards` rewrites the verdict correctly. This is the evidence behind the
write-up's strongest claim — "a confirmation is rejected in code unless the model
quotes text that appears verbatim in the source."

`openai` is never imported (the client is lazy), so this file needs no API key.
"""

from datetime import datetime, timezone

from pipeline.llm import _apply_guards, _Pass2Output, quote_in_article
from pipeline.news import Article


def article(headline="NVIDIA unveils Rubin data-center GPU",
            summary="At GTC, NVIDIA announced the Rubin GPU for data centers, shipping in Q4.",
            has_body=True):
    return Article(
        id="a1",
        ticker="NVDA",
        headline=headline,
        summary=summary if has_body else None,
        source="finnhub",
        url="https://example.com/x",
        published_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
    )


def verdict(proposed_state, quote, source_kind="reporting", confidence=0.9):
    return _Pass2Output(
        catalyst_id="c1",
        proposed_state=proposed_state,
        confidence=confidence,
        supporting_quote=quote,
        source_kind=source_kind,
        reasoning="test",
    )


# --------------------------------------------------------------------------- #
# quote_in_article — the verbatim substring check itself.
# --------------------------------------------------------------------------- #
def test_quote_found_verbatim():
    assert quote_in_article("announced the Rubin GPU for data centers", article()) is True


def test_quote_match_is_case_insensitive():
    assert quote_in_article("ANNOUNCED THE RUBIN GPU", article()) is True


def test_quote_match_normalizes_whitespace():
    assert quote_in_article("announced   the\n  Rubin   GPU", article()) is True


def test_quote_match_tolerates_html_entities():
    art = article(summary="Deal signed between AT&amp;T and the vendor on Monday.")
    assert quote_in_article("AT&T and the vendor", art) is True


def test_quote_can_match_in_the_headline():
    assert quote_in_article("unveils Rubin data-center GPU", article(has_body=False)) is True


def test_absent_quote_is_rejected():
    assert quote_in_article("announced a share buyback", article()) is False


# --------------------------------------------------------------------------- #
# _apply_guards — the guard that voids unsupported confirmations.
# --------------------------------------------------------------------------- #
def test_valid_confirmation_passes_through():
    out = _apply_guards(verdict("confirmed", "announced the Rubin GPU for data centers"), article())
    assert out.proposed_state == "confirmed"
    assert out.guard_note is None
    assert out.article_id == "a1"


def test_confirmation_without_a_quote_is_voided():
    out = _apply_guards(verdict("confirmed", None), article())
    assert out.proposed_state == "no_change"
    assert "no supporting quote" in out.guard_note


def test_confirmation_with_a_fabricated_quote_is_voided():
    # The model "confirms" but cites text that isn't in the article — the exact
    # hallucination the guard exists to catch.
    out = _apply_guards(verdict("confirmed", "NVIDIA announced a $50B buyback"), article())
    assert out.proposed_state == "no_change"
    assert "not found verbatim" in out.guard_note


def test_headline_only_article_caps_confirmation_at_rumored():
    # Quote is in the headline (so guard 1 passes) but there is no body -> a
    # confirmation is downgraded to rumored, never accepted outright.
    out = _apply_guards(
        verdict("confirmed", "unveils Rubin data-center GPU"),
        article(has_body=False),
    )
    assert out.proposed_state == "rumored"
    assert "capped at rumored" in out.guard_note


def test_headline_only_article_caps_invalidation_at_rumored():
    out = _apply_guards(
        verdict("invalidated", "unveils Rubin data-center GPU"),
        article(has_body=False),
    )
    assert out.proposed_state == "rumored"


def test_no_change_is_never_touched():
    out = _apply_guards(verdict("no_change", None), article())
    assert out.proposed_state == "no_change"
    assert out.guard_note is None


def test_rumored_still_requires_a_quote():
    # Any non-no_change verdict must carry a real quote; a bare "rumored" with
    # no textual support is voided too.
    out = _apply_guards(verdict("rumored", None), article())
    assert out.proposed_state == "no_change"


def test_valid_invalidation_with_body_survives():
    art = article(summary="The regulator formally rejected the merger on appeal.")
    out = _apply_guards(verdict("invalidated", "regulator formally rejected the merger"), art)
    assert out.proposed_state == "invalidated"


def test_guard_stamps_provenance():
    out = _apply_guards(verdict("confirmed", "announced the Rubin GPU for data centers"), article())
    assert out.prompt_version  # sha-derived, non-empty
    assert out.classified_at  # ISO timestamp stamped at guard time
