"""Pure scoring functions for the Kestrel eval harness.

No LLM, no I/O — just arithmetic over (gold, prediction) pairs, so this module
is unit-tested and its numbers are reproducible. Every figure the write-up cites
in the Evidence section is produced here.

Vocabulary: we score a binary decision — did the system decide a catalyst is
CONFIRMED (met) or not? `gold` is the human label; `pred` is the system's call.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Confusion:
    tp: int  # gold met, predicted met
    fp: int  # gold not-met, predicted met   <- false confirmations (the dangerous ones)
    fn: int  # gold met, predicted not-met
    tn: int  # gold not-met, predicted not-met

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def precision(self) -> float:
        """Of the confirmations we made, how many were right? Low precision = the
        system cries wolf — the failure mode that actually loses a user money."""
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        """Of the real confirmations, how many did we catch?"""
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def accuracy(self) -> float:
        return (self.tp + self.tn) / self.n if self.n else 0.0

    def as_dict(self) -> dict:
        return {
            "n": self.n, "tp": self.tp, "fp": self.fp, "fn": self.fn, "tn": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
        }


def confusion(pairs: list[tuple[bool, bool]]) -> Confusion:
    """Build a confusion matrix from (gold_met, pred_met) pairs."""
    tp = fp = fn = tn = 0
    for gold, pred in pairs:
        if gold and pred:
            tp += 1
        elif not gold and pred:
            fp += 1
        elif gold and not pred:
            fn += 1
        else:
            tn += 1
    return Confusion(tp=tp, fp=fp, fn=fn, tn=tn)


def hallucination_rate(confirmations: list[bool]) -> float:
    """Fraction of CONFIRMED verdicts whose supporting quote was NOT found
    verbatim in the source article.

    `confirmations` is one bool per confirmed verdict: True == the cited quote
    was actually present, False == it was fabricated. The verbatim guard forces
    this to 0.0 by construction; a single-call baseline that trusts the model
    does not — that gap is the guard's measured value.
    """
    if not confirmations:
        return 0.0
    fabricated = sum(1 for quote_present in confirmations if not quote_present)
    return fabricated / len(confirmations)


def summarize(name: str, pairs: list[tuple[bool, bool]]) -> dict:
    """One system's scored line for the results table."""
    c = confusion(pairs)
    return {"system": name, **c.as_dict()}
