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


def test_sanitize_for_ai_removes_identifiers_and_preserves_general_meaning():
    text = (
        "Meu nome e Maria Silva, meu email e maria.silva@example.com, "
        "telefone (11) 91234-5678, CPF 123.456.789-10, "
        "moro na Rua das Flores 123, CEP 04567-890, "
        "minha mae Ana ficou preocupada, veja https://portal.exemplo.com/protocolo/9988776655. "
        "No trabalho estou ansiosa e cansada. Protocolo 1122334455."
    )

    sanitized = ia_service.sanitize_for_ai(text)

    assert sanitized != text
    assert "maria.silva@example.com" not in sanitized
    assert "91234-5678" not in sanitized
    assert "123.456.789-10" not in sanitized
    assert "Rua das Flores" not in sanitized
    assert "04567-890" not in sanitized
    assert "https://portal.exemplo.com" not in sanitized
    assert "Ana" not in sanitized
    assert "[EMAIL_REMOVIDO]" in sanitized
    assert "[TELEFONE_REMOVIDO]" in sanitized
    assert "[CPF_REMOVIDO]" in sanitized
    assert "[ENDERECO_REMOVIDO]" in sanitized
    assert "[FAMILIAR_REMOVIDO]" in sanitized
    assert "[URL_REMOVIDA]" in sanitized
    assert "[IDENTIFICADOR_REMOVIDO]" in sanitized
    assert "trabalho" in sanitized
    assert "ansiosa" in sanitized
    assert "cansada" in sanitized


def test_sanitize_for_ai_masks_long_identifiers_and_direct_names():
    text = "Eu sou Joao Pedro e o protocolo 998877665544 esta vinculado ao cadastro 112233445566."

    sanitized = ia_service.sanitize_for_ai(text)

    assert "Joao Pedro" not in sanitized
    assert "998877665544" not in sanitized
    assert "112233445566" not in sanitized
    assert "[NOME_REMOVIDO]" in sanitized
    assert sanitized.count("[IDENTIFICADOR_REMOVIDO]") >= 2


def test_detect_reflection_themes_identifies_ansiedade():
    themes = ia_service.detect_reflection_themes(
        "Estou muito ansiosa, preocupada e nervosa com tudo."
    )

    assert "ansiedade" in themes


def test_detect_reflection_themes_identifies_sono():
    themes = ia_service.detect_reflection_themes(
        "Quase nao consegui dormir e acordei varias vezes."
    )

    assert "sono" in themes


def test_detect_reflection_themes_identifies_cansaco():
    themes = ia_service.detect_reflection_themes(
        "Estou exausta, sem energia e muito sobrecarregada."
    )

    assert "cansaco" in themes


def test_detect_reflection_themes_identifies_trabalho():
    themes = ia_service.detect_reflection_themes(
        "O trabalho, os prazos e a reuniao com o chefe me pesaram muito."
    )

    assert "trabalho" in themes


def test_detect_reflection_themes_returns_default_when_nothing_matches():
    themes = ia_service.detect_reflection_themes("Hoje observei o ceu e reguei plantas.")

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
    candidates = ia_service.get_activity_candidates(["sono", "cansaco"])

    assert len(candidates) == 3
    assert len(set(candidates)) == 3
    assert all(ia_service._is_valid_activity(option) for option in candidates)


