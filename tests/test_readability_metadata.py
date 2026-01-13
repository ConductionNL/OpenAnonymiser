"""Tests for readability endpoint metadata (request_id, input_hash, meta)."""

import os
import re
import sys

sys.path.insert(0, os.path.abspath("."))

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


# -----------------------------------------------------------------------------
# request_id tests
# -----------------------------------------------------------------------------


def test_request_id_generated_when_missing(client):
    """When no X-Request-Id header is sent, server generates a UUIDv4."""
    resp = client.post(
        "/api/v1/analyze/readability",
        json={"text": "Dit is een testzin.", "language": "nl"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    # UUIDv4 format: 8-4-4-4-12 hex
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
    )
    assert uuid_pattern.match(data["request_id"]), f"Not a valid UUIDv4: {data['request_id']}"


def test_request_id_from_header(client):
    """When X-Request-Id header is provided, it should be echoed in the response."""
    custom_id = "my-custom-request-12345"
    resp = client.post(
        "/api/v1/analyze/readability",
        json={"text": "Dit is een testzin.", "language": "nl"},
        headers={"X-Request-Id": custom_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == custom_id


# -----------------------------------------------------------------------------
# input_hash tests
# -----------------------------------------------------------------------------


def test_input_hash_format(client):
    """input_hash should be sha256:<hex>."""
    resp = client.post(
        "/api/v1/analyze/readability",
        json={"text": "Hallo wereld.", "language": "nl"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "input_hash" in data
    assert data["input_hash"].startswith("sha256:")
    hex_part = data["input_hash"][7:]
    assert len(hex_part) == 64
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_input_hash_stable(client):
    """Same text should produce the same input_hash across requests."""
    text = "Dit is een reproduceerbare tekst."
    resp1 = client.post(
        "/api/v1/analyze/readability",
        json={"text": text, "language": "nl"},
    )
    resp2 = client.post(
        "/api/v1/analyze/readability",
        json={"text": text, "language": "nl"},
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["input_hash"] == resp2.json()["input_hash"]


def test_input_hash_different_text(client):
    """Different texts should produce different input_hash values."""
    resp1 = client.post(
        "/api/v1/analyze/readability",
        json={"text": "Tekst een.", "language": "nl"},
    )
    resp2 = client.post(
        "/api/v1/analyze/readability",
        json={"text": "Tekst twee.", "language": "nl"},
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["input_hash"] != resp2.json()["input_hash"]


def test_input_hash_normalized_whitespace(client):
    """Whitespace normalization: leading/trailing stripped, multiple spaces collapsed."""
    # These should produce the same hash
    text_a = "  Dit   is   tekst.  "
    text_b = "Dit is tekst."
    resp_a = client.post(
        "/api/v1/analyze/readability",
        json={"text": text_a, "language": "nl"},
    )
    resp_b = client.post(
        "/api/v1/analyze/readability",
        json={"text": text_b, "language": "nl"},
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json()["input_hash"] == resp_b.json()["input_hash"]


# -----------------------------------------------------------------------------
# meta tests
# -----------------------------------------------------------------------------


def test_meta_absent_returns_null(client):
    """When meta is not provided, response should have meta: null."""
    resp = client.post(
        "/api/v1/analyze/readability",
        json={"text": "Tekst zonder meta.", "language": "nl"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert data["meta"] is None


def test_meta_echoed_in_response(client):
    """When meta is provided, it should be echoed back."""
    meta_in = {"source_type": "file", "source_name": "document.txt"}
    resp = client.post(
        "/api/v1/analyze/readability",
        json={
            "text": "Tekst met metadata.",
            "language": "nl",
            "meta": meta_in,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"] == meta_in


def test_meta_partial_fields(client):
    """Meta with only source_type should work, source_name becomes null."""
    meta_in = {"source_type": "api"}
    resp = client.post(
        "/api/v1/analyze/readability",
        json={
            "text": "Tekst met gedeeltelijke meta.",
            "language": "nl",
            "meta": meta_in,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["source_type"] == "api"
    assert data["meta"]["source_name"] is None

