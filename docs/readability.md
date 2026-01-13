# Leesbaarheid/taalniveau – Uitleg

Deze endpoint analyseert Nederlandse tekst op leesbaarheid en geeft deterministische metrics terug.

- Route: `POST /api/v1/analyze/readability`
- Body:
  ```json
  {
    "text": "…",
    "language": "nl",
    "metrics": ["lix", "flesch_douma", "stats"]
  }
  ```
- Default metrics als `metrics` ontbreekt: `["lix","stats"]`.

## Metrics

- LIX (Leesbaarheidsindex):
  - Definitie: `LIX = gemiddelde_zinslengte + percentage_lange_woorden`
  - Gemiddelde zinslengte = aantal woorden / aantal zinnen
  - Lange woorden: > 6 letters (alleen alfabetische tekens geteld). Configureerbaar via `LONG_WORD_LEN` (standaard 7).
  - Let op: Nederlandse samenstellingen verhogen `long_word_pct` zonder per se moeilijker te zijn.
  - Interpretatie (indicatief): hoe hoger, hoe complexer.

- Basisstatistieken (stats):
  - `avg_sentence_length` (float)
  - `long_word_pct` (float, 0-100)
  - `word_count`, `sentence_count` (integers)

- Flesch–Douma (optioneel, benadering):
  - Gebaseerd op schatting van syllaben per woord en woorden per zin.
  - Wordt alleen berekend als `"flesch_douma"` in `metrics` zit.
  - Score is indicatief; voor NL bestaan varianten/constantes in de literatuur.
  - Guardrails: we rapporteren `syllables_per_word`. Als die buiten redelijke bandbreedte valt (bv. < 0.8 of > 4.0), dan markeren we de score als ongeldig en zetten `flesch_douma` op `null` met `flesch_douma_status: "invalid_syllable_estimate"`.

## CEFR hint

We geven een grove CEFR-inschatting op basis van LIX (richtinggevend) met bewuste lage/middelhoge confidence:

- LIX < 25 → A1 (0.6)
- 25–30 → A2 (0.55)
- 30–40 → B1 (0.5)
- 40–50 → B2 (0.45)
- 50–60 → C1 (0.4)
- ≥ 60 → C2 (0.35)

Gebruik dit uitsluitend als indicatie; voor formele niveaubepaling is aanvullend onderzoek nodig.

## Judgement (deterministisch)

Naast de losse metrics geven we een samenvattend oordeel terug:

```json
{
  "band": "easy|medium|complex|very_complex",
  "overall_label_nl": "Eenvoudig|Gemiddeld|Complex|Zeer complex",
  "suitable_for": ["..."],
  "not_suitable_for": ["..."],
  "primary_drivers": ["hoog aandeel lange woorden", "lange zinnen", "..."],
  "notes": ["NL samenstellingen verhogen long_word_pct ...", "CEFR indicatief"]
}
```

Bepaling gebeurt primair op LIX (drempels): `<30 easy`, `<40 medium`, `<55 complex`, `>=55 very_complex`. Drivers zijn o.a. een hoog aandeel lange woorden (`long_word_pct >= 35`) en lange zinnen (`avg_sentence_length >= 20`). CEFR blijft indicatief, met lage confidence.

## Validatie

- Lege tekst → 400
- Extreem lange tekst (>200.000 tekens) → 400

## Voorbeeld

Request:
```bash
curl -s -X POST "$BASE/api/v1/analyze/readability" \
  -H "Content-Type: application/json" \
  -d '{
        "text": "De gemeente publiceert vandaag een overzicht van nieuwe beleidsmaatregelen. Deze maatregelen zijn bedoeld om de dienstverlening te verbeteren en processen te vereenvoudigen. Burgers kunnen via het digitale loket meer informatie vinden en vragen stellen. Daarnaast worden bestaande procedures afgestemd op recente wetgeving.",
        "language": "nl",
        "metrics": ["lix","stats","flesch_douma"]
      }'
```

Response (voorbeeld):
```json
{
  "lix": 60.5,
  "flesch_douma": null,
  "flesch_douma_status": "invalid_syllable_estimate",
  "avg_sentence_length": 10.5,
  "long_word_pct": 50.0,
  "word_count": 42,
  "sentence_count": 4,
  "cefr_hint": "C2",
  "cefr_confidence": 0.35,
  "syllables_per_word": 4.5,
  "judgement": {
    "band": "very_complex",
    "overall_label_nl": "Zeer complex",
    "suitable_for": ["specialistische documenten","beleids- en onderzoeksrapporten"],
    "not_suitable_for": ["publieksgerichte communicatie","laagdrempelige webteksten"],
    "primary_drivers": ["hoog aandeel lange woorden","lange zinnen"],
    "notes": ["NL samenstellingen verhogen long_word_pct zonder per se moeilijker te zijn","CEFR is indicatief; interpretatie met context"]
  },
  "metrics_computed": ["flesch_douma","lix","stats"]
}
```

## Opmerkingen

- De implementatie gebruikt geen externe services en is deterministisch.
- Resultaten kunnen per teksttype sterk variëren; vooral `flesch_douma` is een benadering.


