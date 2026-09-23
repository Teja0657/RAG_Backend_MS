from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text
)

from document_service.database import Base


class Document(Base):

    __tablename__ = "documents"

    id = Column(
        String(64),
        primary_key=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    file_path = Column(
        Text,
        nullable=False
    )

    version = Column(
        Integer,
        nullable=False,
        default=1
    )

    status = Column(
        String(30),
        nullable=False,
        default="PROCESSING"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )