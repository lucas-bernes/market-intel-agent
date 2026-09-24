from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import ModelRecord, ProviderRecord, SessionLocal
from .schema import EvidenceOut, HistoryEntryOut, ModelComparisonOut, ProviderComparisonOut
from .store import load_evidence, load_history

app = FastAPI(title="Market Intel API")

# Libera qualquer origem por enquanto (dev local, frontend em outra porta/
# arquivo estático) — restringir isso é um item pra quando formos pra
# produção de verdade.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _with_evidence(item, evidence: dict[str, dict]):
    item.evidence = {field: EvidenceOut(**data) for field, data in evidence.items()}
    return item


@app.get("/api/models", response_model=list[ModelComparisonOut])
def list_models() -> list[ModelComparisonOut]:
    # Consulta o banco direto aqui (em vez de load_all_comparisons) porque
    # precisamos do model_key junto, que o ModelComparison normal não tem.
    with SessionLocal() as session:
        records = session.query(ModelRecord).all()
        evidence = load_evidence()
        return [_with_evidence(ModelComparisonOut.model_validate(r), evidence.get(("model", r.model_key), {})) for r in records]


@app.get("/api/providers", response_model=list[ProviderComparisonOut])
def list_providers() -> list[ProviderComparisonOut]:
    with SessionLocal() as session:
        records = session.query(ProviderRecord).all()
        evidence = load_evidence()
        return [_with_evidence(ProviderComparisonOut.model_validate(r), evidence.get(("provider", r.provider_key), {})) for r in records]


@app.get("/api/history", response_model=list[HistoryEntryOut])
def list_history() -> list[HistoryEntryOut]:
    # Todas as mudanças já confirmadas, mais antiga primeiro; o front filtra
    # por campo (ex: price_per_second_usd) pra montar o gráfico de preço.
    return [HistoryEntryOut(**row) for row in load_history()]
