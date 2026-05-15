import json
import re
import uuid
import random
import unicodedata
from typing import Any, Dict, Optional

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.core.logger import get_logger

logger = get_logger("ia_service")
client = OpenAI(api_key=OPENAI_API_KEY)

DEFAULT_REFLECTION_THEMES = ["cansaço", "autocobrança", "sono"]

_THEME_KEYWORDS = {
    "ansiedade": [
        "ansiedade", "ansioso", "ansiosa", "ansioso", "ansiosa",
        "preocup", "apreens", "nervos", "taquic", "angust",
    ],
    "sono": [
        "sono", "dormi", "dormir", "insonia", "insônia",
        "acordei", "acordar", "cama", "descanso", "descansar",
    ],
    "cansaço": [
        "cansaco", "cansaço", "exaust", "esgot", "fadig",
        "sem energia", "sem disposição", "sobrecarreg",
    ],
    "trabalho": [
        "trabalho", "empresa", "chefe", "reuniao", "reunião",
        "prazo", "meta", "colega", "escritorio", "escritório", "profissional",
    ],
    "autocobrança": [
        "autocobr", "me cobro", "me cobrar", "perfeccion", "culpa",
        "fracasso", "falhei", "falhar", "erro", "errar", "insuficient",
    ],
    "tristeza": [
        "triste", "tristeza", "desanim", "vazio", "abat",
        "chor", "desmotivad", "para baixo",
    ],
    "raiva": [
        "raiva", "irrit", "odio", "ódio", "bravo", "brava",
        "furios", "furiosa", "explodi", "explodir",
    ],
    "relacionamento": [
        "relacionamento", "parceir", "namor", "casamento", "famil",
        "família", "amigo", "amizade", "mãe", "pai", "irmã", "irma", "irmão", "irmao",
    ],
}

_NEURO_TIP_CATALOG = {
    "ansiedade": [
        "Fazer refeições em horários mais previsíveis e manter água por perto pode ajudar a reduzir picos de fome e desconforto intestinal ao longo do dia.",
        "Incluir aveia, frutas e legumes no dia a dia favorece fibras para a microbiota, o que apoia a comunicação entre intestino e cérebro.",
        "Diminuir o excesso de cafeína no fim do dia e reforçar a hidratação pode deixar o corpo menos sobrecarregado."
    ],
    "sono": [
        "Evitar refeições muito pesadas perto de dormir e manter boa hidratação ao longo do dia pode favorecer um descanso mais confortável.",
        "Uma refeição noturna mais leve, com alimentos de preparo simples, costuma ser mais gentil para o intestino antes de deitar.",
        "Manter horários regulares para jantar e incluir fibras no dia a dia ajuda o intestino a funcionar com mais previsibilidade."
    ],
    "cansaço": [
        "Ficar muitas horas sem comer pode aumentar a sensação de desgaste, então vale distribuir melhor água e refeições ao longo do dia.",
        "Combinar carboidratos simples do dia a dia com fontes de fibras, como frutas e aveia, pode ajudar a evitar oscilações bruscas de energia.",
        "Adicionar legumes, frutas e feijões à rotina alimentar apoia a microbiota e pode contribuir para uma sensação corporal mais estável."
    ],
    "trabalho": [
        "Deixar uma garrafa de água visível durante o trabalho ajuda a lembrar da hidratação mesmo em dias mais corridos.",
        "Ter um lanche simples com fruta, iogurte natural ou aveia pode evitar longos períodos em jejum em dias de agenda apertada.",
        "Quando a rotina fica puxada, refeições mais previsíveis e com menos ultraprocessados costumam ser mais gentis com o intestino."
    ],
    "autocobrança": [
        "Montar refeições simples e possíveis de manter no cotidiano costuma funcionar melhor do que tentar padrões alimentares difíceis de sustentar.",
        "Beber água ao longo do dia e incluir alimentos in natura já é um cuidado consistente com o eixo intestino-cérebro.",
        "Pequenos ajustes repetidos, como colocar fruta ou legumes em uma refeição por vez, já oferecem fibras úteis para a microbiota."
    ],
    "tristeza": [
        "Manter alguma regularidade nas refeições e na hidratação pode ajudar o corpo a não entrar em ciclos longos de jejum.",
        "Alimentos ricos em fibras, como frutas, legumes e aveia, ajudam a microbiota intestinal e sustentam hábitos mais estáveis.",
        "Uma rotina alimentar simples, com menos ultraprocessados e mais água ao longo do dia, pode ser um cuidado gentil com o corpo."
    ],
    "raiva": [
        "Em dias intensos, vale observar se café em excesso e longos períodos sem comer estão aumentando o desconforto físico e ajustar isso com mais água e pausas para se alimentar.",
        "Refeições previsíveis, com alimentos simples e fontes de fibras, ajudam o intestino a manter um ritmo mais estável.",
        "Levar água e um lanche simples para momentos corridos pode reduzir períodos longos de jejum e desconforto corporal."
    ],
    "relacionamento": [
        "Quando a rotina emocional fica bagunçada, manter horários mínimos para comer e beber água já ajuda o corpo a não ficar em segundo plano.",
        "Incluir frutas, legumes e aveia no cotidiano favorece a microbiota intestinal e sustenta hábitos alimentares mais consistentes.",
        "Organizar refeições simples em casa, com menos ultraprocessados, pode deixar a alimentação mais previsível ao longo da semana."
    ],
}

