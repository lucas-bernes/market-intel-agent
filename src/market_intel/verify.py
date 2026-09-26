"""Verificação determinística do que o LLM extraiu.

O LLM lê a página e devolve campos + uma citação por campo. Aqui o CÓDIGO
confere, sem confiar no LLM:
  1. o alvo é o certo (a página/extração é do modelo/provedor que pedimos);
  2. a citação existe mesmo no texto coletado;
  3. o número (ou o tipo de dado) está dentro da citação;
  4. o valor está numa faixa plausível.
Campo que falha vira None (com o motivo registrado) — melhor vazio que errado.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from .promo import find_promo
from .schema import ModelComparison, ModelExtraction, ProviderComparison, ProviderExtraction


class ExtractionRejected(Exception):
    """A coleta inteira é descartada (alvo errado) — nada deve ser salvo."""


@dataclass
class Verified:
    comparison: object  # ModelComparison ou ProviderComparison, só com campos aprovados
    evidence: dict[str, str] = field(default_factory=dict)  # campo -> citação aprovada
    rejected: dict[str, str] = field(default_factory=dict)  # campo -> motivo
    # (preço, citação) quando o preço extraído é PROMOCIONAL: ele não vira o preço
    # de tabela (que o ranking usa), só o selo "PROMO" — ver verify_model_extraction.
    promo: Optional[tuple] = None
    # Mudanças em campos protegidos que o store aplicou (campo, antigo, novo);
    # preenchido pelo pipeline depois de salvar, usado pelos alertas de variação.
    changes: list = field(default_factory=list)


# Faixas plausíveis: valor fora disso quase certamente é erro de leitura
# (ex: preço por 1000 tokens lido como preço por segundo).
RANGES = {
    "price_per_second_usd": (0.001, 5.0),
    "max_reference_images": (0, 100),
    "prompt_max_chars": (50, 100_000),
    "quality_score": (0, 10),
    "uptime_pct": (90, 100),
}

# A citação precisa conter uma dessas pistas — evita aceitar, por exemplo, um
# "$0.014 por 1000 tokens" como se fosse preço por segundo.
KEYWORDS = {
    "price_per_second_usd": r"second|/\s*s\b|/\s*sec|\bsec\b",
    "max_reference_images": r"image|reference|frame|photo",
    "prompt_max_chars": r"char",
    # Precisa nomear o recurso; só "scene"/"shot" soltos casam com exemplos de
    # prompt na documentação ("Cut scene to an octopus...") e dariam um selo
    # de verificado sem sustentação.
    "multi_shot_support": r"multi[-_ ]?(shot|scene|prompt)|multiple (shots|scenes)|storyboard",
    "quality_score": r"score|rating|/\s*10|out of",
    "uptime_pct": r"uptime|%",
}

BOOLEAN_FIELDS = {"multi_shot_support"}

MODEL_FIELDS = (
    "price_per_second_usd",
    "max_reference_images",
    "prompt_max_chars",
    "multi_shot_support",
    "quality_score",
)
PROVIDER_FIELDS = ("uptime_pct",)

_NUMBER_WORDS = {
    w: i
    for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}
_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def normalize(text: str) -> str:
    # Mesma limpeza nos dois lados (citação e texto bruto): tira ruído de
    # markdown, unifica aspas/espaços e ignora maiúsculas.
    text = text.replace(" ", " ").replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[*_`\\|]", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def collapse(text: str) -> str:
    # Só letras e números: "Seedance 2.0", "seedance-2.0" e "seedance_2_0" viram iguais.
    return re.sub(r"[^a-z0-9]", "", text.lower())


def numbers_in(text: str, with_words: bool = False) -> list[float]:
    found = [float(m.group(0).replace(",", "")) for m in _NUMBER_RE.finditer(text)]
    if with_words:
        found += [float(n) for w, n in _NUMBER_WORDS.items() if re.search(rf"\b{w}\b", text)]
    return found


def _has(value: float, candidates: list[float]) -> bool:
    return any(math.isclose(value, c, rel_tol=1e-9, abs_tol=1e-9) for c in candidates)


def _number_supported(field_name: str, value: float, quote: str) -> bool:
    nums = numbers_in(quote, with_words=field_name == "max_reference_images")
    if _has(value, nums):
        return True
    if field_name == "quality_score":
        # Nota normalizada pra 0-10: aceita "83/100" -> 8.3 e "4.5/5" -> 9.0,
        # mas só se a escala de origem aparece na citação.
        if re.search(r"100", quote) and _has(value, [n / 10 for n in nums]):
            return True
        if re.search(r"/\s*5\b|out of 5", quote) and _has(value, [n * 2 for n in nums]):
            return True
    return False


def check_field(field_name: str, value, quote: Optional[str], raw_norm: str) -> Optional[str]:
    """Devolve None se o campo passou, ou o motivo da reprovação."""
    if not quote or not quote.strip():
        return "sem citação"

    if field_name in RANGES:
        low, high = RANGES[field_name]
        if not (low <= value <= high):
            return f"fora da faixa plausível ({low}-{high})"

    quote_norm = normalize(quote)
    if len(quote_norm) < 6 or quote_norm not in raw_norm:
        return "citação não encontrada no texto"

    if not re.search(KEYWORDS[field_name], quote_norm):
        return "citação não fala do assunto do campo"

    if field_name == "price_per_second_usd":
        # Páginas listam um preço por resolução e o LLM alterna entre elas de
        # uma chamada pra outra (Seedance 2.5: 480p em 4 de 5 chamadas, 720p
        # na outra), o que geraria "mudanças de preço" falsas todo dia. A
        # referência é 720p: citação que só fala de outra resolução é rejeitada.
        # Limite conhecido: se a citação lista 720p junto de outras, não dá pra
        # saber qual número é de qual — isso passa.
        resolutions = set(re.findall(r"\b(\d{3,4})p\b", quote_norm))
        if resolutions and "720" not in resolutions:
            return f"preço de outra resolução ({', '.join(sorted(resolutions))}p); referência é 720p"

    if field_name not in BOOLEAN_FIELDS and not _number_supported(field_name, float(value), quote):
        return "número não aparece na citação"

    return None


# ---- identidade do alvo ----------------------------------------------------

# Variantes que são produtos DIFERENTES do modelo base (Sora 2 != Sora 2 Pro).
_VARIANT_WORDS = {"pro", "fast", "turbo", "lite", "max", "omni", "ultra", "mini", "standard", "master", "flash", "plus", "preview"}
# Sufixos de endpoint que aparecem em chaves mas não fazem parte do nome.
_IGNORED_WORDS = {"image", "to", "video", "i2v", "t2v"}


def _words(name: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", name.lower()) if w not in _IGNORED_WORDS]


def _versions(name: str) -> list[str]:
    # Exclui contagens de parâmetros coladas em letras, tipo "A14B" em "Wan
    # 2.2 A14B" — "14" ali não é versão, é tamanho do modelo. Uma exceção:
    # um "v"/"V" logo antes (fal usa "v2.2" no id do endpoint) ainda conta.
    # "2.2", cercado de espaço/hífen, continua capturado normalmente.
    return re.findall(r"(?:(?<![a-zA-Z])|(?<=[vV]))\d+(?:\.\d+)*(?![a-zA-Z])", name)


def _norm_version(v: str) -> str:
    # O LLM às vezes simplifica "2.0" pra "2" (e vice-versa) entre uma
    # chamada e outra — o número é o mesmo, então a comparação não deve
    # tratar isso como produto diferente. Só normaliza quando o token é um
    # número puro (evita quebrar algo como "2.2.1", que não ocorre hoje mas
    # não deve travar caso apareça).
    try:
        text = f"{float(v):.6f}".rstrip("0").rstrip(".")
        return text or "0"
    except ValueError:
        return v


def same_model(expected: str, actual: str) -> bool:
    ordered = _words(expected)
    ew, aw = set(ordered), set(_words(actual))
    ev = [_norm_version(v) for v in _versions(expected)]
    av = [_norm_version(v) for v in _versions(actual)]
    # O LLM às vezes omite a marca ("Hailuo 2.3" em vez de "MiniMax Hailuo
    # 2.3"). Com 2+ palavras, a primeira (a marca) pode faltar; o resto do nome
    # e a versão continuam obrigatórios, então "Luma 3.2" != "Luma Ray 3.2".
    words_ok = ew <= aw or (len(ordered) >= 2 and set(ordered[1:]) <= aw)
    return ev == av and words_ok and not ((aw - ew) & _VARIANT_WORDS)


def _model_in_text(expected: str, raw_collapsed: str) -> bool:
    words, versions = _words(expected), "".join(_versions(expected))
    joined = "".join(words)
    # Nome+versão, nome+versão com "v" no meio (fal escreve "Wan v2.2"), e só
    # "última palavra + versão" (ex: só "Hailuo 2.3" na página) — qualquer
    # uma dessas formas contando como a menção estar presente.
    candidates = {collapse(joined + versions), collapse(joined + "v" + versions)}
    if words:
        candidates.add(collapse(words[-1] + versions))
        candidates.add(collapse(words[-1] + "v" + versions))
    return any(candidate in raw_collapsed for candidate in candidates)


def same_provider(expected: str, actual: str) -> bool:
    e, a = collapse(expected), collapse(actual)
    return bool(e) and (e in a or a in e)


# ---- API pública -----------------------------------------------------------


def _verify_fields(extraction, raw_text: str, fields: tuple[str, ...]) -> tuple[dict, dict[str, str], dict[str, str]]:
    raw_norm = normalize(raw_text)
    quotes: dict[str, list[str]] = {}
    for item in extraction.evidence:
        quotes.setdefault(item.field, []).append(item.quote)

    data = extraction.model_dump(exclude={"evidence"})
    evidence: dict[str, str] = {}
    rejected: dict[str, str] = {}
    for f in fields:
        value = data.get(f)
        if value is None:
            continue
        reasons = [check_field(f, value, q, raw_norm) for q in quotes.get(f, [])] or ["sem citação"]
        if None in reasons:
            evidence[f] = quotes[f][reasons.index(None)]
        else:
            rejected[f] = reasons[0]
            data[f] = None
    return data, evidence, rejected


def verify_model_extraction(extraction: ModelExtraction, raw_text: str, expected_name: str) -> Verified:
    if not same_model(expected_name, extraction.model_name):
        raise ExtractionRejected(
            f"alvo errado: pedimos '{expected_name}' mas a página trouxe '{extraction.model_name}'"
        )
    if not _model_in_text(expected_name, collapse(raw_text)):
        raise ExtractionRejected(f"'{expected_name}' não aparece no texto coletado")

    data, evidence, rejected = _verify_fields(extraction, raw_text, MODEL_FIELDS)

    # Preço promocional não é preço de tabela: se a citação (ou o texto logo em
    # volta) fala de promoção, o valor sai de price_per_second_usd — que o ranking
    # usa — e vai só para o selo. O preço de tabela guardado antes fica intacto.
    promo = None
    price_quote = evidence.get("price_per_second_usd")
    if price_quote:
        phrase = promo_near(raw_text, price_quote)
        if phrase:
            promo = (data["price_per_second_usd"], f'{price_quote} [promo cue: "{phrase}"]')
            evidence.pop("price_per_second_usd")
            data["price_per_second_usd"] = None
    return Verified(ModelComparison(**data), evidence, rejected, promo=promo)


def promo_near(raw_text: str, quote: str, window: int = 350) -> Optional[str]:
    """The promotional phrase within `window` characters around the quote in the page, if any."""
    raw_norm, quote_norm = normalize(raw_text), normalize(quote)
    start = raw_norm.find(quote_norm)
    if start < 0:
        return None
    return find_promo(raw_norm[max(0, start - window): start + len(quote_norm) + window])


def verify_provider_extraction(extraction: ProviderExtraction, raw_text: str, expected_name: str) -> Verified:
    if not same_provider(expected_name, extraction.provider_name):
        raise ExtractionRejected(
            f"alvo errado: pedimos '{expected_name}' mas a página trouxe '{extraction.provider_name}'"
        )
    if collapse(expected_name) not in collapse(raw_text):
        raise ExtractionRejected(f"'{expected_name}' não aparece no texto coletado")

    data, evidence, rejected = _verify_fields(extraction, raw_text, PROVIDER_FIELDS)
    return Verified(ProviderComparison(**data), evidence, rejected)


def verify_uptime(value: Optional[float], quote: Optional[str], raw_text: str, expected_name: str) -> Verified:
    # Usado com páginas de status: o único dado é o uptime, então monta um
    # ProviderComparison mínimo só com ele.
    #
    # Sem checagem de "nome aparece no texto" aqui, ao contrário das outras
    # funções de verify: nesse modo a URL da página de status é escolhida à
    # mão por quem chama (nunca vem de busca), então a identidade do alvo já
    # está garantida por fora. Manter a checagem geraria falso negativo real:
    # a página de status do Together AI (Better Stack) não escreve "Together
    # AI" em lugar nenhum do texto renderizado, só nomes de componente.
    result = Verified(ProviderComparison(provider_name=expected_name))
    if value is None:
        return result
    reason = check_field("uptime_pct", value, quote, normalize(raw_text))
    if reason:
        result.rejected["uptime_pct"] = reason
    else:
        result.comparison.uptime_pct = value
        result.evidence["uptime_pct"] = quote
    return result


# ---- discontinuation --------------------------------------------------------

# The subject must be the endpoint/model/product itself. Without this, a page
# about an ACTIVE model matched a sentence about its client library ("Note:
# @fal-ai/serverless-client is deprecated") and would have been flagged.
_SUBJECT = r"\bthis (?:endpoint|model|product)"

# Current-state statements only. "will be deprecated on <future date>" means the
# model is still available, so it must not flag anything.
_DISCONTINUED_STATE = re.compile(
    _SUBJECT + r" (?:is|has been) (?:deprecated|discontinued|shut down|retired)|"
    + _SUBJECT + r" is no longer (?:supported|available)",
    re.IGNORECASE,
)
_SHUTDOWN_ON = re.compile(
    _SUBJECT + r" will be (?:shut down|shutdown|retired|sunset)[^.]{0,20}?\bon\s+([A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th)?, \d{4})",
    re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    return [" ".join(part.split()) for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def find_discontinuation(text: str, today=None) -> Optional[str]:
    """Returns the sentence that proves the product is discontinued, or None.

    Deterministic on purpose (no LLM): a wrong "discontinued" removes a model
    from the ranking. Accepts a current-state statement whose subject is the
    endpoint/model/product itself ("This model is no longer supported", "This
    endpoint is deprecated") or "This endpoint will be shut down on <date>" when
    that date has already passed; a future date is only an announcement.
    """
    from datetime import datetime, timezone

    today = today or datetime.now(timezone.utc).date()
    for sentence in _sentences(text):
        if len(sentence) > 300:
            continue  # a wall of text, not a banner or a statement
        if _DISCONTINUED_STATE.search(sentence):
            return sentence
        match = _SHUTDOWN_ON.search(sentence)
        if match:
            raw = re.sub(r"(\d)(?:st|nd|rd|th)", r"\1", match.group(1))
            try:
                when = datetime.strptime(raw, "%B %d, %Y").date()
            except ValueError:
                continue
            if when <= today:
                return sentence
    return None


def mentions_model(expected: str, text: str) -> bool:
    """True if the text names the expected model (name + version, tolerant of 'v2.2')."""
    return _model_in_text(expected, collapse(text))
