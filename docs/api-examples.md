# OpenAnonymiser – API voorbeelden (curl)

Snelle voorbeelden om de API buiten Swagger te testen.

## Base URLs
- Prod: https://api.openanonymiser.commonground.nu
- Staging: https://api.openanonymiser.accept.commonground.nu

Vervang BASE door één van bovenstaande.

## Health
```bash
curl -s BASE/api/v1/health
```

## Analyze Text
```bash
curl -s -X POST BASE/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Jan Jansen woont op Kerkstraat 10, 1234 AB Amsterdam. IBAN: NL91ABNA0417164300.",
    "language": "nl",
    "entities": ["PERSON","IBAN","ADDRESS"]
  }'
```

Met engine override:
```bash
curl -s -X POST BASE/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Bel 0612345678 of mail jan@example.com",
    "nlp_engine": "spacy"
  }'
```

## Leesbaarheid / Taalniveau

Endpoint: `POST /api/v1/analyze/readability`

```bash
curl -s -X POST BASE/api/v1/analyze/readability \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Dit is een eenvoudige Nederlandse zin. Nog een simpele zin.",
    "language": "nl",
    "metrics": ["lix","stats","flesch_douma"]
  }'
```

Voorbeeldresponse:
```json
{
  "lix": 28.5,
  "avg_sentence_length": 12.0,
  "long_word_pct": 16.67,
  "word_count": 24,
  "sentence_count": 2,
  "flesch_douma": 68.2,
  "cefr_hint": "B1",
  "cefr_confidence": 0.5,
  "metrics_computed": ["flesch_douma","lix","stats"]
}
```

Notities:
- LIX: woord/zin + percentage lange woorden (>6 letters).
- Flesch–Douma: indicatieve score (benadering). Ranges zijn richtinggevend.
- CEFR-hint is afgeleid van LIX en bij benadering; confidence is bewust laag/midden.

## Anonymize Text
```bash
curl -s -X POST BASE/api/v1/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Mail Jan op jan.jansen@example.com of bel 0612345678.",
    "language": "nl",
    "anonymization_strategy": "replace"
  }'
```

## Documenten

Upload:
```bash
curl -s -X POST \
  -F "files=@test.pdf" \
  BASE/api/v1/documents/upload
```

Anonymize (met het teruggegeven id):
```bash
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"pii_entities_to_anonymize":["PERSON","EMAIL","PHONE_NUMBER","IBAN","ADDRESS"]}' \
  BASE/api/v1/documents/<FILE_ID>/anonymize
```

Download:
```bash
curl -L -o output.pdf BASE/api/v1/documents/<FILE_ID>/download
```


