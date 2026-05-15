import json
import random
import re
import unicodedata
import uuid
from typing import Any, Optional

from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.core.logger import get_logger

logger = get_logger("ia_service")
client = OpenAI(api_key=OPENAI_API_KEY)

DEFAULT_REFLECTION_THEMES = ["cansaco", "autocobranca", "sono"]

_THEME_KEYWORDS = {
    "ansiedade": [
        "ansiedade",
        "ansioso",
        "ansiosa",
        "preocup",
        "apreens",
        "nervos",
        "taquic",
        "angust",
    ],
    "sono": [
        "sono",
        "dormi",
        "dormir",
        "insonia",
        "acordei",
        "acordar",
        "cama",
        "descanso",
        "descansar",
    ],
    "cansaco": [
        "cansaco",
        "exaust",
        "esgot",
        "fadig",
        "sem energia",
        "sem disposicao",
        "sobrecarreg",
    ],
    "trabalho": [
        "trabalho",
        "empresa",
        "chefe",
        "reuniao",
        "prazo",
        "meta",
        "colega",
        "escritorio",
        "profissional",
    ],
    "autocobranca": [
        "autocobr",
        "me cobro",
        "me cobrar",
        "perfeccion",
        "culpa",
        "fracasso",
        "falhei",
        "falhar",
        "erro",
        "errar",
        "insuficient",
    ],
    "tristeza": [
        "triste",
        "tristeza",
        "desanim",
        "vazio",
        "abat",
        "chor",
        "desmotivad",
        "para baixo",
    ],
    "raiva": [
        "raiva",
        "irrit",
        "odio",
        "bravo",
        "brava",
        "furios",
        "furiosa",
        "explodi",
        "explodir",
    ],
    "relacionamento": [
        "relacionamento",
        "parceir",
        "namor",
        "casamento",
        "famil",
        "amigo",
        "amizade",
        "mae",
        "pai",
        "irma",
        "irmao",
    ],
}

_NEURO_TIP_CATALOG = {
    "ansiedade": [
        "Manter agua por perto e evitar longos periodos em jejum pode reduzir desconfortos corporais ao longo do dia.",
        "Incluir aveia, frutas e legumes com regularidade favorece fibras para a microbiota e apoia o eixo intestino-cerebro.",
        "Observar o excesso de cafeina e reforcar a hidratacao pode deixar a rotina alimentar mais estavel.",
        "Refeicoes em horarios previsiveis ajudam o intestino a funcionar com mais constancia em dias tensos.",
    ],
    "sono": [
        "Uma refeicao noturna mais leve e em horario regular costuma ser mais gentil para o intestino antes de deitar.",
        "Evitar refeicoes muito pesadas perto de dormir e manter boa hidratacao ao longo do dia pode favorecer mais conforto corporal.",
        "Incluir fibras de frutas, legumes e aveia no dia a dia ajuda a manter o intestino mais previsivel.",
        "Diminuir cafeina no fim do dia e jantar com simplicidade pode ajudar a rotina do corpo a ficar menos sobrecarregada.",
    ],
    "cansaco": [
        "Distribuir agua e refeicoes ao longo do dia pode ajudar a evitar oscilacoes grandes de energia.",
        "Combinar alimentos do cotidiano com frutas, aveia ou feijoes pode trazer mais fibras e ritmo para o intestino.",
        "Adicionar legumes e frutas na rotina apoia a microbiota e ajuda a manter o corpo mais estavel.",
        "Evitar passar muitas horas sem comer pode ser um cuidado simples para dias de desgaste.",
    ],
    "trabalho": [
        "Deixar uma garrafa de agua visivel durante o trabalho ajuda a lembrar da hidratacao em dias corridos.",
        "Ter um lanche simples com fruta, iogurte natural ou aveia pode evitar longos periodos em jejum na agenda apertada.",
        "Refeicoes mais previsiveis e com menos ultraprocessados costumam ser mais gentis com o intestino em rotinas exigentes.",
        "Separar pausas curtas para agua e comida simples ajuda a nao jogar a alimentacao para depois.",
    ],
    "autocobranca": [
        "Montar refeicoes simples e possiveis de manter costuma funcionar melhor do que tentar regras alimentares muito rigidas.",
        "Beber agua ao longo do dia e incluir alimentos in natura ja e um cuidado consistente com o eixo intestino-cerebro.",
        "Pequenos ajustes repetidos, como colocar fruta ou legumes em uma refeicao por vez, ja oferecem fibras uteis para a microbiota.",
        "Uma rotina alimentar sustentavel costuma ser mais util do que buscar perfeicao nas escolhas.",
    ],
    "tristeza": [
        "Manter alguma regularidade nas refeicoes e na hidratacao pode ajudar o corpo a nao entrar em ciclos longos de jejum.",
        "Frutas, legumes e aveia ajudam a microbiota intestinal e sustentam habitos alimentares mais estaveis.",
        "Uma rotina alimentar simples, com menos ultraprocessados e mais agua ao longo do dia, pode ser um cuidado pratico com o corpo.",
        "Mesmo em dias arrastados, um lanche simples e agua por perto ajudam a manter o corpo assistido.",
    ],
    "raiva": [
        "Observar excesso de cafe, longos periodos sem comer e pouca agua pode ajudar a reduzir desconforto fisico em dias intensos.",
        "Refeicoes previsiveis, com alimentos simples e fontes de fibras, ajudam o intestino a manter um ritmo mais estavel.",
        "Levar agua e um lanche simples para momentos corridos pode reduzir jejum prolongado e mal-estar corporal.",
        "Frutas, legumes e aveia sao opcoes simples para dar mais constancia a rotina alimentar.",
    ],
    "relacionamento": [
        "Manter horarios minimos para comer e beber agua ajuda o corpo a nao ficar em segundo plano quando a rotina emocional aperta.",
        "Incluir frutas, legumes e aveia no cotidiano favorece a microbiota intestinal e sustenta habitos mais consistentes.",
        "Organizar refeicoes simples em casa, com menos ultraprocessados, pode deixar a alimentacao mais previsivel ao longo da semana.",
        "Uma garrafa de agua por perto e um lanche simples pronto podem facilitar o cuidado com o corpo em dias confusos.",
    ],
}

