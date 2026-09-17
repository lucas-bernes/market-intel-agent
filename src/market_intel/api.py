from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import ModelRecord, ProviderRecord, SessionLocal
from .schema import ModelComparisonOut, ProviderComparisonOut

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


@app.get("/api/models", response_model=list[ModelComparisonOut])
def list_models() -> list[ModelComparisonOut]:
    # Consulta o banco direto aqui (em vez de load_all_comparisons) porque
    # precisamos do model_key junto, que o ModelComparison normal não tem.
    with SessionLocal() as session:
        records = session.query(ModelRecord).all()
        return [ModelComparisonOut.model_validate(r) for r in records]


@app.get("/api/providers", response_model=list[ProviderComparisonOut])
def list_providers() -> list[ProviderComparisonOut]:
    with SessionLocal() as session:
        records = session.query(ProviderRecord).all()
        return [ProviderComparisonOut.model_validate(r) for r in records]
