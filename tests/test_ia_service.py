from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import ia_service


def _fake_openai_response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


def test_detect_reflection_themes_identifies_ansiedade():
    themes = ia_service.detect_reflection_themes(
        "Estou muito ansiosa, preocupada e nervosa com tudo."
    )

    assert "ansiedade" in themes


def test_detect_reflection_themes_identifies_sono():
    themes = ia_service.detect_reflection_themes(
        "Quase não consegui dormir e acordei várias vezes."
    )

    assert "sono" in themes


def test_detect_reflection_themes_identifies_cansaco():
    themes = ia_service.detect_reflection_themes(
        "Estou exausta, sem energia e muito sobrecarregada."
    )

    assert "cansaço" in themes


def test_detect_reflection_themes_identifies_trabalho():
    themes = ia_service.detect_reflection_themes(
        "O trabalho, os prazos e a reunião com o chefe me pesaram muito."
    )

    assert "trabalho" in themes


def test_detect_reflection_themes_returns_default_when_nothing_matches():
    themes = ia_service.detect_reflection_themes("Hoje observei o céu e reguei plantas.")

    assert themes == ia_service.DEFAULT_REFLECTION_THEMES


def test_get_neuro_tip_candidates_returns_three_valid_options():
    candidates = ia_service.get_neuro_tip_candidates(["ansiedade", "trabalho"])

    assert len(candidates) == 3
    assert len(set(candidates)) == 3
    assert all(ia_service._is_valid_neuro_tip(option) for option in candidates)


def test_get_neuro_tip_candidates_are_varied_across_calls(monkeypatch):
    monkeypatch.setattr(ia_service.random, "sample", lambda seq, count: list(seq)[-count:])
    first = ia_service.get_neuro_tip_candidates(["ansiedade", "trabalho"])

    monkeypatch.setattr(ia_service.random, "sample", lambda seq, count: list(seq)[:count])
    second = ia_service.get_neuro_tip_candidates(["ansiedade", "trabalho"])

    assert first != second


def test_get_activity_candidates_returns_three_valid_options():
    candidates = ia_service.get_activity_candidates(["sono", "cansaço"])

    assert len(candidates) == 3
    assert len(set(candidates)) == 3
    assert all(ia_service._is_valid_activity(option) for option in candidates)


def test_get_activity_candidates_are_varied_across_calls(monkeypatch):
    monkeypatch.setattr(ia_service.random, "sample", lambda seq, count: list(seq)[-count:])
    first = ia_service.get_activity_candidates(["sono", "cansaço"])

    monkeypatch.setattr(ia_service.random, "sample", lambda seq, count: list(seq)[:count])
    second = ia_service.get_activity_candidates(["sono", "cansaço"])

    assert first != second


def test_neuro_tip_fallback_is_not_always_the_same(monkeypatch):
    options = []

    monkeypatch.setattr(ia_service.random, "choice", lambda seq: seq[0])
    options.append(ia_service._fallback_neuro_tip())

    monkeypatch.setattr(ia_service.random, "choice", lambda seq: seq[-1])
    options.append(ia_service._fallback_neuro_tip())

    assert len(set(options)) == 2


def test_activity_fallback_is_not_always_the_same(monkeypatch):
    options = []

    monkeypatch.setattr(ia_service.random, "choice", lambda seq: seq[0])
    options.append(ia_service._fallback_activity())

    monkeypatch.setattr(ia_service.random, "choice", lambda seq: seq[-1])
    options.append(ia_service._fallback_activity())

    assert len(set(options)) == 2


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tente meditação depois do almoço.", False),
        ("Respiração guiada pode resolver tudo.", False),
        ("Procure terapia porque isso cura.", False),
        ("Falar das emoções ajuda o intestino.", False),
        ("Beber água e incluir aveia no dia a dia ajuda a microbiota.", True),
    ],
)
def test_is_valid_neuro_tip_rules(text: str, expected: bool):
    assert ia_service._is_valid_neuro_tip(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Faça journaling por 10 minutos.", False),
        ("Escreva em um diário à noite.", False),
        ("Pratique meditação guiada.", False),
        ("Converse na terapia antes de dormir.", False),
        ("Faça uma caminhada leve e beba água.", True),
    ],
)
def test_is_valid_activity_rules(text: str, expected: bool):
    assert ia_service._is_valid_activity(text) is expected


def test_generate_feedback_structured_uses_secure_logs_without_clinical_text(monkeypatch):
    log_messages: list[str] = []

    monkeypatch.setattr(
        ia_service.client.chat.completions,
        "create",
        lambda **kwargs: _fake_openai_response(
            '{"feedback":"Texto breve sobre trabalho e ansiedade. O que parece mais pesado nisso?","neuro_tip":"Beba água ao longo do dia e inclua aveia e frutas para apoiar a microbiota.","activity":"Faça uma caminhada leve de 10 minutos e tome água."}'
        ),
    )
    monkeypatch.setattr(ia_service.logger, "info", lambda message: log_messages.append(message))
    monkeypatch.setattr(ia_service.logger, "exception", lambda message: log_messages.append(message))

    reflection_text = "Estou ansiosa com o trabalho e muito cansada."
    anamnesis_summary = "Histórico clínico sensível que não deve aparecer em logs."

    result = ia_service.generate_feedback_structured(
        reflection_text=reflection_text,
        anamnesis_summary=anamnesis_summary,
    )

    joined_logs = "\n".join(log_messages)

    assert result["feedback"]
    assert "RAW_RESPONSE" not in joined_logs
    assert reflection_text not in joined_logs
    assert anamnesis_summary not in joined_logs
    assert result["feedback"] not in joined_logs
    assert result["neuro_tip"] not in joined_logs
    assert result["activity"] not in joined_logs
    assert "response_chars=" in joined_logs
    assert "json_keys=" in joined_logs

