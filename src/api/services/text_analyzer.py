import logging
from typing import List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

from src.api.config import settings
from src.api.utils.nlp.loader import load_nlp_engine
from src.api.utils.patterns import (
    EmailRecognizer,
    DutchIBANRecognizer,
    DutchBSNRecognizer,
    DutchDateRecognizer,
    DutchPhoneNumberRecognizer,
    DutchPassportIdRecognizer,
    DutchDriversLicenseRecognizer,
    CaseNumberRecognizer,
)


class ModularTextAnalyzer:
    """Modulaire analyzer-klasse voor Nederlandse tekst.

    Deze klasse combineert een configureerbare NLP-engine (zoals SpaCy of een
    HuggingFace transformers-model) met pattern recognizers voor het detecteren
    en anonimiseren van PII (zoals namen, telefoonnummers, e-mails, IBAN) in
    Nederlandse tekst. De workflow bestaat uit:

    1. Uitvoeren van NER via de gekozen NLP-engine.
    2. Toepassen van pattern recognizers (zoals custom regex voor IBAN, telefoon).
    3. Combineren en dedupliceren van resultaten.

    De klasse is uitbreidbaar met nieuwe modellen en recognizers en vormt de kern
    van de modulaire architectuur van deze service.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        nlp_engine: str = settings.DEFAULT_NLP_ENGINE,
    ) -> None:
        if model_name is None:
            model_name = (
                settings.DEFAULT_SPACY_MODEL
                if nlp_engine == "spacy"
                else settings.DEFAULT_TRANSFORMERS_MODEL
            )
        self.nlp_engine = load_nlp_engine(
            config_dict={"nlp_engine": nlp_engine, "model_name": model_name}
        )

        # Presidio always uses SpaCy for pattern recognizers, regardless of our NLP engine choice
        spacy_config = {
            "nlp_engine_name": "spacy",  # Presidio only supports spacy
            "models": [
                {
                    "lang_code": settings.DEFAULT_LANGUAGE,
                    "model_name": settings.DEFAULT_SPACY_MODEL,  # Always use SpaCy model for Presidio
                }
            ],
        }

        spacy_provider = NlpEngineProvider(nlp_configuration=spacy_config)
        presidio_spacy_engine = spacy_provider.create_engine()

        # reuse the recognizer registry for the analyzer engine
        registry = RecognizerRegistry()
        registry.supported_languages = [settings.DEFAULT_LANGUAGE]

        recognizers_to_add = [
            DutchPhoneNumberRecognizer(),
            DutchIBANRecognizer(),
            DutchBSNRecognizer(),
            DutchDateRecognizer(),
            EmailRecognizer(),
            DutchPassportIdRecognizer(),
            DutchDriversLicenseRecognizer(),
            CaseNumberRecognizer(),
        ]
        for recognizer in recognizers_to_add:
            registry.add_recognizer(recognizer=recognizer)

        # Initialiseer de AnalyzerEngine met SpaCy-engine voor pattern recognizers
        self.analyzer = AnalyzerEngine(
            nlp_engine=presidio_spacy_engine,
            registry=registry,
            supported_languages=registry.supported_languages,
        )
        logging.debug(
            f"ModularTextAnalyzer is initialized with {len(recognizers_to_add)} recognizers, {spacy_config=}"
        )

    def analyze_text(
        self,
        text: str,
        entities: list = settings.DEFAULT_ENTITIES,
        language: str = settings.DEFAULT_LANGUAGE,
    ) -> list:
        """Analyseer tekst met behulp van de NLP-engine en pattern recognizers.

        Args:
            text (str): de tekst om te analyseren.
            entities (list, optional): entities om te analyseren. Defaults to DEFAULT_ENTITIES.
            language (str, optional): taal om in te analyseren. Defaults to DEFAULT_LANGUAGE.

        Returns:
            list: lijst van gedetecteerde entiteiten met hun start- en eindposities, type en score.
        """
        logging.debug(f"Analyzing text with {entities=} and {language=}")

        # Analyze with NLP engine (supports entity filtering)
        nlp_results = self.nlp_engine.analyze(text, entities, language)
        print(f"nlp_results: {nlp_results}")

        # Use pattern recognizers via Presidio AnalyzerEngine (detect ALL patterns first)
        try:
            pattern_results: List[RecognizerResult] = self.analyzer.analyze(
                text=text,
                entities=None,
                language=language,  # Don't filter here
            )
            print(f"pattern_results: {pattern_results}")
        except Exception as e:
            logging.warning(f"Pattern analysis failed: {e}")
            pattern_results = []

        # Convert pattern results to dict format
        pattern_dicts = [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score,
                "text": text[r.start : r.end],
            }
            for r in pattern_results
        ]

        # Combine all results
        all_results = nlp_results + pattern_dicts

        # Filter by requested entities if specified
        if entities and entities != settings.DEFAULT_ENTITIES:
            all_results = [r for r in all_results if r["entity_type"] in entities]

        # Deduplication based on start, end, entity_type
        seen = set()
        unique_results = []
        for r in all_results:
            key = (r["start"], r["end"], r["entity_type"])
            if key not in seen:
                unique_results.append(r)
                seen.add(key)

        return unique_results

    def anonymize_text(
        self,
        text: str,
        entities: Optional[List] = None,
        language: str = settings.DEFAULT_LANGUAGE,
    ) -> str:
        """Function to anonymize text by replacing detected entities with placeholders.

        Args:
            text (str): the text to anonymize.
            entities (list, optional): the entities to anonymize. Defaults to None.
            language (str, optional): the language to anonymize in. Defaults to DEFAULT_LANGUAGE.

        Returns:
            str: the anonymized text with placeholders for detected entities.
        """
        results = self.analyze_text(text, entities, language)  # type: ignore

        # Sorteer op start, zodat vervangen van achter naar voren kan
        sorted_results = sorted(results, key=lambda x: x["start"], reverse=True)
        anonymized = text
        for ent in sorted_results:
            anonymized = (
                anonymized[: ent["start"]]
                + f"<{ent['entity_type']}>"
                + anonymized[ent["end"] :]
            )
        return anonymized
