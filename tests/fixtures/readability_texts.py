# Calibration anchor texts (Dutch). Longer categories reach approximate word counts
# by repeating base sentences.

def _repeat_sentence(sentence: str, target_words: int) -> str:
    words = sentence.strip().split()
    times = max(1, target_words // max(1, len(words)))
    return " ".join([sentence] * times)


READABILITY_TEXTS = {
    "kleuter": "Dit is een korte zin. Nog een zin.",
    "kind": "Deze tekst is eenvoudig. We gebruiken korte zinnen en simpele woorden.",
    "puber": _repeat_sentence(
        "De leerling leest regelmatig artikelen over sport en muziek op het internet.", 200
    ),
    "volwassen": _repeat_sentence(
        "De gemeente publiceert periodiek informatie over dienstverlening en procedures.", 240
    ),
    "gevorderd": _repeat_sentence(
        "Het beleidskader beschrijft procesafspraken, verantwoordelijkheden en afstemming met partners.", 280
    ),
    "academisch": _repeat_sentence(
        "Deze academische verhandeling bespreekt theoretische kaders en methodologische implicaties uitgebreid.", 320
    ),
}

