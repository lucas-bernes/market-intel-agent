import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, Float, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()

# Valores padrão batem com o docker-compose.yml, pra funcionar sem
# configuração extra em dev local — em produção, essas variáveis viriam
# de configuração de ambiente real (ex: painel do Hostinger).
DB_USER = os.environ.get("POSTGRES_USER", "market_intel")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "market_intel")
DB_HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
# 5433, não a porta padrão do Postgres: essa máquina já tem um Postgres
# nativo do Windows ocupando a 5432, então mapeamos nosso container pra
# uma porta diferente no host pra não colidir com ele.
DB_PORT = os.environ.get("POSTGRES_PORT", "5433")
DB_NAME = os.environ.get("POSTGRES_DB", "market_intel")

def _normalize_database_url(url: str) -> str:
    # "postgresql://" sem driver explícito deixa a SQLAlchemy escolher: até a
    # 2.0 era o psycopg2 (que este projeto instala); a partir da 2.1 passou a
    # ser o psycopg 3, que não está instalado — e o programa quebra no import
    # ("No module named 'psycopg'"). Foi o que derrubou a coleta agendada no
    # GitHub, que sempre instala a versão mais nova. "postgres://" (estilo
    # Heroku/Supabase) nem é aceito pela SQLAlchemy. Fixar o driver aqui evita
    # depender da versão e do formato colado no secret.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


# DATABASE_URL explícita tem prioridade (usada nos testes, com SQLite temporário,
# pra não depender do Postgres estar de pé).
DATABASE_URL = _normalize_database_url(
    os.environ.get("DATABASE_URL")
    or f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# echo=False evita o SQLAlchemy imprimir cada SQL executado no terminal.
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ModelRecord(Base):
    __tablename__ = "models"

    # model_key é a chave primária: o mesmo identificador estável que
    # usávamos como nome de arquivo (ex: "kling-3.0"), agora identificando
    # a linha na tabela em vez do nome do arquivo.
    model_key: Mapped[str] = mapped_column(String, primary_key=True)
    model_name: Mapped[str] = mapped_column(String)
    provider: Mapped[str] = mapped_column(String)
    price_per_second_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_reference_images: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_max_chars: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    multi_shot_support: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    quality_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class ProviderRecord(Base):
    __tablename__ = "providers"

    provider_key: Mapped[str] = mapped_column(String, primary_key=True)
    provider_name: Mapped[str] = mapped_column(String)
    pricing_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    uptime_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pricing_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stability_summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stability_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class FieldEvidenceRecord(Base):
    # Uma linha por (entidade, campo): a prova do valor ATUAL — a frase
    # literal da página, de qual URL e quando foi coletada. É uma tabela
    # separada (e não colunas em models/providers) porque cada campo tem
    # sua própria fonte e data.
    __tablename__ = "field_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String)  # "model" | "provider"
    entity_key: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    quote: Mapped[str] = mapped_column(String)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("entity_type", "entity_key", "field"),)


class FieldHistoryRecord(Base):
    # Registro só de INSERT, nunca UPDATE — ao contrário de FieldEvidenceRecord
    # (que guarda a prova ATUAL e é sobrescrita), aqui cada mudança de valor
    # gera uma linha nova, então dá pra reconstruir a linha do tempo de um
    # campo (ex: o gráfico de preço) em vez de só o "agora".
    __tablename__ = "field_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String)  # "model" | "provider"
    entity_key: Mapped[str] = mapped_column(String)
    field: Mapped[str] = mapped_column(String)
    old_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # None = 1º valor conhecido
    new_value: Mapped[str] = mapped_column(String)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime)


# Cria as tabelas que ainda não existirem (não faz nada com as que já existem).
Base.metadata.create_all(engine)
