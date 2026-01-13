import hashlib
import logging
import re
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status

from src.api.config import settings
from src.api.dtos import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    AnonymizeTextRequest,
    AnonymizeTextResponse,
    PIIEntity,
)
from src.api.services.text_analyzer import ModularTextAnalyzer
from src.api.dtos import ReadabilityRequest, ReadabilityResponse
from src.api.utils.readability import compute_readability

logger = logging.getLogger(__name__)
text_analysis_router = APIRouter(tags=["text-analysis"])


def _normalize_text_for_hash(text: str) -> str:
    """Normalize text for hashing: strip and collapse whitespace."""
    stripped = text.strip()
    return re.sub(r"\s+", " ", stripped)


def _compute_input_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text."""
    normalized = _normalize_text_for_hash(text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def create_pii_entities_from_results(results: list[dict]) -> list[PIIEntity]:
    """Convert ModularTextAnalyzer results to PIIEntity DTOs."""
    pii_entities = []
    for result in results:
        # Handle different score types (some models return empty string, others float)
        score = result.get("score")
        if score == "" or score is None:
            score = None
        elif isinstance(score, str) and score.strip() == "":
            score = None

        pii_entities.append(
            PIIEntity(
                entity_type=result["entity_type"],
                text=result["text"],
                start=result["start"],
                end=result["end"],
                score=score,
            )
        )
    return pii_entities


@text_analysis_router.post("/analyze")
async def analyze_text(
    request: AnalyzeTextRequest,
) -> AnalyzeTextResponse:
    """Analyze text for PII entities using the specified NLP engine.

    This endpoint accepts a text string and returns detected PII entities
    with their positions, types, and confidence scores (when available).

    Args:
        request: AnalyzeTextRequest containing text and analysis parameters

    Returns:
        AnalyzeTextResponse with detected PII entities and metadata

    Raises:
        HTTPException: On analysis failure or invalid parameters
    """
    start_time = time.perf_counter()

    try:
        # Initialize analyzer with specified engine or use default
        nlp_engine = request.nlp_engine or settings.DEFAULT_NLP_ENGINE
        analyzer = ModularTextAnalyzer(nlp_engine=nlp_engine)

        # Perform analysis
        entities_to_analyze = request.entities or settings.DEFAULT_ENTITIES
        results = analyzer.analyze_text(
            text=request.text,
            entities=entities_to_analyze,
            language=request.language,
        )

        # Convert results to DTOs
        pii_entities = create_pii_entities_from_results(results)

        end_time = time.perf_counter()
        processing_time_ms = int((end_time - start_time) * 1000)

        logger.info(
            f"Text analysis completed: {len(pii_entities)} entities found "
            f"in {processing_time_ms}ms using {nlp_engine} engine"
        )

        return AnalyzeTextResponse(
            pii_entities=pii_entities,
            text_length=len(request.text),
            processing_time_ms=processing_time_ms,
            nlp_engine_used=nlp_engine,
        )

    except Exception as e:
        logger.error(f"Text analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text analysis failed: {str(e)}",
        )


@text_analysis_router.post("/anonymize")
async def anonymize_text(
    request: AnonymizeTextRequest,
) -> AnonymizeTextResponse:
    """Anonymize PII entities in text using the specified strategy.

    This endpoint accepts a text string and returns the anonymized version
    along with details about the entities that were found and anonymized.

    Args:
        request: AnonymizeTextRequest containing text and anonymization parameters

    Returns:
        AnonymizeTextResponse with original text, anonymized text, and entities found

    Raises:
        HTTPException: On anonymization failure or invalid parameters
    """
    start_time = time.perf_counter()

    try:
        # Initialize analyzer with specified engine or use default
        nlp_engine = request.nlp_engine or settings.DEFAULT_NLP_ENGINE
        analyzer = ModularTextAnalyzer(nlp_engine=nlp_engine)

        # First analyze to find entities
        entities_to_analyze = request.entities or settings.DEFAULT_ENTITIES
        analysis_results = analyzer.analyze_text(
            text=request.text,
            entities=entities_to_analyze,
            language=request.language,
        )

        # Then anonymize the text
        anonymized_text = analyzer.anonymize_text(
            text=request.text,
            entities=entities_to_analyze,
            language=request.language,
        )

        # Convert analysis results to DTOs
        entities_found = create_pii_entities_from_results(analysis_results)

        end_time = time.perf_counter()
        processing_time_ms = int((end_time - start_time) * 1000)

        logger.info(
            f"Text anonymization completed: {len(entities_found)} entities anonymized "
            f"in {processing_time_ms}ms using {nlp_engine} engine and {request.anonymization_strategy} strategy"
        )

        return AnonymizeTextResponse(
            original_text=request.text,
            anonymized_text=anonymized_text,
            entities_found=entities_found,
            text_length=len(request.text),
            processing_time_ms=processing_time_ms,
            nlp_engine_used=nlp_engine,
            anonymization_strategy=request.anonymization_strategy,
        )

    except Exception as e:
        logger.error(f"Text anonymization failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text anonymization failed: {str(e)}",
        )


@text_analysis_router.post("/analyze/readability")
async def analyze_readability(
    request: ReadabilityRequest,
    x_request_id: Optional[str] = Header(None, alias="X-Request-Id"),
) -> ReadabilityResponse:
    """Compute readability metrics (LIX, basic stats, optional Flesch–Douma) for Dutch text.

    This does not anonymize or alter the text; pure analysis only.

    Headers:
        X-Request-Id: Optional correlation ID. If not provided, a UUIDv4 is generated.
    """
    # Determine request_id: use header or generate
    req_id = x_request_id if x_request_id else str(uuid.uuid4())

    try:
        # Manual input validation → return 400, not 422
        clean_text = (request.text or "").strip()
        if not clean_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Text cannot be empty"
            )
        if len(clean_text) > 200_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text too long; please submit <= 200,000 characters",
            )

        # Compute input hash for fingerprinting (uses original text)
        input_hash = _compute_input_hash(request.text)

        metrics_requested = {m.lower() for m in (request.metrics or ["lix", "stats"])}
        include_flesch = "flesch_douma" in metrics_requested

        stats = compute_readability(clean_text, include_flesch_douma=include_flesch)

        # Build payload with metadata first
        payload: dict = {
            "request_id": req_id,
            "input_hash": input_hash,
            "meta": request.meta.model_dump() if request.meta else None,
            "word_count": stats.word_count,
            "sentence_count": stats.sentence_count,
            "metrics_computed": sorted(list(metrics_requested)),
            "judgement": stats.judgement,
            "cefr_hint": stats.cefr_hint,
            "cefr_confidence": stats.cefr_confidence,
        }

        if "lix" in metrics_requested:
            payload.update(
                {
                    "lix": stats.lix,
                    "avg_sentence_length": stats.avg_sentence_length,
                    "long_word_pct": stats.long_word_pct,
                }
            )

        # Optional debug fields controlled by config
        from src.api.readability_config import get_readability_config

        cfg = get_readability_config()
        if cfg.output.include_debug_fields:
            payload["syllables_per_word"] = stats.syllables_per_word

        if include_flesch:
            payload["flesch_douma"] = stats.flesch_douma
            payload["flesch_douma_status"] = stats.flesch_douma_status

        logger.debug(f"Readability analysis completed [request_id={req_id}]")
        return ReadabilityResponse(**payload)  # type: ignore[arg-type]

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException as he:
        # Preserve explicit HTTP errors (e.g., our 400 validations)
        raise he
    except Exception as e:
        logger.error(
            f"Readability analysis failed [request_id={req_id}]: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Readability analysis failed: {str(e)}",
        )