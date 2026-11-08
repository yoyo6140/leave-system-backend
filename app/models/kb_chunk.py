from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey

from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base

if TYPE_CHECKING:
    from .kb_document import KbDocument


class KbChunk(Base):
    __tablename__ = "kb_chunks"

    id:              Mapped[str]       = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id:     Mapped[str]       = mapped_column(String, ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False, index=True)    
    chunk_index:     Mapped[int]       = mapped_column(Integer, nullable=False)
    content:         Mapped[str]       = mapped_column(String, nullable=False)
    embedding:       Mapped[list[float]] = mapped_column(Vector(1024), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document: Mapped[KbDocument] = relationship("KbDocument")