import re
import unicodedata

MAX_INPUT_CHARS = 1000
MAX_CONSENT_WORDS = 6

INPUT_TOO_LONG_MESSAGE = (
    f"Tu mensaje es muy largo (máximo {MAX_INPUT_CHARS} caracteres)"
    "¿Puedes resumirlo?"
)

CLINICAL_FALLBACK_MESSAGE = (
    """Lamento que tengas esa molestia. No puedo darte recomendaciones médicas ni
    decirte que evitar o cuando descansar, lo mejor es que consultes con un
    profesional. Cuando tengas las recomendaciones te puedo ayudar a ajustar tu plan"""
)

PAIN_WORDS = (
    "dolor", "duele", "lesion", "lastim", "molestia",
    "torcedura", "tirón", "desgarr", "esguince", "contractura",
)

AFFIRMATIVE = frozenset({
    "si", "claro", "dale", "ok", "okay", "vale", "adelante", "registrala",
    "registralo", "guardala", "guardalo", "porfa", "favor", "perfecto",
    "correcto", "afirmativo",
})

NEGATIVE = frozenset({"no", "nunca", "tampoco", "nop"})

CLINICAL_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\b(evita|evites|evitemos)\b",
        r"\b(reposo|descansa|descansar|descanso|descanse)\b",
        r"\b(hielo|antiinflamatori\w*|ibuprofeno|paracetamol|analgesic\w*|pomada|vendaje|inmoviliz\w*)\b",
        r"\b(tendinitis|esguince|desgarro|bursitis|artrosis|hernia|menisco|ligamento)\b",
        r"\bhasta que (te )?(sientas|recuperes|sanes)\b",
        r"\b(no hagas|no entrenes|no cargues|deja de entrenar)\b",
    )
]

def normalize(text: str) -> str:
    descomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in descomposed if unicodedata.category(c) != "Mn")

def mentions_pain(text: str) -> bool:
    normalized = normalize(text)
    return any(word in normalized for word in PAIN_WORDS)

def is_affirmative(text: str) -> bool:
    words = re.findall(r"[a-z]+", normalize(text))
    if not words or len(words) > MAX_CONSENT_WORDS:
        return False
    if any(word in NEGATIVE for word in words):
        return False
    return any(word in AFFIRMATIVE for word in words)

def violates_clinical_policy(text: str) -> bool:
    normalized = normalize(text)
    return any(pattern.search(normalized) for pattern in CLINICAL_PATTERNS)

