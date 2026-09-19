import os
import tempfile

# Precisa rodar ANTES de qualquer import de market_intel: o db.py cria o
# engine e as tabelas no momento do import. Aqui apontamos pra um SQLite
# temporário e damos chaves de API falsas, então os testes não dependem de
# Postgres, rede, nem de credenciais reais.
_tmp_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ.setdefault("DEEP_SEEK_API_KEY", "test-key")
os.environ.setdefault("FIRECRAWL_API_KEY", "test-key")

import pytest  # noqa: E402

from market_intel.db import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    # Cada teste começa com as tabelas vazias.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
