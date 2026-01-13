from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from src.api.main import app


client = TestClient(app)


def test_readability_basic_lix_unit():
    resp = client.post(
        "/api/v1/analyze/readability",
        json={
            "text": "Dit is een eenvoudige Nederlandse zin. Nog een simpele zin.",
            "language": "nl",
            "metrics": ["lix", "stats"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "lix" in data
    assert data["word_count"] >= 6
    assert data["sentence_count"] >= 2


def test_readability_empty_400_unit():
    resp = client.post(
        "/api/v1/analyze/readability",
        json={"text": "   ", "language": "nl", "metrics": ["lix"]},
    )
    assert resp.status_code == 400


def test_readability_flesch_optional_unit():
    resp = client.post(
        "/api/v1/analyze/readability",
        json={
            "text": "Dit is een tekst met verschillende woorden en zinnen. Nog een zin.",
            "language": "nl",
            "metrics": ["lix", "stats", "flesch_douma"],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "flesch_douma" in data
    assert data["flesch_douma"] is None or isinstance(data["flesch_douma"], float)

