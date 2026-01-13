import math
import pytest
import requests
import os

BASE_URL = os.getenv("OPENANONYMISER_BASE_URL", "http://localhost:8080")


def post_readability(payload: dict) -> requests.Response:
    return requests.post(f"{BASE_URL}/api/v1/analyze/readability", json=payload, timeout=30)


def test_readability_basic_lix():
    payload = {
        "text": "Dit is een eenvoudige Nederlandse zin. Nog een simpele zin.",
        "language": "nl",
        "metrics": ["lix", "stats"],
    }
    resp = post_readability(payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "lix" in data
    assert data["word_count"] >= 6
    assert data["sentence_count"] >= 2
    # LIX in a reasonable low range for simple text
    assert 10 <= data["lix"] <= 40


def test_readability_empty_400():
    payload = {"text": "   ", "language": "nl", "metrics": ["lix"]}
    resp = post_readability(payload)
    assert resp.status_code == 400


def test_readability_long_words_effect():
    text = "Supercalifragilisticexpialidocious woordenlangetest woordenlangetest nogeenwoordlang"
    payload = {"text": text, "language": "nl", "metrics": ["lix", "stats"]}
    resp = post_readability(payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["long_word_pct"] >= 50.0
    assert data["lix"] >= data["avg_sentence_length"]


def test_readability_flesch_optional():
    payload = {
        "text": "Dit is een tekst met verschillende woorden en zinnen. Nog een zin.",
        "language": "nl",
        "metrics": ["lix", "stats", "flesch_douma"],
    }
    resp = post_readability(payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "flesch_douma" in data
    assert data["flesch_douma"] is None or isinstance(data["flesch_douma"], float)