_ACTIVITY_CATALOG = {
    "ansiedade": [
        "Faca uma caminhada leve de 10 minutos em ritmo confortavel para tirar o corpo da imobilidade.",
        "Levante por 5 minutos, alongue ombros e pescoco devagar e tome um copo de agua.",
        "Saia um pouco da tela, caminhe pela casa ou pelo quarteirao e beba agua antes de voltar a rotina.",
        "Escolha um trajeto curto para andar devagar e dar ao corpo uma pausa fisica simples.",
    ],
    "sono": [
        "Tente um alongamento leve no fim do dia, com movimentos simples de pescoco, ombros e pernas, sem forcar.",
        "Faca uma caminhada curta no fim da tarde ou no comeco da noite para movimentar o corpo de forma leve.",
        "Pegue alguns minutos de luz natural pela manha e caminhe um pouco em ritmo tranquilo.",
        "Um banho morno seguido de alongamento leve pode ajudar a criar uma transicao corporal para a noite.",
    ],
    "cansaco": [
        "Faca uma pausa curta para caminhar de 5 a 10 minutos e beber agua antes de retomar o que estava fazendo.",
        "Alongue costas, pernas e ombros por alguns minutos, com movimentos lentos e confortaveis.",
        "Se o corpo estiver muito parado, levante, caminhe um pouco pelo ambiente e depois tome agua.",
        "Escolha um movimento leve e simples, como andar alguns minutos ou se espreguicar com calma.",
    ],
    "trabalho": [
        "Programe uma pausa de tela para levantar, andar um pouco e alongar pescoco e ombros por 5 minutos.",
        "Entre uma tarefa e outra, caminhe alguns minutos e beba agua para quebrar o tempo sentado.",
        "Se puder, tome um pouco de sol leve e faca uma volta curta antes de retomar o ritmo de trabalho.",
        "Levantar da cadeira, mudar de ambiente por alguns minutos e tomar agua ja pode ser uma pausa corporal util.",
    ],
    "autocobranca": [
        "Escolha uma acao pequena e concreta, como caminhar 10 minutos em ritmo leve, sem transformar isso em meta rigida.",
        "Faca um alongamento curto e confortavel, focando apenas em movimentar o corpo por alguns minutos.",
        "Levante, tome agua e caminhe um pouco antes de voltar para as proximas demandas.",
        "Experimente um movimento leve e viavel agora, como andar ate a janela, tomar agua e alongar os ombros.",
    ],
    "tristeza": [
        "Tente sair um pouco da cama ou do sofa para caminhar em ritmo leve por alguns minutos.",
        "Tome um banho e depois faca alguns alongamentos simples de ombros e pernas.",
        "Se for possivel, pegue alguns minutos de luz natural e caminhe devagar, sem se cobrar desempenho.",
        "Levantar, abrir a janela e dar alguns passos pela casa ja pode criar um pouco de movimento corporal.",
    ],
    "raiva": [
        "De uma volta curta a pe, em ritmo constante, para ajudar o corpo a descarregar um pouco da tensao fisica.",
        "Faca movimentos simples de ombros, bracos e pernas por alguns minutos, sem pressa e sem forcar.",
        "Saia da tela, beba agua e caminhe um pouco antes de continuar a tarefa ou conversa.",
        "Escolha um deslocamento curto, mesmo dentro de casa, para tirar o corpo do ponto de tensao.",
    ],
    "relacionamento": [
        "Faca uma caminhada leve de 10 minutos para sair do ambiente da conversa e movimentar o corpo.",
        "Tome um banho e depois alongue ombros, costas e pernas por alguns minutos, com calma.",
        "Se puder, pegue um pouco de sol leve e caminhe devagar para mudar o ritmo corporal.",
        "Levante do lugar, mude de ambiente por alguns minutos e tome agua antes de retomar a conversa.",
    ],
}

