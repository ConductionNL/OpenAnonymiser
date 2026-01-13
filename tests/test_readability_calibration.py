import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from src.api.main import app  # noqa: E402
from tests.fixtures.readability_texts import READABILITY_TEXTS  # noqa: E402


client = TestClient(app)


def _post(text: str, metrics=None):
    payload = {"text": text, "language": "nl"}
    if metrics is not None:
        payload["metrics"] = metrics
    return client.post("/api/v1/analyze/readability", json=payload)


@pytest.mark.parametrize(
    "key",
    ["kleuter", "kind", "puber", "volwassen", "gevorderd", "academisch"],
)
def test_sane_stats(key: str):
    r = _post(READABILITY_TEXTS[key], ["lix", "stats"])
    assert r.status_code == 200, (key, r.text)
    data = r.json()
    assert data["word_count"] > 0
    assert data["sentence_count"] > 0
    assert 0.0 <= data["long_word_pct"] <= 100.0


def test_relative_ordering():
    order = ["kleuter", "kind", "puber", "volwassen", "gevorderd", "academisch"]
    lix_scores = []
    for k in order:
        r = _post(READABILITY_TEXTS[k], ["lix", "stats"])
        assert r.status_code == 200, r.text
        lix_scores.append(r.json()["lix"])
    for a, b in zip(lix_scores, lix_scores[1:]):
        assert a <= b


def test_bands_and_drivers():
    r1 = _post(READABILITY_TEXTS["kleuter"], ["lix", "stats"])
    r6 = _post(READABILITY_TEXTS["academisch"], ["lix", "stats"])
    assert r1.status_code == 200 and r6.status_code == 200
    band1 = r1.json()["judgement"]["band"]
    band6 = r6.json()["judgement"]["band"]
    assert band1 == "easy"
    assert band6 == "very_complex"

    drivers6 = r6.json()["judgement"]["primary_drivers"]
    assert isinstance(drivers6, list) and len(drivers6) >= 1

