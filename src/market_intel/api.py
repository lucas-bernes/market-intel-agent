from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schema import ModelComparison
from .store import load_all_comparisons

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


@app.get("/api/models", response_model=list[ModelComparison])
def list_models() -> list[ModelComparison]:
    return load_all_comparisons()
