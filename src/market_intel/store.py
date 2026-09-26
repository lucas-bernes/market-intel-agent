import re
from datetime import datetime, timezone
from typing import Optional

from .db import FieldEvidenceRecord, FieldHistoryRecord, ModelRecord, ProviderRecord, SessionLocal
from .schema import ModelComparison, ProviderComparison

# Campos de fato (incluindo identidade — nome/provider): tratamos a primeira
# fonte que preencheu como confiável e não deixamos uma fonte seguinte (ex:
# uma busca de review que por engano achou um modelo parecido, mas errado)
# sobrescrever. Sem isso, uma busca desalinhada pode renomear silenciosamente
# um registro certo pro nome de outro modelo.
MODEL_PROTECTED_FIELDS = {
    "model_name",
    "provider",
    "price_per_second_usd",
    "max_reference_images",
    "prompt_max_chars",
    "multi_shot_support",
    "quality_score",
}
MODEL_APPENDABLE_FIELDS = {"quality_notes", "notes"}

PROVIDER_PROTECTED_FIELDS = {"provider_name", "uptime_pct"}
PROVIDER_APPENDABLE_FIELDS = {"pricing_notes", "stability_notes", "notes"}

# Identidade nunca é sobrescrita, nem por dado verificado: renomear um
# registro é justamente o erro que a proteção existe pra impedir.
IDENTITY_FIELDS = {"model_name", "provider", "provider_name"}


def _sanitize_key(key: str) -> str:
    # Só letras, números, ponto e hífen; qualquer outra coisa (espaço, barra,
    # parênteses...) vira hífen, e hífens repetidos/nas pontas são colapsados.
    cleaned = re.sub(r"[^a-z0-9.]+", "-", key.lower())
    return cleaned.strip("-")


def _merge_and_save(
    session, model_cls, key_field: str, key_value: str, data: dict, protected: set, appendable: set,
    verified: frozenset = frozenset(),
) -> list[tuple[str, object, object]]:
    # Devolve a lista de mudanças em campos protegidos (campo, antigo, novo)
    # pra quem chamou poder mostrar — valor que muda nunca deve ser silencioso.
    existing = session.get(model_cls, key_value)
    changes: list[tuple[str, object, object]] = []

    if existing is None:
        record = model_cls(**{key_field: key_value}, **data)
        session.add(record)
        # Registro novo: cada fato que já vem preenchido é o "1º valor
        # conhecido" — vale registrar no histórico (old=None) mesmo sem uma
        # mudança de verdade, senão o gráfico só ganha ponto a partir da
        # primeira atualização, nunca do valor inicial.
        changes.extend((field, None, value) for field, value in data.items() if field in protected and value is not None)
    else:
        # Já existe: mescla campo por campo — protegidos não são
        # sobrescritos, texto livre acumula, o resto assume o valor novo.
        for field, value in data.items():
            if value is None:
                continue

            current = getattr(existing, field)

            if field in protected and current is not None:
                # Exceção: valor com evidência verificada pode atualizar um
                # fato que mudou (ex: preço novo). Sem evidência, continua
                # valendo a regra "primeira fonte ganha".
                if field in verified and field not in IDENTITY_FIELDS and current != value:
                    changes.append((field, current, value))
                    setattr(existing, field, value)
                continue

            if field in appendable and current:
                setattr(existing, field, current + "\n\n---\n\n" + value)
                continue

            setattr(existing, field, value)

    session.commit()
    return changes


def _save_evidence(session, entity_type: str, key: str, model_cls, key_field: str, data: dict,
                   evidence: dict[str, str], source_url: Optional[str]) -> None:
    # Só grava a prova de um campo se o valor guardado no banco é o valor que
    # essa prova sustenta — se um valor antigo ficou (protegido), a prova
    # nova não pode ser atribuída a ele.
    record = session.get(model_cls, key)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for field, quote in evidence.items():
        if getattr(record, field) != data.get(field):
            continue
        row = (
            session.query(FieldEvidenceRecord)
            .filter_by(entity_type=entity_type, entity_key=key, field=field)
            .one_or_none()
        )
        if row is None:
            row = FieldEvidenceRecord(entity_type=entity_type, entity_key=key, field=field)
            session.add(row)
        row.value = str(data[field])
        row.quote = quote
        row.source_url = source_url
        row.collected_at = now
    session.commit()


def _save_history(session, entity_type: str, key: str, changes: list[tuple[str, object, object]], source_url: Optional[str]) -> None:
    if not changes:
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for field, old, new in changes:
        session.add(FieldHistoryRecord(
            entity_type=entity_type, entity_key=key, field=field,
            old_value=None if old is None else str(old), new_value=str(new),
            source_url=source_url, changed_at=now,
        ))
    session.commit()


def load_history(entity_type: Optional[str] = None, field: Optional[str] = None) -> list[dict]:
    with SessionLocal() as session:
        query = session.query(FieldHistoryRecord)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if field:
            query = query.filter_by(field=field)
        return [
            {
                "entity_type": r.entity_type,
                "entity_key": r.entity_key,
                "field": r.field,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "source_url": r.source_url,
                "changed_at": r.changed_at.isoformat(),
            }
            for r in query.order_by(FieldHistoryRecord.changed_at).all()
        ]


