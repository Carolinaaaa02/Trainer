import pytest

from src.trainer.guardrails import is_affirmative, mentions_pain, violates_clinical_policy

@pytest.mark.parametrize(
    ("message", "expected"),
    [
("Sí", True),
        ("sí, por favor", True),
        ("Claro que sí", True),
        ("No, no la registres", False),
        ("No", False),
        ("Me duele la rodilla derecha hoy", False),
        ("sí me duele mucho la rodilla desde hace dos semanas", False),
    ]
)
def test_is_affirmative(message: str, expected: bool) -> None:
    assert is_affirmative(message) is expected

@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Me duele el hombro", True),
        ("Tengo una lesion en la rodilla", True),
        ("Hoy entrené piernas", False),
    ],
)
def test_mentions_pain(message: str, expected: bool) -> None:
    assert mentions_pain(message) is expected

@pytest.mark.parametrize(
    "text",
    [
        "Evitemos por completo cualquier ejercicio que involucre los hombros.",
        "Descansa unos días y ponte hielo.",
        "No cargues peso hasta que te sientas recuperada.",
    ],
)
def test_clinical_advice_is_detected(text: str) -> None:
    assert violates_clinical_policy(text) is True

def test_referral_to_professional_is_allowed() -> None:
    text = (
        "Ante cualquier molestia o dolor persistente, lo más recomendable es que "
        "consultes a un profesional de la salud. ¿Te gustaría que registre esta "
        "molestia en tu perfil?"
    )
    assert violates_clinical_policy(text) is False