def test_get_activity_candidates_are_varied_across_calls(monkeypatch):
    monkeypatch.setattr(ia_service.random, "sample", lambda seq, count: list(seq)[-count:])
    first = ia_service.get_activity_candidates(["sono", "cansaco"])

    monkeypatch.setattr(ia_service.random, "sample", lambda seq, count: list(seq)[:count])
    second = ia_service.get_activity_candidates(["sono", "cansaco"])

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
        ("Tente meditacao depois do almoco.", False),
        ("Respiracao guiada pode resolver tudo.", False),
        ("Procure terapia porque isso cura.", False),
        ("Falar das emocoes ajuda o intestino.", False),
        ("Use suplementos para o cerebro.", False),
        ("Beber agua e incluir aveia no dia a dia ajuda a microbiota.", True),
    ],
)
def test_is_valid_neuro_tip_rules(text: str, expected: bool):
    assert ia_service._is_valid_neuro_tip(text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Faca journaling por 10 minutos.", False),
        ("Escreva em um diario a noite.", False),
        ("Pratique meditacao guiada.", False),
        ("Converse na terapia antes de dormir.", False),
        ("Faca uma caminhada leve e beba agua.", True),
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
            '{"feedback":"Voce citou trabalho e ansiedade, junto com cansaco. O que parece mais pesado nisso?","neuro_tip":"Beba agua ao longo do dia e inclua aveia e frutas para apoiar a microbiota.","activity":"Faca uma caminhada leve de 10 minutos e tome agua."}'
        ),
    )
    monkeypatch.setattr(ia_service.logger, "info", lambda message: log_messages.append(message))
    monkeypatch.setattr(ia_service.logger, "exception", lambda message: log_messages.append(message))

    reflection_text = "Meu email e maria@example.com e estou ansiosa com o trabalho."
    anamnesis_summary = "Minha mae Ana relata muita pressao em casa."

    result = ia_service.generate_feedback_structured(
        reflection_text=reflection_text,
        anamnesis_summary=anamnesis_summary,
    )

    joined_logs = "\n".join(log_messages)

    assert result["feedback"]
    assert "RAW_RESPONSE" not in joined_logs
    assert reflection_text not in joined_logs
    assert anamnesis_summary not in joined_logs
    assert ia_service.sanitize_for_ai(reflection_text) not in joined_logs
    assert ia_service.sanitize_for_ai(anamnesis_summary) not in joined_logs
    assert result["feedback"] not in joined_logs
    assert result["neuro_tip"] not in joined_logs
    assert result["activity"] not in joined_logs
    assert "response_chars=" in joined_logs
    assert "json_keys=" in joined_logs


def test_generate_feedback_structured_sends_only_sanitized_prompt(monkeypatch):
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return _fake_openai_response(
            '{"feedback":"Voce citou trabalho e cansaco, alem de ansiedade. O que pode ser priorizado agora?","neuro_tip":"Distribuir agua e refeicoes ao longo do dia pode ajudar a manter mais estabilidade corporal.","activity":"Levante, caminhe alguns minutos e tome agua antes de voltar a rotina."}'
        )

    monkeypatch.setattr(ia_service.client.chat.completions, "create", fake_create)

    reflection_text = (
        "Meu nome e Maria Silva, email maria@example.com, telefone (11) 91234-5678, "
        "CPF 123.456.789-10, moro na Rua Alfa 45. Minha mae Ana discutiu comigo. "
        "No trabalho estou ansiosa e cansada. Veja https://exemplo.com/abc."
    )
    anamnesis_summary = "Paciente Joana Souza relata insonia e protocolo 9988776655."

    ia_service.generate_feedback_structured(
        reflection_text=reflection_text,
        anamnesis_summary=anamnesis_summary,
    )

    prompt = captured["messages"][1]["content"]

    assert "maria@example.com" not in prompt
    assert "91234-5678" not in prompt
    assert "123.456.789-10" not in prompt
    assert "Rua Alfa 45" not in prompt
    assert "mae Ana" not in prompt
    assert "https://exemplo.com/abc" not in prompt
    assert "9988776655" not in prompt
    assert "[EMAIL_REMOVIDO]" in prompt
    assert "[TELEFONE_REMOVIDO]" in prompt
    assert "[CPF_REMOVIDO]" in prompt
    assert "[ENDERECO_REMOVIDO]" in prompt
    assert "[FAMILIAR_REMOVIDO]" in prompt
    assert "[URL_REMOVIDA]" in prompt
    assert "[IDENTIFICADOR_REMOVIDO]" in prompt


def test_generate_feedback_structured_uses_random_catalog_fallback_for_invalid_ai_fields(monkeypatch):
    monkeypatch.setattr(
        ia_service.client.chat.completions,
        "create",
        lambda **kwargs: _fake_openai_response(
            '{"feedback":"Voce citou trabalho e cansaco. O que pode aliviar a sobrecarga?","neuro_tip":"Faca meditacao guiada depois do almoco.","activity":"Escreva em um diario por 10 minutos."}'
        ),
    )
    monkeypatch.setattr(ia_service.random, "choice", lambda seq: seq[-1])

    result = ia_service.generate_feedback_structured(
        reflection_text="Estou cansada e ansiosa com o trabalho.",
        anamnesis_summary=None,
    )

    assert ia_service._is_valid_neuro_tip(result["neuro_tip"])
    assert ia_service._is_valid_activity(result["activity"])
    assert "medit" not in ia_service._normalize_for_match(result["neuro_tip"])
    assert "diario" not in ia_service._normalize_for_match(result["activity"])