_ACTIVITY_CATALOG = {
    "ansiedade": [
        "Faça uma caminhada leve de 10 minutos em ritmo confortável, só para tirar o corpo da imobilidade.",
        "Levante-se por 5 minutos, alongue ombros e pescoço devagar e beba um copo de água.",
        "Saia um pouco da tela, caminhe dentro de casa ou do quarteirão e tome água antes de voltar à rotina."
    ],
    "sono": [
        "Tente um alongamento leve no fim do dia, com movimentos simples de pescoço, ombros e pernas, sem forçar.",
        "Faça uma caminhada curta no começo da noite ou no fim da tarde para ajudar o corpo a desacelerar com movimento leve.",
        "Pegue alguns minutos de luz natural pela manhã e caminhe um pouco, mesmo que seja dentro de um ritmo bem leve."
    ],
    "cansaço": [
        "Faça uma pausa curta para caminhar de 5 a 10 minutos e beber água antes de retomar o que estava fazendo.",
        "Alongue costas, pernas e ombros por alguns minutos, com movimentos lentos e confortáveis.",
        "Se o corpo estiver muito parado, levante, caminhe um pouco pela casa ou trabalho e depois tome água."
    ],
    "trabalho": [
        "Programe uma pausa de tela para levantar, andar um pouco e alongar pescoço e ombros por 5 minutos.",
        "Entre uma tarefa e outra, caminhe alguns minutos e beba água para quebrar o tempo sentado.",
        "Se puder, tome um pouco de sol leve e faça uma volta curta antes de retomar o ritmo de trabalho."
    ],
    "autocobrança": [
        "Escolha uma ação pequena e concreta, como caminhar 10 minutos em ritmo leve, sem transformar isso em meta rígida.",
        "Faça um alongamento curto e confortável, focando só em movimentar o corpo por alguns minutos.",
        "Levante-se, tome água e caminhe um pouco antes de voltar para as próximas demandas."
    ],
    "tristeza": [
        "Tente sair um pouco da cama ou do sofá para caminhar em ritmo leve por alguns minutos e abrir espaço para movimento no corpo.",
        "Tome um banho morno ou fresco e depois faça alguns alongamentos simples de ombros e pernas.",
        "Se for possível, pegue alguns minutos de luz natural e caminhe devagar, sem se cobrar desempenho."
    ],
    "raiva": [
        "Dê uma volta curta a pé, em ritmo constante, só para ajudar o corpo a descarregar um pouco da tensão física.",
        "Faça movimentos simples de ombros, braços e pernas por alguns minutos, sem pressa e sem forçar.",
        "Saia da tela, beba água e caminhe um pouco antes de continuar a conversa ou tarefa."
    ],
    "relacionamento": [
        "Faça uma caminhada leve de 10 minutos para sair do ambiente da conversa e movimentar o corpo.",
        "Tome um banho e depois alongue ombros, costas e pernas por alguns minutos, com calma.",
        "Se puder, pegue um pouco de sol leve e caminhe devagar para mudar o ritmo corporal."
    ],
}

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


def _normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _pick_unique_candidates(candidates: list[str], *, count: int = 3) -> list[str]:
    unique_candidates = list(dict.fromkeys(candidates))
    if not unique_candidates:
        return []
    if len(unique_candidates) <= count:
        return unique_candidates[:count]
    return random.sample(unique_candidates, count)


def detect_reflection_themes(text: str) -> list[str]:
    normalized_text = _normalize_for_match(text)
    detected: list[str] = []

    for theme, keywords in _THEME_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            detected.append(theme)

    return detected or DEFAULT_REFLECTION_THEMES.copy()


