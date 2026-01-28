import json
import re
from typing import Any, Dict, Optional

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

# Indícios de que a frase é realmente sobre alimentação / intestino-cérebro
_NEURO_KEYWORDS = [
    "água", "hidrat", "fibr", "prote", "fruta", "veget", "legume", "salada",
    "ômega", "omega", "probió", "probiot", "prebió", "prebiot", "ferment",
    "iogurte", "kefir", "intestin", "microbi", "cérebro", "nutri",
    "açúcar", "cafe", "cafeína", "refei", "aliment", "comida", "ultraprocess",
    "processad", "sement", "castanh", "aveia"
]

# Termos que indicam que a IA “escapou” pra psicologia no campo de nutrição
_FORBIDDEN_NEURO_HINTS = [
    "autocompaix", "respir", "medit", "mindful", "terapia",
    "emoc", "sentiment", "ansiedad", "depress", "relax", "psicol",
    "journaling", "diário", "autoestima"
]


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` ou ``` ... ``` caso venha cercado."""
    if not text:
        return text
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    """Tenta converter a resposta em JSON de forma resiliente."""
    if not text:
        return None

    cleaned = _strip_code_fences(text)

    # tentativa direta
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # tentativa: extrair o primeiro bloco {...}
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    return None


def _normalize_one_line(text: Optional[str], *, max_chars: int) -> Optional[str]:
    if not text:
        return None
    t = " ".join(str(text).split())
    if len(t) > max_chars:
        t = t[: max_chars - 1].rstrip() + "…"
    return t


def _is_valid_neuro_tip(text: Optional[str]) -> bool:
    """Valida se a dica parece ser de neuro nutrição e não de psicologia."""
    if not text:
        return False
    t = text.strip().lower()
    if not t:
        return False

    if any(bad in t for bad in _FORBIDDEN_NEURO_HINTS):
        return False

    return any(k in t for k in _NEURO_KEYWORDS)


def _fallback_neuro_tip() -> str:
    return (
        "Manter boa hidratação e incluir fibras (frutas, legumes e aveia) ajuda o intestino, "
        "o que pode apoiar o bem-estar do cérebro."
    )


def _fallback_activity() -> str:
    return "Faça uma caminhada leve de 10 a 15 minutos, em um ritmo confortável, apenas para movimentar o corpo."


def generate_feedback_structured(*, reflection_text: str) -> dict:
    """
    Gera feedback terapêutico com saída estruturada (JSON).
    - Não faz diagnóstico
    - Não prescreve medicamentos
    - Não dá instruções de urgência
    - Inclui dica específica de neuro nutrição (alimentação/cérebro-intestino)
    Retorna dict com chaves: feedback, neuro_tip, activity
    """

    reflection_text = (reflection_text or "").strip()
    if not reflection_text:
        return {
            "feedback": "Não recebi o texto da reflexão. Você pode enviar novamente para que eu possa responder com cuidado?",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    system_prompt = (
        "Você é um assistente de apoio terapêutico.\n"
        "Sua função é gerar devolutivas acolhedoras e educativas baseadas no texto do cliente.\n"
        "Regras:\n"
        "- Não faça diagnóstico.\n"
        "- Não prescreva medicamentos.\n"
        "- Não dê instruções de urgência.\n"
        "- Não substitua acompanhamento profissional.\n"
        "- Seja gentil, claro e objetivo.\n"
        "- Responda SEMPRE em JSON puro (sem markdown, sem texto fora do JSON).\n"
    )

    user_prompt = f"""
Gere uma devolutiva baseada na reflexão abaixo.

Retorne exatamente este JSON (apenas JSON):
{{
  "feedback": "texto acolhedor e educativo (até 1200 caracteres)",
  "neuro_tip": "dica curta de NEURO NUTRIÇÃO em 1 frase (alimentação/hidratação/hábitos alimentares ligados a cérebro e intestino). Proibido: respiração, autocompaixão, meditação, terapia, emoções.",
  "activity": "sugestão leve de atividade prática em 1 frase"
}}

Regras obrigatórias do campo neuro_tip:
- Fale apenas de alimentação, hidratação ou hábitos alimentares (microbiota/intestino-cérebro).
- Não prescreva dieta, não prometa cura, não indique suplemento/medicamento.
- Seja simples e aplicável no dia a dia.

Reflexão do cliente:
{reflection_text}
""".strip()

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    content = (response.choices[0].message.content or "").strip()

    data = _safe_json_loads(content)
    if not isinstance(data, dict):
        # fallback: guarda o texto como feedback
        return {
            "feedback": _normalize_one_line(content, max_chars=1200) or "Não foi possível gerar a devolutiva no formato esperado.",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    feedback = _normalize_one_line(data.get("feedback"), max_chars=1200)
    neuro_tip = _normalize_one_line(data.get("neuro_tip"), max_chars=240)
    activity = _normalize_one_line(data.get("activity"), max_chars=240)

    # Garantias mínimas (pra bater com seu feedback/service.py que usa generated["feedback"])
    if not feedback:
        feedback = _normalize_one_line(content, max_chars=1200) or "Não foi possível gerar a devolutiva automaticamente."

    if not _is_valid_neuro_tip(neuro_tip):
        neuro_tip = _fallback_neuro_tip()

    if not activity:
        activity = _fallback_activity()

    return {
        "feedback": feedback,
        "neuro_tip": neuro_tip,
        "activity": activity,
    }
