import pytest

from hy3_evalforge.core.hashing import ngram_similarity, stable_id


def test_stable_id_ignores_object_key_order_and_whitespace() -> None:
    left = {"goal": "answer   safely", "dimensions": ["safety"]}
    right = {"dimensions": ["safety"], "goal": "answer safely"}

    assert stable_id("spec", left) == stable_id("spec", right)


def test_ngram_similarity_is_bounded_and_validates_n() -> None:
    assert ngram_similarity("abc", "abc") == 1.0
    assert 0 < ngram_similarity("abcdef", "abcxyz") < 1
    with pytest.raises(ValueError, match="at least one"):
        ngram_similarity("a", "b", n=0)
