import math
import re
from dataclasses import dataclass
from typing import Iterable


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
    flesch_douma: float | None
    cefr_hint: str | None
    cefr_confidence: float | None


def _split_sentences(text: str) -> list[str]:
    # Basic sentence split; keep non-empty parts
    parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return parts or [text.strip()]


def _tokenize_words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _is_long_word(word: str) -> bool:
    # Long words: > 6 letters
    return len([ch for ch in word if ch.isalpha()]) > 6


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
    wps = len(words) / sentences
    spw = total_syll / len(words)
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
            cefr_hint="A1",
            cefr_confidence=0.3,
        )

    long_word_count = sum(1 for w in words if _is_long_word(w))
    avg_sentence_len = word_count / sentence_count
    long_word_pct = (long_word_count * 100.0) / word_count
    lix = avg_sentence_len + long_word_pct

    flesch = _compute_flesch_douma(words, sentence_count) if include_flesch_douma else None
    cefr_hint, cefr_conf = _cefr_from_lix(lix)

    return ReadabilityStats(
        word_count=word_count,
        sentence_count=sentence_count,
        long_word_count=long_word_count,
        avg_sentence_length=round(avg_sentence_len, 2),
        long_word_pct=round(long_word_pct, 2),
        lix=round(lix, 2),
        flesch_douma=flesch,
        cefr_hint=cefr_hint,
        cefr_confidence=cefr_conf,
    )


