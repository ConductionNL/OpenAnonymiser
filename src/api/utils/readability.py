import math
import re
from dataclasses import dataclass
from typing import Iterable, Optional

from src.api.config import settings
from src.api.readability_config import get_readability_config


SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", re.UNICODE)
VOWEL_RE = re.compile(r"[aeiouyáéíóúàèìòùäëïöüAEIOUYÁÉÍÓÚÀÈÌÒÙÄËÏÖÜ]", re.UNICODE)


@dataclass
class ReadabilityStats:
    word_count: int
    sentence_count: int
    long_word_count: int
    avg_sentence_length: float
    long_word_pct: float
    lix: float
    flesch_douma: Optional[float]
    flesch_douma_status: Optional[str]
    syllables_per_word: Optional[float]
    cefr_hint: str | None
    cefr_confidence: float | None
    judgement: dict


def _split_sentences(text: str) -> list[str]:
    # Basic sentence split; keep non-empty parts
    parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return parts or [text.strip()]


def _tokenize_words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _is_long_word(word: str) -> bool:
    # Long words: strictly more than threshold-1 letters; default > 6 letters
    letters = sum(1 for ch in word if ch.isalpha())
    cfg = get_readability_config()
    return letters > (cfg.lix.long_word_min_len - 1)


def _count_syllables(word: str) -> int:
    """Very rough Dutch syllable estimate: count vowel groups."""
    if not word:
        return 0
    groups = re.findall(r"[aeiouyáéíóúàèìòùäëïöüAEIOUYÁÉÍÓÚÀÈÌÒÙÄËÏÖÜ]+", word)
    return max(1, len(groups))


def _compute_flesch_douma(words: list[str], sentences: int) -> float | None:
    """Approximate Flesch–Douma Reading Ease for Dutch.
    Reference form uses syllables/word and words/sentence; constants differ across sources.
    We use an indicative variant and expose it only when requested.
    """
    if not words or sentences <= 0:
        return None
    total_syll = sum(_count_syllables(w) for w in words)
    wps = len(words) / max(1, sentences)
    spw = total_syll / max(1, len(words))
    # Indicative constants for Dutch (approximate):
    # Higher score = easier text.
    score = 206.835 - (77.0 * wps) - (0.93 * (spw * 100.0) / 10.0)
    return float(round(score, 2))


def _cefr_from_lix(lix: float) -> tuple[str, float]:
    """Indicative CEFR mapping from LIX (rough heuristic)."""
    # Ranges are indicative; set conservative confidences.
    if lix < 25:
        return "A1", 0.6
    if lix < 30:
        return "A2", 0.55
    if lix < 40:
        return "B1", 0.5
    if lix < 50:
        return "B2", 0.45
    if lix < 60:
        return "C1", 0.4
    return "C2", 0.35


def compute_readability(
    text: str, include_flesch_douma: bool = False
) -> ReadabilityStats:
    cfg = get_readability_config()
    sentences = _split_sentences(text)
    words = _tokenize_words(text)
    word_count = len(words)
    sentence_count = max(1, len(sentences))

    if word_count == 0:
        # Degenerate case
        return ReadabilityStats(
            word_count=0,
            sentence_count=sentence_count,
            long_word_count=0,
            avg_sentence_length=0.0,
            long_word_pct=0.0,
            lix=0.0,
            flesch_douma=None,
            flesch_douma_status=None,
            syllables_per_word=None,
            cefr_hint="A1",
            cefr_confidence=0.3,
            judgement=_make_judgement(0.0, 0.0, 0.0),
        )

    long_word_count = sum(1 for w in words if _is_long_word(w))
    avg_sentence_len = word_count / sentence_count
    long_word_pct = (long_word_count * 100.0) / word_count
    lix = avg_sentence_len + long_word_pct

    # Compute syllables/word for guardrails and debugging
    total_syll = sum(_count_syllables(w) for w in words)
    spw = total_syll / word_count if word_count else None

    flesch_status: Optional[str] = None
    flesch: Optional[float] = None
    if include_flesch_douma:
        # Guardrails for absurd estimates
        if spw is not None and (
            spw > cfg.flesch_douma.syllables_per_word_max
            or spw < cfg.flesch_douma.syllables_per_word_min
        ):
            flesch = None
            flesch_status = "invalid_syllable_estimate"
        else:
            flesch = _compute_flesch_douma(words, sentence_count)
            flesch_status = "ok"

    cefr_hint, cefr_conf = _cefr_from_lix(lix)
    # Cap CEFR confidence
    cefr_conf = min(cefr_conf or 0.0, get_readability_config().output.cefr_confidence_cap)

    return ReadabilityStats(
        word_count=word_count,
        sentence_count=sentence_count,
        long_word_count=long_word_count,
        avg_sentence_length=round(avg_sentence_len, 2),
        long_word_pct=round(long_word_pct, 2),
        lix=round(lix, 2),
        flesch_douma=flesch,
        flesch_douma_status=flesch_status,
        syllables_per_word=round(spw, 2) if spw is not None else None,
        cefr_hint=cefr_hint,
        cefr_confidence=cefr_conf,
        judgement=_make_judgement(lix, long_word_pct, avg_sentence_len),
    )


def _make_judgement(lix: float, long_word_pct: float, avg_sentence_len: float) -> dict:
    """Produce deterministic judgement from metrics."""
    cfg = get_readability_config()
    bands = cfg.lix.judgement_bands
    if lix < bands.easy:
        band = "easy"
        label = "Eenvoudig"
        suitable = ["brede publiekscommunicatie", "korte webteksten"]
        not_suitable = ["wet- en regelgeving", "specialistische rapporten"]
    elif lix < bands.medium:
        band = "medium"
        label = "Gemiddeld"
        suitable = ["algemene voorlichting", "nieuwsbrieven"]
        not_suitable = ["academische publicaties", "juridische documenten"]
    elif lix < bands.complex:
        band = "complex"
        label = "Complex"
        suitable = ["vakpublicaties", "beleidsnota’s"]
        not_suitable = ["toegankelijke publieksinformatie"]
    else:
        band = "very_complex"
        label = "Zeer complex"
        suitable = ["specialistische documenten", "beleids- en onderzoeksrapporten"]
        not_suitable = ["publieksgerichte communicatie", "laagdrempelige webteksten"]

    drivers = []
    if long_word_pct >= 35.0:
        drivers.append("hoog aandeel lange woorden")
    if avg_sentence_len >= 20.0:
        drivers.append("lange zinnen")
    if not drivers:
        drivers.append("gemiddelde zinslengte en woordlengte")

    notes = [
        "NL samenstellingen verhogen long_word_pct zonder per se moeilijker te zijn",
        "CEFR is indicatief; interpretatie met context",
    ]

    return {
        "band": band,
        "overall_label_nl": label,
        "suitable_for": suitable,
        "not_suitable_for": not_suitable,
        "primary_drivers": drivers,
        "notes": notes,
    }