def save_model_comparison(
    comparison: ModelComparison, model_key: str,
    source_url: Optional[str] = None, evidence: Optional[dict[str, str]] = None,
    facts_only: bool = False,
) -> list[tuple[str, object, object]]:
    # model_key continua sendo o identificador estável escolhido por quem
    # chama a função — não muda com a extração; antes era o nome do arquivo,
    # agora é a chave primária da linha na tabela "models".
    # facts_only=True (usado pela coleta agendada): ignora quality_notes/notes
    # por completo. Sem isso, o LLM reescreve o mesmo texto com outras
    # palavras a cada execução, e o campo cresce pra sempre com quase-duplicatas.
    key = _sanitize_key(model_key)
    evidence = evidence or {}
    data = comparison.model_dump()
    if facts_only:
        data = {k: v for k, v in data.items() if k not in MODEL_APPENDABLE_FIELDS}
    with SessionLocal() as session:
        changes = _merge_and_save(
            session, ModelRecord, "model_key", key,
            data, MODEL_PROTECTED_FIELDS, MODEL_APPENDABLE_FIELDS, frozenset(evidence),
        )
        _save_evidence(session, "model", key, ModelRecord, "model_key", data, evidence, source_url)
        _save_history(session, "model", key, changes, source_url)
    return changes


def save_provider_comparison(
    comparison: ProviderComparison, provider_key: str,
    source_url: Optional[str] = None, evidence: Optional[dict[str, str]] = None,
) -> list[tuple[str, object, object]]:
    key = _sanitize_key(provider_key)
    evidence = evidence or {}
    data = comparison.model_dump()
    with SessionLocal() as session:
        changes = _merge_and_save(
            session, ProviderRecord, "provider_key", key,
            data, PROVIDER_PROTECTED_FIELDS, PROVIDER_APPENDABLE_FIELDS, frozenset(evidence),
        )
        _save_evidence(session, "provider", key, ProviderRecord, "provider_key", data, evidence, source_url)
        _save_history(session, "provider", key, changes, source_url)
    return changes


def load_verified_fields(entity_type: str, key: str) -> set[str]:
    # Campos deste registro que já tiveram uma evidência verificada — a coleta
    # usa isso pra saber o que "deveria" ter voltado e tentar de novo se sumiu.
    with SessionLocal() as session:
        rows = session.query(FieldEvidenceRecord.field).filter_by(entity_type=entity_type, entity_key=_sanitize_key(key)).all()
        return {row[0] for row in rows}


def set_discontinued(
    model_key: str, discontinued: bool, quote: Optional[str] = None, source_url: Optional[str] = None,
) -> bool:
    """Marks (or unmarks) a model as discontinued. Returns True if the flag changed.

    Not part of the merge rules on purpose: a wrong "discontinued" hides a model
    from the ranking, so it is only set explicitly, with a quote checked by code
    (see verify.find_discontinuation), never by an extraction.
    """
    key = _sanitize_key(model_key)
    with SessionLocal() as session:
        record = session.get(ModelRecord, key)
        if record is None:
            raise KeyError(f"unknown model: {key}")
        old = record.discontinued
        if bool(old) == discontinued:
            return False

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        record.discontinued = discontinued
        evidence = (
            session.query(FieldEvidenceRecord)
            .filter_by(entity_type="model", entity_key=key, field="discontinued")
            .one_or_none()
        )
        if discontinued:
            if evidence is None:
                evidence = FieldEvidenceRecord(entity_type="model", entity_key=key, field="discontinued")
                session.add(evidence)
            evidence.value, evidence.quote, evidence.source_url, evidence.collected_at = (
                "True", quote or "", source_url, now,
            )
        elif evidence is not None:
            session.delete(evidence)

        session.add(FieldHistoryRecord(
            entity_type="model", entity_key=key, field="discontinued",
            old_value=None if old is None else str(old), new_value=str(discontinued),
            source_url=source_url, changed_at=now,
        ))
        session.commit()
        return True


def load_evidence() -> dict[tuple[str, str], dict[str, dict]]:
    # {(entity_type, entity_key): {campo: {quote, source_url, collected_at}}}
    with SessionLocal() as session:
        result: dict[tuple[str, str], dict[str, dict]] = {}
        for r in session.query(FieldEvidenceRecord).all():
            result.setdefault((r.entity_type, r.entity_key), {})[r.field] = {
                "quote": r.quote,
                "source_url": r.source_url,
                "collected_at": r.collected_at.isoformat(),
            }
        return result


def load_all_comparisons() -> list[ModelComparison]:
    with SessionLocal() as session:
        records = session.query(ModelRecord).all()
        return [
            ModelComparison(
                model_name=r.model_name,
                provider=r.provider,
                price_per_second_usd=r.price_per_second_usd,
                max_reference_images=r.max_reference_images,
                prompt_max_chars=r.prompt_max_chars,
                multi_shot_support=r.multi_shot_support,
                quality_notes=r.quality_notes,
                quality_score=r.quality_score,
                notes=r.notes,
            )
            for r in records
        ]


def load_all_providers() -> list[ProviderComparison]:
    with SessionLocal() as session:
        records = session.query(ProviderRecord).all()
        return [
            ProviderComparison(
                provider_name=r.provider_name,
                pricing_notes=r.pricing_notes,
                uptime_pct=r.uptime_pct,
                pricing_summary=r.pricing_summary,
                stability_summary=r.stability_summary,
                stability_notes=r.stability_notes,
                notes=r.notes,
            )
            for r in records
        ]
