from .db import ModelRecord, SessionLocal
from .schema import ModelComparison

# Campos de fato: tratamos a primeira fonte que preencheu como confiável e
# não deixamos uma fonte seguinte (ex: um blog de review) sobrescrever com
# um número diferente — evita que preço/specs "flutuem" dependendo da ordem
# em que as páginas foram processadas.
PROTECTED_FIELDS = {
    "price_per_second_usd",
    "max_reference_images",
    "prompt_window_tokens",
    "multi_shot_support",
}

# Campos de texto livre: aqui o oposto faz sentido — várias fontes podem
# trazer ângulos diferentes sobre qualidade, então acumulamos em vez de
# descartar a informação antiga.
APPENDABLE_FIELDS = {"quality_notes", "notes"}


def _record_to_comparison(record: ModelRecord) -> ModelComparison:
    return ModelComparison(
        model_name=record.model_name,
        provider=record.provider,
        price_per_second_usd=record.price_per_second_usd,
        max_reference_images=record.max_reference_images,
        prompt_window_tokens=record.prompt_window_tokens,
        multi_shot_support=record.multi_shot_support,
        quality_notes=record.quality_notes,
        notes=record.notes,
    )


def save_model_comparison(comparison: ModelComparison, model_key: str) -> None:
    # model_key continua sendo o identificador estável escolhido por quem
    # chama a função — não muda com a extração; antes era o nome do arquivo,
    # agora é a chave primária da linha na tabela "models".
    safe_key = model_key.lower().replace(" ", "-").replace("/", "-")

    with SessionLocal() as session:
        existing = session.get(ModelRecord, safe_key)

        if existing is None:
            # Modelo novo: cria a linha direto com os dados extraídos.
            record = ModelRecord(model_key=safe_key, **comparison.model_dump())
            session.add(record)
        else:
            # Já existe: mescla campo por campo, com a mesma regra de antes
            # (protegidos não são sobrescritos, texto livre acumula).
            for field, value in comparison.model_dump().items():
                if value is None:
                    continue

                current = getattr(existing, field)

                if field in PROTECTED_FIELDS and current is not None:
                    continue

                if field in APPENDABLE_FIELDS and current:
                    setattr(existing, field, f"{current}\n\n---\n\n{value}")
                    continue

                setattr(existing, field, value)

        session.commit()


def load_all_comparisons() -> list[ModelComparison]:
    with SessionLocal() as session:
        records = session.query(ModelRecord).all()
        return [_record_to_comparison(r) for r in records]