_NEURO_KEYWORDS = [
    "agua",
    "hidrat",
    "fibr",
    "fruta",
    "veget",
    "legume",
    "salada",
    "omega",
    "probiot",
    "prebiot",
    "ferment",
    "iogurte",
    "kefir",
    "intestin",
    "microbi",
    "cerebro",
    "nutri",
    "acucar",
    "cafe",
    "cafeina",
    "refei",
    "aliment",
    "comida",
    "ultraprocess",
    "processad",
    "sement",
    "castanh",
    "aveia",
    "lanche",
    "jejum",
]

_FORBIDDEN_NEURO_HINTS = [
    "autocompaix",
    "respir",
    "medit",
    "mindful",
    "terapia",
    "emoc",
    "sentiment",
    "ansiedad",
    "depress",
    "relax",
    "psicol",
    "journaling",
    "diario",
    "autoestima",
    "suplement",
    "medic",
    "remedio",
    "capsula",
]

_ACTIVITY_KEYWORDS = [
    "caminh",
    "along",
    "moviment",
    "pausa",
    "paus",
    "postur",
    "sol",
    "hidrata",
    "agua",
    "banho",
    "andar",
    "levante",
    "levantar",
]

_FORBIDDEN_ACTIVITY_HINTS = [
    "journaling",
    "diario",
    "escrev",
    "anot",
    "medit",
    "mindful",
    "respir",
    "terapia",
    "autocompaix",
    "relax",
]

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CEP_RE = re.compile(r"\b\d{5}-?\d{3}\b")
_PHONE_RE = re.compile(
    r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?(?:9?\d{4})[-\s]\d{4}\b"
)
_LONG_IDENTIFIER_RE = re.compile(r"\b\d[\d.\-/ ]{7,}\d\b")
_ADDRESS_RE = re.compile(
    r"\b(?:rua|avenida|av\.?|travessa|alameda|rodovia|estrada|praca|praça|bairro|"
    r"condominio|condomínio|residencial)\s+[A-Za-z0-9À-ÿ][^,\n;.]{2,}",
    re.IGNORECASE,
)
_FAMILY_NAME_RE = re.compile(
    r"\b(mae|mãe|pai|irma|irmã|irmao|irmão|filho|filha|esposa|marido)\s+"
    r"(?:do|da|de|meu|minha)?\s*[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][a-záàâãéèêíìîóòôõúùûç]+",
)
_DIRECT_NAME_PATTERNS = [
    re.compile(
        r"\b(meu nome e|meu nome é|sou eu|eu sou|me chamo|chamo-me)\s+"
        r"([A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][a-záàâãéèêíìîóòôõúùûç]+){0,2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(paciente|cliente)\s+([A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][a-záàâãéèêíìîóòôõúùûç]+(?:\s+[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ][a-záàâãéèêíìîóòôõúùûç]+){0,2})",
        re.IGNORECASE,
    ),
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


def sanitize_for_ai(text: str) -> str:
    sanitized = (text or "").strip()
    if not sanitized:
        return ""

    sanitized = _URL_RE.sub("[URL_REMOVIDA]", sanitized)
    sanitized = _EMAIL_RE.sub("[EMAIL_REMOVIDO]", sanitized)
    sanitized = _CPF_RE.sub("[CPF_REMOVIDO]", sanitized)
    sanitized = _CEP_RE.sub("[ENDERECO_REMOVIDO]", sanitized)
    sanitized = _PHONE_RE.sub("[TELEFONE_REMOVIDO]", sanitized)
    sanitized = _ADDRESS_RE.sub("[ENDERECO_REMOVIDO]", sanitized)
    sanitized = _FAMILY_NAME_RE.sub(
        lambda m: f"{m.group(1)} [FAMILIAR_REMOVIDO]",
        sanitized,
    )

    for pattern in _DIRECT_NAME_PATTERNS:
        sanitized = pattern.sub(lambda m: f"{m.group(1)} [NOME_REMOVIDO]", sanitized)

    sanitized = _LONG_IDENTIFIER_RE.sub("[IDENTIFICADOR_REMOVIDO]", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized


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
    if not text:
        return text
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _safe_json_loads(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None

    cleaned = _strip_code_fences(text)

    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_one_line(text: Optional[str], *, max_chars: int) -> Optional[str]:
    if not text:
        return None
    normalized = " ".join(str(text).split())
    if len(normalized) > max_chars:
        normalized = normalized[: max_chars - 3].rstrip() + "..."
    return normalized


def _is_valid_neuro_tip(text: Optional[str]) -> bool:
    if not text:
        return False

    normalized = _normalize_for_match(text.strip())
    if not normalized:
        return False

    if any(bad in normalized for bad in _FORBIDDEN_NEURO_HINTS):
        return False

    return any(keyword in normalized for keyword in _NEURO_KEYWORDS)


def _is_valid_activity(text: Optional[str]) -> bool:
    if not text:
        return False

    normalized = _normalize_for_match(text.strip())
    if not normalized:
        return False

    if any(bad in normalized for bad in _FORBIDDEN_ACTIVITY_HINTS):
        return False

    return any(keyword in normalized for keyword in _ACTIVITY_KEYWORDS)


def _fallback_neuro_tip() -> str:
    candidates = get_neuro_tip_candidates(DEFAULT_REFLECTION_THEMES)
    return random.choice(candidates)


def _fallback_activity() -> str:
    candidates = get_activity_candidates(DEFAULT_REFLECTION_THEMES)
    return random.choice(candidates)


def _pick_style() -> str:
    return random.choice(
        [
            "estilo direto e objetivo, sem floreios",
            "estilo acolhedor e conciso, sem clichEs",
            "estilo educativo com um exemplo pratico simples",
        ]
    )


def generate_feedback_structured(
    *,
    reflection_text: str,
    anamnesis_summary: Optional[str] = None,
) -> dict:
    request_id = uuid.uuid4().hex[:8]

    original_reflection = (reflection_text or "").strip()
    original_anamnesis = (anamnesis_summary or "").strip()

    reflection_text = sanitize_for_ai(original_reflection)
    anamnesis_summary = sanitize_for_ai(original_anamnesis)

    if len(anamnesis_summary) > 4000:
        anamnesis_summary = anamnesis_summary[:4000].rstrip() + "..."

    if not reflection_text:
        logger.info(f"[{request_id}] EMPTY_INPUT")
        return {
            "feedback": "Nao recebi o texto da reflexao. Voce pode enviar novamente para que eu possa responder com cuidado?",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    style = _pick_style()
    themes = detect_reflection_themes(reflection_text)
    neuro_tip_candidates = get_neuro_tip_candidates(themes)
    activity_candidates = get_activity_candidates(themes)

    system_prompt = (
        "Voce e um assistente de apoio terapeutico.\n"
        "Sua funcao e gerar devolutivas acolhedoras e educativas baseadas no texto do cliente.\n"
        "Regras:\n"
        "- Nao faca diagnostico.\n"
        "- Nao prescreva medicamentos, suplementos ou dietas.\n"
        "- Nao de instrucoes de urgencia.\n"
        "- Nao substitua acompanhamento profissional.\n"
        "- Responda sempre em JSON puro, sem markdown e sem texto fora do JSON.\n"
        "- Se houver anamnese, use apenas como contexto, sem repetir literalmente.\n"
        "- Nunca invente nem tente reconstruir dados pessoais removidos.\n"
    )

    user_prompt = f"""
Gere uma devolutiva baseada na reflexao sanitizada abaixo.
Use {style}.

Retorne exatamente este JSON:
{{
  "feedback": "texto acolhedor e educativo, com ate 1200 caracteres",
  "neuro_tip": "1 frase curta apenas sobre alimentacao, hidratacao, microbiota, intestino-cerebro ou habitos alimentares. Nao falar de meditacao, respiracao, terapia, autocompaixao, emocoes, suplementos ou medicamentos.",
  "activity": "1 frase curta com pratica corporal leve e segura. Pode sugerir caminhada, alongamento, pausa de tela, banho, exposicao leve ao sol, movimento leve ou hidratacao. Nao sugerir diario, journaling, meditacao, mindfulness, respiracao guiada ou terapia."
}}

Regras do campo feedback:
- Cite explicitamente 2 detalhes presentes no texto sanitizado.
- Evite cliches e aberturas genericas.
- Termine com 1 pergunta reflexiva curta.
- Nao faca diagnostico, nao prometa cura e nao de instrucoes de urgencia.

Temas detectados:
{", ".join(themes)}

Opcoes internas para orientar neuro_tip:
- {neuro_tip_candidates[0]}
- {neuro_tip_candidates[1]}
- {neuro_tip_candidates[2]}

Opcoes internas para orientar activity:
- {activity_candidates[0]}
- {activity_candidates[1]}
- {activity_candidates[2]}

Anamnese sanitizada:
{anamnesis_summary if anamnesis_summary else "(sem anamnese cadastrada)"}

Reflexao sanitizada:
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
    except Exception as exc:
        logger.exception(f"[{request_id}] OPENAI_CALL_FAILED error_type={type(exc).__name__}")
        return {
            "feedback": "Nao consegui gerar a devolutiva agora. Tente novamente em alguns instantes.",
            "neuro_tip": _fallback_neuro_tip(),
            "activity": _fallback_activity(),
        }

    content = (response.choices[0].message.content or "").strip()
    payload = _safe_json_loads(content)

    if not isinstance(payload, dict):
        logger.info(f"[{request_id}] RESPONSE_METADATA response_chars={len(content)} json_keys=[]")
        return {
            "feedback": _normalize_one_line(content, max_chars=1200)
            or "Nao foi possivel gerar a devolutiva no formato esperado.",
            "neuro_tip": random.choice(neuro_tip_candidates),
            "activity": random.choice(activity_candidates),
        }

    logger.info(
        f"[{request_id}] RESPONSE_METADATA response_chars={len(content)} "
        f"json_keys={sorted(payload.keys())}"
    )

    feedback = _normalize_one_line(payload.get("feedback"), max_chars=1200)
    neuro_tip = _normalize_one_line(payload.get("neuro_tip"), max_chars=240)
    activity = _normalize_one_line(payload.get("activity"), max_chars=240)

    if not feedback:
        feedback = (
            _normalize_one_line(content, max_chars=1200)
            or "Nao foi possivel gerar a devolutiva automaticamente."
        )

    if not _is_valid_neuro_tip(neuro_tip):
        neuro_tip = random.choice(neuro_tip_candidates)

    if not _is_valid_activity(activity):
        activity = random.choice(activity_candidates)

    return {
        "feedback": feedback,
        "neuro_tip": neuro_tip,
        "activity": activity,
    }
