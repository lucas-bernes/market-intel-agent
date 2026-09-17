import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Boolean, Float, Integer, String, create_engine
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

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

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
    prompt_window_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    multi_shot_support: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    quality_notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# Cria a tabela no arquivo .db se ela ainda não existir (não faz nada se já existir).
Base.metadata.create_all(engine)
