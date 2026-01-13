import pytest
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from src.api.main import app  # noqa: E402


client = TestClient(app)


@pytest.fixture
def cases():
    return [
        {
            "name": "easy_short",
            "text": "Dit is een korte, eenvoudige zin. Nog een korte zin.",
            "expect": {
                "word_count_min": 6,
                "sentence_count": 2,
                "avg_sentence_length_max": 10.0,
                "long_word_pct_max": 30.0,
                "lix_band": "easy",
            },
        },
        {
            "name": "medium_mixed",
            "text": (
                "Deze tekst bevat gemiddelde zinnen en enkele langere woorden. "
                "Het doel is om een medium leesniveau te benaderen."
            ),
            "expect": {
                "word_count_min": 10,
                "sentence_count_min": 2,
                "avg_sentence_length_max": 20.0,
                "lix_band_in": ["easy", "medium", "complex"],
            },
        },
        {
            "name": "very_complex_longwords",
            "text": (
                "Beleidsuitvoeringskader en verantwoordingsdocumentatie vereisen zorgvuldigheidsinkaderstellingen. "
                "Samenwerkingsafspraken en procesoptimalisatieoverleggen worden geformaliseerd."
            ),
            "expect": {
                "long_word_pct_min": 35.0,
                "lix_band": "very_complex",
            },
        },
    ]


def _post(text: str, metrics=None):
    payload = {"text": text, "language": "nl"}
    if metrics is not None:
        payload["metrics"] = metrics
    return client.post("/api/v1/analyze/readability", json=payload)


def test_metric_ranges_and_bands(cases):
    for case in cases:
        r = _post(case["text"], ["lix", "stats"])
        assert r.status_code == 200, (case["name"], r.text)
        data = r.json()

        exp = case["expect"]
        if "word_count_min" in exp:
            assert data["word_count"] >= exp["word_count_min"], case["name"]
        if "sentence_count" in exp:
            assert data["sentence_count"] == exp["sentence_count"], case["name"]
        if "sentence_count_min" in exp:
            assert data["sentence_count"] >= exp["sentence_count_min"], case["name"]
        if "avg_sentence_length_max" in exp:
            assert data["avg_sentence_length"] <= exp["avg_sentence_length_max"], case["name"]
        if "long_word_pct_min" in exp:
            assert data["long_word_pct"] >= exp["long_word_pct_min"], case["name"]
        if "long_word_pct_max" in exp:
            assert data["long_word_pct"] <= exp["long_word_pct_max"], case["name"]

        band = data["judgement"]["band"]
        if "lix_band" in exp:
            assert band == exp["lix_band"], (case["name"], band)
        if "lix_band_in" in exp:
            assert band in exp["lix_band_in"], (case["name"], band)


def test_flesch_guardrails():
    # Absurd syllables per word by using vowel-heavy pseudo-words
    text = "Aeiou aeiouaeiou aeiouaeiouaeiou aeiouaeiouaeiouaeiou."
    r = _post(text, ["lix", "stats", "flesch_douma"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert "syllables_per_word" in data
    assert data.get("flesch_douma_status") in ("invalid_syllable_estimate", "ok")
    if data.get("flesch_douma_status") == "invalid_syllable_estimate":
        assert data.get("flesch_douma") is None

