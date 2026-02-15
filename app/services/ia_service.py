import json
import re
import uuid
import random
from typing import Any, Dict, Optional

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.core.logger import get_logger

logger = get_logger("ia_service")
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
    "journaling", "diário", "diario", "autoestima"
]

# ✅ Validação para ACTIVITY (pra não vir "diário", "meditação", etc.)
_ACTIVITY_KEYWORDS = [
    "caminh", "along", "moviment", "paus", "postur", "sol",
    "hidrata", "água", "descans", "sono", "banho", "corrid", "exerc"
]

_FORBIDDEN_ACTIVITY_HINTS = [
    "journaling", "diário", "diario", "escrev", "anot",
    "medit", "mindful", "respir", "terapia", "autocompaix", "relax"
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


def _is_valid_activity(text: Optional[str]) -> bool:
    """Valida se a activity é prática e não escapa para journaling/meditação/respiração."""
    if not text:
        return False
    t = text.strip().lower()
    if not t:
        return False

    if any(bad in t for bad in _FORBIDDEN_ACTIVITY_HINTS):
        return False

    return any(k in t for k in _ACTIVITY_KEYWORDS)


def _fallback_neuro_tip() -> str:
    return (
        "Manter boa hidratação e incluir fibras (frutas, legumes e aveia) ajuda o intestino, "
        "o que pode apoiar o bem-estar do cérebro."
    )


def _fallback_activity() -> str:
    return "Faça uma caminhada leve de 10 a 15 minutos, em um ritmo confortável, apenas para movimentar o corpo."


def _pick_style() -> str:
    """Escolhe um estilo para quebrar respostas repetidas (sem mudar schema)."""
    return random.choice([
        "estilo direto e objetivo (sem floreios)",
        "estilo acolhedor e conciso (sem clichês)",
        "estilo educativo com exemplo prático simples (1 exemplo)",
    ])


def generate_feedback_structured(*, reflection_text: str, anamnesis_summary: Optional[str] = None) -> dict:
    """
    Gera feedback terapêutico com saída estruturada (JSON).
    - Não faz diagnóstico
    - Não prescreve medicamentos
    - Não dá instruções de urgência
    - Não substitui acompanhamento profissional
    - Inclui dica específica de neuro nutrição (alimentação/cérebro-intestino)
    Retorna dict com chaves: feedback, neuro_tip, activity

    ✅ Usa "anamnesis_summary" como contexto (quando existir),
    sem reproduzir literalmente e sem expor dados sensíveis.
    """
    request_id = uuid.uuid4().hex[:8]

    reflection_text = (reflection_text or "").strip()
    anamnesis_summary = (anamnesis_summary or "").strip()

    # proteção simples pra não explodir tokens com anamneses enormes
    if len(anamnesis_summary) > 4000:
        anamnesis_summary = anamnesis_summary[:4000].rstrip() + "…"

    logger.info(
        f"[{request_id}] START model={OPENAI_MODEL} "
        f"input_chars={len(reflection_text)} anamnesis_chars={len(anamnesis_summary)}"
    )

    if not reflection_text:
        logger.info(f"[{request_id}] EMPTY_INPUT -> fallback")
        return {
            "feedback": "Não recebi o texto da reflexão. Você pode enviar novamente para que eu possa responder com cuidado?",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    style = _pick_style()
    logger.info(f"[{request_id}] STYLE={style}")

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
        "- Se houver ANAMNESE, use apenas como CONTEXTO; NÃO copie literalmente e NÃO exponha dados sensíveis.\n"
    )

    user_prompt = f"""
Gere uma devolutiva baseada na reflexão abaixo.
Use {style}.

Retorne exatamente este JSON (apenas JSON):
{{
  "feedback": "texto acolhedor e educativo (até 1200 caracteres)",
  "neuro_tip": "dica curta de NEURO NUTRIÇÃO em 1 frase (alimentação/hidratação/hábitos alimentares ligados a cérebro e intestino). Proibido: respiração, autocompaixão, meditação, terapia, emoções.",
  "activity": "sugestão leve e PRÁTICA em 1 frase (preferência: caminhada, alongamento, pausa de tela, tomar água, pegar sol). Proibido: diário/journaling, meditação, mindfulness, respiração guiada, terapia."
}}

Regras de qualidade do campo "feedback":
- Cite explicitamente 2 detalhes do texto do cliente (ex: trabalho, autocobrança, ansiedade, etc.).
- Evite clichês/começos genéricos (ex: "É compreensível...", "Seja gentil consigo mesmo...", "Cada passo é uma conquista...").
- Traga 1 pergunta reflexiva curta no final (1 frase).
- Sem diagnóstico; sem prometer cura; sem instruções de urgência.
- Se usar ANAMNESE: apenas como contexto. Não copiar literal; não revelar detalhes sensíveis.

Regras obrigatórias do campo neuro_tip:
- Fale apenas de alimentação, hidratação ou hábitos alimentares (microbiota/intestino-cérebro).
- Não prescreva dieta, não prometa cura, não indique suplemento/medicamento.
- Seja simples e aplicável no dia a dia.

ANAMNESE DO CLIENTE (contexto; não repetir literalmente):
{anamnesis_summary if anamnesis_summary else "(sem anamnese cadastrada)"}

Reflexão do cliente:
{reflection_text}
""".strip()

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            presence_penalty=0.4,
            frequency_penalty=0.3,
        )
    except Exception as e:
        logger.exception(f"[{request_id}] OPENAI_CALL_FAILED error={str(e)}")
        return {
            "feedback": "Não consegui gerar a devolutiva agora. Tente novamente em alguns instantes.",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    content = (response.choices[0].message.content or "").strip()
    logger.info(f"[{request_id}] RAW_RESPONSE={content}")

    data = _safe_json_loads(content)
    if not isinstance(data, dict):
        logger.info(f"[{request_id}] JSON_PARSE_FAILED -> fallback_structured")
        return {
            "feedback": _normalize_one_line(content, max_chars=1200)
            or "Não foi possível gerar a devolutiva no formato esperado.",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    logger.info(f"[{request_id}] PARSED_JSON keys={list(data.keys())}")

    feedback = _normalize_one_line(data.get("feedback"), max_chars=1200)
    neuro_tip = _normalize_one_line(data.get("neuro_tip"), max_chars=240)
    activity = _normalize_one_line(data.get("activity"), max_chars=240)

    if not feedback:
        logger.info(f"[{request_id}] feedback missing -> fallback_text")
        feedback = _normalize_one_line(content, max_chars=1200) or "Não foi possível gerar a devolutiva automaticamente."

    if not _is_valid_neuro_tip(neuro_tip):
        logger.info(f"[{request_id}] neuro_tip invalid -> fallback")
        neuro_tip = _fallback_neuro_tip()

    if not _is_valid_activity(activity):
        logger.info(f"[{request_id}] activity invalid -> fallback")
        activity = _fallback_activity()

    logger.info(f"[{request_id}] DONE ok")
    return {
        "feedback": feedback,
        "neuro_tip": neuro_tip,
        "activity": activity,
    }
