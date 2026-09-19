import re

from .db import ModelRecord, ProviderRecord, SessionLocal
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
    "prompt_window_tokens",
    "multi_shot_support",
    "quality_score",
}
MODEL_APPENDABLE_FIELDS = {"quality_notes", "notes"}

PROVIDER_PROTECTED_FIELDS = {"provider_name", "uptime_pct"}
PROVIDER_APPENDABLE_FIELDS = {"pricing_notes", "stability_notes", "notes"}


def _sanitize_key(key: str) -> str:
    # Só letras, números, ponto e hífen; qualquer outra coisa (espaço, barra,
    # parênteses...) vira hífen, e hífens repetidos/nas pontas são colapsados.
    cleaned = re.sub(r"[^a-z0-9.]+", "-", key.lower())
    return cleaned.strip("-")


def _merge_and_save(session, model_cls, key_field: str, key_value: str, data: dict, protected: set, appendable: set) -> None:
    existing = session.get(model_cls, key_value)

    if existing is None:
        record = model_cls(**{key_field: key_value}, **data)
        session.add(record)
    else:
        # Já existe: mescla campo por campo — protegidos não são
        # sobrescritos, texto livre acumula, o resto assume o valor novo.
        for field, value in data.items():
            if value is None:
                continue

            current = getattr(existing, field)

            if field in protected and current is not None:
                continue

            if field in appendable and current:
                setattr(existing, field, f"{current}\n\n---\n\n{value}")
                continue

            setattr(existing, field, value)

    session.commit()


def save_model_comparison(comparison: ModelComparison, model_key: str) -> None:
    # model_key continua sendo o identificador estável escolhido por quem
    # chama a função — não muda com a extração; antes era o nome do arquivo,
    # agora é a chave primária da linha na tabela "models".
    with SessionLocal() as session:
        _merge_and_save(
            session, ModelRecord, "model_key", _sanitize_key(model_key),
            comparison.model_dump(), MODEL_PROTECTED_FIELDS, MODEL_APPENDABLE_FIELDS,
        )


def save_provider_comparison(comparison: ProviderComparison, provider_key: str) -> None:
    with SessionLocal() as session:
        _merge_and_save(
            session, ProviderRecord, "provider_key", _sanitize_key(provider_key),
            comparison.model_dump(), PROVIDER_PROTECTED_FIELDS, PROVIDER_APPENDABLE_FIELDS,
        )


def load_all_comparisons() -> list[ModelComparison]:
    with SessionLocal() as session:
        records = session.query(ModelRecord).all()
        return [
            ModelComparison(
                model_name=r.model_name,
                provider=r.provider,
                price_per_second_usd=r.price_per_second_usd,
                max_reference_images=r.max_reference_images,
                prompt_window_tokens=r.prompt_window_tokens,
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
                stability_notes=r.stability_notes,
                notes=r.notes,
            )
            for r in records
        ]
