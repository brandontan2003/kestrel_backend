"""Tests for eval/metrics.py — so the harness's own numbers are trustworthy."""

from eval.metrics import confusion, hallucination_rate, summarize


def test_confusion_counts():
    pairs = [(True, True), (True, True), (False, True), (True, False), (False, False)]
    c = confusion(pairs)
    assert (c.tp, c.fp, c.fn, c.tn) == (2, 1, 1, 1)
    assert c.n == 5


def test_precision_recall_f1_known_values():
    # tp=2 fp=1 fn=1 -> precision 2/3, recall 2/3, f1 2/3
    c = confusion([(True, True), (True, True), (False, True), (True, False)])
    assert round(c.precision, 3) == 0.667
    assert round(c.recall, 3) == 0.667
    assert round(c.f1, 3) == 0.667


def test_perfect_and_empty_edges():
    perfect = confusion([(True, True), (False, False)])
    assert perfect.precision == 1.0 and perfect.recall == 1.0 and perfect.f1 == 1.0
    empty = confusion([])
    assert empty.precision == 0.0 and empty.recall == 0.0 and empty.f1 == 0.0


def test_all_false_positives_zero_precision():
    c = confusion([(False, True), (False, True)])
    assert c.precision == 0.0
    assert c.recall == 0.0  # no real positives to catch


def test_hallucination_rate():
    # 4 confirmations, 1 with a fabricated (absent) quote -> 0.25
    assert hallucination_rate([True, True, False, True]) == 0.25
    assert hallucination_rate([]) == 0.0
    assert hallucination_rate([True, True]) == 0.0  # guard-clean


def test_summarize_shape():
    row = summarize("sys", [(True, True), (False, False)])
    assert row["system"] == "sys"
    for k in ("n", "tp", "fp", "fn", "tn", "precision", "recall", "f1", "accuracy"):
        assert k in row
