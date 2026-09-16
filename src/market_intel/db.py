from pathlib import Path
from typing import Optional

from sqlalchemy import Boolean, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "market_intel.db"

# echo=False evita o SQLAlchemy imprimir cada SQL executado no terminal.
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
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
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# Cria a tabela no arquivo .db se ela ainda não existir (não faz nada se já existir).
Base.metadata.create_all(engine)