def get_neuro_tip_candidates(themes: list[str]) -> list[str]:
    pool: list[str] = []
    for theme in themes:
        pool.extend(_NEURO_TIP_CATALOG.get(theme, []))

    if len(pool) < 3:
        for theme in DEFAULT_REFLECTION_THEMES:
            pool.extend(_NEURO_TIP_CATALOG.get(theme, []))

    return _pick_unique_candidates(pool, count=3)


def get_activity_candidates(themes: list[str]) -> list[str]:
    pool: list[str] = []
    for theme in themes:
        pool.extend(_ACTIVITY_CATALOG.get(theme, []))

    if len(pool) < 3:
        for theme in DEFAULT_REFLECTION_THEMES:
            pool.extend(_ACTIVITY_CATALOG.get(theme, []))

    return _pick_unique_candidates(pool, count=3)


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
    t = _normalize_for_match(text.strip())
    if not t:
        return False

    if any(bad in t for bad in _FORBIDDEN_NEURO_HINTS):
        return False

    return any(k in t for k in _NEURO_KEYWORDS)


def _is_valid_activity(text: Optional[str]) -> bool:
    """Valida se a activity é prática e não escapa para journaling/meditação/respiração."""
    if not text:
        return False
    t = _normalize_for_match(text.strip())
    if not t:
        return False

    if any(bad in t for bad in _FORBIDDEN_ACTIVITY_HINTS):
        return False

    return any(k in t for k in _ACTIVITY_KEYWORDS)


def _fallback_neuro_tip() -> str:
    candidates = get_neuro_tip_candidates(DEFAULT_REFLECTION_THEMES)
    return random.choice(candidates)


def _fallback_activity() -> str:
    candidates = get_activity_candidates(DEFAULT_REFLECTION_THEMES)
    return random.choice(candidates)


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
    themes = detect_reflection_themes(reflection_text)
    neuro_tip_candidates = get_neuro_tip_candidates(themes)
    activity_candidates = get_activity_candidates(themes)
    logger.info(f"[{request_id}] STYLE={style}")
    logger.info(
        f"[{request_id}] CONTEXT themes={themes} "
        f"neuro_candidates={len(neuro_tip_candidates)} activity_candidates={len(activity_candidates)}"
    )

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

TEMAS DETECTADOS DA REFLEXÃO:
{", ".join(themes)}

OPÇÕES INTERNAS PARA BASEAR O CAMPO "neuro_tip" (adapte sem copiar de forma mecânica):
- {neuro_tip_candidates[0]}
- {neuro_tip_candidates[1]}
- {neuro_tip_candidates[2]}

OPÇÕES INTERNAS PARA BASEAR O CAMPO "activity" (adapte sem copiar de forma mecânica):
- {activity_candidates[0]}
- {activity_candidates[1]}
- {activity_candidates[2]}

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

    data = _safe_json_loads(content)
    if not isinstance(data, dict):
        logger.info(
            f"[{request_id}] JSON_PARSE_FAILED response_chars={len(content)} -> fallback_structured"
        )
        return {
            "feedback": _normalize_one_line(content, max_chars=1200)
            or "Não foi possível gerar a devolutiva no formato esperado.",
            "neuro_tip": random.choice(neuro_tip_candidates),
            "activity": random.choice(activity_candidates),
        }

    logger.info(
        f"[{request_id}] RESPONSE_METADATA response_chars={len(content)} "
        f"json_keys={list(data.keys())}"
    )

    feedback = _normalize_one_line(data.get("feedback"), max_chars=1200)
    neuro_tip = _normalize_one_line(data.get("neuro_tip"), max_chars=240)
    activity = _normalize_one_line(data.get("activity"), max_chars=240)

    if not feedback:
        logger.info(f"[{request_id}] feedback missing -> fallback_text")
        feedback = _normalize_one_line(content, max_chars=1200) or "Não foi possível gerar a devolutiva automaticamente."

    if not _is_valid_neuro_tip(neuro_tip):
        logger.info(f"[{request_id}] neuro_tip invalid -> fallback")
        neuro_tip = random.choice(neuro_tip_candidates)

    if not _is_valid_activity(activity):
        logger.info(f"[{request_id}] activity invalid -> fallback")
        activity = random.choice(activity_candidates)

    logger.info(f"[{request_id}] DONE ok")
    return {
        "feedback": feedback,
        "neuro_tip": neuro_tip,
        "activity": activity,
    }
